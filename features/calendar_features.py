"""Turn the daily academic calendar into hourly model inputs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CLASS_START_HOUR = 8
CLASS_END_HOUR = 18  # exclusive


def load_calendar(path: str | Path) -> pd.DataFrame:
    """Read data/academic_calendar.csv, indexed by date."""
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def calendar_features(index: pd.DatetimeIndex, calendar: pd.DataFrame) -> pd.DataFrame:
    """Hourly calendar features for the given timestamps (dates must be in the calendar)."""
    cal = calendar.reindex(index.normalize())
    out = pd.DataFrame(index=index)
    out["hour"] = index.hour
    out["day_of_week"] = index.day_of_week
    out["is_weekend"] = cal["is_weekend"].to_numpy(dtype=bool)
    out["is_holiday"] = cal["is_holiday"].to_numpy(dtype=bool)
    out["is_class_day"] = cal["is_class_day"].to_numpy(dtype=bool)
    out["is_finals_week"] = cal["is_finals_week"].to_numpy(dtype=bool)
    out["term"] = cal["term"].to_numpy()
    in_class_hours = (index.hour >= CLASS_START_HOUR) & (index.hour < CLASS_END_HOUR)
    out["is_class_hours"] = out["is_class_day"].to_numpy() & in_class_hours
    return out