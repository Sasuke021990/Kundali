"""Navamsha (D9) and Vargottama from D1 longitudes. No ephemeris call.

Each sign is nine parts of 3°20'. Fire signs start at Aries, earth at
Capricorn, air at Libra, and water at Cancer. Vargottama means the D9 sign
equals the D1 sign. Pushkara is the classical pair of ninths in each sign:
fire 7 and 9, earth 3 and 5, air 6 and 8, water 2 and 4.
"""

from __future__ import annotations

import math

from kundli import RASHI_NAMES, planet_dignity

NAVAMSHA_SPAN = 10.0 / 3.0
# Sign number where the first navamsha of that element begins.
_ELEMENT_START = (1, 10, 7, 4)
# 0-based parts inside the sign. Two per sign, 24 in the zodiac.
_PUSHKARA_PARTS = (
    (6, 8),
    (2, 4),
    (5, 7),
    (1, 3),
)


def _require(chart: dict[str, object], path: str) -> object:
    current: object = chart
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Natal chart is missing '{path}'.")
        current = current[part]
    return current


def navamsha_placement(longitude: float) -> tuple[int, int, int]:
    """Return D1 sign, D9 sign, and the 1-based navamsha part from one longitude."""
    if not math.isfinite(longitude):
        raise ValueError("Longitude must be a finite degree.")
    arc = longitude % 360.0
    d1 = int(arc // 30.0) + 1
    if d1 == 13:
        d1 = 1
    within = arc - (d1 - 1) * 30.0
    part_index = int(math.floor((within / NAVAMSHA_SPAN) + 1e-9))
    if part_index > 8:
        part_index = 8
    if part_index < 0:
        part_index = 0
    element = (d1 - 1) % 4
    d9 = (_ELEMENT_START[element] - 1 + part_index) % 12 + 1
    return d1, d9, part_index + 1


def _record(name: str | None, longitude: float) -> dict[str, object]:
    d1, d9, part = navamsha_placement(longitude)
    element = (d1 - 1) % 4
    row: dict[str, object] = {
        "d1_sign": RASHI_NAMES[d1],
        "d9_sign": RASHI_NAMES[d9],
        "navamsha_part": part,
        "is_vargottama": d1 == d9,
        "is_pushkara_navamsha": (part - 1) in _PUSHKARA_PARTS[element],
    }
    if name is not None:
        row["d9_dignity"] = planet_dignity(name, d9)
        ordered = {
            "d1_sign": row["d1_sign"],
            "d9_sign": row["d9_sign"],
            "d9_dignity": row["d9_dignity"],
            "is_vargottama": row["is_vargottama"],
            "is_pushkara_navamsha": row["is_pushkara_navamsha"],
            "navamsha_part": part,
        }
        return ordered
    return row


def get_navamsha_json(natal_chart: dict[str, object]) -> dict[str, object]:
    """D9 sign, dignity, Vargottama, and Pushkara for the lagna and nine grahas.

    Longitudes come from the natal chart. The division does not call the
    ephemeris. A planet debilitated in D9 is neecha navamsha. The same sign
    in D1 and D9 is Vargottama.
    """
    if not isinstance(natal_chart, dict):
        raise ValueError("Natal chart must be the dict from get_kundli_json().")
    planets = _require(natal_chart, "planets")
    if not isinstance(planets, dict) or not planets:
        raise ValueError("Natal chart is missing planets.")
    rows: dict[str, object] = {}
    for name, body in planets.items():
        if not isinstance(body, dict) or "total_degree" not in body:
            raise ValueError(f"Planet {name} is missing total_degree.")
        rows[str(name)] = _record(str(name), float(body["total_degree"]))
    lagna_sign = int(_require(natal_chart, "lagna.sign_number"))
    lagna_degree = float(_require(natal_chart, "lagna.degree_in_sign"))
    lagna_longitude = (lagna_sign - 1) * 30.0 + lagna_degree
    return {
        "planets": rows,
        "lagna": _record(None, lagna_longitude),
    }
