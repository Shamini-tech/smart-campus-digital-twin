"""Tests for the ingestion parser."""
import json

import pandas as pd
import pytest

from ingestion.parser import parse_message
from simulator.mqtt_publisher import build_message

TOPIC = "campus/B01/F1/hvac/ac-01"


def _row(**over):
    row = {
        "timestamp": pd.Timestamp("2016-10-05 10:00"), "building_id": "B01",
        "floor_id": "F1", "device_id": "ac-01", "device_type": "hvac",
        "metric": "hvac_energy_kwh", "value": 3.5, "unit": "kWh",
        "reading_id": "ac-01-20161005T100000", "source_type": "simulated",
        "data_quality_status": "ok",
    }
    row.update(over)
    return pd.Series(row)


def test_roundtrip_from_publisher_message():
    topic, payload = build_message(_row())
    r = parse_message(topic, payload)
    assert (r.device_id, r.floor_id, r.value) == ("ac-01", "F1", 3.5)
    assert r.device_type.value == "hvac"
    assert r.fault_label == "none"


def test_naive_timestamp_is_localised_then_stored_as_utc():
    topic, payload = build_message(_row())
    r = parse_message(topic, payload)
    assert r.time.isoformat() == "2016-10-05T04:30:00+00:00"  # 10:00 Asia/Kolkata


def test_missing_value_becomes_none():
    topic, payload = build_message(_row(value=float("nan")))
    assert parse_message(topic, payload).value is None


def test_bad_topic_is_rejected():
    _, payload = build_message(_row())
    for bad in ["campus/B01/hvac/ac-01", "plant/B01/F1/hvac/ac-01"]:
        with pytest.raises(ValueError):
            parse_message(bad, payload)


def test_device_id_must_match_topic():
    _, payload = build_message(_row())
    with pytest.raises(ValueError):
        parse_message("campus/B01/F1/hvac/ac-99", payload)


def test_invalid_json_is_rejected():
    with pytest.raises(ValueError):
        parse_message(TOPIC, "not json")


def test_unknown_source_type_is_rejected():
    _, payload = build_message(_row())
    body = json.loads(payload)
    body["source_type"] = "magic"
    with pytest.raises(ValueError):
        parse_message(TOPIC, json.dumps(body))