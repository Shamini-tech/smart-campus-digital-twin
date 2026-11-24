"""Where do false alarms happen? Control run (no injected faults) by day type and building.

Run: python -m anomaly.diagnose
"""
from __future__ import annotations

import lightgbm as lgb
import pandas as pd

from anomaly.detectors import persistent_flags, residual_flags, robust_scale_by_hour
from features.calendar_features import calendar_features
from forecasting.error_analysis import day_type
from forecasting.features import build_features, term_categories
from forecasting.split import TEST_START, VAL_START


def summarize(flags: pd.DataFrame, by: str) -> pd.DataFrame:
    """Hours, flagged counts and rates per group. flags has columns critical, warning."""
    g = flags.groupby(by).agg(
        hours=("critical", "size"), critical=("critical", "sum"), warning=("warning", "sum")
    )
    g["critical_rate"] = (g["critical"] / g["hours"]).round(3)
    g["warning_rate"] = (g["warning"] / g["hours"]).round(3)
    return g


def collect_flags(meters, weather, calendar, models_dir) -> pd.DataFrame:
    terms = term_categories(calendar)
    frames = []
    for b in meters.columns:
        booster = lgb.Booster(model_file=str(models_dir / f"{b}_lgbm.txt"))
        y = meters[b].asfreq("h")
        X = build_features(y, weather, calendar, terms)
        fc = pd.Series(booster.predict(X), index=X.index)
        in_val = (y.index >= VAL_START) & (y.index < TEST_START)
        scale = robust_scale_by_hour((y - fc)[in_val])
        in_test = y.index >= TEST_START
        actual, forecast = y[in_test], fc[in_test]
        keep = actual.notna()
        actual, forecast = actual[keep], forecast[keep]
        frames.append(
            pd.DataFrame(
                {
                    "building": b,
                    "day_type": day_type(calendar_features(actual.index, calendar)),
                    "critical": residual_flags(actual, forecast, scale, 8.0),
                    "warning": persistent_flags(residual_flags(actual, forecast, scale, 4.0), 3),
                }
            )
        )
    return pd.concat(frames)


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
    flags = collect_flags(meters, weather, calendar, BASE_DIR / "models" / "saved")
    print("False alarms on clean data, by day type")
    print(summarize(flags, "day_type").to_string())
    print("\nFalse alarms on clean data, by building")
    print(summarize(flags, "building").to_string())


if __name__ == "__main__":
    main()