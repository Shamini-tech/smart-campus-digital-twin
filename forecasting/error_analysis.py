"""Where do the day-ahead models go wrong? Error by day type, and the worst days."""
from __future__ import annotations

import pandas as pd

from features.calendar_features import calendar_features
from forecasting.baselines import seasonal_naive
from forecasting.features import build_features, term_categories
from forecasting.metrics import wape
from forecasting.split import TEST_START
from forecasting.train_lgbm import chronological_split, train_model


def day_type(cal: pd.DataFrame) -> pd.Series:
    """Label each hour's day. Later rules win: holiday > finals > weekend > class day."""
    out = pd.Series("no_class_weekday", index=cal.index)
    out[cal["is_class_day"].astype(bool)] = "class_day"
    out[cal["is_weekend"].astype(bool)] = "weekend"
    out[cal["is_finals_week"].astype(bool)] = "finals_week"
    out[cal["is_holiday"].astype(bool)] = "holiday"
    return out


def breakdown(actual: pd.Series, forecasts: dict, labels: pd.Series) -> pd.DataFrame:
    """WAPE of each forecast within each day type."""
    rows = []
    for label, idx in actual.groupby(labels).groups.items():
        row = {"day_type": label, "hours": len(idx)}
        for name, fc in forecasts.items():
            row[name] = round(wape(actual.loc[idx], fc.reindex(idx)), 3)
        rows.append(row)
    return pd.DataFrame(rows)


def worst_days(actual: pd.Series, forecast: pd.Series, labels: pd.Series, n: int = 3) -> pd.DataFrame:
    """The n days with the highest daily WAPE (days with at least 20 hours)."""
    day = actual.index.normalize()
    err = (actual - forecast).abs()
    daily = pd.DataFrame(
        {
            "wape": err.groupby(day).sum() / actual.groupby(day).sum(),
            "day_type": labels.groupby(day).first(),
            "hours": actual.groupby(day).size(),
        }
    )
    daily = daily[daily["hours"] >= 20]
    return daily.nlargest(n, "wape").round(3)

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
    terms = term_categories(calendar)

    for b in meters.columns:
        y = meters[b].asfreq("h")
        X = build_features(y, weather, calendar, terms)
        split = chronological_split(X, y)
        model = train_model(split)
        Xs, ys = split["test"]
        pred = pd.Series(model.predict(Xs), index=Xs.index)
        labels = day_type(calendar_features(ys.index, calendar))
        forecasts = {
            "lgbm": pred,
            "naive_24h": seasonal_naive(y, 24).reindex(ys.index),
            "naive_168h": seasonal_naive(y, 168).reindex(ys.index),
        }
        print(f"\n=== {b} (test from {TEST_START}) ===")
        print(breakdown(ys, forecasts, labels).to_string(index=False))
        print("worst days (LightGBM):")
        print(worst_days(ys, pred, labels).to_string())


if __name__ == "__main__":
    main()