"""Score the anomaly detectors on faults injected into the test window.

Faults are synthetic (spike = reading x3, stuck = value frozen for 12 h) and are
injected only from TEST_START onward. Models and the residual scale use clean history.
Run: python -m anomaly.evaluate
"""
from __future__ import annotations

import lightgbm as lgb
import pandas as pd

from anomaly.detectors import (
    detection_report, flat_run_flags, residual_flags, robust_scale_by_hour,
)
from forecasting.features import build_features, term_categories
from forecasting.split import TEST_START, VAL_START
from simulator.fault_injector import inject_faults

K_VALUES = (3.0, 4.0, 5.0, 6.0)


def inject_into_meters(meters: pd.DataFrame, start: str, seed: int = 42, **kw):
    """Return (faulty_meters, labels). Faults are injected only from `start` onward."""
    long = (
        meters.loc[start:].rename_axis("timestamp").reset_index()
        .melt(id_vars="timestamp", var_name="device_id", value_name="value")
        .dropna(subset=["value"])
    )
    long["device_type"] = "energy_meter"
    long = long.sort_values(["timestamp", "device_id"], ignore_index=True)
    out = inject_faults(long, seed=seed, n_ac=0, **kw)
    values = out.pivot(index="timestamp", columns="device_id", values="value")
    labels = out.pivot(index="timestamp", columns="device_id", values="fault_label")
    faulty = meters.copy()
    faulty.loc[values.index, values.columns] = values
    return faulty, labels.fillna("none")

def evaluate(meters, weather, calendar, models_dir, seed: int = 42, n_spikes: int = 40, n_stuck: int = 10) -> pd.DataFrame:
    terms = term_categories(calendar)
    faulty, labels = inject_into_meters(
        meters, TEST_START, seed, n_stuck=n_stuck, n_spikes=n_spikes, stuck_hours=12
    )
    residual_sets = {k: [] for k in K_VALUES}
    flat_sets, label_sets = [], []
    for b in meters.columns:
        booster = lgb.Booster(model_file=str(models_dir / f"{b}_lgbm.txt"))
        clean_y = meters[b].asfreq("h")
        Xc = build_features(clean_y, weather, calendar, terms)
        fc_clean = pd.Series(booster.predict(Xc), index=Xc.index)
        in_val = (clean_y.index >= VAL_START) & (clean_y.index < TEST_START)
        scale = robust_scale_by_hour((clean_y - fc_clean)[in_val])

        yf = faulty[b].asfreq("h")
        Xf = build_features(yf, weather, calendar, terms)
        fc = pd.Series(booster.predict(Xf), index=Xf.index)
        in_test = yf.index >= TEST_START
        actual, forecast = yf[in_test], fc[in_test]
        lab = labels[b].reindex(actual.index).fillna("none")
        keep = actual.notna()
        actual, forecast, lab = actual[keep], forecast[keep], lab[keep]
        for k in K_VALUES:
            residual_sets[k].append(residual_flags(actual, forecast, scale, k))
        flat_sets.append(flat_run_flags(yf[in_test], 6).reindex(actual.index))
        label_sets.append(lab)

    all_labels = pd.concat(label_sets, ignore_index=True)
    flat_all = pd.concat(flat_sets, ignore_index=True)
    print("injected:", all_labels.value_counts().to_dict())
    rows = []
    for k in K_VALUES:
        res = pd.concat(residual_sets[k], ignore_index=True)
        rows.append({"detector": f"residual k={k:g}", **detection_report(res, all_labels)})
    rows.append({"detector": "flat run >= 6h", **detection_report(flat_all, all_labels)})
    combined = pd.concat(residual_sets[5.0], ignore_index=True) | flat_all
    rows.append({"detector": "residual k=5 + flat run", **detection_report(combined, all_labels)})
    return pd.DataFrame(rows)


def main() -> None:
    import psycopg

    from config.settings import BASE_DIR
    from features.calendar_features import load_calendar
    from features.weather_client import load_site_weather
    from forecasting.data import load_meter_series
    from ingestion.db import get_dsn

    with psycopg.connect(get_dsn()) as conn:
        meters = load_meter_series(conn)
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    models = BASE_DIR / "models" / "saved"
    print("CONTROL: no faults injected (false alarms on clean data)")
    print(evaluate(meters, weather, calendar, models, n_spikes=0, n_stuck=0).to_string(index=False))
    print("\nWITH INJECTED FAULTS")
    print(evaluate(meters, weather, calendar, models).to_string(index=False))


if __name__ == "__main__":
    main()