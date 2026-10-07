"""Shared calls used by the HTTP APIs and the MCP servers."""

from __future__ import annotations

from typing import Any

from kundli import (
    _load_natal_chart,
    generate_forecast_window,
    get_compatibility_json,
    get_kundli_json,
    get_timing_telemetry,
)


def build_kundli(dob: str, tob: str, location: str) -> dict[str, Any]:
    """Return the natal chart dict from birth date, time, and place."""
    chart = get_kundli_json(dob, tob, location, as_string=False)
    if not isinstance(chart, dict):
        raise ValueError("Kundli calculation did not return a chart object.")
    return chart


def resolve_natal_chart(
    natal_chart: dict[str, Any] | str | None,
    dob: str | None,
    tob: str | None,
    location: str | None,
) -> dict[str, Any]:
    """Use a supplied chart, or calculate one from birth details."""
    if natal_chart is not None:
        if isinstance(natal_chart, dict):
            return natal_chart
        return _load_natal_chart(natal_chart)
    if dob and tob and location:
        return build_kundli(dob, tob, location)
    raise ValueError(
        "Provide natal_chart, or all three of dob, tob, and location. "
        "dob is YYYY-MM-DD, tob is HH:MM, and location is a place name."
    )


def build_timing(
    target_date: str,
    target_time: str = "12:00",
    natal_chart: dict[str, Any] | str | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Vimshottari dasha, gochara, and the daily lunar trigger."""
    chart = resolve_natal_chart(natal_chart, dob, tob, location)
    return get_timing_telemetry(chart, target_date, target_time)


def build_forecast(
    start_date: str,
    days: int = 30,
    time_str: str = "09:00",
    natal_chart: dict[str, Any] | str | None = None,
    dob: str | None = None,
    tob: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Concise multi-day timeline of dasha, Tara, and risk flags."""
    chart = resolve_natal_chart(natal_chart, dob, tob, location)
    return generate_forecast_window(chart, start_date, days, time_str)


def build_compatibility(
    male_chart: dict[str, Any] | str | None = None,
    female_chart: dict[str, Any] | str | None = None,
    male_dob: str | None = None,
    male_tob: str | None = None,
    male_location: str | None = None,
    female_dob: str | None = None,
    female_tob: str | None = None,
    female_location: str | None = None,
) -> dict[str, Any]:
    """Ashtakoota, Manglik, and 7th-house synastry. Groom and bride stay distinct."""
    male = resolve_natal_chart(male_chart, male_dob, male_tob, male_location)
    female = resolve_natal_chart(female_chart, female_dob, female_tob, female_location)
    result = get_compatibility_json(male, female, as_string=False)
    if not isinstance(result, dict):
        raise ValueError("Compatibility calculation did not return an object.")
    return result
