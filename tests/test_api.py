"""Tests for the API (a fake connection stands in for the database)."""
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_conn


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        return FakeResult(self.rows)


@pytest.fixture
def make_client():
    def _make(rows=()):
        conn = FakeConn(list(rows))
        app.dependency_overrides[get_conn] = lambda: conn
        return TestClient(app), conn

    yield _make
    app.dependency_overrides.clear()


def test_health(make_client):
    client, _ = make_client()
    assert client.get("/health").json() == {"status": "ok"}


def test_readings_filters_and_limit(make_client):
    client, conn = make_client()
    assert client.get("/readings?device_id=meter-01&limit=5").status_code == 200
    sql, params = conn.calls[-1]
    assert "device_id = %s" in sql and "ORDER BY time DESC" in sql
    assert params == ["meter-01", 5]


def test_naive_start_is_treated_as_campus_local(make_client):
    client, conn = make_client()
    client.get("/readings?start=2016-10-05T00:00:00")
    assert conn.calls[-1][1][0].utcoffset() is not None


def test_limit_is_validated(make_client):
    client, _ = make_client()
    assert client.get("/readings?limit=0").status_code == 422
    assert client.get("/readings?limit=5000").status_code == 422


def test_latest_404_when_building_has_no_readings(make_client):
    client, _ = make_client([])
    assert client.get("/buildings/B99/latest").status_code == 404


def test_latest_returns_rows(make_client):
    client, _ = make_client([{"device_id": "meter-01", "value": 48.59}])
    r = client.get("/buildings/B01/latest")
    assert r.status_code == 200 and r.json()[0]["device_id"] == "meter-01"