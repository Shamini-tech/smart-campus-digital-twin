"""What-if scenarios on the simulated HVAC and lighting shares of building load.

All savings factors below are ASSUMPTIONS. The HVAC and lighting split of the meter
is itself simulated (see simulator/sensor_simulator.py). Nothing controls real equipment.
"""
from __future__ import annotations

import pandas as pd

from optimizer.carbon import co2_kg
from simulator.occupancy_model import occupancy_level
from simulator.sensor_simulator import _building_signals
from twin.entities import Building, DeviceType

SAVING_PER_C = 0.05          # assumed HVAC saving per degree C of setpoint raise
MAX_SETPOINT_SAVING = 0.30   # cap on the setpoint saving
LOW_OCCUPANCY = 0.25         # occupancy level below which a building counts as "nearly empty"


def run_scenario(
    building: Building,
    energy: pd.Series,
    temp_c: pd.Series,
    features: pd.DataFrame,
    setpoint_delta_c: float = 0.0,
    hvac_empty_reduction: float = 0.0,
    lighting_reduction: float = 0.0,
) -> pd.DataFrame:
    """Hourly baseline, savings and scenario energy (kWh) for one building."""
    sig = _building_signals(building, energy, temp_c, features)
    has_hvac = any(d.type == DeviceType.HVAC for d in building.all_devices())
    hvac = sig["hvac"] if has_hvac else sig["hvac"] * 0.0
    light = sig["lighting"]
    empty = occupancy_level(features, building.type) < LOW_OCCUPANCY

    hvac_new = hvac * (1 - min(setpoint_delta_c * SAVING_PER_C, MAX_SETPOINT_SAVING))
    hvac_new = hvac_new.where(~empty, hvac_new * (1 - hvac_empty_reduction))
    light_new = light.where(~empty, light * (1 - lighting_reduction))

    hvac_saved, light_saved = hvac - hvac_new, light - light_new
    saved = hvac_saved + light_saved
    return pd.DataFrame(
        {
            "baseline_kwh": energy,
            "hvac_saved": hvac_saved,
            "lighting_saved": light_saved,
            "saved_kwh": saved,
            "scenario_kwh": energy - saved,
        }
    )

SCENARIOS = {
    "setpoint +2 C": dict(setpoint_delta_c=2.0),
    "HVAC -80% when empty": dict(hvac_empty_reduction=0.8),
    "lighting -30% when empty": dict(lighting_reduction=0.3),
    "all three": dict(setpoint_delta_c=2.0, hvac_empty_reduction=0.8, lighting_reduction=0.3),
}


def summarize(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-building and campus totals: baseline, saved kWh, saved %, CO2 avoided (kg)."""
    rows = []
    for name, df in [*results.items(), ("CAMPUS", pd.concat(results.values()))]:
        base, saved = df["baseline_kwh"].sum(), df["saved_kwh"].sum()
        rows.append(
            {
                "building": name,
                "baseline_kwh": round(base),
                "saved_kwh": round(saved),
                "saved_pct": round(100 * saved / base, 1) if base else float("nan"),
                "co2_saved_kg": round(co2_kg(saved)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    import argparse

    from config.settings import BASE_DIR, get_settings
    from features.calendar_features import calendar_features, load_calendar
    from features.weather_client import load_site_weather
    from simulator.profile_loader import load_profiles
    from twin.entities import Campus

    ap = argparse.ArgumentParser(description="What-if scenarios on historical load")
    ap.add_argument("--start", default="2017-07-01")
    ap.add_argument("--end", default="2017-07-31")
    args = ap.parse_args()

    campus = Campus.from_yaml(get_settings().campus_model_path)
    values, _ = load_profiles()
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")

    print(f"Historical load {args.start} to {args.end}; savings factors are assumptions\n")
    detail = None
    for name, params in SCENARIOS.items():
        results = {}
        for b in campus.buildings:
            energy = values.loc[args.start:args.end, b.id]
            feats = calendar_features(energy.index, calendar)
            temp = weather["air_temp_c"].reindex(energy.index)
            results[b.id] = run_scenario(b, energy, temp, feats, **params)
        table = summarize(results)
        campus_row = table[table["building"] == "CAMPUS"].iloc[0]
        print(f"{name:28s} saved {campus_row['saved_kwh']:>9,.0f} kWh "
              f"({campus_row['saved_pct']}%)  CO2 avoided {campus_row['co2_saved_kg']:>8,.0f} kg")
        detail = table
    print("\nPer building, 'all three':")
    print(detail.to_string(index=False))


if __name__ == "__main__":
    main()