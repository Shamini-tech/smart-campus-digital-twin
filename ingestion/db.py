"""Write validated readings to TimescaleDB."""
from __future__ import annotations

import os

from ingestion.parser import Reading

DEFAULT_DSN = "postgresql://campus:campus_dev@localhost:5433/campus"  # local dev only
COLUMNS = (
    "time", "reading_id", "building_id", "floor_id", "device_id", "device_type",
    "metric", "value", "unit", "source_type", "data_quality_status", "fault_label",
)
INSERT_SQL = (
    f"INSERT INTO readings ({', '.join(COLUMNS)}) "
    f"VALUES ({', '.join(['%s'] * len(COLUMNS))}) "
    "ON CONFLICT (reading_id, time) DO NOTHING"
)


def get_dsn() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DSN)


def to_row(r: Reading) -> tuple:
    return (
        r.time, r.reading_id, r.building_id, r.floor_id, r.device_id,
        r.device_type.value, r.metric, r.value, r.unit, r.source_type,
        r.data_quality_status, r.fault_label,
    )


def insert_readings(conn, readings: list[Reading]) -> int:
    """Insert a batch; rows that already exist are skipped. Returns rows inserted."""
    rows = [to_row(r) for r in readings]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, rows)
        inserted = cur.rowcount
    conn.commit()
    return inserted