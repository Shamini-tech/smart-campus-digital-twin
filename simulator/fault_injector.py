"""Inject labelled synthetic faults into simulated readings.

fault_label: none | ac_overnight | stuck_meter | spike
Faults are synthetic. They are applied to a copy; the input is never modified.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def inject_faults(
    readings: pd.DataFrame,
    seed: int = 42,
    n_ac: int = 3,
    n_stuck: int = 2,
    n_spikes: int = 5,
    stuck_hours: int = 12,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = readings.copy()
    out["fault_label"] = "none"
    times = pd.DatetimeIndex(sorted(out["timestamp"].unique()))
    days = pd.DatetimeIndex(out["timestamp"].dt.normalize().unique())[:-1]
    free = out["fault_label"] == "none"

    # 1. HVAC left running overnight (22:00 to 06:00 at 60% of the unit's peak)
    hvac = out.loc[out["device_type"] == "hvac", "device_id"].unique()
    for _ in range(n_ac):
        dev = rng.choice(hvac)
        start = days[rng.integers(len(days))] + pd.Timedelta(hours=22)
        end = start + pd.Timedelta(hours=8)
        mask = (out["device_id"] == dev) & (out["timestamp"] >= start) & (out["timestamp"] < end)
        mask &= out["fault_label"] == "none"
        cap = out.loc[out["device_id"] == dev, "value"].max() * 0.6
        out.loc[mask, "value"] = np.maximum(out.loc[mask, "value"], cap)
        out.loc[mask, "fault_label"] = "ac_overnight"

    # 2. Stuck meter: the value freezes for a run of hours
    meters = out.loc[out["device_type"] == "energy_meter", "device_id"].unique()
    for _ in range(n_stuck):
        dev = rng.choice(meters)
        start = times[rng.integers(len(times) - stuck_hours)]
        end = start + pd.Timedelta(hours=stuck_hours)
        mask = (out["device_id"] == dev) & (out["timestamp"] >= start) & (out["timestamp"] < end)
        mask &= out["fault_label"] == "none"
        if mask.any():
            out.loc[mask, "value"] = out.loc[mask, "value"].iloc[0]
            out.loc[mask, "fault_label"] = "stuck_meter"

    # 3. Spikes: single meter readings multiplied by 3
    ok = out.index[(out["device_type"] == "energy_meter") & (out["fault_label"] == "none")]
    for i in rng.choice(ok, size=n_spikes, replace=False):
        out.loc[i, "value"] = out.loc[i, "value"] * 3
        out.loc[i, "fault_label"] = "spike"
    return out


def main() -> None:
    from config.settings import BASE_DIR, get_settings
    from features.calendar_features import load_calendar
    from features.weather_client import load_site_weather
    from simulator.profile_loader import load_profiles
    from simulator.sensor_simulator import simulate_readings
    from twin.entities import Campus

    settings = get_settings()
    campus = Campus.from_yaml(settings.campus_model_path)
    values, statuses = load_profiles()
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    clean = simulate_readings(campus, values, statuses, weather, calendar, "2016-10-01", "2016-10-31")
    faulty = inject_faults(clean)
    print(faulty.shape)
    print(faulty["fault_label"].value_counts().to_string())


if __name__ == "__main__":
    main()