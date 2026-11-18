"""Tests for the data-quality checks."""
import numpy as np
import pandas as pd

from features.data_quality import (
    find_flat_runs,
    find_outliers,
    find_simultaneous_dips,
    missing_summary,
)


def _hours(n):
    return pd.date_range("2024-01-01", periods=n, freq="h")


def test_missing_summary_counts_nan_and_zero():
    df = pd.DataFrame({"a": [1.0, np.nan, 0.0, 3.0]}, index=_hours(4))
    out = missing_summary(df)
    assert out.loc["a", "missing_pct"] == 25.0
    assert out.loc["a", "zero_pct"] == 25.0


def test_flat_run_detects_stuck_meter():
    values = np.arange(100, dtype=float)
    values[40:70] = 5.0
    runs = find_flat_runs(pd.Series(values, index=_hours(100)), min_hours=24)
    assert len(runs) == 1
    assert runs.loc[0, "hours"] == 30


def test_flat_run_ignores_short_repeats():
    s = pd.Series([1.0, 1.0, 1.0, 2.0, 3.0], index=_hours(5))
    assert find_flat_runs(s, min_hours=24).empty


def test_simultaneous_dip_found():
    idx = _hours(24 * 14)
    rng = np.random.default_rng(0)
    df = pd.DataFrame({c: 100 + rng.normal(0, 1, len(idx)) for c in "abcd"}, index=idx)
    df.iloc[100] = 10.0
    assert list(find_simultaneous_dips(df, min_buildings=3)) == [idx[100]]


def test_outlier_spike_found():
    idx = _hours(24 * 14)
    rng = np.random.default_rng(0)
    s = pd.Series(100 + rng.normal(0, 1, len(idx)), index=idx)
    s.iloc[150] = 500.0
    assert idx[150] in find_outliers(s)