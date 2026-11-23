"""Tests for the ingestion service logic (no broker or database needed)."""
import pandas as pd

from ingestion import subscriber
from ingestion.subscriber import Ingestor
from simulator.mqtt_publisher import build_message


def _msg():
    row = pd.Series(
        {
            "timestamp": pd.Timestamp("2016-10-05 10:00"), "building_id": "B01",
            "floor_id": "F1", "device_id": "ac-01", "device_type": "hvac",
            "metric": "hvac_energy_kwh", "value": 3.5, "unit": "kWh",
            "reading_id": "ac-01-20161005T100000", "source_type": "simulated",
            "data_quality_status": "ok",
        }
    )
    return build_message(row)


def test_ingestor_batches_and_counts_rejections(monkeypatch):
    saved = []
    monkeypatch.setattr(
        subscriber, "insert_readings", lambda conn, rows: saved.append(len(rows)) or len(rows)
    )
    ing = Ingestor(conn=None, batch_size=2)
    topic, payload = _msg()
    ing.handle(topic, payload)
    ing.handle("bad/topic", payload)
    assert saved == [] and ing.rejected == 1
    ing.handle(topic, payload)
    assert saved == [2] and ing.stored == 2
    ing.flush()
    assert saved == [2]