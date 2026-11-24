# Project decisions

Decisions made so far, and questions still open. Update as the project grows.

## Decided
- Simulated campus of 5 buildings (academic, library, hostel, admin, labs), 28 devices.
- Location and timezone: Coimbatore, Asia/Kolkata.
- Start with hourly data; consider 15-minute data only if the sources support it.
- Device IDs are unique across the campus; topics follow campus/{building}/{floor}/{type}/{device}.
- Settings and contracts live in config/, not in code.
- Results are simulation-based. The system recommends actions and never controls real equipment.

## Open (decide before the phase that needs them)
- Forecast target: whole-building electricity or per-device? Unit and horizon?
- How building-level energy maps to synthetic HVAC and lighting devices.
- Occupancy: calendar-derived proxy or simulated?
- Comfort constraints for the optimizer, with a justified basis.
- Emission factor: exact source, year and units.
## Data source and licence
- Source: Building Data Genome Project 2 (BDG2), https://github.com/buds-lab/building-data-genome-project-2
- Paper: The Building Data Genome Project 2, energy meter data from the ASHRAE Great Energy Predictor III competition, https://arxiv.org/abs/2006.02273
- Licence: Creative Commons Attribution-ShareAlike (the repo LICENSE file is titled 4.0). Credit the authors, link the licence, state that changes were made. Publicly shared derived data must use the same licence, so BDG2-derived data is not committed to this repo.
- Files used: metadata.csv, weather.csv and meters/raw/electricity.csv, stored in data/raw/ (gitignored).
- Site: Fox (about 33.4 N, -111.9 E, US/Mountain time). Buildings are mapped in config/building_mapping.csv.
- Patterns are borrowed from US buildings and replayed as a simulated campus. This is not Coimbatore data.

## Known source-data issues
- Fox_education_Claire has 978 hours of flat (stuck) values between 2016-11-20 and 2017-09-05, so Fox_education_Burton is used instead.
- All five buildings dip together at 2016-10-15 21:00 (one hour); likely a site-wide glitch.
- Several early-Monday dips between May and Aug 2016 where 4+ buildings drop; cause unknown.
- Level shifts around Apr 2016 in the office and classroom series; use chronological validation.

## Cleaning rules
- Exact zeros are treated as missing; flat runs of 24+ identical hours are masked as stuck-meter data.
- Gaps of up to 3 hours are filled by linear interpolation (status: imputed); longer gaps stay missing.
- Raw data is never modified; cleaned data and per-hour status go to data/processed/ (gitignored, BDG2-derived).

## Simulator assumptions
- Meters replay real BDG2 building electricity (historical). HVAC, lighting and occupancy readings are synthetic (simulated).
- Lighting is at most 15% and HVAC at most 40% of building electricity, scaled by occupancy and (for HVAC) by Fox air temperature above 15 C.
- Occupancy count = occupancy level x floor area x assumed density (0.03-0.05 people per m2).
- Timestamps are campus local time without timezone; the publisher decides the ISO/UTC format.

## MQTT payload timestamps
- Payload timestamps are ISO 8601 campus local time without an offset, because the BDG2 source has no timezone. Ingestion applies the campus timezone (config/campus_model.yaml) when storing.
- Missing values are published as JSON null, never NaN.

## Forecasting split and baselines
- Chronological split on 2016 data: train before 2016-09-01, validation Sep-Oct, test from 2016-11-01. No shuffling.
- The loader excludes readings with fault_label != 'none' so injected faults are never learned as normal behaviour.
- Baselines (same hour yesterday, same hour last week) use only past values. A model must beat them on the test window to be kept.

## Calendar closure days
- Added approximate university closure days as holidays: the Friday after Thanksgiving and 24-31 Dec (both years). Chosen from the usual academic calendar, not derived from load, to avoid leakage.
- Reason: error analysis showed the worst forecast days were Thanksgiving week and the winter closure, which the calendar did not flag.
