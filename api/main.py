"""Read-only API over the readings table. Run: python -m uvicorn api.main:app --port 8000"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from ingestion.db import get_dsn
from config.settings import get_settings
from ingestion.parser import DEFAULT_TZ
from twin.entities import Campus
from twin.state import build_twin_state

app = FastAPI(title="Smart Campus Digital Twin API", version="0.1.0")

COLS = (
    "time, reading_id, building_id, floor_id, device_id, device_type, "
    "metric, value, unit, source_type, data_quality_status, fault_label"
)


def get_conn():
    try:
        conn = psycopg.connect(get_dsn(), row_factory=dict_row)
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    try:
        yield conn
    finally:
        conn.close()


def _aware(ts: datetime) -> datetime:
    """Naive times are campus local time, matching the ingestion rule."""
    return ts if ts.tzinfo else ts.replace(tzinfo=ZoneInfo(DEFAULT_TZ))


@app.get("/health")
def health(conn=Depends(get_conn)):
    conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/readings")
def readings(
    device_id: str | None = None,
    building_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    conn=Depends(get_conn),
):
    """Readings, newest first. start is inclusive, end is exclusive."""
    clauses, params = [], []
    if device_id is not None:
        clauses.append("device_id = %s")
        params.append(device_id)
    if building_id is not None:
        clauses.append("building_id = %s")
        params.append(building_id)
    if start is not None:
        clauses.append("time >= %s")
        params.append(_aware(start))
    if end is not None:
        clauses.append("time < %s")
        params.append(_aware(end))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT {COLS} FROM readings {where} ORDER BY time DESC LIMIT %s"
    return conn.execute(sql, [*params, limit]).fetchall()


@app.get("/buildings/{building_id}/latest")
def latest(building_id: str, conn=Depends(get_conn)):
    """The newest stored reading for each device in the building."""
    sql = (
        f"SELECT DISTINCT ON (device_id) {COLS} FROM readings "
        "WHERE building_id = %s ORDER BY device_id, time DESC"
    )
    rows = conn.execute(sql, [building_id]).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=f"no readings for building {building_id}")
    return rows


@app.get("/twin/state")
def twin_state(conn=Depends(get_conn)):
    """Current state of every building, from the newest reading of each device."""
    campus = Campus.from_yaml(get_settings().campus_model_path)
    sql = f"SELECT DISTINCT ON (device_id) {COLS} FROM readings ORDER BY device_id, time DESC"
    rows = conn.execute(sql).fetchall()
    states = build_twin_state(campus, rows)
    return {"campus": campus.name, "buildings": [s.model_dump(mode="json") for s in states]}

from api.whatif import router as whatif_router  # noqa: E402
app.include_router(whatif_router)

from api.forecast import router as forecast_router  # noqa: E402
app.include_router(forecast_router)
