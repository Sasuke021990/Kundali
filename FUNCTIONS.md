# Function guide

This file is the call map for every public function in the Jyotish engine, the fields each one returns, and how an AI should request those details. HTTP examples and curl live in `README.md`. This file is the contract: which function to call, which arguments to pass, and which keys to read.

Dates are `YYYY-MM-DD`. Times are 24-hour local `HH:MM` unless a function also accepts `HH:MM:SS`. A natal chart is the dict from `get_kundli_json`. Pass that object onward. Do not rebuild it from prose.

## How an AI should get details

Call in this order.

1. **Natal chart first.** `get_kundli_json(dob, tob, location)` is the only function that turns a birth into a chart. Keep the dict. Later calls accept that dict as `natal_chart`, or the same birth fields again. Reusing the dict avoids a second geocode.
2. **One moment.** `get_timing_telemetry` for Vimshottari, gochara, Tara Bala, Chandrashtama, Ashtakavarga potency, and Saturn cycles at one local clock time.
3. **Many days.** `generate_forecast_window` for a timeline. For a month, read `critical_windows` and `major_transits`. For one day, read that `timeline` row. If you need degrees, call `get_timing_telemetry` for that date. Do not invent degrees from the forecast row.
4. **Saturn only.** `get_saturn_cycles` when the question is Sade Sati, Kantaka, or Ashtama. Ingress dates are already computed. Copy `next_ingress_date` and `cycle_history` as returned.
5. **Strength of signs.** `get_ashtakavarga_json`. Natal SAV is already inside the kundli. Pass `transits` from timing, or `target_date` on the API, when you need transit potency.
6. **D9.** `get_navamsha_json`. The same block is already on the kundli as `navamsha_d9`. It does not call the ephemeris.
7. **Marriage match.** Build two charts. Groom is `male_chart`. Bride is `female_chart`. Then `get_compatibility_json`. Do not swap them. Varna and Gana are not symmetric.
8. **A place and a day, no birth required.** `get_daily_panchanga`. Observer `location` or coordinates override a natal place. Forecast rows already embed sunrise panchanga for the natal coordinates, without an `instant` block.

Three transports, same functions:

| Need | Python | HTTP `POST` | MCP tool (streamable HTTP) |
| --- | --- | --- | --- |
| Natal chart | `kundli.get_kundli_json` | `/kundli/chart` on port 8741 | `get_kundli_json` on 8742 |
| One moment | `kundli.get_timing_telemetry` | `/timing/telemetry` | `get_timing_telemetry` on 8743 |
| Date window | `kundli.generate_forecast_window` | `/forecast/window` | `generate_forecast_window` on 8744 |
| Match | `kundli.get_compatibility_json` | `/compatibility/match` | `get_compatibility_json` on 8745 |
| Bindus | `ashtakavarga.get_ashtakavarga_json` | `/ashtakavarga/bindus` | `get_ashtakavarga_json` on 8746 |
| Saturn cycles | `saturn_cycles.get_saturn_cycles` | `/saturn-cycles/track` | `get_saturn_cycles` on 8747 |
| Panchanga | `panchanga.get_daily_panchanga` | `/panchanga/day` | `get_daily_panchanga` on 8748 |
| Navamsha | `navamsha.get_navamsha_json` | `/navamsha/chart` | `get_navamsha_json` on 8749 |
| North Indian PNG | `kundli.generate_kundli_chart` | none | none |

Base URL when the API is local: `http://127.0.0.1:8741`. Each prefix has its own `/docs`. MCP health is `GET /health` on that server's port. The index `GET /connections` lists ports.

On HTTP and MCP you may omit `natal_chart` and send `dob`, `tob`, and `location` instead. Compatibility uses `male_dob` / `female_dob` (and matching `tob` and `location`). Panchanga can use `location`, or `latitude` plus `longitude`, or `natal_chart`, or `dob`, `tob`, and `birth_location`.

### Rules an AI must keep

- Quote dasha strings, window start and end timestamps, and Saturn ingress dates exactly. Do not round a window to the nearest hour, and do not force a Sade Sati Rising end to equal the Peak start. Retrograde spans may overlap.
- A null `daytime_kaalam_active` means the clock is outside sunrise-to-sunset. That is not "safe because Rahu is off." Read `is_favorable_for_action` only when it is a boolean.
- A clock time before sunrise belongs to the previous solar day. Use `sunrise_current` and `sunrise_next`, not civil midnight.
- Do not show raw bindu counts to a non-technical reader. Use `transit_potency` (`Very High (Protected)`, `High (Protected)`, `Average (Benchmark)`, `Below Average`, `Weak / High Vulnerability`).
- Identical Moon nakshatra and identical pada is Eka Nakshatra Eka Pada. Nadi is never cancelled in that case. Same rashi lord cancels Nadi only when the signs differ.
- Pushkara is the classical 24 parts. The 9th navamsha of Gemini is Vargottama and is not Pushkara. Air Pushkara is parts 6 and 8.
- Transit records do not include `is_combust`. Combustion of a transit graha is a forecast `risk_flags` entry, or `is_combust(...)` if you have longitudes.
- Rahu is the mean node. Ketu is Rahu plus 180 degrees. Houses are whole sign. Ayanamsa is Lahiri. Dasha years use 365.2425 days, and the birth mahadasha is already partly elapsed.
- Dignity words are `Exalted`, `Debilitated`, `Own`, `Neutral`.

## `get_kundli_json`

```python
get_kundli_json(dob: str, tob: str, location: str, as_string: bool = False) -> dict | str
```

**Use.** Sidereal natal chart for one birth. This is the object every other natal function expects.

**Inputs.** `dob` `YYYY-MM-DD`. `tob` `HH:MM` in the place's local zone. `location` is a place name (`Gadag, Karnataka`); Nominatim resolves it once. `as_string=True` returns indented JSON. Default is a dict.

**What it provides.**

- `metadata`: `dob`, `tob`, `location` (resolved name), `coordinates.latitude`, `coordinates.longitude`, `timezone`, `utc_datetime`, `ayanamsa.system` (`Lahiri (Chitra Paksha)`), `ayanamsa.value_deg`.
- `lagna`: `sign`, `sign_number` (1 Aries through 12 Pisces), `degree_in_sign`, `nakshatra`, `pada`, `ruling_planet`.
- `planets` in order Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. Each has `sign`, `sign_number`, `house`, `degree_in_sign`, `total_degree`, `nakshatra`, `pada`, `is_retrograde`, `is_combust`, `is_in_graha_yuddha`, `dignity`, `lord_of_houses`, `aspected_houses`.
- `houses` `"1"` through `"12"`: `sign`, `sign_number`, `planets` (names in that house; empty list if none).
- `ashtakavarga`: natal BAV and SAV (see that function). No transit filter, because there is no transit yet.
- `navamsha_d9`: D9 for lagna and grahas (see that function).

**AI use.** Call this before timing, forecast, Saturn, compatibility, or a chart image. Read `planets.Moon` for janma rashi and nakshatra, `lagna` for the ascendant lord, `houses` for occupancy, `is_combust` and `is_in_graha_yuddha` for natal affliction, `dignity` for strength, `lord_of_houses` for which bhavas a graha rules, `aspected_houses` for Parashari drishti.

Combustion orbs, short arc: Moon 12°, Mars 17°, Mercury 14° (12° retrograde), Jupiter 11°, Venus 10° (8° retrograde), Saturn 15°. Graha Yuddha is 1° among Mars, Mercury, Jupiter, Venus, and Saturn only. Aspects: all grahas the 7th; Mars also 4 and 8; Jupiter, Rahu, and Ketu also 5 and 9; Saturn also 3 and 10. Rahu and Ketu rule no houses.

HTTP body: `{"dob","tob","location"}`. MCP arguments are the same three strings. PNG is a separate call, `generate_kundli_chart`.

## `generate_kundli_chart`

```python
generate_kundli_chart(dob, tob, location, output_file="kundli.png") -> str
```

**Use.** Draw the North Indian Lagna kundli and return the absolute PNG path. Numbers on the chart are rashi numbers, not house numbers. House 1 is the top-center diamond. Retrograde glyphs look like `Sa (R)`.

**AI use.** Call when the user wants an image. Interpretation still comes from `get_kundli_json`. There is no HTTP or MCP route for the PNG.

CLI: `python kundli.py --dob YYYY-MM-DD --tob HH:MM --location "City, Region" --output_file chart.png`. With no arguments the script writes an example chart.

## `get_timing_telemetry`

```python
get_timing_telemetry(natal_chart, target_date_str, target_time_str="12:00") -> dict
```

**Use.** One local civil moment: running Vimshottari, sidereal transits, lunar day-quality, Ashtakavarga of those transits, and Saturn cycles.

**Inputs.** `natal_chart` dict or JSON string. `target_date_str` `YYYY-MM-DD`. `target_time_str` `HH:MM` in `metadata.timezone`. The target cannot precede birth. Ambiguous or nonexistent civil times are rejected. HTTP and MCP rename the arguments to `target_date` and `target_time` and may build the chart from birth fields.

**What it provides.**

- `target_timestamp`: `local`, `utc`, `timezone`.
- `active_dasha`: `mahadasha`, `antardasha`, `pratyantardasha`, `active_period_string` (`Rahu-Venus-Rahu`).
- `transits` for the nine grahas: `sign`, `sign_number`, `degree_in_sign`, `house_from_lagna`, `house_from_moon`, `is_retrograde`. No combustion flag on these rows.
- `daily_lunar_trigger`: `transit_moon_nakshatra_index` (1–27), `tara_bala`, `is_tara_favorable`, `house_from_natal_moon`, `is_chandrashtama` (transit Moon in the 8th from natal Moon).
- `ashtakavarga` including `transit_filter_status`.
- `saturn_cycles` for the same timestamp (see that function).

**AI use.** This is the function for "what is running now" and for degrees of Jupiter, Saturn, Rahu, and Ketu. Read `active_period_string` before transits. If `is_chandrashtama` is true, treat the day as emotionally volatile. Tara names come from `tara_bala`; favorable Taras set `is_tara_favorable`. Do not recompute the dasha with a 365-day year. The birth nakshatra lord's mahadasha is already partly consumed.

## `generate_forecast_window`

```python
generate_forecast_window(natal_chart, start_date_str, days=30, time_str="09:00") -> dict
```

**Use.** A civil-date timeline at one fixed local clock time (default 09:00). `days` is an integer from 1 to 3660.

**What it provides.**

- `metadata`: `native_dob`, `native_lagna`, `forecast_start`, `total_days`, `time`.
- `critical_windows`: `chandrashtama_dates`, `friction_dates` (Vipat or Naidhana), `peak_execution_dates` (Sadhana and not Chandrashtama), `combustion_dates`. These lists are the source of truth. Do not edit them.
- `major_transits`: `as_of` (the start date), `planets` for Jupiter, Saturn, Rahu, and Ketu (`sign`, `sign_number`, `is_retrograde`), `sign_changes` (`date`, `planet`, `from_sign`, `to_sign`) inside the window.
- `ashtakavarga` and `saturn_cycles` at the first date and `time_str`.
- `timeline` rows: `date`, `active_dasha`, `dasha_transition` (true only when the triple string differs from the previous civil day), `transit_moon` (`sign`, `house_from_moon`, `house_from_lagna`, `is_chandrashtama`), `tara_bala`, `is_favorable`, `risk_flags`, `daily_panchanga`.

`risk_flags` strings:

- `CHANDRASHTAMA (Emotional volatility / poor decision window)`
- `NAIDHANA_TARA (Crisis / sudden obstacles)`
- `VIPAT_TARA (Unplanned delays / losses)`
- `COMBUSTION (<names> within solar orb)`

`daily_panchanga` on each row is the sunrise panchanga at the natal latitude and longitude. It has no `instant` block. A 09:00 snapshot can still fall inside Gulika or Rahu later that morning; check the window timestamps before calling 09:00 a clear hour.

**AI use.** Month question: summarize `critical_windows`, `major_transits.sign_changes`, and `dasha_transition` dates. Single day: one timeline row, then `get_timing_telemetry` if you need graha degrees. Keep dasha first, then transit. Do not walk all 30 Moon rows into a user answer unless they asked for the day list.

HTTP and MCP use `start_date`, `days`, and `time`.

## `get_compatibility_json`

```python
get_compatibility_json(male_chart, female_chart, as_string=False) -> dict | str
```

**Use.** 36-guna Ashtakoota, Manglik from both lagna and Moon, and 7th-house synastry. Groom is the first chart. Bride is the second.

**What it provides.**

- `meta`: `male_dob`, `female_dob`, `male_moon`, `female_moon` (sign, nakshatra, pada).
- `gun_milan_summary`: `total_score`, `maximum_score` (36), `percentage`, `verdict`.
- `ashtakoota_breakdown` kootas, each with `score` and `max`:
  - `varna` (max 1): `male_varna`, `female_varna`.
  - `vashya` (max 2): `male_vashya`, `female_vashya`.
  - `tara` (max 3): `f_to_m_favorable`, `m_to_f_favorable`.
  - `yoni` (max 4): `male_yoni`, `female_yoni`, `is_hostile_pair`.
  - `graha_maitri` (max 5): `male_moon_lord`, `female_moon_lord`.
  - `gana` (max 6): `male_gana`, `female_gana`, `gana_dosha`.
  - `bhakoot` (max 7): `relative_position`, `bhakoot_dosha`, `is_cancelled`.
  - `nadi` (max 8): `male_nadi`, `female_nadi`, `nadi_dosha`, `is_cancelled`.
- `manglik_analysis`: `male` and `female` each have `is_manglik`, `raw_manglik`, `is_cancelled`, `cancellation_reason`, `house_from_lagna`, `house_from_moon`. Pair fields: `is_mutually_cancelled` (both Manglik), `is_compatible` (both Manglik or both clear).
- `synastry_flags`: `active_nadi_dosha`, `active_bhakoot_dosha`, `active_gana_dosha`.
- `seventh_house_synastry`: per person `sign`, `sign_number`, `lord`, `planets`, `mars_in_seventh_from_lagna`, `mars_in_seventh_from_moon`. Cross flags: `female_moon_in_male_seventh`, `male_moon_in_female_seventh`, `female_lagna_is_male_seventh`, `male_lagna_is_female_seventh`.

Verdict:

| Condition | `verdict` |
| --- | --- |
| score ≥ 28, no active Nadi, Manglik status matches | `EXCELLENT` |
| score ≥ 18, no active Nadi, Manglik status matches | `GOOD_AND_FAVORABLE` |
| score ≥ 18 otherwise | `ACCEPTABLE_WITH_DOSHA_REMEDIES` |
| score under 18 | `NOT_RECOMMENDED` |

**AI use.** A high guna total does not cancel an active Nadi dosha or a one-sided Manglik dosha. Read `synastry_flags` and `manglik_analysis.is_compatible` beside `total_score`. Identical nakshatra and pada never clear Nadi.

HTTP and MCP take `male_chart` and `female_chart`, or the six birth fields.

## `get_ashtakavarga_json`

```python
get_ashtakavarga_json(natal_chart, transits=None) -> dict
compute_ashtakavarga(natal_chart) -> dict
transit_filter_status(natal_ashtakavarga, transits, names=("Jupiter","Saturn","Rahu","Ketu")) -> dict
sav_potency(bindus: int) -> str
```

**Use.** Bhinnashtakavarga (0–8) for the seven grahas and Sarvashtakavarga (0–56) per sign. Contributors are the seven grahas plus the lagna. Rahu and Ketu have no BAV of their own. The total of all SAV bindus is 337. The mean per sign is 28.

**What it provides.**

- `sarvashtakavarga`: sign name to integer.
- `bhinnashtakavarga`: graha to sign-name to integer 0–8.
- `total_bindus`, `benchmark` (28).
- `transit_filter_status` only when `transits` is passed. Keys look like `Jupiter_in_Cancer`. Each value has `sign`, `bindus` (SAV), `transit_potency`, and `planet_bindus` (that graha's BAV in the sign) for Sun through Saturn. Rahu and Ketu get SAV potency only.

Potency from `sav_potency`: ≥35 Very High (Protected), ≥32 High (Protected), ≥28 Average (Benchmark), ≥25 Below Average, below 25 Weak / High Vulnerability.

**AI use.** The kundli and the timing payload already include this. Call the function directly when you only want bindus, or when you want to score a transit set you already have. On HTTP and MCP, omit `transits` and set `target_date` (`target_time` defaults to `12:00`) to attach `transit_filter_status`. Judge a transit by potency, not by house alone. SAV of 32 or more protects the sign. SAV of 24 or less is weak even when the house from lagna looks supportive. In a user-facing answer, say the potency label.

## `get_saturn_cycles`

```python
get_saturn_cycles(natal_chart, as_of_date, as_of_time="09:00") -> dict
write_passage_table(path=data/saturn_sign_passages.json) -> None
```

**Use.** Sade Sati (12th, 1st, and 2nd from natal Moon: Rising, Peak, Setting), Kantaka Shani (4th from Moon or from lagna), Ashtama Shani (8th from Moon). Ingress and egress come from `data/saturn_sign_passages.json` (Lahiri, Moshier, 1880–2180 UTC). A request does not search the ephemeris across decades. The as-of instant must fall inside that table.

**What it provides.**

- `as_of`: `local`, `timezone`.
- `saturn`: `sign`, `sign_number` of the unmerged passage that contains the instant. Current sign is never taken from a merged span, because a retrograde gap can sit inside a merged span while Saturn is in the other sign.
- `sade_sati`: `current_status` and `is_active` (same bool), `current_phase` or null, `active_house_from_moon`, `signs.rising`, `signs.peak`, `signs.setting`, `next_ingress_date` and `next_cycle_start` (same date or null), `cycle_history` rows of `phase`, `sign`, `start`, `end`. History merges same-sign gaps of at most 400 days and can overlap.
- `ashtama_shani`: `current_status`, `is_active`, `sign` (the 8th-from-Moon sign), `next_ingress_date`, `next_occurrence`.
- `kantaka_shani`: `current_status`, `is_active`, `from_moon`, `from_lagna`, `house_from_moon`, `house_from_lagna`, `sign` (Saturn now), `moon_kantaka_sign`, `lagna_kantaka_sign`, `next_ingress_date`, `next_occurrence`.

**AI use.** Read `current_status` for "is it on now" and `next_ingress_date` for the next start. Report history dates unchanged. `write_passage_table` (or `python -m saturn_cycles`) rebuilds the JSON. An AI answering a chart question should not call it.

HTTP and MCP: `as_of_date`, `as_of_time`, plus chart or birth fields.

## `get_daily_panchanga`

```python
get_daily_panchanga(
    date,
    location=None,
    at_time=None,
    latitude=None,
    longitude=None,
    elevation_m=None,
    timezone_name=None,
    natal_chart=None,
) -> dict
```

**Use.** True topocentric sunrise and sunset (apparent upper limb, with refraction), the five limbs at sunrise, and Rahu, Yamaganda, and Gulika as eight equal parts of that daytime arc. If `elevation_m` is omitted, elevation comes from Open-Meteo and the call fails if that lookup fails. It does not silently use sea level.

**What it provides.**

- `place`: `name`, `latitude`, `longitude`, `elevation_m`, `timezone`.
- `daily_panchanga.solar_day`: `sunrise`, `sunrise_current`, `sunrise_next`, `sunset`, `day_lord` (`Jupiter (Thursday)`). All times are ISO-8601 with offset. `sunrise` and `sunrise_current` are the same instant. Vara follows the sunrise weekday.
- `daily_panchanga.attributes` at sunrise:
  - `tithi`: `name`, `index` (1–30), `is_rikta` (index mod 15 is 4, 9, or 14).
  - `nakshatra`: `name`, `index`.
  - `yoga`: `name`, `index` (1–27), `is_malefic` (only 17 Vyatipata and 27 Vaidhriti).
  - `karana`: `name`, `index` (1–60), `is_bhadra` (only Vishti).
- `daily_panchanga.inauspicious_windows`: `rahu_kaalam`, `yamaganda`, `gulika_kaalam`, each `{start, end}` as ISO timestamps. They never run past sunset. Weekday segment index (Sunday = 0): Rahu (8, 2, 7, 5, 6, 4, 3), Yamaganda (5, 4, 3, 2, 1, 7, 6), Gulika (7, 6, 5, 4, 3, 2, 1).
- `daily_panchanga.instant` only when `at_time` is set: `local`, `is_current_solar_day` (`sunrise_current <= event < sunrise_next`), `within_daytime_arc`, `daytime_kaalam_active`, `active_inauspicious_window` (`"Rahu Kaalam"`, `"Yamaganda"`, `"Gulika Kaalam"`, or null), `is_favorable_for_action`, `tithi`, `karana` scored at that clock.

`is_favorable_for_action` is true only in daytime, outside those three windows, and not Rikta, not Bhadra, and not a malefic yoga at the instant. If `within_daytime_arc` is false, `daytime_kaalam_active`, `active_inauspicious_window`, and `is_favorable_for_action` are null.

**AI use.** For "is 14:00 a good time in this city", pass `date`, `location` or coordinates, and `at_time`. Read `instant.active_inauspicious_window` and `instant.is_favorable_for_action`. For a birth chart's tomorrow, you can pass the kundli as `natal_chart`, or pass the natal coordinates. Observer `location` wins over the birthplace. Do not treat a night hour as favorable. Do not replace the returned window with a 90-minute block.

## `get_navamsha_json`

```python
navamsha_placement(longitude: float) -> tuple[int, int, int]
get_navamsha_json(natal_chart) -> dict
```

**Use.** Pure D9 division. Each sign is nine parts of 3°20'. Fire signs start the D9 in Aries, earth in Capricorn, air in Libra, water in Cancer. No ephemeris call.

`navamsha_placement` returns `(d1_sign 1–12, d9_sign 1–12, part 1–9)`.

**What `get_navamsha_json` provides.**

- `planets.<name>`: `d1_sign`, `d9_sign`, `d9_dignity`, `is_vargottama`, `is_pushkara_navamsha`, `navamsha_part`.
- `lagna`: the same fields except `d9_dignity`.

Vargottama means D1 sign equals D9 sign. Pushkara parts, 0-based inside the sign: fire 6 and 8 (7th and 9th), earth 2 and 4 (3rd and 5th), air 5 and 7 (6th and 8th), water 1 and 3 (2nd and 4th). Debilitated `d9_dignity` is neecha navamsha.

**AI use.** Read `navamsha_d9` on the kundli unless you only have longitudes, in which case call `navamsha_placement`. Do not claim Pushkara for a Gemini planet in the 9th part. That part is Vargottama only.

HTTP and MCP: `natal_chart`, or `dob`, `tob`, and `location`.

## Geometry and dignity helpers

These do not replace the JSON functions. An AI that already holds a longitude or a chart object can use them without another ephemeris call.

| Function | Returns | Use |
| --- | --- | --- |
| `normalize_longitude(longitude)` | degrees in `[0, 360)` | Wrap any arc before comparing. |
| `longitude_to_rashi(longitude)` | sign number 1–12 | Sidereal sign of a longitude. |
| `degree_in_sign(longitude)` | degrees in `[0, 30)` | Degree inside that sign. |
| `whole_sign_house(planet_rashi, lagna_rashi)` | house 1–12 | Whole-sign house. |
| `house_rashi_index(lagna_rashi, house_number)` | sign number | Sign on a whole-sign house. |
| `nakshatra_placement(longitude)` | `(name, pada 1–4, lord)` | Nakshatra of a sidereal longitude. |
| `planet_dignity(name, rashi_index)` | Exalted, Debilitated, Own, or Neutral | Dignity in a sign. |
| `aspected_houses(name, house)` | list of houses | Parashari aspects from that house. |
| `houses_ruled_by(name, lagna_rashi_index)` | list of houses | Bhavas that graha rules. Rahu and Ketu return an empty list. |
| `is_combust(name, longitude, sun_longitude, retrograde)` | bool | Short-arc combustion. |
| `graha_yuddha_participants(planets)` | set of names | The five tara grahas within 1° of each other. `planets` is the `PlanetPosition` tuple from `compute_chart`, not the JSON dict. |
| `compute_chart(dob, tob, location)` | `ChartData` | Internal chart object. Prefer `get_kundli_json` for anything you will pass on or show. |
| `kundli_as_dict(chart)` | dict | Same payload as `get_kundli_json`. |
| `render_chart(chart, axes, output_file=...)` | path | Draw a chart you already computed. |
| `validate_chart(chart)` | None | Raises if the chart object is inconsistent. |

Exaltation / debilitation: Sun Aries/Libra, Moon Taurus/Scorpio, Mars Capricorn/Cancer, Mercury Virgo/Pisces, Jupiter Cancer/Capricorn, Venus Pisces/Virgo, Saturn Libra/Aries, Rahu Taurus/Scorpio, Ketu Scorpio/Taurus. Own signs follow the usual rashi lords. Rahu and Ketu own none.

## Service layer

`jyotish_api/service.py` is what HTTP and MCP call. An AI with the Python process can use these when it wants the same argument rules as the API (chart object or birth fields).

| Function | Delegates to |
| --- | --- |
| `build_kundli(dob, tob, location)` | `get_kundli_json` |
| `resolve_natal_chart(natal_chart, dob, tob, location)` | the chart if given, otherwise `build_kundli` |
| `build_timing(target_date, target_time, natal_chart, dob, tob, location)` | `get_timing_telemetry` |
| `build_forecast(start_date, days, time, natal_chart, dob, tob, location)` | `generate_forecast_window` |
| `build_compatibility(male_chart, female_chart, male_dob, male_tob, male_location, female_dob, female_tob, female_location)` | `get_compatibility_json` |
| `build_ashtakavarga(natal_chart, dob, tob, location, target_date, target_time)` | `get_ashtakavarga_json`, with transits when `target_date` is set |
| `build_navamsha(natal_chart, dob, tob, location)` | `get_navamsha_json` |
| `build_panchanga(date, at_time, location, latitude, longitude, elevation_m, timezone_name, natal_chart, dob, tob, birth_location)` | `get_daily_panchanga` |
| `build_saturn_cycles(as_of_date, as_of_time, natal_chart, dob, tob, location)` | `get_saturn_cycles` |

Panchanga builds a natal chart only when latitude is missing, location is missing, and birth fields are present. An observer location wins.

## HTTP routes that are not calculations

| Route | Returns |
| --- | --- |
| `GET /` | Short HTML index of the eight APIs. |
| `GET /health` | `{"status": "ok"}`. |
| `GET /connections` | Host, API base, and each MCP name, port, and tool. |
| `GET /kundli/docs` and the same under `/timing`, `/forecast`, `/compatibility`, `/ashtakavarga`, `/navamsha`, `/panchanga`, `/saturn-cycles` | Swagger for that subsystem. `/redoc` and `/openapi.json` sit beside `/docs`. |

Request models: `BirthBody`, `TimingBody`, `ForecastBody`, `CompatibilityBody`, `AshtakavargaBody`, `NavamshaBody`, `PanchangaBody`, `SaturnCycleBody`. A `ValueError` from the engine becomes HTTP 400 with `detail`.

## MCP process helpers

| Function | Use |
| --- | --- |
| `mcp_servers.runtime.serve(server, default_port)` | Bind `MCP_HOST` (default `0.0.0.0`) and `MCP_PORT` or `default_port`. Streamable HTTP, stateless, JSON responses. |
| `mcp_servers.runtime.add_health(server, name)` | `GET /health` on that MCP server. Not an MCP tool. |
| `jyotish_api.serve_all.main` | API on 8741 plus all eight MCP servers. This is the Docker command. |

Tool wrappers only forward arguments into the service layer:

| MCP tool | Port | Server name |
| --- | --- | --- |
| `get_kundli_json_tool` exposed as `get_kundli_json` | 8742 | `jyotish-kundli` |
| `get_timing_telemetry_tool` | 8743 | `jyotish-timing` |
| `generate_forecast_window_tool` | 8744 | `jyotish-forecast` |
| `get_compatibility_json_tool` | 8745 | `jyotish-compatibility` |
| `get_ashtakavarga_json_tool` | 8746 | `jyotish-ashtakavarga` |
| `get_saturn_cycles_tool` | 8747 | `jyotish-saturn` |
| `get_daily_panchanga_tool` | 8748 | `jyotish-panchanga` |
| `get_navamsha_json_tool` | 8749 | `jyotish-navamsha` |

## Data classes

| Class | Fields an AI might read |
| --- | --- |
| `BirthDetails` | `dob`, `tob`, `timezone_name`, `utc_datetime` |
| `LocationDetails` | resolved name, latitude, longitude |
| `PlanetPosition` | name, longitude, speed, rashi, house, retrograde |
| `ChartData` | birth, location, lagna longitude and rashi, ayanamsa, planets |

Prefer the JSON dict. These objects are what `compute_chart` and the PNG path use.

## Internal functions

Names that start with `_` are implementation details. Do not call them from an agent. They are listed so the map is complete.

**kundli.py.** `_parse_dob`, `_parse_tob`, `_parse_location_query`, `_geocode_location`, `_timezone_name_for`, `_format_utc_offset`, `_localize_birth`, `_gregorian_julian_day`, `_birth_details`, `_ephemeris_flags`, `_configure_lahiri`, `_angular_separation`, `_parse_calc_ut`, `_calculate_body`, `_calculate_ascendant`, `_calculate_ayanamsa`, `_planet_record`, `polygon_centroid`, `polygon_area`, `bounding_box`, `inset_polygon`, `_point_segment_distance`, `point_in_polygon`, `horizontal_span`, `rectangle_inside_polygon`, `validate_geometry`, `_format_coordinates`, `_header_text`, `_footer_text`, `_create_figure`, `_draw_geometry`, `_points_to_data`, `_estimate_text_size`, `initial_planet_fontsize`, `rashi_fontsize_for`, `_seek_near`, `_layout_inset`, `_place_stack`, `_layout_house`, `_rashi_fontproperties`, `_add_label`, `_display_pixels`, `_bbox_corners_inside`, `_bboxes_overlap`, `_bbox_edge_clearance`, `_house_labels_fit`, `_planets_by_house`, `_draw_house_labels`, `_validate_drawn_labels`, `_place_header_and_footer`, `_prepare_output_path`, `_verify_output`, `_rounded_longitude`, `_dasha_span_days`, `_walk_dasha_cycle`, `_calculate_vimshottari_triple`, `_load_natal_chart`, `_chart_number`, `_chart_text`, `_transit_record`, `_transit_longitude`, `_combust_transit_names`, `_parse_args`, `main`.

The geometry names without a leading underscore (`polygon_centroid`, `point_in_polygon`, `validate_geometry`, `initial_planet_fontsize`, `rashi_fontsize_for`) exist to lay out and check the PNG. They do not answer a horoscopy question.

**compatibility.py.** `_as_chart`, `_require`, `_relation`, `_get_varna`, `_get_vashya`, `_calc_graha_maitri`, `_check_manglik`, `_seventh_house`, `_nadi_cancelled`, `_gana_points`. Their results are already on `get_compatibility_json`.

**ashtakavarga.py.** `_empty_sign_counts`, `_sign_from_house`, `_contributor_signs`.

**saturn_cycles.py.** `_require`, `_sign_index`, `_house_from`, `_saturn_sign`, `_jd`, `_bisect_ingress`, `_ingresses`, `_utc_iso`, `_raw_passages`, `_merged_passages`, `_sign_on`, `_civil`, `_phase_row`.

**panchanga.py.** `_require`, `_jd`, `_from_jd`, `_slot`, `_elevation_m`, `_sun_event`, `_sidereal_pair`, `_karana_name`, `_tithi_name`, `_nearest_second`, `_iso`, `_seconds_after`, `_moment_from_seconds`, `_window_bounds`, `_window_payload`, `_limbs`, `_resolve_place`, `_rise_on`.

**jyotish_api/main.py.** `_failure`, `_documented_app`, and the route functions `kundli_chart`, `timing_telemetry`, `forecast_window`, `compatibility_match`, `ashtakavarga_bindus`, `navamsha_chart`, `panchanga_day`, `saturn_track`, `connection_card`, `root_health`, `home`.

## Worked call, one birth

```python
from kundli import get_kundli_json, get_timing_telemetry, generate_forecast_window

chart = get_kundli_json("1999-03-31", "21:00", "Gulbarga, Karnataka")
today = get_timing_telemetry(chart, "2026-10-15", "09:00")
week = generate_forecast_window(chart, "2026-10-15", days=7, time_str="09:00")
```

Read `chart["lagna"]`, `chart["planets"]`, `chart["navamsha_d9"]`. Read `today["active_dasha"]["active_period_string"]`, `today["daily_lunar_trigger"]`, and `today["transits"]["Saturn"]`. Read `week["critical_windows"]` and the matching `week["timeline"]` row. For whether 09:00 itself is inside Rahu, Yamaganda, or Gulika, call `get_daily_panchanga` with `at_time="09:00"` and the chart. The forecast row's panchanga is the sunrise limbs and the window clocks, not a verdict on 09:00.
