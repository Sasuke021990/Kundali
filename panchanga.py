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
from decimal import Decimal
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
    """Apparent upper limb, with refraction estimated from elevation.

    ``CALC_RISE`` and ``CALC_SET`` alone are the traditional Indian sunrise:
    first sighting of the upper limb at an apparent zenith of about 90° 50'.
    Disc-center and Hindu-rising flags move that instant by 2–3 minutes and
    are not used.
    """
    if rsmi not in (swe.CALC_RISE, swe.CALC_SET):
        raise ValueError("Sun events must be apparent rise or set of the upper limb.")
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


def _nearest_second(moment: datetime, zone: ZoneInfo) -> datetime:
    local = moment.astimezone(zone).replace(tzinfo=None)
    rounded = local.replace(microsecond=0)
    if local.microsecond >= 500_000:
        rounded += timedelta(seconds=1)
    return rounded.replace(tzinfo=zone)


def _iso(moment: datetime) -> str:
    if moment.microsecond:
        return moment.isoformat(timespec="milliseconds")
    return moment.isoformat(timespec="seconds")


def _seconds_after(origin: datetime, moment: datetime) -> int:
    return int((moment - origin).total_seconds())


def _moment_from_seconds(origin: datetime, seconds: Decimal, zone: ZoneInfo) -> datetime:
    quantized = seconds.quantize(Decimal("0.01"))
    whole = int(quantized.to_integral_value(rounding="ROUND_FLOOR"))
    micros = int((quantized - Decimal(whole)) * 1_000_000)
    return (origin + timedelta(seconds=whole, microseconds=micros)).astimezone(zone)


def _window_bounds(
    origin: datetime,
    sunrise_seconds: int,
    day_seconds: int,
    part: int,
    zone: ZoneInfo,
) -> tuple[datetime, datetime]:
    """One eighth of the daytime arc. The end is never later than sunset."""
    eighth = Decimal(day_seconds) / Decimal(8)
    sunset_seconds = Decimal(sunrise_seconds + day_seconds)
    start_seconds = Decimal(sunrise_seconds) + eighth * (part - 1)
    end_seconds = start_seconds + eighth
    if end_seconds > sunset_seconds:
        end_seconds = sunset_seconds
    start = _moment_from_seconds(origin, start_seconds, zone)
    end = _moment_from_seconds(origin, end_seconds, zone)
    return start, end


def _window_payload(start: datetime, end: datetime) -> dict[str, str]:
    return {"start": _iso(start), "end": _iso(end)}


def _limbs(
    moment: datetime,
    longitude: float,
    latitude: float,
    elevation: float,
) -> dict[str, object]:
    from kundli import NAKSHATRAS, NAKSHATRA_SPAN

    sun_lon, moon_lon = _sidereal_pair(moment, longitude, latitude, elevation)
    elongation = (moon_lon - sun_lon) % 360.0
    tithi_index = _slot(elongation, 12.0, 30)
    tithi_name, is_rikta = _tithi_name(tithi_index)
    yoga_index = _slot(sun_lon + moon_lon, 360.0 / 27.0, 27)
    karana_index = _slot(elongation, 6.0, 60)
    karana_name = _karana_name(karana_index)
    nakshatra_index = _slot(moon_lon, NAKSHATRA_SPAN, 27)
    return {
        "tithi": {"name": tithi_name, "index": tithi_index, "is_rikta": is_rikta},
        "nakshatra": {"name": NAKSHATRAS[nakshatra_index - 1][0], "index": nakshatra_index},
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
    }


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


def _rise_on(
    civil: datetime,
    zone: ZoneInfo,
    longitude: float,
    latitude: float,
    height: float,
) -> datetime:
    midnight = civil.replace(tzinfo=zone)
    sunrise = _sun_event(
        midnight - timedelta(minutes=1),
        swe.CALC_RISE,
        longitude,
        latitude,
        height,
    ).astimezone(zone)
    if sunrise.date() != civil.date():
        raise ValueError(
            f"No topocentric sunrise on {civil.date().isoformat()} at "
            f"latitude {latitude}, longitude {longitude}."
        )
    return sunrise


def get_daily_panchanga(
    date: str,
    location: str | None = None,
    at_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation_m: float | None = None,
    timezone_name: str | None = None,
    natal_chart: dict[str, object] | None = None,
) -> dict[str, object]:
    """Sunrise panchanga, plus Rahu, Yamaganda, and Gulika on the daytime arc.

    ``date`` is a civil date YYYY-MM-DD. A clock time before that morning's
    sunrise still belongs to the previous solar day: 03:30 on Friday is
    Thursday until the Sun rises. ``attributes`` are the Lahiri limbs at
    sunrise. When ``at_time`` is set, ``instant`` repeats tithi and karana at
    that clock time and names the daytime window that contains it. The three
    windows are eight equal parts of sunset minus sunrise and stop at sunset.
    """
    place = _resolve_place(location, latitude, longitude, elevation_m, timezone_name, natal_chart)
    zone = ZoneInfo(str(place["timezone"]))
    try:
        civil = datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Panchanga date must be YYYY-MM-DD, got '{date}'.") from exc
    latitude_f = float(place["latitude"])
    longitude_f = float(place["longitude"])
    height = float(place["elevation_m"])
    moment: datetime | None = None
    if at_time:
        clock: datetime | None = None
        for pattern in ("%H:%M:%S", "%H:%M"):
            try:
                clock = datetime.strptime(at_time, pattern)
            except ValueError:
                continue
            break
        if clock is None:
            raise ValueError("Panchanga time must be HH:MM or HH:MM:SS.")
        moment = civil.replace(
            hour=clock.hour,
            minute=clock.minute,
            second=clock.second,
            tzinfo=zone,
        )
    sunrise = _rise_on(civil, zone, longitude_f, latitude_f, height)
    if moment is not None and moment < sunrise:
        civil = civil - timedelta(days=1)
        sunrise = _rise_on(civil, zone, longitude_f, latitude_f, height)
    sunset = _sun_event(
        sunrise + timedelta(seconds=1),
        swe.CALC_SET,
        longitude_f,
        latitude_f,
        height,
    ).astimezone(zone)
    if sunset <= sunrise:
        raise ValueError(f"Sunset on {civil.date().isoformat()} is not after sunrise.")
    next_sunrise = _sun_event(
        sunset + timedelta(seconds=1),
        swe.CALC_RISE,
        longitude_f,
        latitude_f,
        height,
    ).astimezone(zone)
    sunrise = _nearest_second(sunrise, zone)
    sunset = _nearest_second(sunset, zone)
    next_sunrise = _nearest_second(next_sunrise, zone)
    origin = sunrise.replace(hour=0, minute=0, second=0, microsecond=0)
    sunrise_seconds = _seconds_after(origin, sunrise)
    day_seconds = _seconds_after(sunrise, sunset)
    if day_seconds <= 0:
        raise ValueError(f"Sunset on {civil.date().isoformat()} is not after sunrise.")
    # Python weekday is Monday = 0. The vara table is Sunday = 0.
    vara_index = (sunrise.weekday() + 1) % 7
    lord, vara_name = VARA_LORDS[vara_index]
    attributes = _limbs(sunrise, longitude_f, latitude_f, height)
    labeled_parts = (
        ("Rahu Kaalam", RAHU_PART[vara_index]),
        ("Yamaganda", YAMAGANDA_PART[vara_index]),
        ("Gulika Kaalam", GULIKA_PART[vara_index]),
    )
    bounds = {
        label: _window_bounds(origin, sunrise_seconds, day_seconds, part, zone)
        for label, part in labeled_parts
    }
    windows = {label: _window_payload(*span) for label, span in bounds.items()}
    payload: dict[str, object] = {
        "solar_day": {
            "sunrise": _iso(sunrise),
            "sunrise_current": _iso(sunrise),
            "sunrise_next": _iso(next_sunrise),
            "sunset": _iso(sunset),
            "day_lord": f"{lord} ({vara_name})",
        },
        "attributes": attributes,
        "inauspicious_windows": {
            "rahu_kaalam": windows["Rahu Kaalam"],
            "yamaganda": windows["Yamaganda"],
            "gulika_kaalam": windows["Gulika Kaalam"],
        },
    }
    if moment is not None:
        instant_limbs = _limbs(moment, longitude_f, latitude_f, height)
        in_day = sunrise <= moment < sunset
        active = None
        if in_day:
            for label, (start, end) in bounds.items():
                if start <= moment < end:
                    active = label
                    break
        tithi = instant_limbs["tithi"]
        karana = instant_limbs["karana"]
        yoga = instant_limbs["yoga"]
        if not in_day:
            favorable = None
        else:
            blocked = active is not None
            blocked = blocked or bool(tithi["is_rikta"]) or bool(karana["is_bhadra"])
            blocked = blocked or bool(yoga["is_malefic"])
            favorable = not blocked
        payload["instant"] = {
            "local": _iso(moment),
            "is_current_solar_day": sunrise <= moment < next_sunrise,
            "within_daytime_arc": in_day,
            "daytime_kaalam_active": active if in_day else None,
            "active_inauspicious_window": active,
            "is_favorable_for_action": favorable,
            "tithi": tithi,
            "karana": karana,
        }
    return {"place": place, "daily_panchanga": payload}
