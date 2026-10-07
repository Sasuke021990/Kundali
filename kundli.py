#!/usr/bin/env python3
"""Generate a North Indian (diamond) Lagna Kundli PNG from birth details.

The public entry point is :func:`generate_kundli_chart`. The same function
serves the command-line interface. Astronomical positions are sidereal Lahiri
longitudes from Swiss Ephemeris. Houses are whole-sign. Civil time uses the
IANA zone that contains the geocoded birthplace, including historical offsets
and daylight-saving transitions.

Planetary longitudes use the Moshier ephemeris built into Swiss Ephemeris
(``FLG_MOSEPH``) so a chart does not depend on optional external ephemeris
files. Lahiri mode is set explicitly on every calculation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import swisseph as swe
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.text import Text
from timezonefinder import TimezoneFinder

from ashtakavarga import get_ashtakavarga_json
from compatibility import get_compatibility_json
from saturn_cycles import get_saturn_cycles

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKGROUND = "#FFFDF7"
BORDER = "#2A2A2A"
RASHI_COLOR = "#333333"
PLANET_COLOR = "#8B0000"

OUTPUT_DPI = 400
FIGURE_INCHES = 10.0
LINE_WIDTH = 1.8
MIN_PLANET_FONT = 5.0
MIN_RASHI_FONT = 4.5
MAX_FONT_ATTEMPTS = 18
LAYOUT_INSET = 0.13
ACCEPT_INSET = 0.055
GEOCODER_TIMEOUT_SECONDS = 15
NOMINATIM_USER_AGENT = "production-kundli-generator"
AYANAMSA_DECIMALS = 6
COORDINATE_DECIMALS = 4
SIDEREAL_CONSISTENCY_DEGREES = 0.05

EXAMPLE_DOB = "1990-01-15"
EXAMPLE_TOB = "14:30"
EXAMPLE_LOCATION = "Bengaluru, India"
EXAMPLE_OUTPUT = "kundli_example.png"

RASHI_NAMES: dict[int, str] = {
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

# Canonical graha order. House stacks preserve this order.
GRAHA_BODIES: tuple[tuple[str, str, int], ...] = (
    ("Sun", "Su", swe.SUN),
    ("Moon", "Mo", swe.MOON),
    ("Mars", "Ma", swe.MARS),
    ("Mercury", "Me", swe.MERCURY),
    ("Jupiter", "Ju", swe.JUPITER),
    ("Venus", "Ve", swe.VENUS),
    ("Saturn", "Sa", swe.SATURN),
    # Mean node, not true node. True node can differ by about ±1.5°.
    ("Rahu", "Ra", swe.MEAN_NODE),
)
KETU_NAME = "Ketu"
KETU_ABBREVIATION = "Ke"
INHERENTLY_RETROGRADE = frozenset({"Rahu", "Ketu"})
EXPECTED_ABBREVIATIONS = ("Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke")
PLANET_NAMES: tuple[str, ...] = tuple(name for name, _abbr, _body in GRAHA_BODIES) + (KETU_NAME,)

# 27 nakshatras of 13°20'. The second value is the Vimshottari nakshatra lord.
NAKSHATRAS: tuple[tuple[str, str], ...] = (
    ("Ashwini", "Ketu"),
    ("Bharani", "Venus"),
    ("Krittika", "Sun"),
    ("Rohini", "Moon"),
    ("Mrigashira", "Mars"),
    ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"),
    ("Pushya", "Saturn"),
    ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"),
    ("Purva Phalguni", "Venus"),
    ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"),
    ("Chitra", "Mars"),
    ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"),
    ("Anuradha", "Saturn"),
    ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"),
    ("Purva Ashadha", "Venus"),
    ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"),
    ("Dhanishta", "Mars"),
    ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"),
    ("Uttara Bhadrapada", "Saturn"),
    ("Revati", "Mercury"),
)
NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0
# Vimshottari lords follow the nakshatra cycle. A year is the mean tropical year.
DASHA_ORDER: tuple[str, ...] = tuple(lord for _name, lord in NAKSHATRAS[:9])
DASHA_YEARS: dict[str, int] = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}
VIMSHOTTARI_YEAR_DAYS = 365.2425
TARA_NAMES: tuple[str, ...] = (
    "Janma (Vulnerability / Mental stress)",
    "Sampat (Wealth / Material progress)",
    "Vipat (Obstacles / Unplanned losses)",
    "Kshema (Comfort / Protection & ease)",
    "Pratyak (Friction / Resistance)",
    "Sadhana (Accomplishment / Execution)",
    "Naidhana (Crisis / High friction)",
    "Mitra (Friendly / Cooperation)",
    "Parama Mitra (Supreme favor / High gains)",
)
FAVORABLE_TARA_INDEXES = frozenset({1, 3, 5, 7, 8})

SIGN_LORDS: dict[int, str] = {
    1: "Mars",
    2: "Venus",
    3: "Mercury",
    4: "Moon",
    5: "Sun",
    6: "Mercury",
    7: "Venus",
    8: "Mars",
    9: "Jupiter",
    10: "Saturn",
    11: "Saturn",
    12: "Jupiter",
}
# Whole-sign exaltation and debilitation. Own signs are the signs a graha rules.
EXALTATION_SIGN: dict[str, int] = {
    "Sun": 1,
    "Moon": 2,
    "Mars": 10,
    "Mercury": 6,
    "Jupiter": 4,
    "Venus": 12,
    "Saturn": 7,
    "Rahu": 2,
    "Ketu": 8,
}
DEBILITATION_SIGN: dict[str, int] = {
    "Sun": 7,
    "Moon": 8,
    "Mars": 4,
    "Mercury": 12,
    "Jupiter": 10,
    "Venus": 6,
    "Saturn": 1,
    "Rahu": 8,
    "Ketu": 2,
}
# Direct orb, then the retrograde orb. Only Mercury and Venus tighten when retrograde.
# Separation is the short arc. Sun, Rahu, and Ketu are never combust.
COMBUSTION_ORBS: dict[str, tuple[float, float]] = {
    "Moon": (12.0, 12.0),
    "Mars": (17.0, 17.0),
    "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0),
    "Venus": (10.0, 8.0),
    "Saturn": (15.0, 15.0),
}
GRAHA_YUDDHA_ORB = 1.0
GRAHA_YUDDHA_PLANETS = frozenset({"Mars", "Mercury", "Jupiter", "Venus", "Saturn"})
# Special Parashari aspects, in addition to the 7th that every graha casts.
SPECIAL_ASPECTS: dict[str, tuple[int, ...]] = {
    "Mars": (4, 8),
    "Jupiter": (5, 9),
    "Rahu": (5, 9),
    "Ketu": (5, 9),
    "Saturn": (3, 10),
}

# North Indian house polygons in chart coordinates (x right, y up).
HOUSE_POLYGONS: dict[int, tuple[tuple[float, float], ...]] = {
    1: ((0.5, 1.0), (0.75, 0.75), (0.5, 0.5), (0.25, 0.75)),
    2: ((0.0, 1.0), (0.5, 1.0), (0.25, 0.75)),
    3: ((0.0, 1.0), (0.25, 0.75), (0.0, 0.5)),
    4: ((0.0, 0.5), (0.25, 0.75), (0.5, 0.5), (0.25, 0.25)),
    5: ((0.0, 0.5), (0.25, 0.25), (0.0, 0.0)),
    6: ((0.0, 0.0), (0.25, 0.25), (0.5, 0.0)),
    7: ((0.5, 0.0), (0.25, 0.25), (0.5, 0.5), (0.75, 0.25)),
    8: ((0.5, 0.0), (0.75, 0.25), (1.0, 0.0)),
    9: ((1.0, 0.0), (0.75, 0.25), (1.0, 0.5)),
    10: ((1.0, 0.5), (0.75, 0.25), (0.5, 0.5), (0.75, 0.75)),
    11: ((1.0, 0.5), (0.75, 0.75), (1.0, 1.0)),
    12: ((1.0, 1.0), (0.75, 0.75), (0.5, 1.0)),
}
TRIANGLE_HOUSES = (2, 3, 5, 6, 8, 9, 11, 12)
DIAMOND_HOUSES = (1, 4, 7, 10)
DIAMOND_CENTROIDS = {
    1: (0.5, 0.75),
    4: (0.25, 0.5),
    7: (0.5, 0.25),
    10: (0.75, 0.5),
}

Point = tuple[float, float]
Polygon = tuple[Point, ...]

# Swiss Ephemeris sidereal mode is process-global. It is set inside each
# calculation and is not cached as application state.


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BirthDetails:
    """Validated civil birth moment and its UTC / Julian Day equivalents."""

    dob: str
    tob: str
    local_datetime: datetime
    utc_datetime: datetime
    utc_decimal_hours: float
    julian_day: float
    timezone_name: str


@dataclass(frozen=True)
class LocationDetails:
    """One geocoded birthplace."""

    query: str
    resolved_name: str
    latitude: float
    longitude: float
    country: str


@dataclass(frozen=True)
class PlanetPosition:
    """Sidereal position of one graha and its whole-sign house."""

    name: str
    abbreviation: str
    longitude: float
    speed: float | None
    rashi_index: int
    rashi_name: str
    retrograde: bool
    house: int

    @property
    def label(self) -> str:
        """Chart abbreviation. Rahu and Ketu never receive an ``(R)`` mark."""
        if self.abbreviation in {"Ra", "Ke"}:
            return self.abbreviation
        if self.retrograde:
            return f"{self.abbreviation} (R)"
        return self.abbreviation


@dataclass(frozen=True)
class ChartData:
    """Everything the renderer needs for one Kundli."""

    birth: BirthDetails
    location: LocationDetails
    lagna_longitude: float
    lagna_rashi_index: int
    lagna_rashi_name: str
    ayanamsa: float
    planets: tuple[PlanetPosition, ...]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def _parse_dob(dob: object) -> datetime:
    """Parse a strict ``YYYY-MM-DD`` calendar date."""
    if not isinstance(dob, str):
        raise ValueError(f"Invalid dob {dob!r}. Expected format YYYY-MM-DD.")
    if len(dob) != 10 or dob[4] != "-" or dob[7] != "-":
        raise ValueError(f"Invalid dob '{dob}'. Expected format YYYY-MM-DD.")
    try:
        parsed = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid dob '{dob}'. Expected format YYYY-MM-DD.") from exc
    if parsed.strftime("%Y-%m-%d") != dob:
        raise ValueError(f"Invalid dob '{dob}'. Expected format YYYY-MM-DD.")
    return parsed


def _parse_tob(tob: object) -> time:
    """Parse a strict 24-hour ``HH:MM`` time. Invalid values are not normalized."""
    if not isinstance(tob, str):
        raise ValueError(f"Invalid tob {tob!r}. Expected 24-hour format HH:MM.")
    if len(tob) != 5 or tob[2] != ":" or not (tob[:2].isdigit() and tob[3:].isdigit()):
        raise ValueError(f"Invalid tob '{tob}'. Expected 24-hour format HH:MM.")
    hour = int(tob[:2])
    minute = int(tob[3:])
    if hour > 23 or minute > 59:
        raise ValueError(f"Invalid tob '{tob}'. Expected 24-hour format HH:MM.")
    try:
        parsed = datetime.strptime(tob, "%H:%M")
    except ValueError as exc:
        raise ValueError(f"Invalid tob '{tob}'. Expected 24-hour format HH:MM.") from exc
    if parsed.strftime("%H:%M") != tob:
        raise ValueError(f"Invalid tob '{tob}'. Expected 24-hour format HH:MM.")
    return time(hour, minute)


def _parse_location_query(location: object) -> str:
    if not isinstance(location, str) or not location.strip():
        raise ValueError(
            f"Invalid location {location!r}. Expected a place in the form 'City, Country'."
        )
    return location.strip()


# ---------------------------------------------------------------------------
# Geocoding and civil time
# ---------------------------------------------------------------------------


def _geocode_location(query: str) -> LocationDetails:
    """Resolve ``query`` once with Nominatim. Never invents coordinates."""
    geolocator = Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=GEOCODER_TIMEOUT_SECONDS)
    try:
        found = geolocator.geocode(
            query,
            exactly_one=True,
            addressdetails=True,
            language="en",
        )
    except GeopyError as exc:
        raise ValueError(
            f"Unable to geocode '{query}': network/service error: {exc}"
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Unable to geocode '{query}': network/service error: {exc}"
        ) from exc

    if found is None:
        raise ValueError(
            f"Unable to geocode location '{query}'. No matching location was found."
        )

    try:
        latitude = float(found.latitude)
        longitude = float(found.longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Unable to geocode location '{query}'. The geocoder returned invalid coordinates."
        ) from exc

    if not math.isfinite(latitude) or not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"Unable to geocode location '{query}'. Latitude {latitude!r} is out of range."
        )
    if not math.isfinite(longitude) or not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"Unable to geocode location '{query}'. Longitude {longitude!r} is out of range."
        )

    raw = found.raw if isinstance(found.raw, dict) else {}
    address = raw.get("address") if isinstance(raw.get("address"), dict) else {}
    country = address.get("country")
    if not isinstance(country, str) or not country.strip():
        raise ValueError(
            f"Unable to geocode location '{query}'. No country was returned for the match."
        )
    resolved = found.address if isinstance(found.address, str) and found.address.strip() else query
    return LocationDetails(
        query=query,
        resolved_name=resolved.strip(),
        latitude=latitude,
        longitude=longitude,
        country=country.strip(),
    )


def _timezone_name_for(location: LocationDetails) -> str:
    """Return the IANA zone containing the geocoded point. Never defaults to UTC."""
    try:
        zone = TimezoneFinder().timezone_at(lat=location.latitude, lng=location.longitude)
    except Exception as exc:
        raise ValueError(
            "Unable to determine an IANA timezone for "
            f"latitude {location.latitude}, longitude {location.longitude} "
            f"(location '{location.query}'): {exc}"
        ) from exc
    if not isinstance(zone, str) or not zone.strip():
        raise ValueError(
            "Unable to determine an IANA timezone for "
            f"latitude {location.latitude}, longitude {location.longitude} "
            f"(location '{location.query}')."
        )
    return zone


def _format_utc_offset(offset: object) -> str:
    """Format a ``timedelta`` UTC offset as ``UTC±HH:MM``."""
    total = int(getattr(offset, "total_seconds")())
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _localize_birth(dob: str, tob: str, tz_name: str, moment: str = "birth") -> datetime:
    """Attach ``tz_name`` and reject gaps or repeated civil times.

    The offset comes only from :class:`zoneinfo.ZoneInfo`. Standard time,
    daylight-saving time, and historical IANA revisions are therefore the
    installed tzdata rules for that zone. Ambiguous and nonexistent local
    times raise ``ValueError`` instead of choosing an offset.
    """
    parsed_date = _parse_dob(dob)
    parsed_time = _parse_tob(tob)
    try:
        zone = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unable to determine an IANA timezone for '{tz_name}'. "
            "The timezone identifier is not available in the installed tzdata."
        ) from exc
    except Exception as exc:
        raise ValueError(
            f"Unable to determine an IANA timezone for '{tz_name}': {exc}"
        ) from exc

    naive = datetime(
        parsed_date.year,
        parsed_date.month,
        parsed_date.day,
        parsed_time.hour,
        parsed_time.minute,
    )
    earlier = naive.replace(tzinfo=zone, fold=0)
    later = naive.replace(tzinfo=zone, fold=1)
    offset_earlier = earlier.utcoffset()
    offset_later = later.utcoffset()
    if offset_earlier is None or offset_later is None:
        raise ValueError(
            f"Unable to determine the UTC offset for {dob} {tob} in timezone {tz_name}."
        )

    try:
        utc_moment = earlier.astimezone(timezone.utc)
        round_trip = utc_moment.astimezone(zone).replace(tzinfo=None)
    except Exception as exc:
        raise ValueError(
            f"Unable to convert local {moment} time {dob} {tob} in timezone {tz_name}: {exc}"
        ) from exc

    if round_trip != naive:
        raise ValueError(
            f"Nonexistent local {moment} time {tob} on {dob} in timezone {tz_name}. "
            "This civil time falls in a daylight-saving or historical offset gap "
            "and does not correspond to a real local time."
        )
    if offset_earlier != offset_later:
        raise ValueError(
            f"Ambiguous local {moment} time {tob} on {dob} in timezone {tz_name}. "
            "This civil time occurs twice "
            f"(offsets {_format_utc_offset(offset_earlier)} and "
            f"{_format_utc_offset(offset_later)}) "
            "because of a daylight-saving or historical offset transition. "
            f"Choose a {moment} time outside the overlap."
        )
    return earlier


def _gregorian_julian_day(year: int, month: int, day: int, decimal_hours: float) -> float:
    """Proleptic Gregorian Julian Day, used to cross-check Swiss Ephemeris."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return (jdn - 0.5) + (decimal_hours / 24.0)


def _birth_details(dob: str, tob: str, tz_name: str) -> BirthDetails:
    local_dt = _localize_birth(dob, tob, tz_name)
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_decimal_hours = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3_600_000_000.0
    )
    if not math.isfinite(utc_decimal_hours) or not 0.0 <= utc_decimal_hours < 24.0:
        raise ValueError(
            f"Unable to calculate UTC decimal hours for {dob} {tob} in timezone {tz_name}."
        )
    try:
        julian_day = float(
            swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_decimal_hours)
        )
    except (TypeError, ValueError, swe.Error) as exc:
        raise ValueError(
            "Unable to calculate Julian Day for UTC birth time "
            f"{utc_dt.isoformat()}: {exc}"
        ) from exc
    if not math.isfinite(julian_day):
        raise ValueError(
            f"Unable to calculate Julian Day for UTC birth time {utc_dt.isoformat()}."
        )
    reference = _gregorian_julian_day(
        utc_dt.year, utc_dt.month, utc_dt.day, utc_decimal_hours
    )
    if abs(julian_day - reference) > 1e-6:
        raise ValueError(
            "Unable to calculate Julian Day for UTC birth time "
            f"{utc_dt.isoformat()}: Swiss Ephemeris returned {julian_day}, "
            f"which disagrees with the Gregorian Julian Day {reference}."
        )
    return BirthDetails(
        dob=dob,
        tob=tob,
        local_datetime=local_dt,
        utc_datetime=utc_dt,
        utc_decimal_hours=utc_decimal_hours,
        julian_day=julian_day,
        timezone_name=tz_name,
    )


# ---------------------------------------------------------------------------
# Sidereal astronomy
# ---------------------------------------------------------------------------


def _ephemeris_flags() -> int:
    """Sidereal Moshier calculation with planetary speed.

    ``FLG_MOSEPH`` selects the analytical ephemeris compiled into Swiss
    Ephemeris. ``FLG_SPEED`` is required for a meaningful longitude speed in
    ``result[3]``. ``FLG_SIDEREAL`` requests Lahiri longitudes after
    :func:`swe.set_sid_mode`.
    """
    return swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL


def _configure_lahiri() -> None:
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def normalize_longitude(longitude: float) -> float:
    """Return ``longitude`` wrapped into ``[0, 360)``."""
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        raise ValueError(f"Longitude {longitude!r} is not a real number.")
    value = float(longitude)
    if not math.isfinite(value):
        raise ValueError(f"Longitude {longitude!r} is not finite.")
    wrapped = value % 360.0
    if wrapped < 0.0 or wrapped >= 360.0:
        wrapped = 0.0
    return wrapped


def longitude_to_rashi(longitude: float) -> int:
    """Map a normalized longitude to rashi ``1..12`` without rounding."""
    normalized = normalize_longitude(longitude)
    rashi = int(normalized // 30.0) + 1
    if rashi == 13:
        rashi = 1
    if rashi < 1 or rashi > 12:
        raise ValueError(
            f"Rashi index {rashi} is outside 1..12 for longitude {normalized}."
        )
    return rashi


def whole_sign_house(planet_rashi: int, lagna_rashi: int) -> int:
    """Whole-sign house of ``planet_rashi`` when the lagna is ``lagna_rashi``."""
    return ((planet_rashi - lagna_rashi) % 12) + 1


def house_rashi_index(lagna_rashi: int, house_number: int) -> int:
    """Rashi occupying ``house_number`` under whole-sign houses."""
    return ((lagna_rashi + house_number - 2) % 12) + 1


def _angular_separation(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def _parse_calc_ut(raw: object, body_name: str) -> tuple[float, float]:
    """Extract finite sidereal longitude and speed from ``swe.calc_ut``."""
    values: object
    retflags: object = None
    if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[0], (tuple, list)):
        values = raw[0]
        retflags = raw[1]
    elif isinstance(raw, (tuple, list)) and raw and isinstance(raw[0], (int, float)):
        values = raw
    else:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: "
            f"unexpected result structure ({type(raw).__name__})."
        )
    if not isinstance(values, (tuple, list)) or len(values) < 4:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: "
            "result does not contain longitude and speed."
        )
    if retflags is not None and not isinstance(retflags, int):
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: "
            "result flags are not an integer."
        )
    if isinstance(retflags, int):
        if retflags < 0:
            raise ValueError(
                f"Swiss Ephemeris calculation failed for {body_name}: "
                f"error flag {retflags}."
            )
        if retflags & swe.FLG_SIDEREAL == 0:
            raise ValueError(
                f"Swiss Ephemeris calculation failed for {body_name}: "
                "sidereal mode was not applied."
            )
        if retflags & swe.FLG_SPEED == 0:
            raise ValueError(
                f"Swiss Ephemeris calculation failed for {body_name}: "
                "longitude speed was not returned."
            )
    try:
        longitude = float(values[0])
        speed = float(values[3])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: "
            "longitude or speed is not numeric."
        ) from exc
    if not math.isfinite(longitude) or not math.isfinite(speed):
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: "
            "longitude or speed is not finite."
        )
    return normalize_longitude(longitude), speed


def _calculate_body(julian_day: float, body_name: str, body_id: int) -> tuple[float, float]:
    """Sidereal longitude and speed for one Swiss Ephemeris body."""
    try:
        raw = swe.calc_ut(julian_day, body_id, _ephemeris_flags())
    except swe.Error as exc:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: {exc}"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for {body_name}: {exc}"
        ) from exc
    return _parse_calc_ut(raw, body_name)


def _calculate_ascendant(julian_day: float, latitude: float, longitude: float) -> float:
    """Sidereal ascendant longitude from ``swe.houses_ex``.

    Whole-sign cusps returned by Swiss Ephemeris are not used for placement.
    House numbers are assigned later from the ascendant rashi alone.
    """
    flags = _ephemeris_flags()
    try:
        sidereal = swe.houses_ex(julian_day, latitude, longitude, b"W", flags)
        tropical = swe.houses_ex(
            julian_day,
            latitude,
            longitude,
            b"W",
            swe.FLG_MOSEPH | swe.FLG_SPEED,
        )
    except swe.Error as exc:
        raise ValueError(f"Swiss Ephemeris calculation failed for Ascendant: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Swiss Ephemeris calculation failed for Ascendant: {exc}") from exc

    if not isinstance(sidereal, tuple) or len(sidereal) != 2:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: unexpected result structure."
        )
    ascmc = sidereal[1]
    if not isinstance(ascmc, (tuple, list)) or len(ascmc) < 1:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: missing ascendant longitude."
        )
    try:
        ascendant = float(ascmc[0])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: longitude is not numeric."
        ) from exc
    if not math.isfinite(ascendant):
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: longitude is not finite."
        )

    if not isinstance(tropical, tuple) or len(tropical) != 2:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: "
            "unexpected tropical result structure."
        )
    tropical_ascmc = tropical[1]
    if not isinstance(tropical_ascmc, (tuple, list)) or len(tropical_ascmc) < 1:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: missing tropical longitude."
        )
    try:
        tropical_asc = float(tropical_ascmc[0])
        ayanamsa = float(swe.get_ayanamsa_ut(julian_day))
    except (TypeError, ValueError, swe.Error) as exc:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for Lahiri ayanamsa: {exc}"
        ) from exc
    if not math.isfinite(tropical_asc) or not math.isfinite(ayanamsa):
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: "
            "tropical longitude or ayanamsa is not finite."
        )
    separation = (tropical_asc - ascendant) % 360.0
    if _angular_separation(separation, ayanamsa % 360.0) > SIDEREAL_CONSISTENCY_DEGREES:
        raise ValueError(
            "Swiss Ephemeris calculation failed for Ascendant: sidereal longitude "
            f"{ascendant:.6f} is inconsistent with tropical longitude {tropical_asc:.6f} "
            f"and Lahiri ayanamsa {ayanamsa:.6f}."
        )
    return normalize_longitude(ascendant)


def _calculate_ayanamsa(julian_day: float) -> float:
    try:
        ayanamsa = float(swe.get_ayanamsa_ut(julian_day))
    except (TypeError, ValueError, swe.Error) as exc:
        raise ValueError(
            f"Swiss Ephemeris calculation failed for Lahiri ayanamsa: {exc}"
        ) from exc
    if not math.isfinite(ayanamsa):
        raise ValueError(
            "Swiss Ephemeris calculation failed for Lahiri ayanamsa: value is not finite."
        )
    return ayanamsa


def _planet_record(
    name: str,
    abbreviation: str,
    longitude: float,
    speed: float | None,
    retrograde: bool,
    lagna_rashi: int,
) -> PlanetPosition:
    rashi_index = longitude_to_rashi(longitude)
    house = whole_sign_house(rashi_index, lagna_rashi)
    if house < 1 or house > 12:
        raise ValueError(f"House {house} for {name} is outside 1..12.")
    return PlanetPosition(
        name=name,
        abbreviation=abbreviation,
        longitude=longitude,
        speed=speed,
        rashi_index=rashi_index,
        rashi_name=RASHI_NAMES[rashi_index],
        retrograde=retrograde,
        house=house,
    )


def compute_chart(dob: str, tob: str, location: str) -> ChartData:
    """Geocode ``location``, convert civil time to UT, and compute the Kundli."""
    # Parse before any network or ephemeris work so bad input fails fast.
    _parse_dob(dob)
    _parse_tob(tob)
    query = _parse_location_query(location)

    place = _geocode_location(query)
    tz_name = _timezone_name_for(place)
    birth = _birth_details(dob, tob, tz_name)

    _configure_lahiri()
    ayanamsa = _calculate_ayanamsa(birth.julian_day)
    lagna_longitude = _calculate_ascendant(
        birth.julian_day, place.latitude, place.longitude
    )
    lagna_rashi = longitude_to_rashi(lagna_longitude)

    planets: list[PlanetPosition] = []
    rahu_longitude: float | None = None
    for name, abbreviation, body_id in GRAHA_BODIES:
        longitude, speed = _calculate_body(birth.julian_day, name, body_id)
        if name in INHERENTLY_RETROGRADE:
            # Speed is read from result[3] above. Rahu stays retrograde on the
            # chart without an (R) suffix, including when the node speed is negative.
            retrograde = True
        else:
            retrograde = speed < 0.0
        if name == "Rahu":
            rahu_longitude = longitude
        planets.append(
            _planet_record(name, abbreviation, longitude, speed, retrograde, lagna_rashi)
        )

    if rahu_longitude is None:
        raise ValueError("Swiss Ephemeris calculation failed for Rahu: longitude is missing.")
    ketu_longitude = normalize_longitude(rahu_longitude + 180.0)
    planets.append(
        _planet_record(
            KETU_NAME,
            KETU_ABBREVIATION,
            ketu_longitude,
            None,
            True,
            lagna_rashi,
        )
    )

    chart = ChartData(
        birth=birth,
        location=place,
        lagna_longitude=lagna_longitude,
        lagna_rashi_index=lagna_rashi,
        lagna_rashi_name=RASHI_NAMES[lagna_rashi],
        ayanamsa=ayanamsa,
        planets=tuple(planets),
    )
    validate_chart(chart)
    return chart


def validate_chart(chart: ChartData) -> None:
    """Raise ``ValueError`` when houses, rashis, or grahas are inconsistent."""
    if len(HOUSE_POLYGONS) != 12:
        raise ValueError("Chart validation failed: expected 12 houses.")
    rashis = [
        house_rashi_index(chart.lagna_rashi_index, house) for house in range(1, 13)
    ]
    if sorted(rashis) != list(range(1, 13)):
        raise ValueError(
            "Chart validation failed: whole-sign houses do not contain rashi numbers 1..12 "
            f"exactly once ({rashis})."
        )
    if any(rashi < 1 or rashi > 12 for rashi in rashis):
        raise ValueError(f"Chart validation failed: rashi numbers out of range ({rashis}).")

    if len(chart.planets) != 9:
        raise ValueError(
            f"Chart validation failed: expected 9 grahas, found {len(chart.planets)}."
        )
    abbreviations = [planet.abbreviation for planet in chart.planets]
    if abbreviations != list(EXPECTED_ABBREVIATIONS):
        raise ValueError(
            "Chart validation failed: graha order or labels are "
            f"{abbreviations}, expected {list(EXPECTED_ABBREVIATIONS)}."
        )
    if len(set(abbreviations)) != 9:
        raise ValueError("Chart validation failed: a graha abbreviation is duplicated.")

    names = [planet.name for planet in chart.planets]
    expected_names = [name for name, _abbr, _body in GRAHA_BODIES] + [KETU_NAME]
    if names != expected_names:
        raise ValueError(
            f"Chart validation failed: graha names {names} differ from {expected_names}."
        )

    rahu = chart.planets[7]
    ketu = chart.planets[8]
    expected_ketu = normalize_longitude(rahu.longitude + 180.0)
    if abs(ketu.longitude - expected_ketu) > 1e-9:
        raise ValueError(
            "Chart validation failed: Ketu longitude "
            f"{ketu.longitude} is not Rahu + 180 degrees ({expected_ketu})."
        )
    if not rahu.retrograde or not ketu.retrograde:
        raise ValueError("Chart validation failed: Rahu and Ketu must be retrograde.")

    for planet in chart.planets:
        if planet.house < 1 or planet.house > 12:
            raise ValueError(
                f"Chart validation failed: {planet.name} house {planet.house} is outside 1..12."
            )
        expected_house = whole_sign_house(planet.rashi_index, chart.lagna_rashi_index)
        if planet.house != expected_house:
            raise ValueError(
                f"Chart validation failed: {planet.name} is in house {planet.house}, "
                f"but rashi {planet.rashi_index} from lagna {chart.lagna_rashi_index} "
                f"belongs in house {expected_house}."
            )
        expected_rashi = longitude_to_rashi(planet.longitude)
        if planet.rashi_index != expected_rashi:
            raise ValueError(
                f"Chart validation failed: {planet.name} rashi {planet.rashi_index} "
                f"does not match longitude {planet.longitude}."
            )
        if planet.abbreviation in {"Ra", "Ke"} and planet.label != planet.abbreviation:
            raise ValueError(
                f"Chart validation failed: {planet.name} must not be marked with (R)."
            )

    if chart.lagna_rashi_index != longitude_to_rashi(chart.lagna_longitude):
        raise ValueError(
            "Chart validation failed: lagna rashi does not match lagna longitude."
        )
    if chart.lagna_rashi_name != RASHI_NAMES[chart.lagna_rashi_index]:
        raise ValueError("Chart validation failed: lagna rashi name is incorrect.")


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def polygon_centroid(vertices: Polygon) -> Point:
    """Geometric centroid of a simple polygon (shoelace), not a bounding-box mean."""
    if len(vertices) < 3:
        raise ValueError("A polygon centroid requires at least 3 vertices.")
    cross_sum = 0.0
    cx_sum = 0.0
    cy_sum = 0.0
    count = len(vertices)
    for index in range(count):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % count]
        cross = (x1 * y2) - (x2 * y1)
        cross_sum += cross
        cx_sum += (x1 + x2) * cross
        cy_sum += (y1 + y2) * cross
    if abs(cross_sum) < 1e-12:
        raise ValueError("Polygon area is zero; the centroid is undefined.")
    signed_area = cross_sum / 2.0
    return (cx_sum / (6.0 * signed_area), cy_sum / (6.0 * signed_area))


def polygon_area(vertices: Polygon) -> float:
    cross_sum = 0.0
    count = len(vertices)
    for index in range(count):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % count]
        cross_sum += (x1 * y2) - (x2 * y1)
    return abs(cross_sum) / 2.0


def bounding_box(vertices: Polygon) -> tuple[float, float, float, float]:
    xs = [point[0] for point in vertices]
    ys = [point[1] for point in vertices]
    return min(xs), min(ys), max(xs), max(ys)


def inset_polygon(vertices: Polygon, ratio: float) -> Polygon:
    """Shrink ``vertices`` toward the centroid by ``ratio`` of the radial distance."""
    if ratio < 0.0 or ratio >= 1.0:
        raise ValueError(f"Inset ratio {ratio} must be in [0, 1).")
    cx, cy = polygon_centroid(vertices)
    scale = 1.0 - ratio
    return tuple((cx + (x - cx) * scale, cy + (y - cy) * scale) for x, y in vertices)


def _point_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - x1, py - y1)
    fraction = ((px - x1) * dx + (py - y1) * dy) / length_sq
    fraction = max(0.0, min(1.0, fraction))
    nearest_x = x1 + fraction * dx
    nearest_y = y1 + fraction * dy
    return math.hypot(px - nearest_x, py - nearest_y)


def point_in_polygon(x: float, y: float, vertices: Polygon) -> bool:
    """Ray-cast membership, treating a numerical boundary hit as inside."""
    inside = False
    count = len(vertices)
    previous = count - 1
    for index in range(count):
        xi, yi = vertices[index]
        xj, yj = vertices[previous]
        intersects = (yi > y) != (yj > y)
        if intersects:
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        previous = index
    if inside:
        return True
    distance = min(
        _point_segment_distance(
            x,
            y,
            vertices[index][0],
            vertices[index][1],
            vertices[(index + 1) % count][0],
            vertices[(index + 1) % count][1],
        )
        for index in range(count)
    )
    return distance <= 1e-8


def horizontal_span(vertices: Polygon, y: float) -> tuple[float, float] | None:
    """Inclusive horizontal intersection of the polygon with the line ``y``."""
    hits: list[float] = []
    count = len(vertices)
    for index in range(count):
        x1, y1 = vertices[index]
        x2, y2 = vertices[(index + 1) % count]
        if abs(y1 - y2) <= 1e-12:
            if abs(y - y1) <= 1e-9:
                hits.extend((x1, x2))
            continue
        low = min(y1, y2)
        high = max(y1, y2)
        if y < low - 1e-12 or y > high + 1e-12:
            continue
        if y == high and y != low:
            # Count the upper endpoint once via the adjacent edge to avoid duplicates.
            continue
        fraction = (y - y1) / (y2 - y1)
        if -1e-9 <= fraction <= 1.0 + 1e-9:
            hits.append(x1 + fraction * (x2 - x1))
    if len(hits) < 2:
        return None
    return min(hits), max(hits)


def rectangle_inside_polygon(
    x: float,
    y: float,
    width: float,
    height: float,
    vertices: Polygon,
) -> bool:
    """True when the axis-aligned rectangle centered at ``(x, y)`` lies in the polygon."""
    if width <= 0.0 or height <= 0.0:
        return False
    half_w = width / 2.0
    half_h = height / 2.0
    corners = (
        (x - half_w, y - half_h),
        (x + half_w, y - half_h),
        (x + half_w, y + half_h),
        (x - half_w, y + half_h),
    )
    return all(point_in_polygon(px, py, vertices) for px, py in corners)


def validate_geometry(polygons: dict[int, Polygon] | None = None) -> None:
    """Check the North Indian house polygons before any text is drawn."""
    houses = HOUSE_POLYGONS if polygons is None else polygons
    if len(houses) != 12 or set(houses) != set(range(1, 13)):
        raise ValueError(
            "Geometry validation failed: house numbers 1..12 must each exist once."
        )
    for house, vertices in houses.items():
        if len(vertices) < 3:
            raise ValueError(
                f"Geometry validation failed: house {house} has fewer than 3 vertices."
            )
        for x, y in vertices:
            if (
                not math.isfinite(x)
                or not math.isfinite(y)
                or not 0.0 <= x <= 1.0
                or not 0.0 <= y <= 1.0
            ):
                raise ValueError(
                    f"Geometry validation failed: house {house} vertex {(x, y)} is outside [0, 1]."
                )
        if polygon_area(vertices) <= 1e-8:
            raise ValueError(f"Geometry validation failed: house {house} area is degenerate.")
        centroid = polygon_centroid(vertices)
        if not point_in_polygon(centroid[0], centroid[1], vertices):
            raise ValueError(
                f"Geometry validation failed: centroid of house {house} is outside the polygon."
            )

    if houses[1] != HOUSE_POLYGONS[1]:
        raise ValueError("Geometry validation failed: house 1 is not the upper central diamond.")
    if houses[7] != HOUSE_POLYGONS[7]:
        raise ValueError("Geometry validation failed: house 7 is not the lower central diamond.")
    for house in TRIANGLE_HOUSES:
        if len(houses[house]) != 3 or houses[house] != HOUSE_POLYGONS[house]:
            raise ValueError(
                f"Geometry validation failed: house {house} is not the required triangle."
            )
    for house in DIAMOND_HOUSES:
        if len(houses[house]) != 4:
            raise ValueError(
                f"Geometry validation failed: house {house} is not a 4-vertex diamond."
            )
        centroid = polygon_centroid(houses[house])
        expected = DIAMOND_CENTROIDS[house]
        if abs(centroid[0] - expected[0]) > 1e-9 or abs(centroid[1] - expected[1]) > 1e-9:
            raise ValueError(
                f"Geometry validation failed: house {house} centroid {centroid} "
                f"does not match {expected}."
            )
    for house in TRIANGLE_HOUSES:
        vertices = houses[house]
        mean = (
            sum(point[0] for point in vertices) / 3.0,
            sum(point[1] for point in vertices) / 3.0,
        )
        centroid = polygon_centroid(vertices)
        if abs(centroid[0] - mean[0]) > 1e-9 or abs(centroid[1] - mean[1]) > 1e-9:
            raise ValueError(
                f"Geometry validation failed: triangle centroid of house {house} "
                "disagrees with the vertex mean."
            )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _format_coordinates(latitude: float, longitude: float) -> str:
    lat_hemisphere = "N" if latitude >= 0.0 else "S"
    lon_hemisphere = "E" if longitude >= 0.0 else "W"
    return (
        f"{abs(latitude):.{COORDINATE_DECIMALS}f}° {lat_hemisphere}, "
        f"{abs(longitude):.{COORDINATE_DECIMALS}f}° {lon_hemisphere}"
    )


def _header_text(chart: ChartData) -> str:
    location_line = textwrap.fill(
        f"Location: {chart.location.resolved_name}",
        width=92,
        subsequent_indent="          ",
    )
    return "\n".join(
        (
            "North Indian Lagna Kundli",
            "Name: Not Provided",
            f"DOB: {chart.birth.dob}",
            f"TOB: {chart.birth.tob}",
            location_line,
            "Coordinates: "
            + _format_coordinates(chart.location.latitude, chart.location.longitude),
        )
    )


def _footer_text(chart: ChartData) -> str:
    ayanamsa = f"{chart.ayanamsa:.{AYANAMSA_DECIMALS}f}"
    return f"Lagna: {chart.lagna_rashi_name}\nLahiri Ayanamsa: {ayanamsa}°"


def _create_figure() -> tuple[Figure, Axes]:
    figure = plt.figure(
        figsize=(FIGURE_INCHES, FIGURE_INCHES),
        dpi=OUTPUT_DPI,
        facecolor=BACKGROUND,
    )
    # Square axes inside the square figure, leaving room for header and footer.
    axes = figure.add_axes([0.12, 0.105, 0.76, 0.76])
    axes.set_xlim(0.0, 1.0)
    axes.set_ylim(0.0, 1.0)
    axes.set_aspect("equal", adjustable="box")
    axes.axis("off")
    axes.set_facecolor(BACKGROUND)
    return figure, axes


def _draw_geometry(axes: Axes) -> None:
    """Draw the outer square, both diagonals, and the inner diamond, in that order."""
    style = {
        "color": BORDER,
        "linewidth": LINE_WIDTH,
        "solid_capstyle": "projecting",
        "solid_joinstyle": "miter",
        "clip_on": False,
        "zorder": 2,
    }
    axes.plot([0.0, 1.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 1.0, 0.0], **style)
    axes.plot([0.0, 1.0], [0.0, 1.0], **style)
    axes.plot([0.0, 1.0], [1.0, 0.0], **style)
    axes.plot([0.5, 1.0, 0.5, 0.0, 0.5], [1.0, 0.5, 0.0, 0.5, 1.0], **style)


def _points_to_data(axes: Axes, points: float) -> tuple[float, float]:
    """Convert a font size in points into data-coordinate width and height units."""
    figure = axes.figure
    dpi = float(figure.dpi)
    pixels = points * dpi / 72.0
    origin = axes.transData.inverted().transform((0.0, 0.0))
    shifted = axes.transData.inverted().transform((pixels, pixels))
    return abs(float(shifted[0] - origin[0])), abs(float(shifted[1] - origin[1]))


def _estimate_text_size(
    axes: Axes,
    label: str,
    fontsize: float,
    weight: str,
) -> tuple[float, float]:
    """Conservative width and height of ``label`` in data coordinates."""
    em_w, em_h = _points_to_data(axes, fontsize)
    char_width = 0.72 if weight == "bold" else 0.62
    width = max(len(label), 1) * char_width * em_w
    height = 1.25 * em_h
    return width, height


def initial_planet_fontsize(count: int) -> float:
    """Larger type for a quiet house, smaller type as grahas stack up."""
    if count <= 1:
        return 13.5
    if count == 2:
        return 11.0
    if count == 3:
        return 8.0
    if count == 4:
        return 7.0
    return max(MIN_PLANET_FONT, 7.0 - (count - 4) * 0.5)


def rashi_fontsize_for(planet_fontsize: float, planet_count: int) -> float:
    """Keep the rashi number visually secondary to the planet labels."""
    if planet_count <= 0:
        return 11.0
    return max(MIN_RASHI_FONT, min(8.0, planet_fontsize * 0.68))


def _seek_near(
    polygon: Polygon,
    target_y: float,
    width: float,
    height: float,
    y_low: float,
    y_high: float,
) -> Point | None:
    """Place a box on the polygon cross-section nearest ``target_y`` inside the band."""
    _minx, miny, _maxx, maxy = bounding_box(polygon)
    low = max(y_low, miny + height / 2.0)
    high = min(y_high, maxy - height / 2.0)
    if high < low:
        return None
    target = min(max(target_y, low), high)
    step = max(height * 0.18, (high - low) / 40.0)
    candidates = [target]
    for index in range(1, 42):
        candidates.append(target + index * step)
        candidates.append(target - index * step)
    for y in candidates:
        if y < low - 1e-12 or y > high + 1e-12:
            continue
        cross = horizontal_span(polygon, y)
        if cross is None:
            continue
        x = (cross[0] + cross[1]) / 2.0
        if rectangle_inside_polygon(x, y, width, height, polygon):
            return (x, y)
    return None


def _layout_inset(label_count: int) -> float:
    """Pull crowded stacks farther inside the polygon so glyphs clear the border."""
    if label_count >= 4:
        return 0.26
    if label_count >= 3:
        return 0.22
    if label_count == 2:
        return 0.16
    return LAYOUT_INSET


def _place_stack(
    safe: Polygon,
    labels: tuple[str, ...],
    sizes: list[tuple[float, float]],
    planet_font: float,
    center_y: float,
    gap: float,
    y_low: float,
    y_high: float,
) -> list[tuple[str, float, float, float, str]] | None:
    """Stack planet labels vertically around ``center_y``, one line each."""
    stack_height = sum(height for _width, height in sizes) + gap * (len(labels) - 1)
    cursor_top = center_y + stack_height / 2.0
    if cursor_top > y_high or cursor_top - stack_height < y_low:
        return None
    placed: list[tuple[str, float, float, float, str]] = []
    for label, (width, height) in zip(labels, sizes):
        preferred = cursor_top - height / 2.0
        found = _seek_near(
            safe,
            preferred,
            width,
            height,
            preferred - height * 0.45,
            preferred + height * 0.2,
        )
        if found is None:
            return None
        placed.append((label, found[0], found[1], planet_font, "planet"))
        cursor_top = found[1] - height / 2.0 - gap
    return placed


def _layout_house(
    axes: Axes,
    vertices: Polygon,
    rashi_number: int,
    labels: tuple[str, ...],
    planet_font: float,
    rashi_font: float,
    house_number: int,
) -> list[tuple[str, float, float, float, str]] | None:
    """Return text placements ``(text, x, y, fontsize, kind)`` or ``None`` if they do not fit.

    The rashi number sits in the upper part of the inset polygon. Planet labels
    are separate centered lines in the region below it. House 1 is the exception:
    its sign number is shifted toward the inner bottom vertex so the planet label
    keeps a clear gap. Every coordinate is the midpoint of the polygon's
    horizontal cross-section, not a fixed house offset.
    """
    safe = inset_polygon(vertices, _layout_inset(len(labels)))
    _cx, cy = polygon_centroid(safe)
    _minx, miny, _maxx, maxy = bounding_box(safe)
    span = maxy - miny
    rashi_w, rashi_h = _estimate_text_size(axes, str(rashi_number), rashi_font, "medium")
    sizes = [_estimate_text_size(axes, label, planet_font, "bold") for label in labels]

    if house_number == 1 and labels:
        line_gap = max(rashi_h, sizes[0][1]) * 0.35
        planet_center = miny + 0.62 * span
        planets = _place_stack(
            safe,
            labels,
            sizes,
            planet_font,
            planet_center,
            line_gap,
            miny + 0.42 * span,
            maxy - sizes[0][1],
        )
        if planets is None:
            return None
        planet_bottom = min(
            y - height / 2.0
            for (_text, _x, y, _size, _kind), (_width, height) in zip(planets, sizes)
        )
        # Sign number sits toward the inner bottom vertex, clear of the planet.
        separation = max(0.055, rashi_h * 1.6)
        rashi_target = min(miny + 0.30 * span, planet_bottom - separation - rashi_h / 2.0)
        rashi_pos = _seek_near(
            safe,
            rashi_target,
            rashi_w,
            rashi_h,
            miny,
            planet_bottom - separation,
        )
        if rashi_pos is None or rashi_pos[1] > planet_bottom - separation * 0.75:
            return None
        return [
            (str(rashi_number), rashi_pos[0], rashi_pos[1], rashi_font, "rashi"),
            *planets,
        ]

    rashi_target = miny + (0.72 if labels else 0.78) * span
    rashi_pos = _seek_near(
        safe,
        rashi_target,
        rashi_w,
        rashi_h,
        (miny + maxy) / 2.0,
        maxy,
    )
    if rashi_pos is None:
        return None
    placements: list[tuple[str, float, float, float, str]] = [
        (str(rashi_number), rashi_pos[0], rashi_pos[1], rashi_font, "rashi")
    ]
    if not labels:
        return placements

    gap = max(rashi_h, sizes[0][1]) * (0.55 if len(labels) >= 3 else 0.35)
    stack_height = sum(height for _width, height in sizes) + gap * (len(labels) - 1)
    region_top = rashi_pos[1] - (rashi_h / 2.0) - gap
    if region_top - miny < stack_height:
        return None
    center = min(cy, region_top - stack_height / 2.0)
    center = max(center, miny + stack_height / 2.0)
    planets = _place_stack(
        safe,
        labels,
        sizes,
        planet_font,
        center,
        gap,
        miny,
        region_top,
    )
    if planets is None:
        return None
    placements.extend(planets)
    return placements


def _rashi_fontproperties(size: float) -> FontProperties:
    """Slightly heavier than regular. Prefer a real medium face when installed."""
    for font in fontManager.ttflist:
        if font.fname.endswith(("Inter-Medium.ttf", "Inter-Medium.otf")):
            return FontProperties(fname=font.fname, size=size)
    return FontProperties(family="DejaVu Sans", size=size, weight="bold")


def _add_label(
    axes: Axes,
    text: str,
    x: float,
    y: float,
    fontsize: float,
    kind: str,
    gid: str,
) -> Text:
    if kind == "planet":
        artist = axes.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=PLANET_COLOR,
            fontfamily="DejaVu Sans",
            clip_on=False,
            zorder=4,
            gid=gid,
        )
        return artist
    artist = axes.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        color=RASHI_COLOR,
        fontproperties=_rashi_fontproperties(fontsize),
        clip_on=False,
        zorder=4,
        gid=gid,
    )
    return artist


def _display_pixels(axes: Axes, pixels: float) -> tuple[float, float]:
    origin = axes.transData.inverted().transform((0.0, 0.0))
    shifted = axes.transData.inverted().transform((pixels, pixels))
    return abs(float(shifted[0] - origin[0])), abs(float(shifted[1] - origin[1]))


def _bbox_corners_inside(axes: Axes, artist: Text, polygon: Polygon, renderer: object) -> bool:
    bbox = artist.get_window_extent(renderer=renderer).transformed(axes.transData.inverted())
    pad_x, pad_y = _display_pixels(axes, 1.0)
    x0 = bbox.x0 + pad_x
    y0 = bbox.y0 + pad_y
    x1 = bbox.x1 - pad_x
    y1 = bbox.y1 - pad_y
    if x1 <= x0 or y1 <= y0:
        x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    if not all(point_in_polygon(x, y, polygon) for x, y in corners):
        return False
    center_y = (y0 + y1) / 2.0
    span = horizontal_span(polygon, center_y)
    if span is None:
        return False
    return (x1 - x0) <= (span[1] - span[0]) + 1e-6


def _bboxes_overlap(first: Text, second: Text, axes: Axes, renderer: object) -> bool:
    a = first.get_window_extent(renderer=renderer).transformed(axes.transData.inverted())
    b = second.get_window_extent(renderer=renderer).transformed(axes.transData.inverted())
    gap_x, gap_y = _display_pixels(axes, 1.5)
    separated = (
        a.x1 < b.x0 + gap_x
        or b.x1 < a.x0 + gap_x
        or a.y1 < b.y0 + gap_y
        or b.y1 < a.y0 + gap_y
    )
    return not separated


def _bbox_edge_clearance(axes: Axes, artist: Text, polygon: Polygon, renderer: object) -> float:
    """Smallest distance from the text box to the polygon boundary."""
    bbox = artist.get_window_extent(renderer=renderer).transformed(axes.transData.inverted())
    samples = (
        (bbox.x0, bbox.y0),
        (bbox.x1, bbox.y0),
        (bbox.x1, bbox.y1),
        (bbox.x0, bbox.y1),
        ((bbox.x0 + bbox.x1) / 2.0, bbox.y0),
        ((bbox.x0 + bbox.x1) / 2.0, bbox.y1),
        (bbox.x0, (bbox.y0 + bbox.y1) / 2.0),
        (bbox.x1, (bbox.y0 + bbox.y1) / 2.0),
    )
    count = len(polygon)
    return min(
        _point_segment_distance(
            x,
            y,
            polygon[index][0],
            polygon[index][1],
            polygon[(index + 1) % count][0],
            polygon[(index + 1) % count][1],
        )
        for x, y in samples
        for index in range(count)
    )


def _house_labels_fit(
    axes: Axes,
    artists: list[Text],
    polygon: Polygon,
    renderer: object,
    label_count: int,
) -> bool:
    accept_ratio = 0.11 if label_count >= 3 else ACCEPT_INSET
    clearance = 0.045 if label_count >= 3 else 0.02
    accept = inset_polygon(polygon, accept_ratio)
    for artist in artists:
        if not _bbox_corners_inside(axes, artist, accept, renderer):
            return False
        if str(artist.get_gid() or "").startswith("planet-"):
            if _bbox_edge_clearance(axes, artist, polygon, renderer) < clearance:
                return False
    for index, artist in enumerate(artists):
        for other in artists[index + 1 :]:
            if _bboxes_overlap(artist, other, axes, renderer):
                return False
    return True


def _planets_by_house(chart: ChartData) -> dict[int, tuple[str, ...]]:
    grouped: dict[int, list[str]] = {house: [] for house in range(1, 13)}
    for planet in chart.planets:
        grouped[planet.house].append(planet.label)
    return {house: tuple(labels) for house, labels in grouped.items()}


def _draw_house_labels(
    figure: Figure,
    axes: Axes,
    chart: ChartData,
    min_planet_font: float = MIN_PLANET_FONT,
) -> None:
    """Place, measure, and shrink house text until it fits or the minimum is reached."""
    grouped = _planets_by_house(chart)
    pending = set(range(1, 13))
    fonts: dict[int, float] = {
        house: initial_planet_fontsize(len(grouped[house])) for house in pending
    }
    rashi_fonts: dict[int, float] = {
        house: rashi_fontsize_for(fonts[house], len(grouped[house])) for house in pending
    }
    kept: list[Text] = []

    for _attempt in range(MAX_FONT_ATTEMPTS):
        for artist in kept:
            artist.remove()
        kept = []
        placed: dict[int, list[Text]] = {}
        unplaced: set[int] = set()
        for house in range(1, 13):
            rashi_number = house_rashi_index(chart.lagna_rashi_index, house)
            layout = _layout_house(
                axes,
                HOUSE_POLYGONS[house],
                rashi_number,
                grouped[house],
                fonts[house],
                rashi_fonts[house],
                house,
            )
            if layout is None:
                unplaced.add(house)
                continue
            house_artists: list[Text] = []
            planet_ordinal = 0
            for text, x, y, size, kind in layout:
                if kind == "planet":
                    planet_ordinal += 1
                    gid = f"planet-{house}-{planet_ordinal}"
                else:
                    gid = f"rashi-{house}"
                artist = _add_label(axes, text, x, y, size, kind, gid)
                house_artists.append(artist)
                kept.append(artist)
            placed[house] = house_artists

        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        failed: set[int] = set(unplaced)
        for house, artists in placed.items():
            if not _house_labels_fit(
                axes,
                artists,
                HOUSE_POLYGONS[house],
                renderer,
                len(grouped[house]),
            ):
                failed.add(house)

        if not failed:
            _validate_drawn_labels(axes, chart)
            return

        stuck: list[int] = []
        for house in failed:
            count = len(grouped[house])
            if count == 0:
                if rashi_fonts[house] <= MIN_RASHI_FONT + 1e-6:
                    stuck.append(house)
                else:
                    rashi_fonts[house] = max(MIN_RASHI_FONT, rashi_fonts[house] * 0.86)
                continue
            previous = fonts[house]
            reduced = max(min_planet_font, previous * 0.86)
            if reduced >= previous - 1e-6:
                stuck.append(house)
                continue
            fonts[house] = reduced
            rashi_fonts[house] = rashi_fontsize_for(reduced, count)
        if stuck:
            houses = ", ".join(str(house) for house in stuck)
            raise ValueError(
                "Unable to render chart: labels in house "
                f"{houses} do not fit within the house polygon at the minimum "
                f"readable font size ({min_planet_font:.1f} pt)."
            )

    raise ValueError(
        "Unable to render chart: house labels did not fit within the maximum layout attempts."
    )


def _validate_drawn_labels(axes: Axes, chart: ChartData) -> None:
    """Confirm the drawn text is exactly 12 rashis and 9 stacked graha labels."""
    rashi_artists = [
        artist for artist in axes.texts if str(artist.get_gid() or "").startswith("rashi-")
    ]
    planet_artists = [
        artist for artist in axes.texts if str(artist.get_gid() or "").startswith("planet-")
    ]
    if len(rashi_artists) != 12:
        raise ValueError(
            f"Unable to render chart: expected 12 rashi numbers, found {len(rashi_artists)}."
        )
    if len(planet_artists) != 9:
        raise ValueError(
            f"Unable to render chart: expected 9 graha labels, found {len(planet_artists)}."
        )
    seen_houses: set[int] = set()
    for artist in rashi_artists:
        gid = str(artist.get_gid())
        house = int(gid.split("-")[1])
        expected = str(house_rashi_index(chart.lagna_rashi_index, house))
        if artist.get_text() != expected:
            raise ValueError(
                f"Unable to render chart: house {house} shows rashi '{artist.get_text()}', "
                f"expected {expected}."
            )
        seen_houses.add(house)
    if seen_houses != set(range(1, 13)):
        raise ValueError("Unable to render chart: rashi numbers are not drawn in every house.")

    drawn = [artist.get_text() for artist in planet_artists]
    if any("," in label for label in drawn):
        raise ValueError(
            "Unable to render chart: graha labels must be stacked, not comma-separated."
        )
    expected_labels = [planet.label for planet in chart.planets]
    if sorted(drawn) != sorted(expected_labels):
        raise ValueError(
            f"Unable to render chart: drawn grahas {drawn} do not match {expected_labels}."
        )
    for planet in chart.planets:
        if planet.abbreviation in {"Ra", "Ke"} and "(R)" in planet.label:
            raise ValueError(f"Unable to render chart: {planet.name} must not display (R).")


def _place_header_and_footer(figure: Figure, axes: Axes, chart: ChartData) -> None:
    header = figure.text(
        0.50,
        0.985,
        _header_text(chart),
        ha="center",
        va="top",
        multialignment="center",
        fontsize=10.5,
        color=BORDER,
        fontfamily="DejaVu Sans",
        linespacing=1.35,
        clip_on=False,
    )
    footer = figure.text(
        0.50,
        0.018,
        _footer_text(chart),
        ha="center",
        va="bottom",
        multialignment="center",
        fontsize=11,
        color=BORDER,
        fontfamily="DejaVu Sans",
        linespacing=1.35,
        clip_on=False,
    )
    header_size = 10.5
    footer_size = 11.0
    for _ in range(8):
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        header_box = header.get_window_extent(renderer=renderer)
        footer_box = footer.get_window_extent(renderer=renderer)
        axes_box = axes.get_window_extent(renderer=renderer)
        width = renderer.width
        height = renderer.height
        header_ok = (
            header_box.y0 >= axes_box.y1 + 6
            and header_box.y1 <= height - 2
            and header_box.x0 >= 4
            and header_box.x1 <= width - 4
        )
        footer_ok = (
            footer_box.y1 <= axes_box.y0 - 6
            and footer_box.y0 >= 2
            and footer_box.x0 >= 4
            and footer_box.x1 <= width - 4
        )
        if header_ok and footer_ok:
            return
        if not header_ok and header_size > 7.0:
            header_size *= 0.9
            header.set_fontsize(header_size)
            continue
        if not footer_ok and footer_size > 7.0:
            footer_size *= 0.9
            footer.set_fontsize(footer_size)
            continue
        raise ValueError(
            "Unable to render chart: header or footer does not fit outside the Kundli."
        )
    raise ValueError("Unable to render chart: header or footer does not fit outside the Kundli.")


def _prepare_output_path(output_file: object) -> Path:
    if not isinstance(output_file, str) or not output_file.strip():
        raise ValueError(
            f"Invalid output_file {output_file!r}. Expected a PNG file path."
        )
    path = Path(output_file).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path = path.resolve()
    except OSError as exc:
        raise ValueError(f"Unable to save Kundli PNG to '{output_file}': {exc}") from exc
    if path.exists() and path.is_dir():
        raise ValueError(f"Unable to save Kundli PNG to '{path}': destination is a directory.")
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"Unable to save Kundli PNG to '{path}': {exc}") from exc
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise ValueError(f"Unable to save Kundli PNG to '{path}': directory is not writable.")
    if path.exists() and not os.access(path, os.W_OK):
        raise ValueError(f"Unable to save Kundli PNG to '{path}': file is not writable.")
    return path


def _verify_output(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise ValueError(f"Unable to save Kundli PNG to '{path}': file was not created.")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"Unable to save Kundli PNG to '{path}': {exc}") from exc
    if size <= 0:
        raise ValueError(f"Unable to save Kundli PNG to '{path}': file is empty.")
    try:
        with path.open("rb") as handle:
            signature = handle.read(8)
    except OSError as exc:
        raise ValueError(f"Unable to save Kundli PNG to '{path}': {exc}") from exc
    if signature != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unable to save Kundli PNG to '{path}': file is not a PNG.")
    return str(path)


def render_chart(
    chart: ChartData,
    output_file: str,
    min_planet_font: float = MIN_PLANET_FONT,
) -> str:
    """Draw ``chart`` and return the verified PNG path."""
    validate_geometry()
    validate_chart(chart)
    path = _prepare_output_path(output_file)
    figure, axes = _create_figure()
    try:
        _draw_geometry(axes)
        _place_header_and_footer(figure, axes, chart)
        _draw_house_labels(figure, axes, chart, min_planet_font=min_planet_font)
        try:
            figure.savefig(
                path,
                dpi=OUTPUT_DPI,
                format="png",
                facecolor=BACKGROUND,
                edgecolor="none",
            )
        except OSError as exc:
            raise ValueError(f"Unable to save Kundli PNG to '{path}': {exc}") from exc
        except Exception as exc:
            raise ValueError(f"Unable to save Kundli PNG to '{path}': {exc}") from exc
    finally:
        plt.close(figure)
    return _verify_output(path)


# ---------------------------------------------------------------------------
# Public API and CLI
# ---------------------------------------------------------------------------


def degree_in_sign(longitude: float) -> float:
    """Degree within the current rashi, in ``[0, 30)``."""
    return normalize_longitude(longitude) % 30.0


def nakshatra_placement(longitude: float) -> tuple[str, int, str]:
    """Return ``(nakshatra name, pada 1..4, nakshatra lord)`` for a sidereal longitude."""
    longitude = normalize_longitude(longitude)
    index = int(math.floor((longitude / NAKSHATRA_SPAN) + 1e-10))
    if index >= len(NAKSHATRAS):
        index = len(NAKSHATRAS) - 1
    if index < 0:
        raise ValueError(f"Nakshatra index {index} is invalid for longitude {longitude}.")
    offset = longitude - (index * NAKSHATRA_SPAN)
    pada = int(math.floor((offset / PADA_SPAN) + 1e-10)) + 1
    if pada < 1 or pada > 4:
        pada = min(4, max(1, pada))
    name, lord = NAKSHATRAS[index]
    return name, pada, lord


def planet_dignity(name: str, rashi_index: int) -> str:
    """Exalted, Debilitated, Own, or Neutral for ``name`` in ``rashi_index``."""
    if EXALTATION_SIGN.get(name) == rashi_index:
        return "Exalted"
    if DEBILITATION_SIGN.get(name) == rashi_index:
        return "Debilitated"
    owned = [sign for sign, lord in SIGN_LORDS.items() if lord == name]
    if rashi_index in owned:
        return "Own"
    return "Neutral"


def aspected_houses(name: str, house: int) -> list[int]:
    """Whole-sign houses receiving a Parashari aspect from ``name`` in ``house``.

    Every graha aspects the 7th. Mars also aspects the 4th and 8th. Jupiter,
    Rahu, and Ketu also aspect the 5th and 9th. Saturn also aspects the 3rd
    and 10th.
    """
    if house < 1 or house > 12:
        raise ValueError(f"House must be from 1 to 12, got {house}.")
    aspects = (7,) + SPECIAL_ASPECTS.get(name, ())
    return sorted({((house + aspect - 2) % 12) + 1 for aspect in aspects})


def is_combust(name: str, longitude: float, sun_longitude: float, retrograde: bool) -> bool:
    """True when a graha is within its combustion orb of the Sun.

    The orb is the short arc in longitude, so a sign boundary does not cancel
    combustion. Moon 12°, Mars 17°, Mercury 14° (12° retrograde), Jupiter 11°,
    Venus 10° (8° retrograde), Saturn 15°. Sun, Rahu, and Ketu are never combust.
    """
    orbs = COMBUSTION_ORBS.get(name)
    if orbs is None:
        return False
    orb = orbs[1] if retrograde else orbs[0]
    return _angular_separation(longitude, sun_longitude) <= orb


def graha_yuddha_participants(planets: tuple[PlanetPosition, ...]) -> set[str]:
    """Names of tara grahas within 1° of another tara graha.

    Sun, Moon, Rahu, and Ketu do not enter a planetary war. Sharing a sign is
    not enough; the longitudes must be within one degree.
    """
    fighters = [planet for planet in planets if planet.name in GRAHA_YUDDHA_PLANETS]
    engaged: set[str] = set()
    for index, left in enumerate(fighters):
        for right in fighters[index + 1 :]:
            if _angular_separation(left.longitude, right.longitude) <= GRAHA_YUDDHA_ORB:
                engaged.add(left.name)
                engaged.add(right.name)
    return engaged


def houses_ruled_by(name: str, lagna_rashi_index: int) -> list[int]:
    """Whole-sign houses whose rashi lord is ``name``. Rahu and Ketu rule none."""
    signs = [sign for sign, lord in SIGN_LORDS.items() if lord == name]
    return sorted(whole_sign_house(sign, lagna_rashi_index) for sign in signs)


def _rounded_longitude(longitude: float) -> float:
    value = round(normalize_longitude(longitude), 4)
    if value >= 360.0:
        return 0.0
    return value


def kundli_as_dict(chart: ChartData) -> dict[str, object]:
    """Structured Kundli used by :func:`get_kundli_json`."""
    validate_chart(chart)
    lagna_total = _rounded_longitude(chart.lagna_longitude)
    lagna_nakshatra, lagna_pada, _lagna_nakshatra_lord = nakshatra_placement(lagna_total)
    planets: dict[str, object] = {}
    occupants: dict[int, list[str]] = {house: [] for house in range(1, 13)}
    sun = next(planet for planet in chart.planets if planet.name == "Sun")
    at_war = graha_yuddha_participants(chart.planets)
    for planet in chart.planets:
        total = _rounded_longitude(planet.longitude)
        nakshatra, pada, _lord = nakshatra_placement(total)
        occupants[planet.house].append(planet.name)
        planets[planet.name] = {
            "sign": planet.rashi_name,
            "sign_number": planet.rashi_index,
            "house": planet.house,
            "degree_in_sign": round(total % 30.0, 4),
            "total_degree": total,
            "nakshatra": nakshatra,
            "pada": pada,
            "is_retrograde": planet.retrograde,
            "is_combust": is_combust(
                planet.name, planet.longitude, sun.longitude, planet.retrograde
            ),
            "is_in_graha_yuddha": planet.name in at_war,
            "dignity": planet_dignity(planet.name, planet.rashi_index),
            "lord_of_houses": houses_ruled_by(planet.name, chart.lagna_rashi_index),
            "aspected_houses": aspected_houses(planet.name, planet.house),
        }
    if list(planets) != list(PLANET_NAMES):
        raise ValueError(
            f"Kundli JSON is missing grahas. Found {list(planets)}, expected {list(PLANET_NAMES)}."
        )
    houses = {
        str(house): {
            "sign": RASHI_NAMES[house_rashi_index(chart.lagna_rashi_index, house)],
            "sign_number": house_rashi_index(chart.lagna_rashi_index, house),
            "planets": occupants[house],
        }
        for house in range(1, 13)
    }
    payload: dict[str, object] = {
        "metadata": {
            "dob": chart.birth.dob,
            "tob": chart.birth.tob,
            "location": chart.location.resolved_name,
            "coordinates": {
                "latitude": round(chart.location.latitude, 4),
                "longitude": round(chart.location.longitude, 4),
            },
            "timezone": chart.birth.timezone_name,
            "utc_datetime": chart.birth.utc_datetime.isoformat(),
            "ayanamsa": {
                "system": "Lahiri (Chitra Paksha)",
                "value_deg": round(chart.ayanamsa, 6),
            },
        },
        "lagna": {
            "sign": chart.lagna_rashi_name,
            "sign_number": chart.lagna_rashi_index,
            "degree_in_sign": round(lagna_total % 30.0, 4),
            "nakshatra": lagna_nakshatra,
            "pada": lagna_pada,
            "ruling_planet": SIGN_LORDS[chart.lagna_rashi_index],
        },
        "planets": planets,
        "houses": houses,
    }
    payload["ashtakavarga"] = get_ashtakavarga_json(payload)
    return payload


def get_kundli_json(
    dob: str,
    tob: str,
    location: str,
    as_string: bool = False,
) -> dict[str, object] | str:
    """Return the sidereal Kundli for ``dob``, ``tob``, and ``location``.

    The default is a Python dict so it can be passed straight to
    :func:`get_timing_telemetry`. Set ``as_string`` to receive indented JSON.
    The calculation path matches :func:`generate_kundli_chart`.

    ``ruling_planet`` is the rashi lord of the lagna. ``dignity`` is Exalted,
    Debilitated, Own, or Neutral. ``lord_of_houses`` lists the whole-sign
    houses that graha rules from this lagna. Rahu and Ketu rule no signs.
    ``aspected_houses`` lists the Parashari aspects from that graha's house.
    Rahu is the mean node. ``is_combust`` uses the short-arc orbs Moon 12°,
    Mars 17°, Mercury 14° (12° retrograde), Jupiter 11°, Venus 10° (8°
    retrograde), and Saturn 15°. ``is_in_graha_yuddha`` is true when Mars,
    Mercury, Jupiter, Venus, or Saturn is within 1° of another of those five.
    """
    chart = compute_chart(dob, tob, location)
    payload = kundli_as_dict(chart)
    if as_string:
        return json.dumps(payload, indent=2, ensure_ascii=False)
    return payload


def _dasha_span_days(parent_days: float, lord: str) -> float:
    """Length of ``lord`` as a sub-period of a span that totals 120 dasha years."""
    return parent_days * (DASHA_YEARS[lord] / 120.0)


def _walk_dasha_cycle(
    start_lord: str, elapsed_days: float, parent_days: float
) -> tuple[str, float]:
    """Return the active lord and the days already elapsed inside that lord's span."""
    if elapsed_days < -1e-6:
        raise ValueError("Dasha elapsed time cannot be negative.")
    elapsed_days = max(0.0, elapsed_days)
    index = DASHA_ORDER.index(start_lord)
    cursor = 0.0
    for step in range(9):
        lord = DASHA_ORDER[index]
        span = _dasha_span_days(parent_days, lord)
        if elapsed_days <= cursor + span + 1e-6 or step == 8:
            return lord, max(0.0, elapsed_days - cursor)
        cursor += span
        index = (index + 1) % 9
    raise ValueError("Unable to resolve a Vimshottari sub-period.")


def _calculate_vimshottari_triple(
    natal_moon_deg: float,
    birth_utc: datetime,
    target_utc: datetime,
) -> dict[str, str]:
    """Active Mahadasha, Antardasha, and Pratyantardasha at ``target_utc``.

    The birth nakshatra lord's mahadasha is already partly elapsed. Antardasha
    and pratyantardasha are counted from that point inside the full period, not
    restarted at birth. Period lengths use the 365.2425-day mean tropical year.
    """
    moon = normalize_longitude(natal_moon_deg)
    nak_index = int(math.floor((moon / NAKSHATRA_SPAN) + 1e-10)) % 27
    degree_in_nakshatra = moon - (nak_index * NAKSHATRA_SPAN)
    first_lord = DASHA_ORDER[nak_index % 9]
    first_span_days = DASHA_YEARS[first_lord] * VIMSHOTTARI_YEAR_DAYS
    consumed_before_birth = (degree_in_nakshatra / NAKSHATRA_SPAN) * first_span_days
    balance_days = first_span_days - consumed_before_birth
    days_elapsed = (target_utc - birth_utc).total_seconds() / 86400.0
    if days_elapsed < -1e-6:
        raise ValueError("Target date cannot precede birth date.")
    days_elapsed = max(0.0, days_elapsed)

    if days_elapsed <= balance_days + 1e-6:
        md_lord = first_lord
        # Balance is the remainder at birth, so the years already lived
        # inside this mahadasha must be added before antardasha is resolved.
        md_elapsed = (first_span_days - balance_days) + days_elapsed
        md_span_days = first_span_days
    else:
        cursor = balance_days
        index = (DASHA_ORDER.index(first_lord) + 1) % 9
        md_lord = first_lord
        md_elapsed = 0.0
        md_span_days = first_span_days
        resolved = False
        for _step in range(36):
            md_lord = DASHA_ORDER[index]
            md_span_days = DASHA_YEARS[md_lord] * VIMSHOTTARI_YEAR_DAYS
            if days_elapsed <= cursor + md_span_days + 1e-6:
                md_elapsed = days_elapsed - cursor
                resolved = True
                break
            cursor += md_span_days
            index = (index + 1) % 9
        if not resolved:
            raise ValueError(
                "Target date is too far from birth to resolve a Vimshottari mahadasha."
            )

    ad_lord, days_into_ad = _walk_dasha_cycle(md_lord, md_elapsed, md_span_days)
    ad_span_days = _dasha_span_days(md_span_days, ad_lord)
    pd_lord, _days_into_pd = _walk_dasha_cycle(ad_lord, days_into_ad, ad_span_days)
    return {
        "mahadasha": md_lord,
        "antardasha": ad_lord,
        "pratyantardasha": pd_lord,
        "active_period_string": f"{md_lord}-{ad_lord}-{pd_lord}",
    }


def _load_natal_chart(natal_chart: object) -> dict[str, object]:
    """Accept the dict or JSON string returned by :func:`get_kundli_json`."""
    if isinstance(natal_chart, str):
        try:
            loaded = json.loads(natal_chart)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid natal chart JSON: {exc}") from exc
    elif isinstance(natal_chart, dict):
        loaded = natal_chart
    else:
        raise ValueError(
            "Invalid natal chart. Expected the dict or JSON string from get_kundli_json()."
        )
    if not isinstance(loaded, dict):
        raise ValueError(
            "Invalid natal chart. Expected the dict or JSON string from get_kundli_json()."
        )
    return loaded


def _chart_number(payload: dict[str, object], path: str) -> float:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Natal chart is missing '{path}'.")
        current = current[part]
    try:
        value = float(current)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Natal chart field '{path}' is not a number.") from exc
    if not math.isfinite(value):
        raise ValueError(f"Natal chart field '{path}' is not finite.")
    return value


def _chart_text(payload: dict[str, object], path: str) -> str:
    current: object = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Natal chart is missing '{path}'.")
        current = current[part]
    if not isinstance(current, str) or not current.strip():
        raise ValueError(f"Natal chart field '{path}' is empty.")
    return current


def _transit_record(
    name: str,
    longitude: float,
    speed: float | None,
    natal_lagna_rashi: int,
    natal_moon_rashi: int,
) -> dict[str, object]:
    longitude = normalize_longitude(longitude)
    rashi = longitude_to_rashi(longitude)
    retrograde = True if name in INHERENTLY_RETROGRADE else bool(speed is not None and speed < 0.0)
    return {
        "sign": RASHI_NAMES[rashi],
        "sign_number": rashi,
        "degree_in_sign": round(longitude % 30.0, 2),
        "house_from_lagna": whole_sign_house(rashi, natal_lagna_rashi),
        "house_from_moon": whole_sign_house(rashi, natal_moon_rashi),
        "is_retrograde": retrograde,
    }


def get_timing_telemetry(
    natal_chart: object,
    target_date_str: str,
    target_time_str: str = "12:00",
) -> dict[str, object]:
    """Vimshottari timing, sidereal gochara, and the daily lunar trigger.

    ``natal_chart`` is the dict or JSON string from :func:`get_kundli_json`.
    ``target_date_str`` is ``YYYY-MM-DD`` and ``target_time_str`` is 24-hour
    ``HH:MM`` in the natal chart's IANA timezone. Ambiguous and nonexistent
    civil times are rejected. Transits use Lahiri sidereal positions and the
    mean lunar node.

    The returned ``daily_lunar_trigger`` classifies the transit Moon against
    the natal Moon's nakshatra. Chandrashtama is the transit Moon in the 8th
    house from the natal Moon.
    """
    chart = _load_natal_chart(natal_chart)
    birth_text = _chart_text(chart, "metadata.utc_datetime")
    timezone_name = _chart_text(chart, "metadata.timezone")
    try:
        birth_utc = datetime.fromisoformat(birth_text)
    except ValueError as exc:
        raise ValueError(
            f"Natal chart field 'metadata.utc_datetime' is not a valid timestamp: {exc}"
        ) from exc
    if birth_utc.tzinfo is None:
        raise ValueError(
            "Natal chart field 'metadata.utc_datetime' must include a UTC offset."
        )
    birth_utc = birth_utc.astimezone(timezone.utc)

    natal_lagna_rashi = int(_chart_number(chart, "lagna.sign_number"))
    natal_moon_degree = _chart_number(chart, "planets.Moon.total_degree")
    natal_moon_rashi = int(_chart_number(chart, "planets.Moon.sign_number"))
    if natal_lagna_rashi < 1 or natal_lagna_rashi > 12:
        raise ValueError("Natal lagna sign_number must be from 1 to 12.")
    if natal_moon_rashi < 1 or natal_moon_rashi > 12:
        raise ValueError("Natal Moon sign_number must be from 1 to 12.")

    target_local = _localize_birth(
        target_date_str, target_time_str, timezone_name, moment="target"
    )
    target_utc = target_local.astimezone(timezone.utc)
    utc_decimal_hours = (
        target_utc.hour
        + target_utc.minute / 60.0
        + target_utc.second / 3600.0
        + target_utc.microsecond / 3_600_000_000.0
    )
    try:
        julian_day = float(
            swe.julday(target_utc.year, target_utc.month, target_utc.day, utc_decimal_hours)
        )
    except (TypeError, ValueError, swe.Error) as exc:
        raise ValueError(
            f"Unable to calculate Julian Day for target time {target_utc.isoformat()}: {exc}"
        ) from exc
    if not math.isfinite(julian_day):
        raise ValueError(
            f"Unable to calculate Julian Day for target time {target_utc.isoformat()}."
        )

    dasha = _calculate_vimshottari_triple(natal_moon_degree, birth_utc, target_utc)
    _configure_lahiri()
    transits: dict[str, object] = {}
    rahu_longitude: float | None = None
    moon_longitude: float | None = None
    for name, _abbreviation, body_id in GRAHA_BODIES:
        longitude, speed = _calculate_body(julian_day, name, body_id)
        if name == "Rahu":
            rahu_longitude = longitude
        if name == "Moon":
            moon_longitude = longitude
        transits[name] = _transit_record(
            name, longitude, speed, natal_lagna_rashi, natal_moon_rashi
        )
    if rahu_longitude is None:
        raise ValueError("Swiss Ephemeris calculation failed for Rahu: longitude is missing.")
    if moon_longitude is None:
        raise ValueError("Swiss Ephemeris calculation failed for Moon: longitude is missing.")
    ketu_longitude = normalize_longitude(rahu_longitude + 180.0)
    transits[KETU_NAME] = _transit_record(
        KETU_NAME, ketu_longitude, None, natal_lagna_rashi, natal_moon_rashi
    )

    natal_nakshatra = int(
        math.floor((normalize_longitude(natal_moon_degree) / NAKSHATRA_SPAN) + 1e-10)
    ) % 27
    transit_nakshatra = int(math.floor((moon_longitude / NAKSHATRA_SPAN) + 1e-10)) % 27
    tara_distance = ((transit_nakshatra - natal_nakshatra) % 27) + 1
    tara_index = (tara_distance - 1) % 9
    moon_from_natal_moon = int(transits["Moon"]["house_from_moon"])  # type: ignore[index]
    return {
        "target_timestamp": {
            "local": target_local.isoformat(),
            "utc": target_utc.isoformat(),
            "timezone": timezone_name,
        },
        "active_dasha": dasha,
        "transits": transits,
        "daily_lunar_trigger": {
            "transit_moon_nakshatra_index": transit_nakshatra + 1,
            "tara_bala": TARA_NAMES[tara_index],
            "is_tara_favorable": tara_index in FAVORABLE_TARA_INDEXES,
            "house_from_natal_moon": moon_from_natal_moon,
            "is_chandrashtama": moon_from_natal_moon == 8,
        },
        "ashtakavarga": get_ashtakavarga_json(chart, transits),
        "saturn_cycles": get_saturn_cycles(chart, target_date_str, target_time_str),
    }


def _transit_longitude(record: object) -> float:
    """Sidereal longitude from a gochara record, to the stored hundredth of a degree."""
    if not isinstance(record, dict):
        raise ValueError("Transit record is missing.")
    try:
        sign_number = int(record["sign_number"])
        degree = float(record["degree_in_sign"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Transit record is missing sign_number or degree_in_sign.") from exc
    return normalize_longitude((sign_number - 1) * 30.0 + degree)


def _combust_transit_names(transits: dict[str, object]) -> list[str]:
    """Grahas within their solar combustion orb on this transit snapshot."""
    sun = _transit_longitude(transits["Sun"])
    combust: list[str] = []
    for name in COMBUSTION_ORBS:
        record = transits[name]
        if not isinstance(record, dict):
            raise ValueError(f"Transit record for {name} is missing.")
        retrograde = bool(record.get("is_retrograde"))
        if is_combust(name, _transit_longitude(record), sun, retrograde):
            combust.append(name)
    return combust


def generate_forecast_window(
    natal_chart: object,
    start_date_str: str,
    days: int = 30,
    time_str: str = "09:00",
) -> dict[str, object]:
    """Daily lunar timeline for ``days`` civil dates, starting at ``start_date_str``.

    Each row keeps the dasha string, Moon sign and houses, Tara Bala, and risk
    flags. It does not repeat the full nine-graha state. Chandrashtama, Vipat,
    and Naidhana are collected into ``critical_windows``. A day is a peak
    execution day when Tara is Sadhana and the Moon is not in Chandrashtama.
    ``dasha_transition`` is true only when the mahadasha-antardasha-pratyantardasha
    string differs from the previous civil day. Jupiter, Saturn, Rahu, and Ketu
    signs are summarized once for a month-scale reading. Each row also carries
    ``daily_panchanga`` for the natal place: topocentric sunrise, the five limbs
    at sunrise, and Rahu, Yamaganda, and Gulika.
    """
    if isinstance(days, bool) or not isinstance(days, int) or days < 1 or days > 3660:
        raise ValueError("Forecast days must be an integer from 1 to 3660.")
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"Forecast start date must be YYYY-MM-DD, got '{start_date_str}'."
        ) from exc

    from panchanga import get_daily_panchanga

    chart = _load_natal_chart(natal_chart)
    native_dob = _chart_text(chart, "metadata.dob")
    native_lagna = _chart_text(chart, "lagna.sign")
    observer_latitude = _chart_number(chart, "metadata.coordinates.latitude")
    observer_longitude = _chart_number(chart, "metadata.coordinates.longitude")
    observer_zone = _chart_text(chart, "metadata.timezone")

    prior_date = (start_date - timedelta(days=1)).isoformat()
    try:
        prior = get_timing_telemetry(chart, prior_date, time_str)
    except ValueError as exc:
        if "precede" not in str(exc):
            raise
        previous_dasha = None
    else:
        previous_dasha = str(prior["active_dasha"]["active_period_string"])  # type: ignore[index]

    timeline: list[dict[str, object]] = []
    chandrashtama_days: list[str] = []
    friction_days: list[str] = []
    execution_days: list[str] = []
    combustion_days: list[str] = []
    major_names = ("Jupiter", "Saturn", "Rahu", "Ketu")
    major_at_start: dict[str, object] = {}
    sign_changes: list[dict[str, str]] = []
    previous_signs: dict[str, str] = {}
    natal_ashtakavarga: object | None = None

    for offset in range(days):
        current_date = (start_date + timedelta(days=offset)).isoformat()
        daily = get_timing_telemetry(chart, current_date, time_str)
        dasha = daily["active_dasha"]
        lunar = daily["daily_lunar_trigger"]
        transits = daily["transits"]
        if (
            not isinstance(dasha, dict)
            or not isinstance(lunar, dict)
            or not isinstance(transits, dict)
        ):
            raise ValueError(f"Timing telemetry for {current_date} is incomplete.")
        moon = transits["Moon"]
        if not isinstance(moon, dict):
            raise ValueError(f"Timing telemetry for {current_date} is missing the Moon.")

        dasha_string = str(dasha["active_period_string"])
        dasha_transition = previous_dasha is not None and dasha_string != previous_dasha
        previous_dasha = dasha_string
        tara_bala = str(lunar["tara_bala"])
        is_chandrashtama = bool(lunar["is_chandrashtama"])
        risk_flags: list[str] = []

        if is_chandrashtama:
            risk_flags.append("CHANDRASHTAMA (Emotional volatility / poor decision window)")
            chandrashtama_days.append(current_date)
        if "Naidhana" in tara_bala:
            risk_flags.append("NAIDHANA_TARA (Crisis / sudden obstacles)")
            friction_days.append(current_date)
        elif "Vipat" in tara_bala:
            risk_flags.append("VIPAT_TARA (Unplanned delays / losses)")
            friction_days.append(current_date)
        elif "Sadhana" in tara_bala and not is_chandrashtama:
            execution_days.append(current_date)

        combust = _combust_transit_names(transits)
        if combust:
            names = ", ".join(combust)
            risk_flags.append(f"COMBUSTION ({names} within solar orb)")
            combustion_days.append(current_date)

        for name in major_names:
            record = transits[name]
            if not isinstance(record, dict):
                raise ValueError(f"Timing telemetry for {current_date} is missing {name}.")
            sign = str(record["sign"])
            if offset == 0:
                natal_ashtakavarga = daily.get("ashtakavarga")
                major_at_start[name] = {
                    "sign": sign,
                    "sign_number": int(record["sign_number"]),
                    "is_retrograde": bool(record["is_retrograde"]),
                }
                previous_signs[name] = sign
            elif previous_signs[name] != sign:
                sign_changes.append(
                    {
                        "date": current_date,
                        "planet": name,
                        "from_sign": previous_signs[name],
                        "to_sign": sign,
                    }
                )
                previous_signs[name] = sign

        panchanga = get_daily_panchanga(
            current_date,
            latitude=observer_latitude,
            longitude=observer_longitude,
            timezone_name=observer_zone,
        )
        daily_panchanga = panchanga["daily_panchanga"]
        timeline.append(
            {
                "date": current_date,
                "active_dasha": dasha_string,
                "dasha_transition": dasha_transition,
                "transit_moon": {
                    "sign": moon["sign"],
                    "house_from_moon": moon["house_from_moon"],
                    "house_from_lagna": moon["house_from_lagna"],
                    "is_chandrashtama": is_chandrashtama,
                },
                "tara_bala": tara_bala,
                "is_favorable": bool(lunar["is_tara_favorable"]) and not is_chandrashtama,
                "risk_flags": risk_flags,
                "daily_panchanga": daily_panchanga,
            }
        )

    return {
        "metadata": {
            "native_dob": native_dob,
            "native_lagna": native_lagna,
            "forecast_start": start_date_str,
            "total_days": days,
            "time": time_str,
        },
        "critical_windows": {
            "chandrashtama_dates": chandrashtama_days,
            "friction_dates": sorted(set(friction_days)),
            "peak_execution_dates": execution_days,
            "combustion_dates": combustion_days,
        },
        "major_transits": {
            "as_of": start_date_str,
            "planets": major_at_start,
            "sign_changes": sign_changes,
        },
        "ashtakavarga": natal_ashtakavarga,
        "saturn_cycles": get_saturn_cycles(chart, start_date_str, time_str),
        "timeline": timeline,
    }


def generate_kundli_chart(
    dob: str,
    tob: str,
    location: str,
    output_file: str = "kundli.png",
) -> str:
    """Generate a North Indian Lagna Kundli PNG and return its path.

    Parameters
    ----------
    dob:
        Birth date as ``YYYY-MM-DD``.
    tob:
        Birth time as 24-hour ``HH:MM``.
    location:
        Birthplace as ``City, Country``. Resolved once with Nominatim.
    output_file:
        Destination PNG path. Parent directories are created when needed.

    Returns
    -------
    str
        Absolute path of the written PNG.

    Raises
    ------
    ValueError
        Invalid input, geocoding failure, timezone failure, a nonexistent or
        ambiguous civil time, a Swiss Ephemeris failure, a layout that cannot
        fit, or an output path that cannot be written.
    """
    chart = compute_chart(dob, tob, location)
    return render_chart(chart, output_file)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kundli.py",
        description="Generate a North Indian Lagna Kundli PNG from birth details.",
    )
    parser.add_argument("--dob", help="Birth date in YYYY-MM-DD.")
    parser.add_argument("--tob", help="Birth time in 24-hour HH:MM.")
    parser.add_argument("--location", help='Birth place as "City, Country".')
    parser.add_argument(
        "--output_file",
        default="kundli.png",
        help="Output PNG path (default: kundli.png).",
    )
    args = parser.parse_args(argv)
    missing = [
        flag
        for flag, value in (
            ("--dob", args.dob),
            ("--tob", args.tob),
            ("--location", args.location),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(
            f"Missing required argument(s): {joined}. "
            'Example: python kundli.py --dob 1990-01-15 --tob 14:30 '
            '--location "Bengaluru, India"'
        )
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. With no arguments, render the built-in example chart."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        if not argv:
            path = generate_kundli_chart(
                EXAMPLE_DOB,
                EXAMPLE_TOB,
                EXAMPLE_LOCATION,
                EXAMPLE_OUTPUT,
            )
        else:
            args = _parse_args(argv)
            path = generate_kundli_chart(args.dob, args.tob, args.location, args.output_file)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: Unable to generate Kundli: {exc}", file=sys.stderr)
        return 1
    print(f"Successfully generated Kundli: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
