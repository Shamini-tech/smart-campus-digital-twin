"""Tests for the what-if scenarios and carbon factor."""
import pandas as pd
import pytest

from config.settings import get_settings
from features.calendar_features import calendar_features
from optimizer.carbon import co2_kg
from optimizer.scenarios import run_scenario
from twin.entities import Campus

CAMPUS = Campus.from_yaml(get_settings().campus_model_path)


def _inputs(days=3):
    idx = pd.date_range("2017-09-04", periods=24 * days, freq="h")
    d = pd.date_range("2017-09-04", periods=days, freq="D")
    cal = pd.DataFrame(
        {"is_weekend": False, "is_holiday": False, "is_class_day": True,
         "is_finals_week": False, "term": "fall"},
        index=d,
    )
    return pd.Series(100.0, index=idx), pd.Series(35.0, index=idx), calendar_features(idx, cal)


def test_no_measures_means_no_savings():
    energy, temp, feats = _inputs()
    df = run_scenario(CAMPUS.get_building("B01"), energy, temp, feats)
    assert df["saved_kwh"].abs().sum() == 0


def test_bigger_setpoint_saves_more_and_never_exceeds_hvac_plus_lighting():
    energy, temp, feats = _inputs()
    b = CAMPUS.get_building("B01")
    s1 = run_scenario(b, energy, temp, feats, setpoint_delta_c=1.0)["saved_kwh"].sum()
    s3 = run_scenario(b, energy, temp, feats, setpoint_delta_c=3.0)["saved_kwh"].sum()
    assert 0 < s1 < s3
    allm = run_scenario(b, energy, temp, feats, 3.0, 1.0, 1.0)
    assert (allm["scenario_kwh"] > 0).all() and (allm["saved_kwh"] < energy).all()


def test_building_without_ac_gets_no_hvac_savings():
    energy, temp, feats = _inputs()
    df = run_scenario(CAMPUS.get_building("B03"), energy, temp, feats,
                      setpoint_delta_c=3.0, hvac_empty_reduction=0.8)
    assert df["hvac_saved"].abs().sum() == 0


def test_empty_hours_rule_saves_something():
    energy, temp, feats = _inputs()
    df = run_scenario(CAMPUS.get_building("B01"), energy, temp, feats, hvac_empty_reduction=0.8)
    assert df["hvac_saved"].sum() > 0 and df["lighting_saved"].sum() == 0


def test_co2_uses_the_cea_factor():
    assert co2_kg(1000) == pytest.approx(716.0)