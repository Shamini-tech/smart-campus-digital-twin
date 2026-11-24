"""Load hourly building meter series from the database."""
from __future__ import annotations

import pandas as pd

SQL = (
    "SELECT time, building_id, value FROM readings "
    "WHERE device_type = 'energy_meter' AND fault_label = 'none' ORDER BY time"
)


def load_meter_series(conn, tz: str = "Asia/Kolkata") -> pd.DataFrame:
    """Hourly kWh, one column per building, indexed by campus-local naive time.

    Hours with an injected fault or no value are left as NaN. Converting back
    to local time undoes the ingestion step, so the index matches the calendar
    and weather files.
    """
    rows = conn.execute(SQL).fetchall()
    df = pd.DataFrame(rows, columns=["time", "building_id", "value"])
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(tz).dt.tz_localize(None)
    return df.pivot(index="time", columns="building_id", values="value").sort_index()