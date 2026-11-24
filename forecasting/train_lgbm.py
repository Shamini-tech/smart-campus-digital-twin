"""Train one LightGBM day-ahead model per building and compare with the baselines.

Train: before VAL_START. Validation (early stopping only): VAL_START to TEST_START.
Test: from TEST_START, never used for fitting or stopping.
"""
from __future__ import annotations

import lightgbm as lgb
import pandas as pd

from forecasting.baselines import seasonal_naive
from forecasting.features import build_features, term_categories
from forecasting.metrics import score
from forecasting.split import TEST_START, VAL_START

PARAMS = dict(
    objective="regression_l1", n_estimators=3000, learning_rate=0.03,
    num_leaves=31, min_child_samples=20, subsample=0.8, subsample_freq=1,
    colsample_bytree=0.8, random_state=42, verbose=-1,
)


def chronological_split(X, y, val_start=VAL_START, test_start=TEST_START) -> dict:
    """Split by time; rows with no target value are dropped."""
    ok = y.notna()
    X, y = X[ok], y[ok]
    train = X.index < pd.Timestamp(val_start)
    val = (X.index >= pd.Timestamp(val_start)) & (X.index < pd.Timestamp(test_start))
    test = X.index >= pd.Timestamp(test_start)
    return {"train": (X[train], y[train]), "val": (X[val], y[val]), "test": (X[test], y[test])}


def train_model(split: dict) -> lgb.LGBMRegressor:
    Xt, yt = split["train"]
    Xv, yv = split["val"]
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(
        Xt, yt, eval_X=Xv, eval_y=yv, eval_metric="l1",
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    return model

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
    out_dir = BASE_DIR / "models" / "saved"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for b in meters.columns:
        y = meters[b].asfreq("h")
        X = build_features(y, weather, calendar, terms)
        split = chronological_split(X, y)
        model = train_model(split)
        Xs, ys = split["test"]
        pred = pd.Series(model.predict(Xs), index=Xs.index)
        m = score(ys, pred)
        base = min(
            score(ys, seasonal_naive(y, lag).reindex(ys.index))["wape"] for lag in (24, 168)
        )
        model.booster_.save_model(str(out_dir / f"{b}_lgbm.txt"))
        top = pd.Series(model.booster_.feature_importance("gain"), index=X.columns).nlargest(3)
        rows.append(
            {
                "building": b,
                "lgbm_wape": round(m["wape"], 3),
                "best_baseline_wape": round(base, 3),
                "lgbm_mae": round(m["mae"], 3),
                "trees": model.best_iteration_,
                "top_features": ", ".join(top.index),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()