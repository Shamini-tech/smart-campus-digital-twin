"""Generate device-level readings for the simulated campus.

Meters replay real BDG2 building electricity (source_type "historical").
HVAC, lighting and occupancy readings are SYNTHETIC (source_type "simulated"):
shares of the building total driven by temperature and the occupancy proxy.
All shares and densities below are assumptions (see docs/decisions.md).
Timestamps are campus local time (naive).
"""
from __future__ import annotations

import pandas as pd

from features.calendar_features import calendar_features
from simulator.occupancy_model import occupancy_level
from twin.entities import Building, Campus

LIGHTING_FRAC = 0.15   # max share of building electricity used by lighting
HVAC_FRAC = 0.40       # max share used by HVAC at full cooling demand
COOLING_BASE_C = 15.0  # no cooling demand below this air temperature
COOLING_SPAN_C = 20.0  # full cooling demand at base + span
DENSITY = {            # people per m2 of floor area
    "academic": 0.05, "laboratory": 0.05, "library": 0.04,
    "residential": 0.03, "office": 0.05,
}
METRIC = {
    "energy_meter": ("energy_kwh", "kWh"),
    "hvac": ("hvac_energy_kwh", "kWh"),
    "lighting": ("lighting_energy_kwh", "kWh"),
    "occupancy": ("occupancy_count", "people"),
}


def _building_signals(
    building: Building, energy: pd.Series, temp_c: pd.Series, features: pd.DataFrame
) -> dict[str, pd.Series]:
    """Hourly totals for one building: meter, HVAC, lighting and occupancy."""
    occ = occupancy_level(features, building.type)
    cooling = ((temp_c - COOLING_BASE_C) / COOLING_SPAN_C).clip(0, 1).fillna(0)
    activity = 0.3 + 0.7 * occ
    return {
        "energy_meter": energy,
        "hvac": energy * HVAC_FRAC * cooling * activity,
        "lighting": energy * LIGHTING_FRAC * activity,
        "occupancy": occ * building.floor_area_m2 * DENSITY[building.type],
    }


def simulate_readings(
    campus: Campus,
    values: pd.DataFrame,
    statuses: pd.DataFrame,
    weather: pd.DataFrame,
    calendar: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Long table of readings: one row per device per hour."""
    frames = []
    for building in campus.buildings:
        energy = values.loc[start:end, building.id]
        status = statuses.loc[start:end, building.id]
        features = calendar_features(energy.index, calendar)
        temp_c = weather["air_temp_c"].reindex(energy.index)
        totals = _building_signals(building, energy, temp_c, features)

        devices = [(floor.id, d) for floor in building.floors for d in floor.devices]
        counts: dict[str, int] = {}
        for _, d in devices:
            counts[d.type.value] = counts.get(d.type.value, 0) + 1

        for floor_id, device in devices:
            dtype = device.type.value
            metric, unit = METRIC[dtype]
            value = totals[dtype] / counts[dtype]
            if dtype == "occupancy":
                value = value.round(0)
            frames.append(
                pd.DataFrame(
                    {
                        "timestamp": energy.index,
                        "building_id": building.id,
                        "floor_id": floor_id,
                        "device_id": device.id,
                        "device_type": dtype,
                        "metric": metric,
                        "value": value.round(3).to_numpy(),
                        "unit": unit,
                        "source_type": "historical" if dtype == "energy_meter" else "simulated",
                        "data_quality_status": status.to_numpy(),
                    }
                )
            )
    out = pd.concat(frames, ignore_index=True)
    out["reading_id"] = out["device_id"] + "-" + out["timestamp"].dt.strftime("%Y%m%dT%H%M%S")
    return out.sort_values(["timestamp", "device_id"], ignore_index=True)


def main() -> None:
    from config.settings import BASE_DIR, get_settings
    from features.calendar_features import load_calendar
    from features.weather_client import load_site_weather
    from simulator.profile_loader import load_profiles

    settings = get_settings()
    campus = Campus.from_yaml(settings.campus_model_path)
    values, statuses = load_profiles()
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    readings = simulate_readings(campus, values, statuses, weather, calendar, "2016-10-03", "2016-10-09")
    print(readings.shape)
    print(readings.groupby("source_type").size().to_string())
    day = readings[
        (readings["building_id"] == "B01") & (readings["timestamp"].dt.date == pd.Timestamp("2016-10-05").date())
    ]
    print(day.pivot_table(index="timestamp", columns="device_id", values="value").round(1).to_string())


if __name__ == "__main__":
    main()