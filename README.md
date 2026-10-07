# North Indian Lagna Kundli

Deterministic Python program that builds a traditional North Indian (diamond) Lagna Kundli PNG from a birth date, time, and place.

The chart uses:

- Nominatim for geocoding
- TimezoneFinder plus IANA `zoneinfo` for the historical civil timezone, including DST
- Swiss Ephemeris (Lahiri sidereal mode) for the ascendant and grahas
- Whole-sign houses
- Matplotlib for a high-resolution PNG

Planetary positions use the built-in Moshier ephemeris shipped with Swiss Ephemeris (`FLG_MOSEPH`). That keeps results reproducible after a normal dependency install, without a separate ephemeris-file download. Lahiri ayanamsa still comes from Swiss Ephemeris.

## Requirements

Python 3.9 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the built-in example

```bash
python kundli.py
```

This writes `kundli_example.png` for 15 January 1990, 14:30, Bengaluru, India.

## Run with birth details

```bash
python kundli.py \
  --dob 1990-01-15 \
  --tob 14:30 \
  --location "Bengaluru, India" \
  --output_file kundli.png
```

## JSON

`get_kundli_json` uses the same calculation as the PNG. It returns a Python dict by default, so the chart can be passed to `get_timing_telemetry` without encoding it again. Pass `as_string=True` for indented JSON. The payload has birth metadata, lagna, nine grahas, and twelve whole-sign houses. Rahu is the mean node.

Each graha includes `is_combust`, `is_in_graha_yuddha`, and `aspected_houses`. Combustion uses the short arc from the Sun: Moon 12°, Mars 17°, Mercury 14° (12° when retrograde), Jupiter 11°, Venus 10° (8° when retrograde), and Saturn 15°. Planetary war is two of Mars, Mercury, Jupiter, Venus, and Saturn within 1°. Aspects are Parashari: every graha aspects the 7th; Mars also the 4th and 8th; Jupiter, Rahu, and Ketu also the 5th and 9th; Saturn also the 3rd and 10th.

```python
import json
from kundli import get_kundli_json

chart = get_kundli_json("1990-04-02", "06:30", "Gadag, Karnataka")
print(json.dumps(chart, indent=2))
```

## Timing telemetry

`get_timing_telemetry` reads that natal JSON (a dict or a JSON string) and a target civil date in the natal timezone. It returns the active Vimshottari mahadasha, antardasha, and pratyantardasha, Lahiri gochara for all nine grahas measured from both the natal lagna and the natal Moon, and the daily lunar trigger (Tara Bala and Chandrashtama).

Dasha lengths use the mean tropical year of 365.2425 days. The birth mahadasha is already partly elapsed by the Moon's position inside its nakshatra. That consumed span is added to the time since birth before antardasha and pratyantardasha are resolved. Rahu is the mean node and Ketu is opposite Rahu. When `is_chandrashtama` is true, the transit Moon is in the 8th house from the natal Moon. When Mercury is combust, including a separation under 7°, treat intellectual and partnership decisions with caution even if the dasha lords are favorable.

```python
import json
from kundli import get_kundli_json, get_timing_telemetry

natal = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
timing = get_timing_telemetry(natal, "2026-10-15", "09:00")
print(json.dumps(timing, indent=2))
```

## Forecast window

`generate_forecast_window` walks consecutive civil dates at one local time and returns a short timeline. Each day has the dasha string, whether that string changed from the previous day, the transit Moon, Tara Bala, and risk flags. Chandrashtama, Vipat, Naidhana, and transit combustion are collected under `critical_windows`. Jupiter, Saturn, Rahu, and Ketu are listed once in `major_transits`, with any sign change inside the window.

For a month outlook, pass the natal chart, `critical_windows`, and `major_transits`. For one day, pass that single `timeline` row plus the natal chart and that day's transit degrees from `get_timing_telemetry`. Highlight dates where `dasha_transition` is true.

```python
import json
from kundli import generate_forecast_window, get_kundli_json

natal = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
forecast = generate_forecast_window(natal, "2026-10-01", days=30)
print(json.dumps(forecast["critical_windows"], indent=2))
```

## Use as a library

```python
from kundli import generate_kundli_chart

path = generate_kundli_chart(
    "1990-01-15",
    "14:30",
    "Bengaluru, India",
    "kundli.png",
)
```

Geocoding needs network access to OpenStreetMap Nominatim. The program does not substitute coordinates or UTC when lookup fails.

## Compatibility

`get_compatibility_json` takes two charts from `get_kundli_json`. It scores the 36-guna Ashtakoota, Manglik dosha from both lagna and Moon, and 7th-house synastry. Varna and Gana use the groom as `male_chart` and the bride as `female_chart`. Swapping them can change the score.

```python
from kundli import get_compatibility_json, get_kundli_json

groom = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
bride = get_kundli_json("1990-04-02", "06:30", "Gadag, Karnataka")
print(get_compatibility_json(groom, bride, as_string=True))
```

## Ashtakavarga

`get_ashtakavarga_json` scores Bhinnashtakavarga (0–8 bindus per sign for each of the seven grahas) and Sarvashtakavarga (0–56 per sign, mean 28). Natal JSON, timing telemetry, and the forecast window all include these tables. A transit is not judged by house from lagna or Moon alone: SAV of 32 or more protects the occupied sign; SAV of 24 or fewer is weak even in a good house.

```python
from kundli import get_ashtakavarga_json, get_kundli_json, get_timing_telemetry

natal = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
timing = get_timing_telemetry(natal, "2026-10-15", "09:00")
print(timing["ashtakavarga"]["transit_filter_status"])
```

## Saturn cycles

`get_saturn_cycles` reads Lahiri Saturn sign passages from `data/saturn_sign_passages.json` (1880–2180 UTC) and maps them onto the natal Moon and lagna. A request does not search the ephemeris. Rebuild the table with `python -m saturn_cycles` only when the ayanamsa or the covered range changes.

Sade Sati is Saturn in the 12th, 1st, or 2nd from the natal Moon. Each of those blocks, plus Ashtama Shani and Kantaka Shani, returns `current_status` and `next_ingress_date`. A retrograde return to the same sign stays inside one passage, so a Rising end date is not forced to equal the Peak start date.

```python
from kundli import get_kundli_json, get_saturn_cycles

natal = get_kundli_json("1990-04-02", "06:30", "Gadag, Karnataka")
print(get_saturn_cycles(natal, "2026-10-07", "09:00")["sade_sati"]["next_ingress_date"])
```

## Panchanga

`get_daily_panchanga` takes the observer's latitude, longitude, and elevation. Sunrise and sunset come from Swiss Ephemeris `rise_trans` at that point, with refraction estimated from the height. Tithi, nakshatra, yoga, and karana are Lahiri positions at sunrise. The weekday is the weekday of sunrise.

Rahu Kaalam, Yamaganda, and Gulika Kaalam are eighths of that sunrise-to-sunset arc and stop at sunset. A clock time such as 13:30–15:00 is only the Thursday Rahu window of a 06:00–18:00 day. Pass the place where the action happens.

`attributes` are the sunrise limbs. `at_time` adds `instant` tithi and karana at that clock. 03:30 on a Friday civil date is still Thursday when sunrise is later that morning.

```python
from panchanga import get_daily_panchanga

gadag = get_daily_panchanga("2026-10-15", location="Gadag, Karnataka")
print(gadag["daily_panchanga"]["inauspicious_windows"]["rahu_kaalam"])
```

## HTTP APIs and MCP servers

Seven HTTP APIs and seven MCP servers call the same functions. One Docker image runs all of them.

| Service | What it calls | Swagger | MCP endpoint |
| --- | --- | --- | --- |
| Kundli | `get_kundli_json` | http://127.0.0.1:8741/kundli/docs | http://127.0.0.1:8742/mcp |
| Timing | `get_timing_telemetry` | http://127.0.0.1:8741/timing/docs | http://127.0.0.1:8743/mcp |
| Forecast | `generate_forecast_window` | http://127.0.0.1:8741/forecast/docs | http://127.0.0.1:8744/mcp |
| Compatibility | `get_compatibility_json` | http://127.0.0.1:8741/compatibility/docs | http://127.0.0.1:8745/mcp |
| Ashtakavarga | `get_ashtakavarga_json` | http://127.0.0.1:8741/ashtakavarga/docs | http://127.0.0.1:8746/mcp |
| Saturn cycles | `get_saturn_cycles` | http://127.0.0.1:8741/saturn-cycles/docs | http://127.0.0.1:8747/mcp |
| Panchanga | `get_daily_panchanga` | http://127.0.0.1:8741/panchanga/docs | http://127.0.0.1:8748/mcp |

OpenAPI documents are on port 8741 at `/kundli/openapi.json`, `/timing/openapi.json`, `/forecast/openapi.json`, `/compatibility/openapi.json`, `/ashtakavarga/openapi.json`, `/saturn-cycles/openapi.json`, and `/panchanga/openapi.json`. ReDoc is the same path with `/redoc` instead of `/docs`. The index is at http://127.0.0.1:8741/ and JSON URLs are at http://127.0.0.1:8741/connections.

### Run with Docker

```bash
docker compose up --build
```

The API container listens on 8741. The MCP containers listen on 8742–8748. Each container has a `GET /health` check. Chart calls need outbound access to OpenStreetMap Nominatim. Panchanga looks up elevation from Open-Meteo when `elevation_m` is omitted.

One container can run every process instead of Compose:

```bash
docker build -t jyotish-telemetry .
docker run --rm -p 8741:8741 -p 8742:8742 -p 8743:8743 -p 8744:8744 -p 8745:8745 -p 8746:8746 -p 8747:8747 -p 8748:8748 jyotish-telemetry
```

### Run without Docker

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn jyotish_api.main:app --host 0.0.0.0 --port 8741
MCP_PORT=8742 python -m mcp_servers.kundli_server
MCP_PORT=8743 python -m mcp_servers.timing_server
MCP_PORT=8744 python -m mcp_servers.forecast_server
MCP_PORT=8745 python -m mcp_servers.compatibility_server
MCP_PORT=8746 python -m mcp_servers.ashtakavarga_server
MCP_PORT=8747 python -m mcp_servers.saturn_server
MCP_PORT=8748 python -m mcp_servers.panchanga_server
```

Start each process in its own terminal. `MCP_HOST` defaults to `0.0.0.0`.

### Swagger calls

Kundli, `POST /kundli/chart`:

```json
{
  "dob": "1998-04-10",
  "tob": "17:25",
  "location": "Hubli, Karnataka"
}
```

Timing, `POST /timing/telemetry`. Pass the Kundli response as `natal_chart`, or send birth details and the API calculates the chart:

```json
{
  "dob": "1998-04-10",
  "tob": "17:25",
  "location": "Hubli, Karnataka",
  "target_date": "2026-10-15",
  "target_time": "09:00"
}
```

Forecast, `POST /forecast/window`:

```json
{
  "dob": "1998-04-10",
  "tob": "17:25",
  "location": "Hubli, Karnataka",
  "start_date": "2026-10-01",
  "days": 30,
  "time": "09:00"
}
```

Compatibility, `POST /compatibility/match`. The groom is the male chart and the bride is the female chart:

```json
{
  "male_dob": "1998-04-10",
  "male_tob": "17:25",
  "male_location": "Hubli, Karnataka",
  "female_dob": "1990-04-02",
  "female_tob": "06:30",
  "female_location": "Gadag, Karnataka"
}
```

Ashtakavarga, `POST /ashtakavarga/bindus`:

```json
{
  "dob": "1998-04-10",
  "tob": "17:25",
  "location": "Hubli, Karnataka",
  "target_date": "2026-10-15",
  "target_time": "09:00"
}
```

Panchanga, `POST /panchanga/day`. `location` is where the action happens:

```json
{
  "date": "2026-10-15",
  "location": "Gadag, Karnataka"
}
```

A bad date, an unknown place, or a daylight-saving gap returns HTTP 400 with the validation message in `detail`.

For a month outlook, send a model the natal chart, `critical_windows`, and `major_transits`. For one day, send that `timeline` row plus the Timing API degrees. Treat `dasha_transition: true` as the day the period changes.

### MCP client configuration

The servers speak streamable HTTP at `/mcp` and answer JSON. In Cursor, add this to the MCP settings:

```json
{
  "mcpServers": {
    "jyotish-kundli": {
      "type": "http",
      "url": "http://127.0.0.1:8742/mcp"
    },
    "jyotish-timing": {
      "type": "http",
      "url": "http://127.0.0.1:8743/mcp"
    },
    "jyotish-forecast": {
      "type": "http",
      "url": "http://127.0.0.1:8744/mcp"
    },
    "jyotish-compatibility": {
      "type": "http",
      "url": "http://127.0.0.1:8745/mcp"
    },
    "jyotish-ashtakavarga": {
      "type": "http",
      "url": "http://127.0.0.1:8746/mcp"
    },
    "jyotish-saturn": {
      "type": "http",
      "url": "http://127.0.0.1:8747/mcp"
    },
    "jyotish-panchanga": {
      "type": "http",
      "url": "http://127.0.0.1:8748/mcp"
    }
  }
}
```

| MCP server | Tool | Required arguments |
| --- | --- | --- |
| jyotish-kundli | `get_kundli_json` | `dob`, `tob`, `location` |
| jyotish-timing | `get_timing_telemetry` | `target_date`. Also `natal_chart`, or `dob` + `tob` + `location`. `target_time` defaults to `12:00`. |
| jyotish-forecast | `generate_forecast_window` | `start_date`. Also `natal_chart`, or `dob` + `tob` + `location`. `days` defaults to 30 and `time` defaults to `09:00`. |
| jyotish-compatibility | `get_compatibility_json` | `male_chart` and `female_chart`, or birth fields for each person. |
| jyotish-ashtakavarga | `get_ashtakavarga_json` | `natal_chart`, or `dob` + `tob` + `location`. `target_date` is optional. |
| jyotish-saturn | `get_saturn_cycles` | `as_of_date`. Also `natal_chart`, or `dob` + `tob` + `location`. `as_of_time` defaults to `09:00`. |
| jyotish-panchanga | `get_daily_panchanga` | `date`. Also `location`, or `latitude` + `longitude`, or a natal chart. |

Health checks for the MCP processes are `GET http://127.0.0.1:8742/health` through `GET http://127.0.0.1:8746/health`. Those routes are not MCP tools.
