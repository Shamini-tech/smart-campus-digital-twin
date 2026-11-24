"""Turn detector flags into an alert table that the API and dashboard can show."""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from anomaly.detectors import flat_run_flags, residual_flags, robust_scale_by_hour
from features.calendar_features import calendar_features
from forecasting.features import build_features
from forecasting.split import TEST_START, VAL_START

DEFAULT_K = 6.0          # alert when error exceeds k x the typical error for that hour
HOLIDAY_FACTOR = 2.0     # thresholds are multiplied by this on holiday and closure days
MIN_FLAT_HOURS = 6       # identical readings in a row that count as a stuck sensor


def detect(
    building_id: str,
    actual: pd.Series,
    forecast: pd.Series,
    scale_by_hour: pd.Series,
    calendar: pd.DataFrame,
    k: float = DEFAULT_K,
    holiday_factor: float = HOLIDAY_FACTOR,
    min_flat: int = MIN_FLAT_HOURS,
) -> pd.DataFrame:
    """Alerts for one building. A stuck sensor takes priority over a plain deviation."""
    is_hol = calendar_features(actual.index, calendar)["is_holiday"].astype(float)
    mult = 1.0 + (holiday_factor - 1.0) * is_hol
    deviation = residual_flags(actual, forecast, scale_by_hour, k, multiplier=mult)
    stuck = flat_run_flags(actual, min_flat)
    kind = np.select([stuck.to_numpy(), deviation.to_numpy()], ["stuck_sensor", "deviation"], default="")
    scale = scale_by_hour.reindex(actual.index.hour).to_numpy(dtype=float)
    out = pd.DataFrame(
        {
            "building_id": building_id,
            "kind": kind,
            "actual": actual.round(3),
            "expected": forecast.round(3),
            "times_typical_error": ((actual - forecast).abs().to_numpy() / scale).round(1),
        },
        index=actual.index,
    )
    return out[out["kind"] != ""].rename_axis("time").reset_index()


def alerts_for_building(
    building_id, clean_y, observed_y, weather, calendar, terms, booster, start, end=None, **kw
) -> pd.DataFrame:
    """Forecast from the observed history; typical error from the clean validation period."""
    Xc = build_features(clean_y, weather, calendar, terms)
    fc_clean = pd.Series(booster.predict(Xc), index=Xc.index)
    in_val = (clean_y.index >= VAL_START) & (clean_y.index < TEST_START)
    scale = robust_scale_by_hour((clean_y - fc_clean)[in_val])

    Xo = build_features(observed_y, weather, calendar, terms)
    fc = pd.Series(booster.predict(Xo), index=Xo.index)
    in_window = observed_y.index >= pd.Timestamp(start)
    if end is not None:
        in_window &= observed_y.index < pd.Timestamp(end)
    actual, forecast = observed_y[in_window], fc[in_window]
    keep = actual.notna()
    return detect(building_id, actual[keep], forecast[keep], scale, calendar, **kw)

def main() -> None:
    import psycopg

    from anomaly.evaluate import inject_into_meters
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
    faulty, labels = inject_into_meters(
        meters, TEST_START, 42, n_stuck=10, n_spikes=40, stuck_hours=12
    )
    frames = []
    for b in meters.columns:
        booster = lgb.Booster(model_file=str(BASE_DIR / "models" / "saved" / f"{b}_lgbm.txt"))
        frames.append(
            alerts_for_building(
                b, meters[b].asfreq("h"), faulty[b].asfreq("h"),
                weather, calendar, terms, booster, TEST_START,
            )
        )
    alerts = pd.concat(frames, ignore_index=True)
    alerts["injected"] = [
        labels.loc[t, b] if t in labels.index else "none"
        for t, b in zip(alerts["time"], alerts["building_id"])
    ]
    print(alerts.groupby(["building_id", "kind"]).size().to_string())
    print("\nStrongest 10 alerts (injected = what we planted there):")
    top = alerts.sort_values("times_typical_error", ascending=False).head(10)
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()