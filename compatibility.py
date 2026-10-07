"""36-guna Ashtakoota, Manglik dosha, and 7th-house synastry."""

from __future__ import annotations

import json
from typing import Any

NAKSHATRA_NAMES: tuple[str, ...] = (
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
)

SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

PLANETARY_RELATIONSHIPS: dict[str, dict[str, list[str]]] = {
    "Sun": {
        "friends": ["Moon", "Mars", "Jupiter"],
        "neutrals": ["Mercury"],
        "enemies": ["Venus", "Saturn"],
    },
    "Moon": {
        "friends": ["Sun", "Mercury"],
        "neutrals": ["Mars", "Jupiter", "Venus", "Saturn"],
        "enemies": [],
    },
    "Mars": {
        "friends": ["Sun", "Moon", "Jupiter"],
        "neutrals": ["Venus", "Saturn"],
        "enemies": ["Mercury"],
    },
    "Mercury": {
        "friends": ["Sun", "Venus"],
        "neutrals": ["Mars", "Jupiter", "Saturn"],
        "enemies": ["Moon"],
    },
    "Jupiter": {
        "friends": ["Sun", "Moon", "Mars"],
        "neutrals": ["Saturn"],
        "enemies": ["Mercury", "Venus"],
    },
    "Venus": {
        "friends": ["Mercury", "Saturn"],
        "neutrals": ["Mars", "Jupiter"],
        "enemies": ["Sun", "Moon"],
    },
    "Saturn": {
        "friends": ["Mercury", "Venus"],
        "neutrals": ["Jupiter"],
        "enemies": ["Sun", "Moon", "Mars"],
    },
}

NADI_MAP: dict[str, str] = {
    "Ashwini": "Aadi",
    "Ardra": "Aadi",
    "Punarvasu": "Aadi",
    "Uttara Phalguni": "Aadi",
    "Hasta": "Aadi",
    "Jyeshtha": "Aadi",
    "Mula": "Aadi",
    "Shatabhisha": "Aadi",
    "Purva Bhadrapada": "Aadi",
    "Bharani": "Madhya",
    "Mrigashira": "Madhya",
    "Pushya": "Madhya",
    "Purva Phalguni": "Madhya",
    "Chitra": "Madhya",
    "Anuradha": "Madhya",
    "Purva Ashadha": "Madhya",
    "Dhanishta": "Madhya",
    "Uttara Bhadrapada": "Madhya",
    "Krittika": "Antya",
    "Rohini": "Antya",
    "Ashlesha": "Antya",
    "Magha": "Antya",
    "Swati": "Antya",
    "Vishakha": "Antya",
    "Uttara Ashadha": "Antya",
    "Shravana": "Antya",
    "Revati": "Antya",
}

GANA_MAP: dict[str, str] = {
    "Ashwini": "Deva",
    "Mrigashira": "Deva",
    "Punarvasu": "Deva",
    "Pushya": "Deva",
    "Hasta": "Deva",
    "Swati": "Deva",
    "Anuradha": "Deva",
    "Shravana": "Deva",
    "Revati": "Deva",
    "Bharani": "Manushya",
    "Rohini": "Manushya",
    "Ardra": "Manushya",
    "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya",
    "Purva Ashadha": "Manushya",
    "Uttara Ashadha": "Manushya",
    "Purva Bhadrapada": "Manushya",
    "Uttara Bhadrapada": "Manushya",
    "Krittika": "Rakshasa",
    "Ashlesha": "Rakshasa",
    "Magha": "Rakshasa",
    "Chitra": "Rakshasa",
    "Vishakha": "Rakshasa",
    "Jyeshtha": "Rakshasa",
    "Mula": "Rakshasa",
    "Dhanishta": "Rakshasa",
    "Shatabhisha": "Rakshasa",
}

YONI_MAP: dict[str, str] = {
    "Ashwini": "Horse",
    "Bharani": "Elephant",
    "Krittika": "Sheep",
    "Rohini": "Serpent",
    "Mrigashira": "Serpent",
    "Ardra": "Dog",
    "Punarvasu": "Cat",
    "Pushya": "Sheep",
    "Ashlesha": "Cat",
    "Magha": "Rat",
    "Purva Phalguni": "Rat",
    "Uttara Phalguni": "Cow",
    "Hasta": "Buffalo",
    "Chitra": "Tiger",
    "Swati": "Buffalo",
    "Vishakha": "Tiger",
    "Anuradha": "Deer",
    "Jyeshtha": "Deer",
    "Mula": "Dog",
    "Purva Ashadha": "Monkey",
    "Uttara Ashadha": "Mongoose",
    "Shravana": "Monkey",
    "Dhanishta": "Lion",
    "Shatabhisha": "Horse",
    "Purva Bhadrapada": "Lion",
    "Uttara Bhadrapada": "Cow",
    "Revati": "Elephant",
}

YONI_ENEMIES = frozenset(
    {
        ("Horse", "Buffalo"),
        ("Elephant", "Lion"),
        ("Sheep", "Monkey"),
        ("Serpent", "Mongoose"),
        ("Dog", "Deer"),
        ("Cat", "Rat"),
        ("Cow", "Tiger"),
    }
)

for _name in NAKSHATRA_NAMES:
    if _name not in NADI_MAP or _name not in GANA_MAP or _name not in YONI_MAP:
        raise RuntimeError(f"Nakshatra {_name} is missing from a compatibility table.")


def _as_chart(chart: object, label: str) -> dict[str, Any]:
    if isinstance(chart, str):
        try:
            loaded = json.loads(chart)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid {label} chart JSON: {exc}") from exc
        chart = loaded
    if not isinstance(chart, dict):
        raise ValueError(
            f"Invalid {label} chart. Expected the dict or JSON string from get_kundli_json()."
        )
    return chart


def _require(chart: dict[str, Any], path: str, label: str) -> Any:
    current: object = chart
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"{label} chart is missing '{path}'.")
        current = current[part]
    return current


def _relation(lord: str, other: str) -> str:
    table = PLANETARY_RELATIONSHIPS[lord]
    if other in table["friends"]:
        return "friends"
    if other in table["neutrals"]:
        return "neutrals"
    return "enemies"


def _get_varna(sign_number: int) -> tuple[str, int]:
    """Brahmin 4, Kshatriya 3, Vaishya 2, Shudra 1, from the Moon's rashi element."""
    if sign_number in (4, 8, 12):
        return ("Brahmin", 4)
    if sign_number in (1, 5, 9):
        return ("Kshatriya", 3)
    if sign_number in (2, 6, 10):
        return ("Vaishya", 2)
    return ("Shudra", 1)


def _get_vashya(sign_number: int, degree_in_sign: float) -> str:
    if sign_number in (1, 2):
        return "Chatushpada"
    if sign_number in (3, 6, 7, 11):
        return "Manava"
    if sign_number in (4, 12):
        return "Jalachara"
    if sign_number == 5:
        return "Vanachara"
    if sign_number == 8:
        return "Keeta"
    if sign_number == 9:
        return "Manava" if degree_in_sign < 15.0 else "Chatushpada"
    if sign_number == 10:
        return "Jalachara" if degree_in_sign < 15.0 else "Chatushpada"
    return "Manava"


def _calc_graha_maitri(lord1: str, lord2: str) -> float:
    if lord1 == lord2:
        return 5.0
    first = _relation(lord1, lord2)
    second = _relation(lord2, lord1)
    if first == "friends" and second == "friends":
        return 5.0
    if {first, second} == {"friends", "neutrals"}:
        return 4.0
    if first == "neutrals" and second == "neutrals":
        return 3.0
    if {first, second} == {"friends", "enemies"}:
        return 1.0
    if {first, second} == {"neutrals", "enemies"}:
        return 0.5
    return 0.0


def _check_manglik(chart: dict[str, Any], label: str) -> dict[str, Any]:
    """Kuja dosha from Lagna and from the Moon, with the classical cancellations."""
    mars = _require(chart, "planets.Mars", label)
    if not isinstance(mars, dict):
        raise ValueError(f"{label} chart field 'planets.Mars' is incomplete.")
    house_from_lagna = int(mars["house"])
    mars_sign_number = int(mars["sign_number"])
    moon_sign_number = int(_require(chart, "planets.Moon.sign_number", label))
    house_from_moon = ((mars_sign_number - moon_sign_number) % 12) + 1
    manglik_houses = {1, 2, 4, 7, 8, 12}
    raw_manglik = house_from_lagna in manglik_houses or house_from_moon in manglik_houses
    cancelled = False
    reason = None
    dignity = str(mars["dignity"])
    sign = str(mars["sign"])
    if raw_manglik:
        if dignity in ("Exalted", "Own"):
            cancelled = True
            reason = f"Mars is in {dignity} sign ({sign})."
        elif house_from_lagna == 2 and sign in ("Gemini", "Virgo"):
            cancelled = True
            reason = "Mars in 2nd house in Mercury sign."
        elif house_from_lagna == 12 and sign in ("Taurus", "Libra"):
            cancelled = True
            reason = "Mars in 12th house in Venus sign."
    return {
        "is_manglik": raw_manglik and not cancelled,
        "raw_manglik": raw_manglik,
        "is_cancelled": cancelled,
        "cancellation_reason": reason,
        "house_from_lagna": house_from_lagna,
        "house_from_moon": house_from_moon,
    }


def _seventh_house(chart: dict[str, Any], label: str) -> dict[str, Any]:
    house = _require(chart, "houses.7", label)
    if not isinstance(house, dict):
        raise ValueError(f"{label} chart field 'houses.7' is incomplete.")
    planets = house.get("planets", [])
    if not isinstance(planets, list):
        raise ValueError(f"{label} chart field 'houses.7.planets' is incomplete.")
    moon_sign = int(_require(chart, "planets.Moon.sign_number", label))
    mars_sign = int(_require(chart, "planets.Mars.sign_number", label))
    mars_from_moon = ((mars_sign - moon_sign) % 12) + 1
    return {
        "sign": house["sign"],
        "sign_number": int(house["sign_number"]),
        "lord": SIGN_LORDS[str(house["sign"])],
        "planets": list(planets),
        "mars_in_seventh_from_lagna": "Mars" in planets,
        "mars_in_seventh_from_moon": mars_from_moon == 7,
    }


def _gana_points(male_gana: str, female_gana: str) -> float:
    """Gana points depend on which chart is the groom and which is the bride."""
    if male_gana == female_gana:
        return 6.0
    if {male_gana, female_gana} == {"Deva", "Manushya"}:
        return 5.0
    if male_gana == "Deva" and female_gana == "Rakshasa":
        return 1.0
    return 0.0


def get_compatibility_json(
    male_chart: object,
    female_chart: object,
    as_string: bool = False,
) -> dict[str, Any] | str:
    """36-guna Milan, Manglik dosha, and 7th-house synastry for one pair.

    ``male_chart`` and ``female_chart`` are dicts or JSON strings from
    :func:`kundli.get_kundli_json`. Varna and Gana are not symmetric: swapping
    the two charts can change the score. Manglik is judged from both the lagna
    and the Moon. A high guna total does not erase an uncancelled Manglik
    mismatch or an active Nadi dosha.
    """
    male = _as_chart(male_chart, "male")
    female = _as_chart(female_chart, "female")
    male_moon = _require(male, "planets.Moon", "male")
    female_moon = _require(female, "planets.Moon", "female")
    if not isinstance(male_moon, dict) or not isinstance(female_moon, dict):
        raise ValueError("Both charts need a Moon object.")

    male_nakshatra = str(male_moon["nakshatra"])
    female_nakshatra = str(female_moon["nakshatra"])
    try:
        male_nak_index = NAKSHATRA_NAMES.index(male_nakshatra)
        female_nak_index = NAKSHATRA_NAMES.index(female_nakshatra)
    except ValueError as exc:
        raise ValueError(f"Unknown Moon nakshatra: {exc}") from exc

    male_sign = int(male_moon["sign_number"])
    female_sign = int(female_moon["sign_number"])
    male_lord = SIGN_LORDS[str(male_moon["sign"])]
    female_lord = SIGN_LORDS[str(female_moon["sign"])]
    kootas: dict[str, Any] = {}

    male_varna, male_varna_value = _get_varna(male_sign)
    female_varna, female_varna_value = _get_varna(female_sign)
    varna_points = 1.0 if male_varna_value >= female_varna_value else 0.0
    kootas["varna"] = {
        "score": varna_points,
        "max": 1,
        "male_varna": male_varna,
        "female_varna": female_varna,
    }

    male_vashya = _get_vashya(male_sign, float(male_moon["degree_in_sign"]))
    female_vashya = _get_vashya(female_sign, float(female_moon["degree_in_sign"]))
    if male_vashya == female_vashya:
        vashya_points = 2.0
    elif {male_vashya, female_vashya} == {"Manava", "Jalachara"}:
        vashya_points = 0.5
    elif male_vashya == "Vanachara" and female_vashya != "Vanachara":
        vashya_points = 0.0
    else:
        vashya_points = 1.0
    kootas["vashya"] = {
        "score": vashya_points,
        "max": 2,
        "male_vashya": male_vashya,
        "female_vashya": female_vashya,
    }

    female_to_male = ((male_nak_index - female_nak_index) % 27) + 1
    male_to_female = ((female_nak_index - male_nak_index) % 27) + 1
    female_to_male_bad = (female_to_male % 9) in (3, 5, 7)
    male_to_female_bad = (male_to_female % 9) in (3, 5, 7)
    if not female_to_male_bad and not male_to_female_bad:
        tara_points = 3.0
    elif not female_to_male_bad or not male_to_female_bad:
        tara_points = 1.5
    else:
        tara_points = 0.0
    kootas["tara"] = {
        "score": tara_points,
        "max": 3,
        "f_to_m_favorable": not female_to_male_bad,
        "m_to_f_favorable": not male_to_female_bad,
    }

    male_yoni = YONI_MAP[male_nakshatra]
    female_yoni = YONI_MAP[female_nakshatra]
    hostile = (male_yoni, female_yoni) in YONI_ENEMIES or (female_yoni, male_yoni) in YONI_ENEMIES
    if male_yoni == female_yoni:
        yoni_points = 4.0
    elif hostile:
        yoni_points = 0.0
    else:
        yoni_points = 2.0
    kootas["yoni"] = {
        "score": yoni_points,
        "max": 4,
        "male_yoni": male_yoni,
        "female_yoni": female_yoni,
        "is_hostile_pair": hostile,
    }

    maitri_points = _calc_graha_maitri(male_lord, female_lord)
    kootas["graha_maitri"] = {
        "score": maitri_points,
        "max": 5,
        "male_moon_lord": male_lord,
        "female_moon_lord": female_lord,
    }

    male_gana = GANA_MAP[male_nakshatra]
    female_gana = GANA_MAP[female_nakshatra]
    gana_points = _gana_points(male_gana, female_gana)
    kootas["gana"] = {
        "score": gana_points,
        "max": 6,
        "male_gana": male_gana,
        "female_gana": female_gana,
        "gana_dosha": gana_points == 0.0,
    }

    moon_distance = ((male_sign - female_sign) % 12) + 1
    reverse_distance = ((14 - moon_distance) % 12) or 12
    bhakoot_dosha = moon_distance in (2, 12, 6, 8, 5, 9)
    bhakoot_cancelled = False
    if bhakoot_dosha and (male_lord == female_lord or maitri_points == 5.0):
        bhakoot_cancelled = True
        bhakoot_points = 7.0
    elif bhakoot_dosha:
        bhakoot_points = 0.0
    else:
        bhakoot_points = 7.0
    kootas["bhakoot"] = {
        "score": bhakoot_points,
        "max": 7,
        "relative_position": f"{moon_distance}/{reverse_distance}",
        "bhakoot_dosha": bhakoot_dosha and not bhakoot_cancelled,
        "is_cancelled": bhakoot_cancelled,
    }

    male_nadi = NADI_MAP[male_nakshatra]
    female_nadi = NADI_MAP[female_nakshatra]
    same_nadi = male_nadi == female_nadi
    nadi_cancelled = False
    if same_nadi:
        different_nakshatra = male_sign == female_sign and male_nakshatra != female_nakshatra
        different_pada = (
            male_nakshatra == female_nakshatra and male_moon["pada"] != female_moon["pada"]
        )
        if different_nakshatra or different_pada or male_lord == female_lord:
            nadi_cancelled = True
    nadi_points = 8.0 if (not same_nadi or nadi_cancelled) else 0.0
    kootas["nadi"] = {
        "score": nadi_points,
        "max": 8,
        "male_nadi": male_nadi,
        "female_nadi": female_nadi,
        "nadi_dosha": same_nadi and not nadi_cancelled,
        "is_cancelled": nadi_cancelled,
    }

    total = float(sum(item["score"] for item in kootas.values()))
    male_manglik = _check_manglik(male, "male")
    female_manglik = _check_manglik(female, "female")
    manglik_compatible = male_manglik["is_manglik"] == female_manglik["is_manglik"]
    nadi_active = bool(kootas["nadi"]["nadi_dosha"])
    if total >= 28 and not nadi_active and manglik_compatible:
        verdict = "EXCELLENT"
    elif total >= 18 and not nadi_active and manglik_compatible:
        verdict = "GOOD_AND_FAVORABLE"
    elif total >= 18:
        verdict = "ACCEPTABLE_WITH_DOSHA_REMEDIES"
    else:
        verdict = "NOT_RECOMMENDED"

    male_seventh = _seventh_house(male, "male")
    female_seventh = _seventh_house(female, "female")
    male_lagna_sign = int(_require(male, "lagna.sign_number", "male"))
    female_lagna_sign = int(_require(female, "lagna.sign_number", "female"))
    both_manglik = bool(male_manglik["is_manglik"] and female_manglik["is_manglik"])
    payload: dict[str, Any] = {
        "meta": {
            "male_dob": _require(male, "metadata.dob", "male"),
            "female_dob": _require(female, "metadata.dob", "female"),
            "male_moon": f"{male_moon['sign']} ({male_nakshatra}, Pada {male_moon['pada']})",
            "female_moon": (
                f"{female_moon['sign']} ({female_nakshatra}, Pada {female_moon['pada']})"
            ),
        },
        "gun_milan_summary": {
            "total_score": total,
            "maximum_score": 36,
            "percentage": round((total / 36.0) * 100, 1),
            "verdict": verdict,
        },
        "ashtakoota_breakdown": kootas,
        "manglik_analysis": {
            "male": male_manglik,
            "female": female_manglik,
            "is_mutually_cancelled": both_manglik,
            "is_compatible": manglik_compatible,
        },
        "synastry_flags": {
            "active_nadi_dosha": nadi_active,
            "active_bhakoot_dosha": bool(kootas["bhakoot"]["bhakoot_dosha"]),
            "active_gana_dosha": bool(kootas["gana"]["gana_dosha"]),
        },
        "seventh_house_synastry": {
            "male": male_seventh,
            "female": female_seventh,
            "female_moon_in_male_seventh": female_sign == male_seventh["sign_number"],
            "male_moon_in_female_seventh": male_sign == female_seventh["sign_number"],
            "female_lagna_is_male_seventh": female_lagna_sign == male_seventh["sign_number"],
            "male_lagna_is_female_seventh": male_lagna_sign == female_seventh["sign_number"],
        },
    }
    if as_string:
        return json.dumps(payload, indent=2, ensure_ascii=False)
    return payload
