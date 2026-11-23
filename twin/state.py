"""Build the live state of the campus from the latest reading of each device.

fault_label is deliberately NOT used: it is the answer key for testing the
anomaly detector, so the twin must derive its state from the readings alone.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from twin.entities import Campus

QUALITY_RANK = {"ok": 0, "imputed": 1, "missing": 2}


class BuildingState(BaseModel):
    building_id: str
    name: str
    type: str
    as_of: datetime | None
    energy_kwh: float | None
    hvac_kwh: float
    lighting_kwh: float
    occupancy: float
    hvac_share: float | None
    devices_expected: int
    devices_reporting: int
    missing_devices: list[str]
    stale_devices: list[str]
    data_quality: str


def _total(rows: list[dict], device_type: str) -> float:
    return sum((r["value"] or 0.0) for r in rows if r["device_type"] == device_type)


def build_twin_state(
    campus: Campus, latest_rows: list[dict], stale_after_hours: float = 2
) -> list[BuildingState]:
    """latest_rows: the newest reading per device, as dicts (e.g. from the API query)."""
    by_building: dict[str, list[dict]] = {}
    for row in latest_rows:
        by_building.setdefault(row["building_id"], []).append(row)

    states = []
    for b in campus.buildings:
        rows = by_building.get(b.id, [])
        expected = [d.id for d in b.all_devices()]
        reporting = {r["device_id"] for r in rows}
        as_of = max((r["time"] for r in rows), default=None)
        stale = []
        if as_of is not None:
            cutoff = as_of - timedelta(hours=stale_after_hours)
            stale = sorted(r["device_id"] for r in rows if r["time"] < cutoff)

        meter = [r["value"] for r in rows if r["device_type"] == "energy_meter"]
        meter = [v for v in meter if v is not None]
        energy = round(sum(meter), 3) if meter else None
        hvac = round(_total(rows, "hvac"), 3)
        worst = max((r["data_quality_status"] for r in rows),
                    key=lambda s: QUALITY_RANK.get(s, 0), default="missing")
        states.append(
            BuildingState(
                building_id=b.id,
                name=b.name,
                type=str(getattr(b.type, "value", b.type)),
                as_of=as_of,
                energy_kwh=energy,
                hvac_kwh=hvac,
                lighting_kwh=round(_total(rows, "lighting"), 3),
                occupancy=_total(rows, "occupancy"),
                hvac_share=round(hvac / energy, 3) if energy else None,
                devices_expected=len(expected),
                devices_reporting=len(reporting),
                missing_devices=[d for d in expected if d not in reporting],
                stale_devices=stale,
                data_quality=worst,
            )
        )
    return states