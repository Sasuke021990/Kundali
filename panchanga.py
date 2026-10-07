"""Local panchanga and the three daytime inauspicious windows.

Sunrise and sunset come from Swiss Ephemeris ``rise_trans`` at the observer's
latitude, longitude, and elevation. Rahu Kaalam, Yamaganda, and Gulika Kaalam
are eighths of that topocentric day, so they move with the place. They are not
read from a fixed civil clock.
"""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

TITHI_NAMES: tuple[str, ...] = (
    "Pratipada",
    "Dwitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dwadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
)
YOGA_NAMES: tuple[str, ...] = (
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Sobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shoola",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyan",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
)
MALEFIC_YOGAS = {17, 27}
RIKTA_IN_PAKSHA = {4, 9, 14}
MOVABLE_KARANAS: tuple[str, ...] = (
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Gara",
    "Vanija",
    "Vishti",
)
FIXED_END_KARANAS = ("Shakuni", "Chatushpada", "Naga")
# Sunday = 0. The integer is which eighth of the sunrise-to-sunset day.
RAHU_PART = (8, 2, 7, 5, 6, 4, 3)
YAMAGANDA_PART = (5, 4, 3, 2, 1, 7, 6)
GULIKA_PART = (7, 6, 5, 4, 3, 2, 1)
VARA_LORDS = (
    ("Sun", "Sunday"),
    ("Moon", "Monday"),
    ("Mars", "Tuesday"),
    ("Mercury", "Wednesday"),
    ("Jupiter", "Thursday"),
    ("Venus", "Friday"),
    ("Saturn", "Saturday"),
)
_ELEVATION_CACHE: dict[tuple[float, float], float] = {}


def _require(chart: dict[str, object], path: str) -> object:
    current: object = chart
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Natal chart is missing '{path}'.")
        current = current[part]
    return current


def _jd(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    hour += utc.microsecond / 3_600_000_000.0
    return float(swe.julday(utc.year, utc.month, utc.day, hour))


def _from_jd(julian_day: float) -> datetime:
    year, month, day, ut_hour = swe.revjul(julian_day, swe.GREG_CAL)
    moment = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    return moment + timedelta(hours=float(ut_hour))


def _slot(arc: float, width: float, count: int) -> int:
    index = int(math.floor((arc % 360.0) / width + 1e-10))
    if index >= count:
        index = count - 1
    return index + 1


def _elevation_m(latitude: float, longitude: float) -> float:
    key = (round(latitude, 4), round(longitude, 4))
    cached = _ELEVATION_CACHE.get(key)
    if cached is not None:
        return cached
    url = (
        "https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude}&longitude={longitude}"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "jyotish-panchanga"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        height = float(payload["elevation"][0])
    except Exception as exc:
        raise ValueError(
            "Unable to look up elevation for "
            f"latitude {latitude}, longitude {longitude}: {exc}. "
            "Pass elevation_m so sunrise stays topocentric."
        ) from exc
    if not math.isfinite(height):
        raise ValueError(
            f"Elevation lookup for latitude {latitude}, longitude {longitude} was not finite."
        )
    _ELEVATION_CACHE[key] = height
    return height


def _sun_event(
    after: datetime,
    rsmi: int,
    longitude: float,
    latitude: float,
    elevation: float,
) -> datetime:
    flags = swe.FLG_MOSEPH | swe.FLG_TOPOCTR
    swe.set_topo(longitude, latitude, elevation)
    code, result = swe.rise_trans(
        _jd(after),
        swe.SUN,
        rsmi,
        (longitude, latitude, elevation),
        0.0,
        0.0,
        flags,
    )
    julian = float(result[0]) if result else float("nan")
    if code < 0 or not math.isfinite(julian):
        event = "sunrise" if rsmi == swe.CALC_RISE else "sunset"
        raise ValueError(
            f"Swiss Ephemeris could not find {event} at "
            f"latitude {latitude}, longitude {longitude}, elevation {elevation} m."
        )
    return _from_jd(julian)


def _sidereal_pair(
    moment: datetime,
    longitude: float,
    latitude: float,
    elevation: float,
) -> tuple[float, float]:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    swe.set_topo(longitude, latitude, elevation)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_TOPOCTR
    sun, sun_flags = swe.calc_ut(_jd(moment), swe.SUN, flags)
    moon, moon_flags = swe.calc_ut(_jd(moment), swe.MOON, flags)
    if not (sun_flags & swe.FLG_SIDEREAL and moon_flags & swe.FLG_SIDEREAL):
        raise ValueError("Swiss Ephemeris did not return sidereal Sun and Moon longitudes.")
    return float(sun[0]) % 360.0, float(moon[0]) % 360.0


def _karana_name(index: int) -> str:
    if index == 1:
        return "Kimstughna"
    if index >= 58:
        return FIXED_END_KARANAS[index - 58]
    return MOVABLE_KARANAS[(index - 2) % 7]


def _tithi_name(index: int) -> tuple[str, bool]:
    if index == 15:
        return "Purnima", False
    if index == 30:
        return "Amavasya", False
    paksha = "Shukla" if index <= 15 else "Krishna"
    number = index if index <= 15 else index - 15
    return f"{paksha} {TITHI_NAMES[number - 1]}", number in RIKTA_IN_PAKSHA


def _clock(moment: datetime, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).strftime("%H:%M:%S")


def _window(sunrise: datetime, eighth: timedelta, part: int, zone: ZoneInfo) -> dict[str, str]:
    start = sunrise + eighth * (part - 1)
    end = start + eighth
    return {"start": _clock(start, zone), "end": _clock(end, zone)}


def _resolve_place(
    location: str | None,
    latitude: float | None,
    longitude: float | None,
    elevation_m: float | None,
    timezone_name: str | None,
    natal_chart: dict[str, object] | None,
) -> dict[str, object]:
    name = location
    if latitude is None or longitude is None:
        if location:
            from kundli import _geocode_location, _timezone_name_for

            place = _geocode_location(location)
            latitude = place.latitude
            longitude = place.longitude
            name = place.resolved_name
            if timezone_name is None:
                timezone_name = _timezone_name_for(place)
        elif natal_chart is not None:
            latitude = float(_require(natal_chart, "metadata.coordinates.latitude"))
            longitude = float(_require(natal_chart, "metadata.coordinates.longitude"))
            name = str(_require(natal_chart, "metadata.location"))
            if timezone_name is None:
                timezone_name = str(_require(natal_chart, "metadata.timezone"))
            stored = natal_chart.get("metadata")
            if elevation_m is None and isinstance(stored, dict):
                coordinates = stored.get("coordinates")
                if isinstance(coordinates, dict) and "elevation_m" in coordinates:
                    elevation_m = float(coordinates["elevation_m"])
        else:
            raise ValueError("Provide location, or latitude and longitude, or a natal chart.")
    if latitude is None or longitude is None:
        raise ValueError("Latitude and longitude are required for topocentric sunrise.")
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise ValueError("Latitude must be from -90 to 90 and longitude from -180 to 180.")
    if timezone_name is None:
        from kundli import LocationDetails, _timezone_name_for

        timezone_name = _timezone_name_for(
            LocationDetails("coordinates", "coordinates", latitude, longitude, "")
        )
    try:
        ZoneInfo(timezone_name)
    except Exception as exc:
        raise ValueError(f"Timezone '{timezone_name}' is not available: {exc}") from exc
    if elevation_m is None:
        elevation_m = _elevation_m(latitude, longitude)
    return {
        "name": name,
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "elevation_m": round(float(elevation_m), 1),
        "timezone": timezone_name,
    }


def get_daily_panchanga(
    date: str,
    location: str | None = None,
    at_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation_m: float | None = None,
    timezone_name: str | None = None,
    natal_chart: dict[str, object] | None = None,
    _solar_date_locked: bool = False,
) -> dict[str, object]:
    """Panchanga at local sunrise, plus Rahu, Yamaganda, and Gulika.

    ``date`` is the civil date YYYY-MM-DD in the observer's timezone. A clock
    time before that morning's sunrise belongs to the previous solar day.
    Limbs are Lahiri and topocentric at sunrise. The three windows divide the
    topocentric sunrise-to-sunset arc into eight equal parts.
    """
    place = _resolve_place(location, latitude, longitude, elevation_m, timezone_name, natal_chart)
    zone = ZoneInfo(str(place["timezone"]))
    try:
        civil = datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Panchanga date must be YYYY-MM-DD, got '{date}'.") from exc
    midnight = civil.replace(tzinfo=zone)
    latitude_f = float(place["latitude"])
    longitude_f = float(place["longitude"])
    height = float(place["elevation_m"])
    sunrise = _sun_event(
        midnight - timedelta(minutes=1),
        swe.CALC_RISE,
        longitude_f,
        latitude_f,
        height,
    )
    if sunrise.astimezone(zone).date() != civil.date():
        raise ValueError(
            f"No topocentric sunrise on {date} at latitude {latitude_f}, longitude {longitude_f}."
        )
    if at_time and not _solar_date_locked:
        try:
            clock = datetime.strptime(at_time, "%H:%M")
        except ValueError as exc:
            raise ValueError("Panchanga time must be HH:MM.") from exc
        probe = civil.replace(hour=clock.hour, minute=clock.minute, tzinfo=zone)
        if probe < sunrise.astimezone(zone):
            previous = (civil.date() - timedelta(days=1)).isoformat()
            return get_daily_panchanga(
                previous,
                latitude=latitude_f,
                longitude=longitude_f,
                elevation_m=height,
                timezone_name=str(place["timezone"]),
                _solar_date_locked=True,
            )
    sunset = _sun_event(
        sunrise + timedelta(seconds=1),
        swe.CALC_SET,
        longitude_f,
        latitude_f,
        height,
    )
    if sunset <= sunrise:
        raise ValueError(f"Sunset on {date} is not after sunrise.")
    eighth = (sunset - sunrise) / 8
    # Python weekday is Monday = 0. The vara table is Sunday = 0.
    vara_index = (sunrise.astimezone(zone).weekday() + 1) % 7
    lord, vara_name = VARA_LORDS[vara_index]
    sun_lon, moon_lon = _sidereal_pair(sunrise, longitude_f, latitude_f, height)
    elongation = (moon_lon - sun_lon) % 360.0
    tithi_index = _slot(elongation, 12.0, 30)
    tithi_name, is_rikta = _tithi_name(tithi_index)
    yoga_index = _slot(sun_lon + moon_lon, 360.0 / 27.0, 27)
    karana_index = _slot(elongation, 6.0, 60)
    karana_name = _karana_name(karana_index)
    from kundli import NAKSHATRAS, NAKSHATRA_SPAN

    nakshatra_index = _slot(moon_lon, NAKSHATRA_SPAN, 27)
    sunrise_local = sunrise.astimezone(zone)
    sunset_local = sunset.astimezone(zone)
    return {
        "place": place,
        "daily_panchanga": {
            "solar_day": {
                "sunrise": sunrise_local.isoformat(timespec="seconds"),
                "sunset": sunset_local.isoformat(timespec="seconds"),
                "day_lord": f"{lord} ({vara_name})",
            },
            "attributes": {
                "tithi": {"name": tithi_name, "index": tithi_index, "is_rikta": is_rikta},
                "nakshatra": {
                    "name": NAKSHATRAS[nakshatra_index - 1][0],
                    "index": nakshatra_index,
                },
                "yoga": {
                    "name": YOGA_NAMES[yoga_index - 1],
                    "index": yoga_index,
                    "is_malefic": yoga_index in MALEFIC_YOGAS,
                },
                "karana": {
                    "name": karana_name,
                    "index": karana_index,
                    "is_bhadra": karana_name == "Vishti",
                },
            },
            "inauspicious_windows": {
                "rahu_kaalam": _window(sunrise_local, eighth, RAHU_PART[vara_index], zone),
                "yamaganda": _window(sunrise_local, eighth, YAMAGANDA_PART[vara_index], zone),
                "gulika_kaalam": _window(sunrise_local, eighth, GULIKA_PART[vara_index], zone),
            },
        },
    }
