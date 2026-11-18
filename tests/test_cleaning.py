"""Tests for the cleaning rules."""
import numpy as np
import pandas as pd

from features.cleaning import clean_series


def _s(values):
    idx = pd.date_range("2024-01-01", periods=len(values), freq="h")
    return pd.Series(values, index=idx, dtype=float)


def test_short_gap_and_zero_are_imputed():
    out = clean_series(_s([10, 0, 12, np.nan, np.nan, 18, 20]))
    assert out["value"].tolist() == [10, 11, 12, 14, 16, 18, 20]
    assert out["status"].tolist() == ["ok", "imputed", "ok", "imputed", "imputed", "ok", "ok"]


def test_long_gap_stays_missing():
    out = clean_series(_s([1, np.nan, np.nan, np.nan, np.nan, np.nan, 7]), max_gap=3)
    assert (out["status"].iloc[1:6] == "missing").all()


def test_long_flat_run_is_masked_and_not_filled():
    values = list(np.arange(1.0, 11.0)) + [5.0] * 30 + list(np.arange(11.0, 21.0))
    out = clean_series(_s(values), max_gap=3, min_flat_hours=24)
    assert (out["status"].iloc[10:40] == "missing").all()