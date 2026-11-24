"""Tests for the forecasting features."""
import numpy as np
import pandas as pd
import pytest

from forecasting.features import build_features, term_categories


def _inputs(n=400):
    idx = pd.date_range("2016-09-01", periods=n, freq="h")
    energy = pd.Series(np.arange(n, dtype=float), index=idx)
    weather = pd.DataFrame({"air_temp_c": 30.0}, index=idx)
    days = pd.date_range("2016-09-01", periods=30, freq="D")
    calendar = pd.DataFrame(
        {
            "is_weekend": days.day_of_week >= 5, "is_holiday": False,
            "is_class_day": days.day_of_week < 5, "is_finals_week": False,
            "term": "fall",
        },
        index=days,
    )
    return energy, weather, calendar


def _build(energy, weather, calendar):
    return build_features(energy, weather, calendar, term_categories(calendar))


def test_columns_and_lag_values():
    f = _build(*_inputs())
    for col in ["lag_24h", "lag_168h", "mean_24h", "mean_168h", "term_code", "air_temp_c", "hour"]:
        assert col in f.columns
    assert f["lag_24h"].iloc[30] == 6.0
    assert f["lag_168h"].iloc[200] == 32.0


def test_no_leakage_from_the_last_day():
    energy, weather, calendar = _inputs()
    changed = energy.copy()
    changed.iloc[100] = 1e9
    f1, f2 = _build(energy, weather, calendar), _build(changed, weather, calendar)
    for col in ["lag_24h", "lag_168h", "mean_24h", "mean_168h"]:
        pd.testing.assert_series_equal(f1[col].iloc[:124], f2[col].iloc[:124])


def test_missing_hour_in_the_index_is_restored_as_nan():
    energy, weather, calendar = _inputs()
    f = _build(energy.drop(energy.index[10]), weather, calendar)
    assert len(f) == 400
    assert f["lag_24h"].iloc[30] == 6.0
    assert np.isnan(f["lag_24h"].iloc[34])  # hour 34 looks back to the missing hour 10
