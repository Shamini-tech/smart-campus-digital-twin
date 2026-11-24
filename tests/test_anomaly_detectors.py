"""Tests for the anomaly detectors."""
import numpy as np
import pandas as pd
import pytest

from anomaly.detectors import (
    detection_report, flat_run_flags, residual_flags, robust_scale_by_hour,
)


def test_scale_falls_back_to_overall_when_an_hour_has_no_spread():
    idx = pd.date_range("2017-09-01", periods=240, freq="h")
    resid = pd.Series([1.0 if h % 2 == 0 else -1.0 for h in idx.hour], index=idx)
    scale = robust_scale_by_hour(resid)
    assert len(scale) == 24
    assert scale.to_numpy() == pytest.approx(1.4826)


def test_residual_flags_catch_a_spike():
    idx = pd.date_range("2017-11-01", periods=48, freq="h")
    actual = pd.Series(100.0, index=idx)
    actual.iloc[30] = 150.0
    forecast = pd.Series(100.0, index=idx)
    scale = pd.Series(2.0, index=range(24))
    flags = residual_flags(actual, forecast, scale, k=4.0)
    assert flags.sum() == 1 and flags.iloc[30]


def test_flat_run_flags_mark_whole_runs_only():
    s = pd.Series([1, 2, 3, 3, 3, 3, 3, 3, 4, 5, 5], dtype=float)
    flags = flat_run_flags(s, min_len=6)
    assert list(flags[flags].index) == [2, 3, 4, 5, 6, 7]


def test_detection_report():
    labels = pd.Series(["none", "spike", "stuck_meter", "stuck_meter", "none"])
    flags = pd.Series([False, True, True, False, True])
    r = detection_report(flags, labels)
    assert r["recall_spike"] == 1.0
    assert r["recall_stuck_meter"] == 0.5
    assert r["false_alarm_rate"] == 0.5
    assert r["flagged"] == 3

def test_persistent_flags_keep_only_long_runs():
    from anomaly.detectors import persistent_flags

    flags = pd.Series([False, True, True, False, True, True, True, False])
    out = persistent_flags(flags, min_len=3)
    assert list(out[out].index) == [4, 5, 6]