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
