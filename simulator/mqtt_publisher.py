"""Publish simulated readings to MQTT.

Topic:   campus/{building_id}/{floor_id}/{device_type}/{device_id}
Payload: JSON. The timestamp is ISO 8601 campus local time WITHOUT an offset
(the source data has no timezone); ingestion applies the campus timezone.
"""
from __future__ import annotations

import json
import time

import pandas as pd

TOPIC_ROOT = "campus"
PAYLOAD_FIELDS = [
    "device_id", "timestamp", "metric", "value", "unit", "reading_id",
    "building_id", "source_type", "data_quality_status", "fault_label",
]


def build_message(row: pd.Series) -> tuple[str, str]:
    """Return (topic, json_payload) for one reading row."""
    topic = (
        f"{TOPIC_ROOT}/{row['building_id']}/{row['floor_id']}/"
        f"{row['device_type']}/{row['device_id']}"
    )
    payload: dict = {}
    for field in PAYLOAD_FIELDS:
        v = row.get(field)
        if v is None:
            continue
        if field == "timestamp":
            v = pd.Timestamp(v).isoformat()
        elif field == "value":
            v = None if pd.isna(v) else float(v)
        else:
            v = str(v)
        payload[field] = v
    return topic, json.dumps(payload)


def publish_readings(client, readings: pd.DataFrame, delay_s: float = 0.0, qos: int = 1) -> int:
    """Publish hour by hour; wait delay_s seconds between simulated hours."""
    sent = 0
    info = None
    for _, hour in readings.groupby("timestamp", sort=True):
        for _, row in hour.iterrows():
            topic, payload = build_message(row)
            info = client.publish(topic, payload, qos=qos)
            sent += 1
        if delay_s:
            time.sleep(delay_s)
    if info is not None:
        info.wait_for_publish()
    return sent