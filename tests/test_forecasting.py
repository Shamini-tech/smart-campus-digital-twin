"""Tests for the forecasting data loader, metrics and baselines."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from forecasting.baselines import seasonal_naive
from forecasting.data import load_meter_series
from forecasting.metrics import score


def test_metrics_known_values():
    s = score(pd.Series([100.0, 200.0]), pd.Series([110.0, 180.0]))
    assert s["mae"] == pytest.approx(15.0)
    assert s["rmse"] == pytest.approx(15.811, abs=0.001)
    assert s["wape"] == pytest.approx(0.1)


def test_metrics_ignore_missing_pairs():
    s = score(pd.Series([100.0, np.nan, 200.0]), pd.Series([110.0, 5.0, 180.0]))
    assert s["n"] == 2 and s["wape"] == pytest.approx(0.1)


def test_seasonal_naive_uses_only_past_values():
    idx = pd.date_range("2016-10-01", periods=10, freq="h")
    fc = seasonal_naive(pd.Series(range(10), index=idx, dtype=float), 3)
    assert fc.loc[idx[5]] == 2.0  # hour 5 is forecast with hour 2
    assert idx[0] not in fc.index or np.isnan(fc.loc[idx[0]])


class _Conn:
    def __init__(self, rows):
        self.rows, self.sql = rows, None

    def execute(self, sql, params=None):
        self.sql = sql
        return self

    def fetchall(self):
        return self.rows


def test_loader_returns_campus_local_naive_index_and_excludes_faults():
    utc = lambda h, m=0: datetime(2016, 10, 4, h, m, tzinfo=timezone.utc)
    conn = _Conn([(utc(18, 30), "B01", 48.59), (utc(18, 30), "B02", 10.0), (utc(19, 30), "B01", 47.6)])
    df = load_meter_series(conn)
    assert "fault_label = 'none'" in conn.sql
    assert df.index[0] == pd.Timestamp("2016-10-05 00:00")  # 18:30 UTC is 00:00 in Kolkata
    assert list(df.columns) == ["B01", "B02"]
    assert df.loc["2016-10-05 00:00", "B01"] == 48.59