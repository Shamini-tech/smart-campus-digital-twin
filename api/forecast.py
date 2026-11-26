"""Forecast and anomaly endpoints (historical data; needs the database running)."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["forecast"])


@lru_cache(maxsize=1)
def _data():
    import psycopg
    import lightgbm as lgb

    from config.settings import BASE_DIR
    from features.calendar_features import load_calendar
    from features.weather_client import load_site_weather
    from forecasting.data import load_meter_series
    from forecasting.features import term_categories
    from ingestion.db import get_dsn

    with psycopg.connect(get_dsn()) as conn:
        meters = load_meter_series(conn)
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    terms = term_categories(calendar)
    boosters = {
        b: lgb.Booster(model_file=str(BASE_DIR / "models" / "saved" / f"{b}_lgbm.txt"))
        for b in meters.columns
    }
    return meters, weather, calendar, terms, boosters


def _load():
    try:
        return _data()
    except Exception as exc:  # database down, model file missing, ...
        raise HTTPException(status_code=503, detail=f"Forecast data unavailable: {exc}")


def _split_label(day: pd.Timestamp) -> str:
    from forecasting.split import TEST_START, VAL_START

    if day >= pd.Timestamp(TEST_START):
        return "test (model never saw this period)"
    if day >= pd.Timestamp(VAL_START):
        return "validation (used to stop training early)"
    return "train (in-sample: accuracy here is NOT a fair score)"


@router.get("/forecast/{building_id}")
def forecast(building_id: str, date: str = Query("2017-11-15", description="YYYY-MM-DD")):
    from forecasting.features import build_features

    meters, weather, calendar, terms, boosters = _load()
    if building_id not in boosters:
        raise HTTPException(status_code=404, detail=f"Unknown building. Choose from {list(boosters)}")
    day = pd.Timestamp(date)
    y = meters[building_id].asfreq("h")
    X = build_features(y, weather, calendar, terms)
    pred = pd.Series(boosters[building_id].predict(X), index=X.index)
    sel = (pred.index >= day) & (pred.index < day + pd.Timedelta(days=1))
    if not sel.any():
        raise HTTPException(status_code=404, detail="No data for that date")
    out = pd.DataFrame({"forecast_kwh": pred[sel], "actual_kwh": y.reindex(pred.index)[sel]})
    return {
        "building_id": building_id,
        "date": date,
        "period": _split_label(day),
        "note": "Day-ahead forecast using lags >= 24 h and OBSERVED weather (assumes a perfect weather forecast). Historical Arizona data.",
        "hours": [
            {"time": t.isoformat(), "forecast_kwh": round(r.forecast_kwh, 2),
             "actual_kwh": None if pd.isna(r.actual_kwh) else round(r.actual_kwh, 2)}
            for t, r in out.iterrows()
        ],
    }


@router.get("/anomalies")
def anomalies(
    start: str = Query("2017-11-01"),
    end: str = Query("2017-12-01"),
    demo_faults: bool = Query(False, description="Inject SYNTHETIC faults to demonstrate detection"),
):
    from anomaly.evaluate import inject_into_meters
    from anomaly.service import alerts_for_building
    from forecasting.split import TEST_START

    meters, weather, calendar, terms, boosters = _load()
    labels = None
    observed = meters
    if demo_faults:
        observed, labels = inject_into_meters(meters, TEST_START, 42, n_stuck=10, n_spikes=40, stuck_hours=12)
    frames = []
    for b, booster in boosters.items():
        frames.append(
            alerts_for_building(
                b, meters[b].asfreq("h"), observed[b].asfreq("h"),
                weather, calendar, terms, booster, start, end,
            )
        )
    alerts = pd.concat(frames, ignore_index=True)
    if labels is not None and len(alerts):
        alerts["injected"] = [
            labels.loc[t, b] if t in labels.index else "none"
            for t, b in zip(alerts["time"], alerts["building_id"])
        ]
    alerts["time"] = alerts["time"].astype(str)
    return {
        "start": start, "end": end, "demo_faults": demo_faults,
        "note": ("SYNTHETIC faults were injected to demonstrate detection; 'injected' is the answer key."
                 if demo_faults else
                 "Real historical data, no injected faults: every alert here is a possible false alarm or genuine oddity."),
        "count": len(alerts),
        "alerts": alerts.fillna("").to_dict(orient="records"),
    }