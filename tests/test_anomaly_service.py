"""Tests for the alert service."""
import numpy as np
import pandas as pd

from anomaly.service import detect


def _cal(holiday_dates=()):
    days = pd.date_range("2017-11-01", periods=3, freq="D")
    return pd.DataFrame(
        {
            "is_weekend": False,
            "is_holiday": days.isin(pd.to_datetime(list(holiday_dates))),
            "is_class_day": True, "is_finals_week": False, "term": "fall",
        },
        index=days,
    )


def _base():
    idx = pd.date_range("2017-11-01", periods=48, freq="h")
    return pd.Series(100.0 + (np.arange(48) % 5), index=idx)


SCALE = pd.Series(2.0, index=range(24))


def test_spike_and_stuck_sensor_are_reported_with_the_right_kind():
    base = _base()
    actual = base.copy()
    actual.iloc[30] = 300.0
    actual.iloc[5:13] = 77.0
    alerts = detect("B01", actual, base, SCALE, _cal())
    assert alerts["kind"].value_counts().to_dict() == {"stuck_sensor": 8, "deviation": 1}
    spike = alerts[alerts["kind"] == "deviation"].iloc[0]
    assert spike["time"] == base.index[30]
    assert spike["building_id"] == "B01" and spike["times_typical_error"] > 50


def test_holiday_doubles_the_threshold():
    base = _base()
    actual = base.copy()
    actual.iloc[30] += 20.0  # 2 Nov 06:00; threshold 12 normally, 24 on a holiday
    assert len(detect("B01", actual, base, SCALE, _cal())) == 1
    assert len(detect("B01", actual, base, SCALE, _cal(["2017-11-02"]))) == 0