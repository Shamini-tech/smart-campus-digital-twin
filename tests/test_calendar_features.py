"""Tests for the calendar features."""
import pandas as pd

from features.calendar_features import calendar_features


def _calendar():
    return pd.DataFrame(
        {
            "is_weekend": [False, True],
            "is_holiday": [False, False],
            "is_class_day": [True, False],
            "is_finals_week": [False, False],
            "term": ["fall", "fall"],
        },
        index=pd.to_datetime(["2016-09-01", "2016-09-02"]),
    )


def test_class_hours_only_on_class_days_during_the_day():
    idx = pd.date_range("2016-09-01 06:00", periods=24, freq="h")
    out = calendar_features(idx, _calendar())
    assert out.loc["2016-09-01 09:00", "is_class_hours"]
    assert not out.loc["2016-09-01 20:00", "is_class_hours"]
    assert not out.loc["2016-09-02 03:00", "is_class_day"]
    assert (out["term"] == "fall").all()