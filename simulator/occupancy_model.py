"""Occupancy proxy (0-1) per building type from the academic calendar and hour of day.

These schedules are ASSUMPTIONS, not measurements. They give the simulator a
plausible occupancy signal; results built on them must be labelled simulated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BREAK_TERMS = {"winter_break", "spring_break"}


def _hours(bands):
    """Build a 24-value array from (start_hour, end_hour, level) bands."""
    arr = np.zeros(24)
    for start, end, level in bands:
        arr[start:end] = level
    return arr


_OFFICE_DAY = [(0, 8, 0.02), (8, 17, 0.85), (17, 19, 0.2), (19, 24, 0.02)]

# schedule name -> day kind -> 24 hourly levels
SCHEDULES = {
    "academic": {
        "class": _hours([(0, 7, 0.02), (7, 8, 0.2), (8, 18, 0.85), (18, 21, 0.3), (21, 24, 0.05)]),
        "finals": _hours([(0, 8, 0.02), (8, 18, 0.5), (18, 22, 0.2), (22, 24, 0.02)]),
        "summer": _hours([(0, 8, 0.02), (8, 17, 0.3), (17, 24, 0.03)]),
        "off": _hours([(0, 24, 0.04)]),
        "break": _hours([(0, 24, 0.02)]),
    },
    "library": {
        "class": _hours([(0, 8, 0.03), (8, 12, 0.5), (12, 18, 0.65), (18, 22, 0.8), (22, 24, 0.2)]),
        "finals": _hours([(0, 8, 0.1), (8, 24, 0.9)]),
        "summer": _hours([(0, 8, 0.02), (8, 18, 0.3), (18, 24, 0.1)]),
        "off": _hours([(0, 10, 0.03), (10, 18, 0.35), (18, 24, 0.1)]),
        "break": _hours([(0, 24, 0.05)]),
    },
    "residential": {
        "class": _hours([(0, 7, 0.95), (7, 9, 0.6), (9, 17, 0.35), (17, 22, 0.7), (22, 24, 0.95)]),
        "finals": _hours([(0, 24, 0.7)]),
        "summer": _hours([(0, 24, 0.3)]),
        "off": _hours([(0, 10, 0.9), (10, 24, 0.7)]),
        "break": _hours([(0, 24, 0.15)]),
    },
    "office": {
        "class": _hours(_OFFICE_DAY),
        "finals": _hours(_OFFICE_DAY),
        "summer": _hours(_OFFICE_DAY),
        "off": _hours([(0, 24, 0.03)]),
        "break": _hours([(0, 8, 0.02), (8, 17, 0.4), (17, 24, 0.02)]),
    },
}

TYPE_TO_SCHEDULE = {
    "academic": "academic",
    "laboratory": "academic",
    "library": "library",
    "residential": "residential",
    "office": "office",
}


def day_kind(features: pd.DataFrame) -> pd.Series:
    """Classify each hour's day as break, summer, finals, class or off (later rules override)."""
    weekday = ~features["is_weekend"] & ~features["is_holiday"]
    kind = pd.Series("off", index=features.index)
    kind[features["is_class_day"]] = "class"
    kind[features["is_finals_week"] & weekday] = "finals"
    kind[(features["term"] == "summer") & weekday] = "summer"
    kind[features["term"].isin(BREAK_TERMS)] = "break"
    return kind


def occupancy_level(features: pd.DataFrame, building_type: str) -> pd.Series:
    """Occupancy level (0-1) for every hour, for one building type."""
    schedule = SCHEDULES[TYPE_TO_SCHEDULE[building_type]]
    kinds = day_kind(features)
    levels = [schedule[k][h] for k, h in zip(kinds, features["hour"])]
    return pd.Series(levels, index=features.index, name="occupancy_level")