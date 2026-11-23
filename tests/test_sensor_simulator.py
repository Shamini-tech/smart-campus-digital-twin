"""Tests for the sensor simulator."""
import pandas as pd
import pytest

from simulator.sensor_simulator import simulate_readings
from twin.entities import Campus


def _inputs():
    idx = pd.date_range("2016-09-01", periods=48, freq="h")
    device = lambda i, t, u: {"id": i, "type": t, "unit": u}
    building = {
        "id": "B01", "name": "Test", "type": "academic", "floor_area_m2": 2000,
        "floors": [{"id": "F1", "devices": [
            device("meter-01", "energy_meter", "kWh"),
            device("ac-01", "hvac", "kWh"), device("ac-02", "hvac", "kWh"),
            device("light-01", "lighting", "kWh"), device("occ-01", "occupancy", "people"),
        ]}],
    }
    campus = Campus(name="c", location="l", timezone="UTC", buildings=[building])
    values = pd.DataFrame({"B01": 100.0}, index=idx)
    statuses = pd.DataFrame({"B01": "ok"}, index=idx)
    weather = pd.DataFrame({"air_temp_c": 35.0}, index=idx)
    calendar = pd.DataFrame(
        {
            "is_weekend": [False, False], "is_holiday": [False, False],
            "is_class_day": [True, True], "is_finals_week": [False, False],
            "term": ["fall", "fall"],
        },
        index=pd.to_datetime(["2016-09-01", "2016-09-02"]),
    )
    return campus, values, statuses, weather, calendar


def test_readings_shape_labels_and_values():
    r = simulate_readings(*_inputs())
    assert len(r) == 48 * 5
    assert r["reading_id"].is_unique
    assert (r.loc[r["device_type"] == "energy_meter", "source_type"] == "historical").all()
    assert (r.loc[r["device_type"] != "energy_meter", "source_type"] == "simulated").all()
    at10 = r[r["timestamp"] == "2016-09-01 10:00"].set_index("device_id")["value"]
    assert at10["meter-01"] == pytest.approx(100.0)
    assert at10["ac-01"] == pytest.approx(17.9, abs=0.01)   # 100*0.4*1.0*0.895 split over 2 units
    assert at10["occ-01"] == pytest.approx(85.0)


def test_synthetic_energy_never_exceeds_meter():
    r = simulate_readings(*_inputs())
    sums = r[r["device_type"].isin(["hvac", "lighting"])].groupby("timestamp")["value"].sum()
    meter = r[r["device_type"] == "energy_meter"].set_index("timestamp")["value"]
    assert (sums <= meter).all()