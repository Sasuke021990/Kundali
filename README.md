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

`get_kundli_json` uses the same calculation as the PNG and returns a JSON string: birth metadata, lagna, nine grahas, and twelve whole-sign houses. Rahu is the mean node. Each graha includes `is_combust` and `is_in_graha_yuddha`.

```python
from kundli import get_kundli_json

print(get_kundli_json("1990-04-02", "06:30", "Gadag, Karnataka"))
```

## Timing telemetry

`get_timing_telemetry` reads that natal JSON (a dict or a JSON string) and a target civil date in the natal timezone. It returns the active Vimshottari mahadasha, antardasha, and pratyantardasha, Lahiri gochara for all nine grahas measured from both the natal lagna and the natal Moon, and the daily lunar trigger (Tara Bala and Chandrashtama).

Dasha lengths use the mean tropical year of 365.2425 days. The birth mahadasha is already partly elapsed by the Moon's position inside its nakshatra, so antardasha and pratyantardasha are not restarted at birth. Rahu is the mean node and Ketu is opposite Rahu. When `is_chandrashtama` is true, the transit Moon is in the 8th house from the natal Moon.

```python
import json
from kundli import get_kundli_json, get_timing_telemetry

natal = get_kundli_json("1998-04-10", "17:25", "Hubli, Karnataka")
timing = get_timing_telemetry(natal, "2026-10-15", "09:00")
print(json.dumps(timing, indent=2))
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
