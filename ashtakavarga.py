"""Bhinnashtakavarga and Sarvashtakavarga from a natal Kundli dict."""

from __future__ import annotations

from typing import Any

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

BAV_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)
CONTRIBUTORS: tuple[str, ...] = BAV_PLANETS + ("Lagna",)
SAV_BENCHMARK = 28

# Houses from each contributor that receive a bindu. Totals 337.
# Mercury's Jupiter row includes 9; Venus's Saturn row includes 12.
BAV_HOUSES: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {
        "Sun": (1, 2, 4, 7, 8, 9, 10, 11),
        "Moon": (3, 6, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (5, 6, 9, 11),
        "Venus": (6, 7, 12),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna": (3, 4, 6, 10, 11, 12),
    },
    "Moon": {
        "Sun": (3, 6, 7, 8, 10, 11),
        "Moon": (1, 3, 6, 7, 10, 11),
        "Mars": (2, 3, 5, 6, 9, 10, 11),
        "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 2, 4, 7, 8, 10, 11),
        "Venus": (3, 4, 5, 7, 9, 10, 11),
        "Saturn": (3, 5, 6, 11),
        "Lagna": (3, 6, 10, 11),
    },
    "Mars": {
        "Sun": (3, 5, 6, 10, 11),
        "Moon": (3, 6, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (3, 5, 6, 11),
        "Jupiter": (6, 10, 11, 12),
        "Venus": (6, 8, 11, 12),
        "Saturn": (1, 4, 7, 8, 9, 10, 11),
        "Lagna": (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun": (5, 6, 9, 11, 12),
        "Moon": (2, 4, 6, 8, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
        "Mercury": (1, 3, 5, 6, 9, 10, 11),
        "Jupiter": (6, 8, 9, 11, 12),
        "Venus": (1, 2, 3, 4, 5, 8, 9, 11),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11),
        "Lagna": (1, 2, 4, 6, 8, 10, 11),
    },
    "Jupiter": {
        "Sun": (1, 2, 3, 4, 7, 8, 9, 10, 11),
        "Moon": (2, 5, 7, 9, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11),
        "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
        "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11),
        "Venus": (2, 5, 6, 9, 10, 11),
        "Saturn": (3, 5, 6, 12),
        "Lagna": (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun": (8, 11, 12),
        "Moon": (1, 2, 3, 4, 5, 8, 9, 11),
        "Mars": (3, 4, 6, 9, 11, 12),
        "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (5, 8, 9, 10, 11),
        "Venus": (1, 2, 3, 4, 5, 8, 9, 10, 11),
        "Saturn": (3, 4, 5, 8, 9, 10, 11, 12),
        "Lagna": (1, 2, 3, 4, 5, 8, 9, 11),
    },
    "Saturn": {
        "Sun": (1, 2, 4, 7, 8, 10, 11),
        "Moon": (3, 6, 11),
        "Mars": (3, 5, 6, 10, 11, 12),
        "Mercury": (6, 8, 9, 10, 11, 12),
        "Jupiter": (5, 6, 11, 12),
        "Venus": (6, 11, 12),
        "Saturn": (3, 5, 6, 11),
        "Lagna": (1, 3, 4, 6, 10, 11),
    },
}


def sav_potency(bindus: int) -> str:
    """Label a sign's Sarvashtakavarga against the 28-bindu mean."""
    if bindus >= 35:
        return "Very High (Protected)"
    if bindus >= 32:
        return "High (Protected)"
    if bindus >= SAV_BENCHMARK:
        return "Average (Benchmark)"
    if bindus >= 25:
        return "Below Average"
    return "Weak / High Vulnerability"


def _empty_sign_counts() -> dict[str, int]:
    return {name: 0 for name in SIGN_NAMES}


def _sign_from_house(origin_sign: int, house: int) -> str:
    index = ((origin_sign - 1) + (house - 1)) % 12
    return SIGN_NAMES[index]


def _contributor_signs(chart: dict[str, Any]) -> dict[str, int]:
    planets = chart.get("planets")
    if not isinstance(planets, dict):
        raise ValueError("Natal chart is missing 'planets'.")
    signs: dict[str, int] = {}
    lagna = chart.get("lagna")
    if not isinstance(lagna, dict) or "sign_number" not in lagna:
        raise ValueError("Natal chart is missing 'lagna.sign_number'.")
    signs["Lagna"] = int(lagna["sign_number"])
    for name in BAV_PLANETS:
        body = planets.get(name)
        if not isinstance(body, dict) or "sign_number" not in body:
            raise ValueError(f"Natal chart is missing 'planets.{name}.sign_number'.")
        signs[name] = int(body["sign_number"])
        if signs[name] < 1 or signs[name] > 12:
            raise ValueError(f"Natal {name} sign_number must be from 1 to 12.")
    if signs["Lagna"] < 1 or signs["Lagna"] > 12:
        raise ValueError("Natal lagna sign_number must be from 1 to 12.")
    return signs


def compute_ashtakavarga(natal_chart: dict[str, Any]) -> dict[str, Any]:
    """Bhinnashtakavarga (0–8) per graha and Sarvashtakavarga (0–56) per sign."""
    origins = _contributor_signs(natal_chart)
    bhinnashtakavarga: dict[str, dict[str, int]] = {}
    sarvashtakavarga = _empty_sign_counts()
    for planet in BAV_PLANETS:
        counts = _empty_sign_counts()
        table = BAV_HOUSES[planet]
        for contributor in CONTRIBUTORS:
            origin = origins[contributor]
            for house in table[contributor]:
                sign = _sign_from_house(origin, house)
                counts[sign] += 1
        for sign, value in counts.items():
            if value < 0 or value > 8:
                raise ValueError(
                    f"{planet} Bhinnashtakavarga in {sign} is {value}, expected 0 to 8."
                )
            sarvashtakavarga[sign] += value
        bhinnashtakavarga[planet] = counts
    total = sum(sarvashtakavarga.values())
    return {
        "bhinnashtakavarga": bhinnashtakavarga,
        "sarvashtakavarga": sarvashtakavarga,
        "total_bindus": total,
        "benchmark": SAV_BENCHMARK,
    }


def transit_filter_status(
    natal_ashtakavarga: dict[str, Any],
    transits: dict[str, Any],
    names: tuple[str, ...] = ("Jupiter", "Saturn", "Rahu", "Ketu"),
) -> dict[str, Any]:
    """SAV of the sign each named graha occupies, with a potency label."""
    sav = natal_ashtakavarga.get("sarvashtakavarga")
    bav = natal_ashtakavarga.get("bhinnashtakavarga")
    if not isinstance(sav, dict):
        raise ValueError("Ashtakavarga is missing sarvashtakavarga.")
    status: dict[str, Any] = {}
    for name in names:
        record = transits.get(name)
        if not isinstance(record, dict):
            raise ValueError(f"Transit record for {name} is missing.")
        sign = str(record["sign"])
        bindus = int(sav[sign])
        entry: dict[str, Any] = {
            "sign": sign,
            "bindus": bindus,
            "transit_potency": sav_potency(bindus),
        }
        if isinstance(bav, dict) and name in bav and isinstance(bav[name], dict):
            entry["planet_bindus"] = int(bav[name][sign])
        status[f"{name}_in_{sign}"] = entry
    return status


def get_ashtakavarga_json(
    natal_chart: dict[str, Any],
    transits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Natal BAV/SAV, and optional gochara potency from current transits."""
    computed = compute_ashtakavarga(natal_chart)
    payload: dict[str, Any] = {
        "sarvashtakavarga": computed["sarvashtakavarga"],
        "bhinnashtakavarga": computed["bhinnashtakavarga"],
        "total_bindus": computed["total_bindus"],
        "benchmark": computed["benchmark"],
    }
    if transits is not None:
        payload["transit_filter_status"] = transit_filter_status(computed, transits)
    return payload
