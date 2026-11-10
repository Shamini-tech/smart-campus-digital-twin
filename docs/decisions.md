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