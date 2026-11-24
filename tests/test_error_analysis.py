"""Tests for the error-analysis helpers."""
import pandas as pd
import pytest

from forecasting.error_analysis import breakdown, day_type, worst_days


def test_day_type_precedence():
    cal = pd.DataFrame(
        {
            "is_class_day": [True, False, False, True, False],
            "is_weekend": [False, True, False, False, False],
            "is_finals_week": [False, False, True, False, False],
            "is_holiday": [False, False, False, True, False],
        }
    )
    assert list(day_type(cal)) == ["class_day", "weekend", "finals_week", "holiday", "no_class_weekday"]


def test_breakdown_wape_per_day_type():
    idx = pd.date_range("2016-11-01", periods=4, freq="h")
    actual = pd.Series([100.0] * 4, index=idx)
    labels = pd.Series(["A", "A", "B", "B"], index=idx)
    fc = pd.Series([110.0, 90.0, 100.0, 100.0], index=idx)
    out = breakdown(actual, {"m": fc}, labels).set_index("day_type")
    assert out.loc["A", "m"] == pytest.approx(0.1)
    assert out.loc["B", "m"] == pytest.approx(0.0)


def test_worst_days_finds_the_bad_day():
    idx = pd.date_range("2016-11-01", periods=48, freq="h")
    actual = pd.Series(100.0, index=idx)
    fc = pd.Series([100.0] * 24 + [150.0] * 24, index=idx)
    labels = pd.Series("class_day", index=idx)
    w = worst_days(actual, fc, labels, n=1)
    assert w.index[0] == pd.Timestamp("2016-11-02")
    assert w["wape"].iloc[0] == pytest.approx(0.5)