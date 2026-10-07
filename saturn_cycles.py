"""Sade Sati, Kantaka Shani, and Ashtama Shani from Saturn's sidereal ingresses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

SIGN_NAMES: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
SADE_SATI_PHASES = {
    12: "Rising (12th)",
    1: "Peak (1st)",
    2: "Setting (2nd)",
}
# Retrograde re-entry of the same sign stays inside one passage.
_MERGE_GAP_DAYS = 400.0
_STEP_DAYS = 5.0
_SPAN_CACHE: dict[tuple[str, str, int, int], list[dict[str, object]]] = {}


def _require(chart: dict[str, object], path: str) -> object:
    current: object = chart
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Natal chart is missing '{path}'.")
        current = current[part]
    return current


def _sign_index(longitude: float) -> int:
    return int(longitude % 360.0 // 30.0) + 1


def _house_from(origin: int, sign: int) -> int:
    return ((sign - origin) % 12) + 1


def _saturn_sign(julian_day: float) -> int:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    result, retflags = swe.calc_ut(julian_day, swe.SATURN, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)
    if not retflags & swe.FLG_SIDEREAL:
        raise ValueError("Swiss Ephemeris did not return a sidereal Saturn longitude.")
    return _sign_index(float(result[0]))


def _jd(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + utc.second / 3600.0 + utc.microsecond / 3_600_000_000.0
    return float(swe.julday(utc.year, utc.month, utc.day, hour))


def _local_date(julian_day: float, zone: ZoneInfo) -> str:
    year, month, day, ut_hour = swe.revjul(julian_day, swe.GREG_CAL)
    moment = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    moment += timedelta(hours=float(ut_hour))
    return moment.astimezone(zone).date().isoformat()


def _bisect_ingress(before: float, after: float, new_sign: int) -> float:
    lo, hi = before, after
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if _saturn_sign(mid) == new_sign:
            hi = mid
        else:
            lo = mid
    return hi


def _ingresses(start_jd: float, end_jd: float) -> list[tuple[float, int]]:
    cursor = start_jd
    sign = _saturn_sign(cursor)
    changes = [(cursor, sign)]
    while cursor < end_jd:
        nxt = min(end_jd, cursor + _STEP_DAYS)
        nxt_sign = _saturn_sign(nxt)
        if nxt_sign != sign:
            crossed = _bisect_ingress(cursor, nxt, nxt_sign)
            changes.append((crossed, nxt_sign))
            sign = nxt_sign
            cursor = crossed
        else:
            cursor = nxt
    return changes


def _passages(changes: list[tuple[float, int]]) -> list[dict[str, object]]:
    """One span per sign visit, with retrograde gaps shorter than 400 days merged."""
    if not changes:
        return []
    raw: list[list[float | int]] = []
    for index, (start, sign) in enumerate(changes):
        end = changes[index + 1][0] if index + 1 < len(changes) else start
        if end <= start:
            continue
        raw.append([sign, start, end])
    merged: list[list[float | int]] = []
    for sign, start, end in raw:
        earlier = next((item for item in reversed(merged) if item[0] == sign), None)
        gap = float(start) - float(earlier[2]) if earlier else _MERGE_GAP_DAYS + 1
        if earlier is not None and gap <= _MERGE_GAP_DAYS:
            earlier[2] = max(float(earlier[2]), float(end))
        else:
            merged.append([sign, start, end])
    return [
        {"sign": int(sign), "start_jd": float(start), "end_jd": float(end)}
        for sign, start, end in merged
    ]


def _chart_spans(chart: dict[str, object], zone: ZoneInfo) -> list[dict[str, object]]:
    birth_text = str(_require(chart, "metadata.utc_datetime"))
    birth = datetime.fromisoformat(birth_text)
    if birth.tzinfo is None:
        raise ValueError("Natal chart field 'metadata.utc_datetime' must include a UTC offset.")
    moon = int(_require(chart, "planets.Moon.sign_number"))
    lagna = int(_require(chart, "lagna.sign_number"))
    key = (birth.astimezone(timezone.utc).isoformat(), str(zone), moon, lagna)
    cached = _SPAN_CACHE.get(key)
    if cached is not None:
        return cached
    start = birth.astimezone(timezone.utc) - timedelta(days=40)
    end = birth.astimezone(timezone.utc) + timedelta(days=int(100 * 365.2425))
    spans = _passages(_ingresses(_jd(start), _jd(end)))
    _SPAN_CACHE[key] = spans
    return spans


def _phase_row(span: dict[str, object], zone: ZoneInfo, phase: str) -> dict[str, str]:
    sign = int(span["sign"])
    return {
        "phase": phase,
        "sign": SIGN_NAMES[sign - 1],
        "start": _local_date(float(span["start_jd"]), zone),
        "end": _local_date(float(span["end_jd"]), zone),
    }


def get_saturn_cycles(
    natal_chart: dict[str, object],
    as_of_date: str,
    as_of_time: str = "09:00",
) -> dict[str, object]:
    """Sade Sati, Kantaka Shani, and Ashtama Shani at one civil moment.

    Sade Sati is Saturn in the 12th, 1st, or 2nd from the natal Moon. Kantaka
    Shani is the 4th from the natal Moon or the natal lagna. Ashtama Shani is
    the 8th from the natal Moon. Ingress times come from a sidereal step search,
    and a retrograde return to the same sign stays inside one passage.
    """
    if not isinstance(natal_chart, dict):
        raise ValueError("Natal chart must be the dict from get_kundli_json().")
    zone_name = str(_require(natal_chart, "metadata.timezone"))
    try:
        zone = ZoneInfo(zone_name)
    except Exception as exc:
        raise ValueError(f"Natal chart timezone '{zone_name}' is not available: {exc}") from exc
    try:
        as_of_naive = datetime.strptime(f"{as_of_date} {as_of_time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("As-of date must be YYYY-MM-DD and time HH:MM.") from exc
    as_of = as_of_naive.replace(tzinfo=zone)
    as_of_jd = _jd(as_of)
    moon = int(_require(natal_chart, "planets.Moon.sign_number"))
    lagna = int(_require(natal_chart, "lagna.sign_number"))
    if not 1 <= moon <= 12 or not 1 <= lagna <= 12:
        raise ValueError("Natal Moon and lagna sign numbers must be from 1 to 12.")
    birth_date = str(_require(natal_chart, "metadata.dob"))
    spans = _chart_spans(natal_chart, zone)
    sign_now = _saturn_sign(as_of_jd)
    house_moon = _house_from(moon, sign_now)
    house_lagna = _house_from(lagna, sign_now)

    history: list[dict[str, str]] = []
    next_sade = None
    next_ashtama = None
    next_kantaka = None
    for span in spans:
        sign = int(span["sign"])
        start_jd = float(span["start_jd"])
        end_jd = float(span["end_jd"])
        start_date = _local_date(start_jd, zone)
        house = _house_from(moon, sign)
        lagna_house = _house_from(lagna, sign)
        phase = SADE_SATI_PHASES.get(house)
        end_date = _local_date(end_jd, zone)
        if phase and end_date >= birth_date and end_jd <= as_of_jd:
            history.append(_phase_row(span, zone, phase))
        if phase == "Rising (12th)" and start_jd > as_of_jd and next_sade is None:
            next_sade = start_date
        if house == 8 and start_jd > as_of_jd and next_ashtama is None:
            next_ashtama = start_date
        if (house == 4 or lagna_house == 4) and start_jd > as_of_jd and next_kantaka is None:
            next_kantaka = start_date

    rising = (moon - 2) % 12 + 1
    peak = moon
    setting = moon % 12 + 1
    ashtama_sign = (moon + 6) % 12 + 1
    kantaka_from_moon = (moon + 2) % 12 + 1
    kantaka_from_lagna = (lagna + 2) % 12 + 1
    return {
        "as_of": {"local": as_of.isoformat(), "timezone": zone_name},
        "saturn": {"sign": SIGN_NAMES[sign_now - 1], "sign_number": sign_now},
        "sade_sati": {
            "is_active": house_moon in SADE_SATI_PHASES,
            "current_phase": SADE_SATI_PHASES.get(house_moon),
            "active_house_from_moon": house_moon,
            "signs": {
                "rising": SIGN_NAMES[rising - 1],
                "peak": SIGN_NAMES[peak - 1],
                "setting": SIGN_NAMES[setting - 1],
            },
            "next_cycle_start": next_sade,
            "cycle_history": history,
        },
        "ashtama_shani": {
            "is_active": house_moon == 8,
            "sign": SIGN_NAMES[ashtama_sign - 1],
            "next_occurrence": next_ashtama,
        },
        "kantaka_shani": {
            "is_active": house_moon == 4 or house_lagna == 4,
            "from_moon": house_moon == 4,
            "from_lagna": house_lagna == 4,
            "house_from_moon": house_moon,
            "house_from_lagna": house_lagna,
            "sign": SIGN_NAMES[sign_now - 1],
            "moon_kantaka_sign": SIGN_NAMES[kantaka_from_moon - 1],
            "lagna_kantaka_sign": SIGN_NAMES[kantaka_from_lagna - 1],
            "next_occurrence": next_kantaka,
        },
    }
