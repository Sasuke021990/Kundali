"""HTTP APIs, each with its own Swagger UI.

Kundli:         /kundli/docs
Timing:         /timing/docs
Forecast:       /forecast/docs
Compatibility:  /compatibility/docs
Ashtakavarga:   /ashtakavarga/docs
Saturn cycles:  /saturn-cycles/docs
Panchanga:      /panchanga/docs
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from jyotish_api.service import (
    build_ashtakavarga,
    build_compatibility,
    build_forecast,
    build_kundli,
    build_panchanga,
    build_saturn_cycles,
    build_timing,
)

API_PORT = 8741
KUNDLI_MCP_PORT = 8742
TIMING_MCP_PORT = 8743
FORECAST_MCP_PORT = 8744
COMPATIBILITY_MCP_PORT = 8745
ASHTAKAVARGA_MCP_PORT = 8746
SATURN_MCP_PORT = 8747
PANCHANGA_MCP_PORT = 8748


class BirthBody(BaseModel):
    dob: str = Field(examples=["1998-04-10"], description="Birth date, YYYY-MM-DD.")
    tob: str = Field(examples=["17:25"], description="Local birth time, 24-hour HH:MM.")
    location: str = Field(
        examples=["Hubli, Karnataka"],
        description="Place name geocoded with OpenStreetMap Nominatim.",
    )


class TimingBody(BaseModel):
    target_date: str = Field(examples=["2026-10-15"], description="Civil date, YYYY-MM-DD.")
    target_time: str = Field(
        "12:00",
        examples=["09:00"],
        description="Local time HH:MM in the natal chart timezone. Noon if omitted.",
    )
    natal_chart: dict[str, Any] | None = Field(
        None,
        description="Dict returned by the Kundli API. Omit it to send dob, tob, and location.",
    )
    dob: str | None = Field(None, examples=["1998-04-10"])
    tob: str | None = Field(None, examples=["17:25"])
    location: str | None = Field(None, examples=["Hubli, Karnataka"])


class ForecastBody(BaseModel):
    start_date: str = Field(examples=["2026-10-01"], description="First civil date, YYYY-MM-DD.")
    days: int = Field(30, ge=1, le=3660, description="Number of civil dates, from 1 to 3660.")
    time: str = Field(
        "09:00",
        examples=["09:00"],
        description="Local clock time applied to every date.",
    )
    natal_chart: dict[str, Any] | None = Field(
        None,
        description="Dict returned by the Kundli API. Omit it to send dob, tob, and location.",
    )
    dob: str | None = Field(None, examples=["1998-04-10"])
    tob: str | None = Field(None, examples=["17:25"])
    location: str | None = Field(None, examples=["Hubli, Karnataka"])


class CompatibilityBody(BaseModel):
    male_chart: dict[str, Any] | None = Field(
        None,
        description="Groom chart from the Kundli API, or omit and send the male birth fields.",
    )
    female_chart: dict[str, Any] | None = Field(
        None,
        description="Bride chart from the Kundli API, or omit and send the female birth fields.",
    )
    male_dob: str | None = Field(None, examples=["1998-04-10"])
    male_tob: str | None = Field(None, examples=["17:25"])
    male_location: str | None = Field(None, examples=["Hubli, Karnataka"])
    female_dob: str | None = Field(None, examples=["1990-04-02"])
    female_tob: str | None = Field(None, examples=["06:30"])
    female_location: str | None = Field(None, examples=["Gadag, Karnataka"])


class AshtakavargaBody(BaseModel):
    natal_chart: dict[str, Any] | None = Field(
        None,
        description="Dict from the Kundli API. Omit it to send dob, tob, and location.",
    )
    dob: str | None = Field(None, examples=["1998-04-10"])
    tob: str | None = Field(None, examples=["17:25"])
    location: str | None = Field(None, examples=["Hubli, Karnataka"])
    target_date: str | None = Field(
        None,
        examples=["2026-10-15"],
        description="Optional civil date for transit_filter_status.",
    )
    target_time: str = Field("12:00", examples=["09:00"])


class PanchangaBody(BaseModel):
    date: str = Field(examples=["2026-10-15"], description="Civil date, YYYY-MM-DD.")
    at_time: str | None = Field(
        None,
        examples=["09:00"],
        description="Local HH:MM. A time before sunrise uses the previous solar day.",
    )
    location: str | None = Field(
        None,
        examples=["Gadag, Karnataka"],
        description="Observer place. Rahu Kaalam is computed here, not at a fixed clock.",
    )
    latitude: float | None = Field(None, examples=[15.4316])
    longitude: float | None = Field(None, examples=[75.635])
    elevation_m: float | None = Field(
        None,
        examples=[648],
        description="Meters above sea level. Looked up when omitted.",
    )
    timezone_name: str | None = Field(None, examples=["Asia/Kolkata"])
    natal_chart: dict[str, Any] | None = Field(
        None,
        description="Used for the observer place when location and coordinates are omitted.",
    )
    dob: str | None = Field(None, examples=["1990-04-02"])
    tob: str | None = Field(None, examples=["06:30"])
    birth_location: str | None = Field(None, examples=["Gadag, Karnataka"])


class SaturnCycleBody(BaseModel):
    as_of_date: str = Field(examples=["2026-10-07"], description="Civil date, YYYY-MM-DD.")
    as_of_time: str = Field("09:00", examples=["09:00"], description="Local time HH:MM.")
    natal_chart: dict[str, Any] | None = Field(None)
    dob: str | None = Field(None, examples=["1990-04-02"])
    tob: str | None = Field(None, examples=["06:30"])
    location: str | None = Field(None, examples=["Gadag, Karnataka"])


def _failure(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _documented_app(title: str, description: str, prefix: str) -> FastAPI:
    api = FastAPI(
        title=title,
        description=description,
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
    )

    @api.get("/docs", include_in_schema=False)
    def swagger() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url=f"{prefix}/openapi.json", title=title)

    @api.get("/redoc", include_in_schema=False)
    def redoc() -> HTMLResponse:
        return get_redoc_html(openapi_url=f"{prefix}/openapi.json", title=title)

    @api.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok", "api": title}

    return api


KUNDLI_DESCRIPTION = """
Sidereal Lahiri natal chart from a birth date, time, and place.

Send `POST /chart` with `dob`, `tob`, and `location`. The body that comes back
is the `natal_chart` the Timing and Forecast APIs accept.

The chart uses whole-sign houses, the mean lunar node, Parashari `aspected_houses`,
combustion orbs, and graha yuddha within 1°. Geocoding needs network access to
Nominatim. Ambiguous and nonexistent civil times are rejected.
""".strip()

TIMING_DESCRIPTION = """
Vimshottari mahadasha, antardasha, and pratyantardasha, plus Lahiri gochara
from the natal lagna and the natal Moon, and the daily Tara Bala and Chandrashtama flags.

Send the Kundli API object as `natal_chart`, or send `dob`, `tob`, and `location`
and this API will calculate the chart first. `target_date` is YYYY-MM-DD in the
natal timezone. Dasha years are 365.2425 days, and the birth mahadasha includes
the portion already elapsed at birth.

When `is_chandrashtama` is true, treat the day as a poor window for contracts
and high-risk decisions. When Mercury is combust, treat intellectual and
partnership decisions with caution.
""".strip()

FORECAST_DESCRIPTION = """
A short timeline across consecutive civil dates. Each row has the dasha string,
whether it changed from the previous day, the transit Moon, Tara Bala, and risk flags.
It does not repeat the full nine-graha state.

`critical_windows` lists Chandrashtama, Vipat/Naidhana, Sadhana, and transit combustion.
`major_transits` lists Jupiter, Saturn, Rahu, and Ketu once, plus any sign change
inside the window. `dasha_transition: true` is an inflection day. Each timeline
row includes `daily_panchanga` for the birthplace: topocentric sunrise and sunset,
the panchanga limbs at sunrise, and Rahu, Yamaganda, and Gulika.

For a month outlook, keep `critical_windows` and `major_transits`. For one day,
take that single `timeline` row and call the Timing API for the degrees.
""".strip()

COMPATIBILITY_DESCRIPTION = """
36-guna Ashtakoota Milan for one groom and one bride, plus Manglik dosha from
both the lagna and the Moon, and 7th-house synastry.

Send `male_chart` and `female_chart` from the Kundli API, or send birth fields
for each person. Varna and Gana are not symmetric, so do not swap the two people.
A score of 30/36 is not enough when Nadi dosha is active or only one chart has
an uncancelled Manglik dosha.
""".strip()

ASHTAKAVARGA_DESCRIPTION = """
Bhinnashtakavarga (0–8 bindus per sign for each of the seven grahas) and
Sarvashtakavarga (0–56 per sign, mean 28). A transit in a sign with 32 or more
SAV bindus is protected even in a hard house. A transit in a sign with 24 or
fewer bindus is weak even in a good house.

Send a natal chart or birth details. Add `target_date` to score Jupiter, Saturn,
Rahu, and Ketu against the natal SAV of the signs they occupy.
""".strip()

kundli_api = _documented_app("Kundli API", KUNDLI_DESCRIPTION, "/kundli")
timing_api = _documented_app("Timing API", TIMING_DESCRIPTION, "/timing")
forecast_api = _documented_app("Forecast API", FORECAST_DESCRIPTION, "/forecast")
compatibility_api = _documented_app(
    "Compatibility API", COMPATIBILITY_DESCRIPTION, "/compatibility"
)
ashtakavarga_api = _documented_app(
    "Ashtakavarga API", ASHTAKAVARGA_DESCRIPTION, "/ashtakavarga"
)
SATURN_DESCRIPTION = """
Sade Sati (Saturn in the 12th, 1st, and 2nd from the natal Moon), Kantaka Shani
(4th from the natal Moon or the natal lagna), and Ashtama Shani (8th from the
natal Moon). Dates are sidereal ingresses. A retrograde return to the same sign
stays inside one passage.
""".strip()
saturn_api = _documented_app("Saturn Cycle API", SATURN_DESCRIPTION, "/saturn-cycles")
PANCHANGA_DESCRIPTION = """
Local panchanga for one solar day, and the three daytime windows used to avoid
starting work: Rahu Kaalam, Yamaganda, and Gulika Kaalam.

Sunrise and sunset are topocentric. Swiss Ephemeris `rise_trans` uses the
observer latitude, longitude, and elevation, with refraction estimated from
that height. The weekday is the weekday of sunrise, not of civil midnight.
Tithi, nakshatra, yoga, and karana are Lahiri positions of the Sun and Moon
at that sunrise. Rikta tithis are 4, 9, and 14 in either paksha. Vyatipata and
Vaidhriti are the malefic yogas. Vishti is Bhadra.

The daylight arc is split into eight equal parts. The windows move between
North and South India because sunrise moves. Do not replace them with a fixed
1:30–3:00 style clock.

Send `location` for the place where the action happens, or `latitude`,
`longitude`, and optional `elevation_m`. A natal chart or birth fields are
used only when no observer place is sent. `at_time` before sunrise selects
the previous solar day.
""".strip()
panchanga_api = _documented_app("Panchanga API", PANCHANGA_DESCRIPTION, "/panchanga")


@kundli_api.post(
    "/chart",
    summary="Calculate a natal Kundli",
    response_description="Natal chart with metadata, lagna, nine grahas, and twelve houses.",
)
def kundli_chart(body: BirthBody) -> dict[str, Any]:
    try:
        return build_kundli(body.dob, body.tob, body.location)
    except ValueError as exc:
        raise _failure(exc) from exc


@timing_api.post(
    "/telemetry",
    summary="Dasha, transits, and the lunar trigger",
    response_description="Target timestamp, active dasha, nine transits, and daily lunar trigger.",
)
def timing_telemetry(body: TimingBody) -> dict[str, Any]:
    try:
        return build_timing(
            body.target_date,
            body.target_time,
            body.natal_chart,
            body.dob,
            body.tob,
            body.location,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


@forecast_api.post(
    "/window",
    summary="Multi-day forecast timeline",
    response_description="Critical windows, major transits, and one concise row per day.",
)
def forecast_window(body: ForecastBody) -> dict[str, Any]:
    try:
        return build_forecast(
            body.start_date,
            body.days,
            body.time,
            body.natal_chart,
            body.dob,
            body.tob,
            body.location,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


@compatibility_api.post(
    "/match",
    summary="Ashtakoota, Manglik, and 7th-house synastry",
    response_description="Guna breakdown, Manglik analysis, dosha flags, and 7th-house synastry.",
)
def compatibility_match(body: CompatibilityBody) -> dict[str, Any]:
    try:
        return build_compatibility(
            body.male_chart,
            body.female_chart,
            body.male_dob,
            body.male_tob,
            body.male_location,
            body.female_dob,
            body.female_tob,
            body.female_location,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


@ashtakavarga_api.post(
    "/bindus",
    summary="Bhinnashtakavarga, Sarvashtakavarga, and transit potency",
    response_description="SAV per sign, BAV per graha, and optional transit_filter_status.",
)
def ashtakavarga_bindus(body: AshtakavargaBody) -> dict[str, Any]:
    try:
        return build_ashtakavarga(
            body.natal_chart,
            body.dob,
            body.tob,
            body.location,
            body.target_date,
            body.target_time,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


@panchanga_api.post(
    "/day",
    summary="Sunrise panchanga and Rahu, Yamaganda, Gulika",
    response_description="Topocentric solar day, five limbs, and three inauspicious windows.",
)
def panchanga_day(body: PanchangaBody) -> dict[str, Any]:
    try:
        return build_panchanga(
            body.date,
            body.at_time,
            body.location,
            body.latitude,
            body.longitude,
            body.elevation_m,
            body.timezone_name,
            body.natal_chart,
            body.dob,
            body.tob,
            body.birth_location,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


@saturn_api.post(
    "/track",
    summary="Sade Sati, Kantaka Shani, and Ashtama Shani",
    response_description="Active phase, past passages, and the next ingress.",
)
def saturn_track(body: SaturnCycleBody) -> dict[str, Any]:
    try:
        return build_saturn_cycles(
            body.as_of_date,
            body.as_of_time,
            body.natal_chart,
            body.dob,
            body.tob,
            body.location,
        )
    except ValueError as exc:
        raise _failure(exc) from exc


def connection_card(host: str = "127.0.0.1") -> dict[str, Any]:
    """URLs a browser or an MCP client uses on this machine."""
    return {
        "swagger": {
            "kundli": f"http://{host}:{API_PORT}/kundli/docs",
            "timing": f"http://{host}:{API_PORT}/timing/docs",
            "forecast": f"http://{host}:{API_PORT}/forecast/docs",
            "compatibility": f"http://{host}:{API_PORT}/compatibility/docs",
            "ashtakavarga": f"http://{host}:{API_PORT}/ashtakavarga/docs",
            "saturn_cycles": f"http://{host}:{API_PORT}/saturn-cycles/docs",
            "panchanga": f"http://{host}:{API_PORT}/panchanga/docs",
        },
        "openapi": {
            "kundli": f"http://{host}:{API_PORT}/kundli/openapi.json",
            "timing": f"http://{host}:{API_PORT}/timing/openapi.json",
            "forecast": f"http://{host}:{API_PORT}/forecast/openapi.json",
            "compatibility": f"http://{host}:{API_PORT}/compatibility/openapi.json",
            "ashtakavarga": f"http://{host}:{API_PORT}/ashtakavarga/openapi.json",
            "saturn_cycles": f"http://{host}:{API_PORT}/saturn-cycles/openapi.json",
            "panchanga": f"http://{host}:{API_PORT}/panchanga/openapi.json",
        },
        "mcp": {
            "kundli": f"http://{host}:{KUNDLI_MCP_PORT}/mcp",
            "timing": f"http://{host}:{TIMING_MCP_PORT}/mcp",
            "forecast": f"http://{host}:{FORECAST_MCP_PORT}/mcp",
            "compatibility": f"http://{host}:{COMPATIBILITY_MCP_PORT}/mcp",
            "ashtakavarga": f"http://{host}:{ASHTAKAVARGA_MCP_PORT}/mcp",
            "saturn_cycles": f"http://{host}:{SATURN_MCP_PORT}/mcp",
            "panchanga": f"http://{host}:{PANCHANGA_MCP_PORT}/mcp",
        },
    }


app = FastAPI(
    title="Jyotish telemetry",
    description="Index for the Kundli, Timing, and Forecast APIs.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
for mounted in (
    kundli_api,
    timing_api,
    forecast_api,
    compatibility_api,
    ashtakavarga_api,
    saturn_api,
    panchanga_api,
):
    mounted.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/kundli", kundli_api)
app.mount("/timing", timing_api)
app.mount("/forecast", forecast_api)
app.mount("/compatibility", compatibility_api)
app.mount("/ashtakavarga", ashtakavarga_api)
app.mount("/saturn-cycles", saturn_api)
app.mount("/panchanga", panchanga_api)


@app.get("/health", include_in_schema=False)
def root_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/connections", include_in_schema=False)
def connections() -> dict[str, Any]:
    return connection_card()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    card = connection_card()
    labels = {
        "kundli": "Kundli",
        "timing": "Timing",
        "forecast": "Forecast",
        "compatibility": "Compatibility",
        "ashtakavarga": "Ashtakavarga",
        "saturn_cycles": "Saturn cycles",
        "panchanga": "Panchanga",
    }
    rows = []
    for name, url in card["swagger"].items():
        rows.append(f"<li><a href=\"{url}\">{labels[name]} Swagger</a></li>")
    mcp_rows = "".join(f"<li><code>{name}</code> {url}</li>" for name, url in card["mcp"].items())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Jyotish telemetry</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 42rem; margin: 2.5rem auto; padding: 0 1rem;
           color: #1c1917; background: #fffdf7; }}
    code {{ font-family: ui-monospace, monospace; }}
    a {{ color: #7f1d1d; }}
  </style>
</head>
<body>
  <h1>Jyotish telemetry</h1>
  <p>Seven HTTP APIs, from the natal chart through the local panchanga.</p>
  <ul>
    {''.join(rows)}
  </ul>
  <h2>MCP endpoints</h2>
  <ul>{mcp_rows}</ul>
  <p>Machine-readable URLs are at <a href="/connections"><code>/connections</code></a>.</p>
</body>
</html>"""
