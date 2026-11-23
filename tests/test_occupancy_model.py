"""Tests for the occupancy model."""
import pandas as pd
import pytest

from simulator.occupancy_model import occupancy_level


def _row(hour, term="fall", is_class_day=False, is_weekend=False, is_holiday=False, is_finals_week=False):
    return pd.DataFrame(
        {
            "hour": [hour], "term": [term], "is_class_day": [is_class_day],
            "is_weekend": [is_weekend], "is_holiday": [is_holiday],
            "is_finals_week": [is_finals_week],
        },
        index=pd.date_range("2016-09-01", periods=1, freq="h"),
    )


def test_academic_is_busy_on_class_days_and_empty_in_breaks():
    assert occupancy_level(_row(10, is_class_day=True), "academic").iloc[0] == pytest.approx(0.85)
    assert occupancy_level(_row(10, term="winter_break"), "academic").iloc[0] == pytest.approx(0.02)


def test_residential_is_full_at_night():
    assert occupancy_level(_row(3, is_class_day=True), "residential").iloc[0] == pytest.approx(0.95)


def test_office_is_empty_on_weekends():
    assert occupancy_level(_row(10, is_weekend=True), "office").iloc[0] == pytest.approx(0.03)


def test_library_is_busy_during_finals():
    assert occupancy_level(_row(12, is_finals_week=True), "library").iloc[0] == pytest.approx(0.9)