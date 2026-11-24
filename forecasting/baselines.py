"""Seasonal-naive baselines: repeat the value from lag_hours earlier."""
from __future__ import annotations

import pandas as pd


def seasonal_naive(series: pd.Series, lag_hours: int) -> pd.Series:
    """Forecast each hour with the value lag_hours before it (past data only)."""
    return series.shift(lag_hours, freq="h")


def main() -> None:
    import psycopg

    from forecasting.data import load_meter_series
    from forecasting.metrics import score
    from forecasting.split import TEST_START
    from ingestion.db import get_dsn

    with psycopg.connect(get_dsn()) as conn:
        meters = load_meter_series(conn)
    rows = []
    for building in meters.columns:
        actual = meters[building].loc[TEST_START:]
        for name, lag in (("naive_24h", 24), ("naive_168h", 168)):
            fc = seasonal_naive(meters[building], lag).loc[TEST_START:]
            rows.append({"building": building, "baseline": name,
                         **{k: round(v, 3) for k, v in score(actual, fc).items()}})
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()