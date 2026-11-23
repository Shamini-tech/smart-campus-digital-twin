"""Tests for the MQTT publisher (no broker needed)."""
import json

import pandas as pd

from simulator.mqtt_publisher import build_message, publish_readings


def _df(value=3.5):
    rows = []
    for t in pd.to_datetime(["2016-10-05 10:00", "2016-10-05 11:00"]):
        rows.append(
            {
                "timestamp": t, "building_id": "B01", "floor_id": "F1",
                "device_id": "ac-01", "device_type": "hvac",
                "metric": "hvac_energy_kwh", "value": value, "unit": "kWh",
                "reading_id": "ac-01-x", "source_type": "simulated",
                "data_quality_status": "ok",
            }
        )
    return pd.DataFrame(rows)


class FakeInfo:
    def wait_for_publish(self):
        pass


class FakeClient:
    def __init__(self):
        self.sent = []

    def publish(self, topic, payload, qos=1):
        self.sent.append((topic, payload))
        return FakeInfo()


def test_topic_and_payload():
    topic, payload = build_message(_df().iloc[0])
    assert topic == "campus/B01/F1/hvac/ac-01"
    body = json.loads(payload)
    assert body["timestamp"] == "2016-10-05T10:00:00"
    assert body["value"] == 3.5
    assert body["source_type"] == "simulated"
    assert "fault_label" not in body


def test_missing_value_becomes_null():
    _, payload = build_message(_df(value=float("nan")).iloc[0])
    assert json.loads(payload)["value"] is None


def test_publish_readings_sends_all_in_time_order():
    client = FakeClient()
    assert publish_readings(client, _df()) == 2
    times = [json.loads(p)["timestamp"] for _, p in client.sent]
    assert times == sorted(times)