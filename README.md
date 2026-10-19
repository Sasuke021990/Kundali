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

`solar_day.sunrise_current` and `solar_day.sunrise_next` are full ISO-8601 timestamps. `instant.is_current_solar_day` is true when the event falls in that half-open range. `at_time` adds tithi, karana, and `active_inauspicious_window`. Outside the daytime arc, `daytime_kaalam_active` and `is_favorable_for_action` are null.

```python
from panchanga import get_daily_panchanga

gadag = get_daily_panchanga("2026-10-15", location="Gadag, Karnataka")
print(gadag["daily_panchanga"]["inauspicious_windows"]["rahu_kaalam"])
```

## Navamsha

`get_navamsha_json` divides each natal longitude into navamshas of 3°20' without calling the ephemeris. Fire signs start at Aries, earth at Capricorn, air at Libra, and water at Cancer. The same sign in D1 and D9 is Vargottama. Debilitation in D9 is neecha navamsha. Pushkara parts are fire 7 and 9, earth 3 and 5, air 6 and 8, and water 2 and 4.

```python
from kundli import get_kundli_json

chart = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
print(chart["navamsha_d9"]["planets"]["Jupiter"])
```

## HTTP APIs and MCP servers

`FUNCTIONS.md` is the AI call map: every public function, the fields it returns, and which key to read. Curl examples for the same routes are below.

Eight HTTP APIs and eight MCP servers call the same functions. One Docker image runs all of them. Dates are `YYYY-MM-DD`. Times are 24-hour `HH:MM` unless a service also accepts `HH:MM:SS`. A bad date, an unknown place, or a daylight-saving gap returns HTTP 400 with the message in `detail`.

Chart calls need outbound access to OpenStreetMap Nominatim. Panchanga looks up elevation from Open-Meteo when `elevation_m` is omitted. Saturn ingresses are read from `data/saturn_sign_passages.json`. Navamsha does not call the ephemeris again.

The index is http://127.0.0.1:8741/. Machine-readable URLs are at http://127.0.0.1:8741/connections. Each API also serves `/redoc` and `/openapi.json` on the same prefix as `/docs`. Each process, including every MCP server, answers `GET /health`.

| Service | Python function | POST | Swagger | OpenAPI | MCP server | MCP tool | MCP endpoint |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Kundli | `get_kundli_json` | `/kundli/chart` | http://127.0.0.1:8741/kundli/docs | http://127.0.0.1:8741/kundli/openapi.json | `jyotish-kundli` | `get_kundli_json` | http://127.0.0.1:8742/mcp |
| Timing | `get_timing_telemetry` | `/timing/telemetry` | http://127.0.0.1:8741/timing/docs | http://127.0.0.1:8741/timing/openapi.json | `jyotish-timing` | `get_timing_telemetry` | http://127.0.0.1:8743/mcp |
| Forecast | `generate_forecast_window` | `/forecast/window` | http://127.0.0.1:8741/forecast/docs | http://127.0.0.1:8741/forecast/openapi.json | `jyotish-forecast` | `generate_forecast_window` | http://127.0.0.1:8744/mcp |
| Compatibility | `get_compatibility_json` | `/compatibility/match` | http://127.0.0.1:8741/compatibility/docs | http://127.0.0.1:8741/compatibility/openapi.json | `jyotish-compatibility` | `get_compatibility_json` | http://127.0.0.1:8745/mcp |
| Ashtakavarga | `get_ashtakavarga_json` | `/ashtakavarga/bindus` | http://127.0.0.1:8741/ashtakavarga/docs | http://127.0.0.1:8741/ashtakavarga/openapi.json | `jyotish-ashtakavarga` | `get_ashtakavarga_json` | http://127.0.0.1:8746/mcp |
| Saturn cycles | `get_saturn_cycles` | `/saturn-cycles/track` | http://127.0.0.1:8741/saturn-cycles/docs | http://127.0.0.1:8741/saturn-cycles/openapi.json | `jyotish-saturn` | `get_saturn_cycles` | http://127.0.0.1:8747/mcp |
| Panchanga | `get_daily_panchanga` | `/panchanga/day` | http://127.0.0.1:8741/panchanga/docs | http://127.0.0.1:8741/panchanga/openapi.json | `jyotish-panchanga` | `get_daily_panchanga` | http://127.0.0.1:8748/mcp |
| Navamsha | `get_navamsha_json` | `/navamsha/chart` | http://127.0.0.1:8741/navamsha/docs | http://127.0.0.1:8741/navamsha/openapi.json | `jyotish-navamsha` | `get_navamsha_json` | http://127.0.0.1:8749/mcp |

Where a service accepts a chart, send the Kundli response as `natal_chart`, or omit it and send `dob`, `tob`, and `location`. Compatibility uses `male_chart` and `female_chart`, or `male_dob` / `male_tob` / `male_location` and `female_dob` / `female_tob` / `female_location`. Panchanga uses `birth_location` for that fallback, because `location` is the place of the action.

### Run with Docker

```bash
docker compose up --build
```

The API container listens on 8741. The MCP containers listen on 8742–8749.

One container can run every process instead of Compose:

```bash
docker build -t jyotish-telemetry .
docker run --rm -p 8741:8741 -p 8742:8742 -p 8743:8743 -p 8744:8744 -p 8745:8745 -p 8746:8746 -p 8747:8747 -p 8748:8748 -p 8749:8749 jyotish-telemetry
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
MCP_PORT=8749 python -m mcp_servers.navamsha_server
```

Start each process in its own terminal. `MCP_HOST` defaults to `0.0.0.0`.

### Cursor MCP configuration

The servers speak streamable HTTP at `/mcp` and answer JSON. Add this to Cursor MCP settings:

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
    },
    "jyotish-navamsha": {
      "type": "http",
      "url": "http://127.0.0.1:8749/mcp"
    }
  }
}
```

Health checks are `GET http://127.0.0.1:8742/health` through `GET http://127.0.0.1:8749/health`. Those routes are not MCP tools.

### Kundli

Lahiri natal chart: metadata, lagna, nine grahas, twelve whole-sign houses, Ashtakavarga, and Navamsha.

| Field | Required | Meaning |
| --- | --- | --- |
| `dob` | yes | Birth date, `YYYY-MM-DD`. |
| `tob` | yes | Local birth time, `HH:MM`. |
| `location` | yes | Place name, geocoded with Nominatim. |

```bash
curl -s http://127.0.0.1:8741/kundli/chart \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka"}'
```

The response includes `metadata` (place, coordinates, timezone, UTC instant, Lahiri ayanamsa), `lagna`, `planets`, `houses`, `ashtakavarga`, and `navamsha_d9`. Save this object and pass it as `natal_chart` to the other APIs.

MCP tool `get_kundli_json` on port 8742 takes the same three arguments: `dob`, `tob`, `location`.

### Timing

Vimshottari mahadasha, antardasha, and pratyantardasha, Lahiri gochara from lagna and Moon, Tara Bala, Chandrashtama, Ashtakavarga, and Saturn cycles at one local time.

| Field | Required | Meaning |
| --- | --- | --- |
| `target_date` | yes | Civil date in the natal timezone. |
| `target_time` | no | Local `HH:MM`. Default `12:00`. |
| `natal_chart` | one of these | Kundli response. |
| `dob`, `tob`, `location` | one of these | Birth details, if `natal_chart` is omitted. |

```bash
curl -s http://127.0.0.1:8741/timing/telemetry \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka","target_date":"2026-10-15","target_time":"09:00"}'
```

Read `active_dasha.active_period_string`, `transits`, `daily_lunar_trigger.is_chandrashtama`, and `daily_lunar_trigger.tara_bala`. `is_chandrashtama: true` means the transit Moon is in the 8th from the natal Moon.

MCP tool `get_timing_telemetry` on port 8743 takes `target_date`, optional `target_time`, and either `natal_chart` or `dob`, `tob`, and `location`.

### Forecast

One row per civil date: dasha string, whether it changed, transit Moon, Tara Bala, risk flags, and that day's panchanga at the birthplace.

| Field | Required | Meaning |
| --- | --- | --- |
| `start_date` | yes | First civil date. |
| `days` | no | Length of the window, 1 to 3660. Default 30. |
| `time` | no | Local clock applied to every date. Default `09:00`. |
| `natal_chart` | one of these | Kundli response. |
| `dob`, `tob`, `location` | one of these | Birth details, if `natal_chart` is omitted. |

```bash
curl -s http://127.0.0.1:8741/forecast/window \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka","start_date":"2026-10-01","days":30,"time":"09:00"}'
```

`critical_windows` lists Chandrashtama, Vipat or Naidhana, Sadhana, and combustion dates. `major_transits` lists Jupiter, Saturn, Rahu, and Ketu once, plus sign changes inside the window. `dasha_transition: true` is the day the mahadasha-antardasha-pratyantardasha string changes. Each `timeline` row also has `daily_panchanga` for the birthplace.

MCP tool `generate_forecast_window` on port 8744 takes `start_date`, optional `days` and `time`, and either `natal_chart` or birth details.

### Compatibility

36-guna Ashtakoota, Manglik dosha from lagna and Moon, and 7th-house synastry. The groom is the male chart and the bride is the female chart. Swapping them can change Varna and Gana.

| Field | Required | Meaning |
| --- | --- | --- |
| `male_chart` | one of these | Groom chart from Kundli. |
| `male_dob`, `male_tob`, `male_location` | one of these | Groom birth, if `male_chart` is omitted. |
| `female_chart` | one of these | Bride chart from Kundli. |
| `female_dob`, `female_tob`, `female_location` | one of these | Bride birth, if `female_chart` is omitted. |

```bash
curl -s http://127.0.0.1:8741/compatibility/match \
  -H 'Content-Type: application/json' \
  -d '{"male_dob":"1998-04-10","male_tob":"17:25","male_location":"Hubli, Karnataka","female_dob":"1990-04-02","female_tob":"06:30","female_location":"Gadag, Karnataka"}'
```

The response has the guna breakdown and total out of 36, Manglik analysis for both people, dosha flags, and 7th-house synastry. Identical nakshatra and identical pada is Nadi dosha and is not cancelled.

MCP tool `get_compatibility_json` on port 8745 takes `male_chart` and `female_chart`, or the six birth fields.

### Ashtakavarga

Bhinnashtakavarga (0–8 bindus per sign for each of the seven grahas) and Sarvashtakavarga (0–56 per sign, mean 28, total 337). Add a target date to score Jupiter, Saturn, Rahu, and Ketu against the natal SAV of the signs they occupy.

| Field | Required | Meaning |
| --- | --- | --- |
| `natal_chart` | one of these | Kundli response. The natal chart already contains this table. |
| `dob`, `tob`, `location` | one of these | Birth details, if `natal_chart` is omitted. |
| `target_date` | no | Civil date for `transit_filter_status`. |
| `target_time` | no | Local `HH:MM` for that transit. Default `12:00`. |

```bash
curl -s http://127.0.0.1:8741/ashtakavarga/bindus \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka","target_date":"2026-10-15","target_time":"09:00"}'
```

SAV of 32 or more protects the occupied sign. SAV of 24 or fewer is weak even in a good house.

MCP tool `get_ashtakavarga_json` on port 8746 takes the chart or birth details, and optional `target_date` and `target_time`.

### Saturn cycles

Sade Sati (12th, 1st, and 2nd from the natal Moon), Kantaka Shani (4th from the Moon or the lagna), and Ashtama Shani (8th from the Moon). Ingress dates come from the precomputed Lahiri table. A retrograde return stays inside one passage, so a Rising end is not forced to equal the Peak start.

| Field | Required | Meaning |
| --- | --- | --- |
| `as_of_date` | yes | Civil date, `YYYY-MM-DD`. |
| `as_of_time` | no | Local `HH:MM`. Default `09:00`. |
| `natal_chart` | one of these | Kundli response. |
| `dob`, `tob`, `location` | one of these | Birth details, if `natal_chart` is omitted. |

```bash
curl -s http://127.0.0.1:8741/saturn-cycles/track \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka","as_of_date":"2026-10-07","as_of_time":"09:00"}'
```

Each block has `current_status` and `next_ingress_date` (also exposed as `is_active` and `next_cycle_start` or `next_occurrence`). `sade_sati.cycle_history` lists completed passages. For this Gadag chart on 7 October 2026, Sade Sati is inactive and the next Rising ingress is `2029-08-08`.

MCP tool `get_saturn_cycles` on port 8747 takes `as_of_date`, optional `as_of_time`, and the chart or birth details.

### Panchanga

Topocentric sunrise and sunset at the observer's latitude, longitude, and elevation. Tithi, nakshatra, yoga, and karana are Lahiri positions at sunrise. Rahu Kaalam, Yamaganda, and Gulika Kaalam are eight equal parts of sunset minus sunrise and stop at sunset. `location` is where the action happens, which can differ from the birthplace.

| Field | Required | Meaning |
| --- | --- | --- |
| `date` | yes | Civil date, `YYYY-MM-DD`. |
| `at_time` | no | `HH:MM` or `HH:MM:SS`. Before sunrise, the previous solar day is used, and tithi, karana, and the active window are scored at this clock. |
| `location` | one place source | Observer place name. |
| `latitude`, `longitude` | one place source | Decimal degrees. `elevation_m` and `timezone_name` are optional with them. |
| `elevation_m` | no | Meters above sea level. Looked up when omitted. |
| `timezone_name` | no | IANA name, such as `Asia/Kolkata`. Derived from the coordinates when omitted. |
| `natal_chart` | one place source | Used only when `location` and coordinates are omitted. |
| `dob`, `tob`, `birth_location` | one place source | Birth place fallback. |

```bash
curl -s http://127.0.0.1:8741/panchanga/day \
  -H 'Content-Type: application/json' \
  -d '{"date":"2026-10-15","at_time":"14:00:00","location":"Gadag, Karnataka"}'
```

`solar_day.sunrise_current` and `solar_day.sunrise_next` are ISO-8601 timestamps with the UTC offset. `instant.is_current_solar_day` is true when `sunrise_current <= event < sunrise_next`. At 14:00 in Gadag on this date, `active_inauspicious_window` is `Rahu Kaalam` and `is_favorable_for_action` is false. Outside sunrise-to-sunset, `daytime_kaalam_active` and `is_favorable_for_action` are null. Night is not marked safe.

MCP tool `get_daily_panchanga` on port 8748 takes `date` and the same place and time fields.

### Navamsha

D9 from the natal longitudes. Each sign is nine parts of 3°20'. Fire signs start at Aries, earth at Capricorn, air at Libra, and water at Cancer. No second ephemeris call.

| Field | Required | Meaning |
| --- | --- | --- |
| `natal_chart` | one of these | Kundli response. The natal chart already contains `navamsha_d9`. |
| `dob`, `tob`, `location` | one of these | Birth details, if `natal_chart` is omitted. |

```bash
curl -s http://127.0.0.1:8741/navamsha/chart \
  -H 'Content-Type: application/json' \
  -d '{"dob":"1990-04-02","tob":"06:30","location":"Gadag, Karnataka"}'
```

Each graha has `d1_sign`, `d9_sign`, `d9_dignity` (`Exalted`, `Debilitated`, `Own`, or `Neutral`), `is_vargottama`, `is_pushkara_navamsha`, and `navamsha_part` (1–9). The lagna has the same fields except dignity. For this Gadag chart, Mars is Capricorn in D1 and Cancer in D9 (debilitated). Mercury and Saturn are Vargottama.

MCP tool `get_navamsha_json` on port 8749 takes `natal_chart`, or `dob`, `tob`, and `location`.
