"""Parse and validate one MQTT message into a Reading."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from twin.entities import DeviceType

TOPIC_ROOT = "campus"
DEFAULT_TZ = "Asia/Kolkata"


class Reading(BaseModel):
    time: datetime
    reading_id: str
    building_id: str
    floor_id: str
    device_id: str
    device_type: DeviceType
    metric: str
    value: float | None
    unit: str
    source_type: Literal["historical", "simulated"]
    data_quality_status: str
    fault_label: str = "none"


def parse_message(topic: str, payload: str | bytes, tz: str = DEFAULT_TZ) -> Reading:
    """Return a validated Reading, or raise ValueError saying why it was rejected."""
    parts = topic.split("/")
    if len(parts) != 5 or parts[0] != TOPIC_ROOT:
        raise ValueError(f"bad topic: {topic!r}")
    _, building_id, floor_id, device_type, device_id = parts
    try:
        body = json.loads(payload)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("payload is not valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("payload must be a JSON object")
    if body.get("device_id") != device_id:
        raise ValueError("payload device_id does not match topic")
    if body.get("building_id", building_id) != building_id:
        raise ValueError("payload building_id does not match topic")
    try:
        ts = datetime.fromisoformat(body["timestamp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("missing or invalid timestamp") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo(tz))
    value = body.get("value")
    if isinstance(value, float) and math.isnan(value):
        value = None
    return Reading(
        **{
            **body,
            "time": ts.astimezone(timezone.utc),
            "building_id": building_id,
            "floor_id": floor_id,
            "device_type": device_type,
            "value": value,
        }
    )