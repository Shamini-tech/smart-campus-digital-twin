"""Weather inputs for forecasting features.

Loads hourly weather for one BDG2 site and derives relative humidity.
Fetching Coimbatore weather from Open-Meteo is a later, optional extra.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

KEEP = {
    "airTemperature": "air_temp_c",
    "dewTemperature": "dew_point_c",
    "windSpeed": "wind_speed_ms",
}


def relative_humidity(air_temp_c, dew_point_c):
    """Relative humidity (%) from air and dew-point temperature (Magnus formula)."""
    a, b = 17.625, 243.04
    rh = 100 * np.exp(a * dew_point_c / (b + dew_point_c)) / np.exp(a * air_temp_c / (b + air_temp_c))
    return np.clip(rh, 0, 100)


def fill_short_gaps(s: pd.Series, max_gap: int = 3) -> pd.Series:
    """Linearly fill runs of missing values no longer than max_gap; leave longer gaps empty."""
    gap_id = s.notna().cumsum()
    gap_len = s.isna().groupby(gap_id).transform("sum")
    filled = s.interpolate(limit_area="inside")
    return s.where(~(s.isna() & (gap_len <= max_gap)), filled)


def load_site_weather(path: str | Path, site_id: str, max_gap_hours: int = 3) -> pd.DataFrame:
    """Hourly weather for one site: complete hourly index, short gaps filled, humidity added."""
    raw = pd.read_csv(path, parse_dates=["timestamp"])
    site = raw[raw["site_id"] == site_id].set_index("timestamp").sort_index()
    site = site[~site.index.duplicated(keep="first")]
    df = site[list(KEEP)].rename(columns=KEEP)
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="h"))
    df.index.name = "timestamp"
    for col in df.columns:
        df[col] = fill_short_gaps(df[col], max_gap_hours)
    df["rel_humidity_pct"] = relative_humidity(df["air_temp_c"], df["dew_point_c"]).round(1)
    return df