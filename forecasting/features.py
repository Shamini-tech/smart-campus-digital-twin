"""Features for day-ahead hourly forecasts.

The forecast origin is 24 hours before the target hour: every lag or rolling
feature of the building's own load uses values at least 24 hours old.
Weather and calendar columns for the target hour are used as given. Weather is
the OBSERVED value, so scores assume a perfect weather forecast.
"""
from __future__ import annotations

import pandas as pd

from features.calendar_features import calendar_features

HORIZON_H = 24


def term_categories(calendar: pd.DataFrame) -> list[str]:
    """Fixed, sorted term names so term codes mean the same in train and test."""
    return sorted(calendar["term"].dropna().unique())


def build_features(
    energy: pd.Series,
    weather: pd.DataFrame,
    calendar: pd.DataFrame,
    terms: list[str],
) -> pd.DataFrame:
    """One row per hour of `energy` (made regular); NaN where history is missing."""
    energy = energy.asfreq("h")
    idx = energy.index
    cal = calendar_features(idx, calendar)
    feats = cal.drop(columns=["term"]).astype(int)
    feats["term_code"] = pd.Categorical(cal["term"], categories=terms).codes
    feats = feats.join(weather.select_dtypes("number").reindex(idx))

    past = energy.shift(HORIZON_H)
    feats["lag_24h"] = past
    feats["lag_168h"] = energy.shift(168)
    feats["mean_24h"] = past.rolling(24, min_periods=12).mean()
    feats["mean_168h"] = past.rolling(168, min_periods=84).mean()
    return feats