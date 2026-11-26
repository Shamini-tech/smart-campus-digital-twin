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

## Forecasting split v2 (two years)
- Data now covers 2016-2017. Split: train before 2017-09-01, validation Sep-Oct 2017, test Nov-Dec 2017, so training includes one Thanksgiving and one winter closure.
- The first experiment (train Jan-Aug 2016, test Nov-Dec 2016) is kept in docs/forecasting_results.md for comparison.

## Known forecasting limitations (experiment 2)
- Library (B02) holiday error is high (WAPE 0.46); few holiday examples and irregular library hours.
- The day before a holiday (e.g. 22 Nov 2017) is labelled an ordinary class day; a day-before/after-holiday feature is a candidate improvement.
- Some high-error days (4-5 Nov 2017) are unexplained by the calendar and may be events.

## Anomaly detector findings (test Nov-Dec 2017, faults injected: 40 spikes x3, 10 stuck meters of 12 h)
- Residual detector (|actual-forecast| > k x typical error for that hour of day): k=8 catches 92.5% of spikes with 1.7% false alarms on clean data; stuck meters are mostly missed (17%).
- Flat-run rule (>= 6 identical hours): catches 100% of stuck meters, 0 false alarms.
- Requiring 3 consecutive flagged hours did NOT reduce false alarms much (3.9% at k=4): forecast misses are multi-hour, not single-hour blips.
- Current best simple setup: critical (k=8) + flat run. A moderate one-hour deviation is not alerted (deliberate trade-off against noise).
- Results are on synthetic injected faults, not real equipment faults.

## Anomaly alert settings
- Alerts = residual deviation (|actual - forecast| > 6 x typical error for that hour; thresholds doubled on holiday/closure days) OR flat run of >= 6 identical hours.
- On injected faults (Nov-Dec 2017): 95% of spikes, 100% of stuck meters; false alarms 2.2% of clean hours (k=8 gives 1.1% false alarms and 87.5% spike recall). k is a setting.
- Remaining false alarms are concentrated in the Library and Admin block, the least predictable buildings.
- Faults are synthetic; these numbers are not evidence about real equipment faults.

## What-if scenarios and carbon
- Scenarios act on the SIMULATED hvac/lighting shares of building load. Assumed factors: 5% HVAC saving per C of setpoint raise (cap 30%), HVAC -80% and lighting -30% when occupancy < 25%. These are assumptions, not measurements. No real equipment is controlled.
- Carbon factor: 0.716 kgCO2/kWh, CEA CO2 Baseline Database v19.0, FY2022-23 all-India weighted average incl. renewables. CEA v22.0 exists and was not read; update the constant when it is.
