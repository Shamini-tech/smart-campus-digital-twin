"""Tests for forecast and anomaly endpoints (skipped if the database is not running)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _db_or_skip():
    r = client.get("/forecast/B01", params={"date": "2017-11-15"})
    if r.status_code == 503:
        pytest.skip("database not available")
    return r


def test_forecast_day_has_24_hours_and_split_label():
    r = _db_or_skip()
    body = r.json()
    assert r.status_code == 200 and len(body["hours"]) == 24
    assert body["period"].startswith("test")


def test_forecast_train_day_is_labelled_in_sample():
    _db_or_skip()
    body = client.get("/forecast/B01", params={"date": "2017-03-15"}).json()
    assert "NOT a fair score" in body["period"]


def test_forecast_unknown_building():
    _db_or_skip()
    assert client.get("/forecast/B99").status_code == 404


def test_anomalies_demo_flag_changes_note():
    _db_or_skip()
    a = client.get("/anomalies", params={"start": "2017-11-01", "end": "2017-11-08"}).json()
    b = client.get("/anomalies", params={"start": "2017-11-01", "end": "2017-11-08", "demo_faults": True}).json()
    assert "no injected faults" in a["note"] and "SYNTHETIC" in b["note"]