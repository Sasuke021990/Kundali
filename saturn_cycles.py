"""Sade Sati, Kantaka Shani, and Ashtama Shani from a precomputed Saturn table.

Saturn's Lahiri sign passages are stored in ``data/saturn_sign_passages.json``.
A request maps those dates onto the natal Moon and lagna. It does not run a
Swiss Ephemeris search. Retrograde re-entries stay inside one passage, so a
Rising end date is not forced to equal the Peak start date.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

_TABLE_PATH = Path(__file__).with_name("data") / "saturn_sign_passages.json"
_TABLE_START = datetime(1880, 1, 1, tzinfo=timezone.utc)
_TABLE_END = datetime(2180, 1, 1, tzinfo=timezone.utc)

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


def write_passage_table(path: Path = _TABLE_PATH) -> None:
    """Rebuild the checked-in Lahiri Saturn table. Not used by API requests."""
    changes = _ingresses(_jd(_TABLE_START), _jd(_TABLE_END))
    raw: list[dict[str, str | int]] = []
    for index, (start, sign) in enumerate(changes):
        end = changes[index + 1][0] if index + 1 < len(changes) else _jd(_TABLE_END)
        if end <= start:
            continue
        raw.append(
            {
                "sign_number": int(sign),
                "sign": SIGN_NAMES[int(sign) - 1],
                "start_utc": _utc_iso(start),
                "end_utc": _utc_iso(end),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ayanamsa": "Lahiri",
        "ephemeris": "Moshier",
        "start_utc": _TABLE_START.isoformat(),
        "end_utc": _TABLE_END.isoformat(),
        "passages": raw,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _raw_passages.cache_clear()
    _merged_passages.cache_clear()


def _utc_iso(julian_day: float) -> str:
    year, month, day, ut_hour = swe.revjul(julian_day, swe.GREG_CAL)
    moment = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    moment += timedelta(hours=float(ut_hour))
    return moment.isoformat()


@lru_cache(maxsize=1)
def _raw_passages() -> tuple[dict[str, object], ...]:
    if not _TABLE_PATH.is_file():
        raise ValueError(
            f"Saturn passage table is missing at {_TABLE_PATH}. "
            "Rebuild it with python -m saturn_cycles."
        )
    loaded = json.loads(_TABLE_PATH.read_text(encoding="utf-8"))
    rows = loaded.get("passages")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Saturn passage table has no passages.")
    parsed: list[dict[str, object]] = []
    for row in rows:
        parsed.append(
            {
                "sign": int(row["sign_number"]),
                "start": datetime.fromisoformat(str(row["start_utc"])),
                "end": datetime.fromisoformat(str(row["end_utc"])),
            }
        )
    return tuple(parsed)


@lru_cache(maxsize=1)
def _merged_passages() -> tuple[dict[str, object], ...]:
    """First ingress through final egress. Retrograde gaps stay inside the span."""
    merged: list[dict[str, object]] = []
    for row in _raw_passages():
        sign = int(row["sign"])
        start = row["start"]
        end = row["end"]
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("Saturn passage dates must be datetimes.")
        earlier = next((item for item in reversed(merged) if item["sign"] == sign), None)
        earlier_end = earlier["end"] if earlier is not None else None
        if isinstance(earlier_end, datetime):
            gap_days = (start - earlier_end).total_seconds() / 86400.0
        else:
            gap_days = _MERGE_GAP_DAYS + 1
        if earlier is not None and gap_days <= _MERGE_GAP_DAYS:
            if isinstance(earlier_end, datetime) and end > earlier_end:
                earlier["end"] = end
        else:
            merged.append({"sign": sign, "start": start, "end": end})
    return tuple(merged)


def _sign_on(moment: datetime) -> int:
    for row in _raw_passages():
        start = row["start"]
        end = row["end"]
        if start <= moment < end:  # type: ignore[operator]
            return int(row["sign"])
    raise ValueError(
        "As-of date is outside the precomputed Saturn table "
        f"({_TABLE_START.date().isoformat()} to {_TABLE_END.date().isoformat()} UTC)."
    )


def _civil(moment: datetime, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).date().isoformat()


def _phase_row(span: dict[str, object], zone: ZoneInfo, phase: str) -> dict[str, str]:
    sign = int(span["sign"])
    start = span["start"]
    end = span["end"]
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError("Saturn passage dates must be datetimes.")
    return {
        "phase": phase,
        "sign": SIGN_NAMES[sign - 1],
        "start": _civil(start, zone),
        "end": _civil(end, zone),
    }


def get_saturn_cycles(
    natal_chart: dict[str, object],
    as_of_date: str,
    as_of_time: str = "09:00",
) -> dict[str, object]:
    """Sade Sati, Kantaka Shani, and Ashtama Shani at one civil moment.

    Sade Sati is Saturn in the 12th, 1st, or 2nd from the natal Moon. Kantaka
    Shani is the 4th from the natal Moon or the natal lagna. Ashtama Shani is
    the 8th from the natal Moon. Ingress dates come from the precomputed Lahiri
    table. A retrograde return to the same sign stays inside one passage, so
    adjacent phases may overlap.
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
    as_of_utc = as_of.astimezone(timezone.utc)
    moon = int(_require(natal_chart, "planets.Moon.sign_number"))
    lagna = int(_require(natal_chart, "lagna.sign_number"))
    if not 1 <= moon <= 12 or not 1 <= lagna <= 12:
        raise ValueError("Natal Moon and lagna sign numbers must be from 1 to 12.")
    birth_date = str(_require(natal_chart, "metadata.dob"))
    sign_now = _sign_on(as_of_utc)
    house_moon = _house_from(moon, sign_now)
    house_lagna = _house_from(lagna, sign_now)

    history: list[dict[str, str]] = []
    next_sade = None
    next_ashtama = None
    next_kantaka = None
    for span in _merged_passages():
        sign = int(span["sign"])
        start = span["start"]
        end = span["end"]
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("Saturn passage dates must be datetimes.")
        house = _house_from(moon, sign)
        lagna_house = _house_from(lagna, sign)
        phase = SADE_SATI_PHASES.get(house)
        end_date = _civil(end, zone)
        if phase and end_date >= birth_date and end <= as_of_utc:
            history.append(_phase_row(span, zone, phase))
        if phase == "Rising (12th)" and start > as_of_utc and next_sade is None:
            next_sade = _civil(start, zone)
        if house == 8 and start > as_of_utc and next_ashtama is None:
            next_ashtama = _civil(start, zone)
        kantaka = house == 4 or lagna_house == 4
        if kantaka and start > as_of_utc and next_kantaka is None:
            next_kantaka = _civil(start, zone)

    rising = (moon - 2) % 12 + 1
    peak = moon
    setting = moon % 12 + 1
    ashtama_sign = (moon + 6) % 12 + 1
    kantaka_from_moon = (moon + 2) % 12 + 1
    kantaka_from_lagna = (lagna + 2) % 12 + 1
    sade_active = house_moon in SADE_SATI_PHASES
    ashtama_active = house_moon == 8
    kantaka_active = house_moon == 4 or house_lagna == 4
    return {
        "as_of": {"local": as_of.isoformat(), "timezone": zone_name},
        "saturn": {"sign": SIGN_NAMES[sign_now - 1], "sign_number": sign_now},
        "sade_sati": {
            "current_status": sade_active,
            "is_active": sade_active,
            "current_phase": SADE_SATI_PHASES.get(house_moon),
            "active_house_from_moon": house_moon,
            "signs": {
                "rising": SIGN_NAMES[rising - 1],
                "peak": SIGN_NAMES[peak - 1],
                "setting": SIGN_NAMES[setting - 1],
            },
            "next_ingress_date": next_sade,
            "next_cycle_start": next_sade,
            "cycle_history": history,
        },
        "ashtama_shani": {
            "current_status": ashtama_active,
            "is_active": ashtama_active,
            "sign": SIGN_NAMES[ashtama_sign - 1],
            "next_ingress_date": next_ashtama,
            "next_occurrence": next_ashtama,
        },
        "kantaka_shani": {
            "current_status": kantaka_active,
            "is_active": kantaka_active,
            "from_moon": house_moon == 4,
            "from_lagna": house_lagna == 4,
            "house_from_moon": house_moon,
            "house_from_lagna": house_lagna,
            "sign": SIGN_NAMES[sign_now - 1],
            "moon_kantaka_sign": SIGN_NAMES[kantaka_from_moon - 1],
            "lagna_kantaka_sign": SIGN_NAMES[kantaka_from_lagna - 1],
            "next_ingress_date": next_kantaka,
            "next_occurrence": next_kantaka,
        },
    }


if __name__ == "__main__":
    write_passage_table()
    print(f"Wrote {_TABLE_PATH}")
