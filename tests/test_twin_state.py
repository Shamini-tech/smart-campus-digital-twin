"""Tests for the twin state."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from api.main import app, get_conn
from config.settings import get_settings
from twin.entities import Campus
from twin.state import build_twin_state

T = datetime(2016, 10, 5, 17, 30, tzinfo=timezone.utc)
CAMPUS = Campus.from_yaml(get_settings().campus_model_path)


def _row(device_id, dtype, value, time=T, status="ok"):
    return {"device_id": device_id, "device_type": dtype, "building_id": "B01",
            "value": value, "time": time, "data_quality_status": status}


def _b01_rows():
    return [
        _row("meter-01", "energy_meter", 50.0),
        _row("ac-01", "hvac", 2.0), _row("ac-02", "hvac", 3.0),
        _row("light-01", "lighting", 1.0), _row("light-02", "lighting", 1.0),
        _row("occ-01", "occupancy", 10.0), _row("occ-02", "occupancy", 20.0),
    ]


def _states(rows):
    return {s.building_id: s for s in build_twin_state(CAMPUS, rows)}


def test_building_totals_and_share():
    s = _states(_b01_rows())["B01"]
    assert (s.energy_kwh, s.hvac_kwh, s.lighting_kwh, s.occupancy) == (50.0, 5.0, 2.0, 30.0)
    assert s.hvac_share == 0.1
    assert s.devices_reporting == s.devices_expected == 7
    assert s.missing_devices == [] and s.stale_devices == []


def test_missing_and_stale_devices_are_reported():
    rows = [r for r in _b01_rows() if r["device_id"] != "occ-02"]
    for r in rows:
        if r["device_id"] == "ac-02":
            r["time"] = T - timedelta(hours=3)
    s = _states(rows)["B01"]
    assert s.missing_devices == ["occ-02"]
    assert s.stale_devices == ["ac-02"]


def test_building_with_no_readings():
    s = _states(_b01_rows())["B02"]
    assert s.as_of is None and s.energy_kwh is None
    assert s.devices_reporting == 0 and len(s.missing_devices) == s.devices_expected


def test_missing_meter_value_gives_no_share_and_worst_quality():
    rows = _b01_rows()
    rows[0] = _row("meter-01", "energy_meter", None, status="missing")
    s = _states(rows)["B01"]
    assert s.energy_kwh is None and s.hvac_share is None
    assert s.data_quality == "missing"


class _Result:
    def fetchall(self):
        return []


class _Conn:
    def execute(self, sql, params=None):
        return _Result()


def test_twin_state_endpoint_lists_every_building():
    app.dependency_overrides[get_conn] = lambda: _Conn()
    try:
        r = TestClient(app).get("/twin/state")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()["buildings"]) == 5