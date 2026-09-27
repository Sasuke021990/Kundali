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

## HTTP APIs and MCP servers

Three HTTP APIs and three MCP servers call the same functions. One Docker image runs all of them.

| Service | What it calls | Swagger | MCP endpoint |
| --- | --- | --- | --- |
| Kundli | `get_kundli_json` | http://127.0.0.1:8741/kundli/docs | http://127.0.0.1:8742/mcp |
| Timing | `get_timing_telemetry` | http://127.0.0.1:8741/timing/docs | http://127.0.0.1:8743/mcp |
| Forecast | `generate_forecast_window` | http://127.0.0.1:8741/forecast/docs | http://127.0.0.1:8744/mcp |

OpenAPI documents, without the Swagger UI, are at `/kundli/openapi.json`, `/timing/openapi.json`, and `/forecast/openapi.json` on port 8741. ReDoc for each API is the same path with `/redoc` instead of `/docs`. A short index of these URLs is at http://127.0.0.1:8741/ and the same data as JSON is at http://127.0.0.1:8741/connections.

### Run with Docker

```bash
docker compose up --build
```

The API container listens on 8741. The Kundli, Timing, and Forecast MCP containers listen on 8742, 8743, and 8744. Each container has a `GET /health` check. The chart calls need outbound access to OpenStreetMap Nominatim.

One container can run every process instead of Compose:

```bash
docker build -t jyotish-telemetry .
docker run --rm -p 8741:8741 -p 8742:8742 -p 8743:8743 -p 8744:8744 jyotish-telemetry
```

### Run without Docker

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn jyotish_api.main:app --host 0.0.0.0 --port 8741
MCP_PORT=8742 python -m mcp_servers.kundli_server
MCP_PORT=8743 python -m mcp_servers.timing_server
MCP_PORT=8744 python -m mcp_servers.forecast_server
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
    }
  }
}
```

| MCP server | Tool | Required arguments |
| --- | --- | --- |
| jyotish-kundli | `get_kundli_json` | `dob`, `tob`, `location` |
| jyotish-timing | `get_timing_telemetry` | `target_date`. Also `natal_chart`, or `dob` + `tob` + `location`. `target_time` defaults to `12:00`. |
| jyotish-forecast | `generate_forecast_window` | `start_date`. Also `natal_chart`, or `dob` + `tob` + `location`. `days` defaults to 30 and `time` defaults to `09:00`. |

Health checks for the MCP processes are `GET http://127.0.0.1:8742/health`, `GET http://127.0.0.1:8743/health`, and `GET http://127.0.0.1:8744/health`. Those routes are not MCP tools.
