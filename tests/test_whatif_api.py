"""Tests for the what-if API endpoints."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_carbon_factor():
    r = client.get("/carbon/factor")
    assert r.status_code == 200 and r.json()["kg_co2_per_kwh"] == 0.716


def test_whatif_named_scenario_has_campus_row_and_note():
    r = client.get("/whatif", params={"scenario": "all three", "start": "2017-07-01", "end": "2017-07-07"})
    assert r.status_code == 200
    body = r.json()
    assert "assumptions" in body["note"]
    campus = [x for x in body["results"] if x["building"] == "CAMPUS"][0]
    assert campus["saved_kwh"] > 0


def test_whatif_unknown_scenario_and_empty_range():
    assert client.get("/whatif", params={"scenario": "nope"}).status_code == 404
    assert client.get("/whatif", params={"start": "2030-01-01", "end": "2030-01-02"}).status_code == 404