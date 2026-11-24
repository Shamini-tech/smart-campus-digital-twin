"""Anomaly detectors for building meter readings, and scoring against fault labels."""
from __future__ import annotations

import pandas as pd

MAD_TO_SIGMA = 1.4826  # converts median absolute deviation to a std-dev equivalent


def _mad(x: pd.Series) -> float:
    return float(MAD_TO_SIGMA * (x - x.median()).abs().median())


def robust_scale_by_hour(residuals: pd.Series) -> pd.Series:
    """Typical forecast error for each hour of day (0-23), from normal-period residuals."""
    r = residuals.dropna()
    overall = _mad(r)
    by_hour = r.groupby(r.index.hour).apply(_mad).reindex(range(24))
    by_hour = by_hour.fillna(overall)
    return by_hour.where(by_hour > 0, overall).clip(lower=1e-6)


def residual_flags(
    actual: pd.Series, forecast: pd.Series, scale_by_hour: pd.Series, k: float = 4.0
) -> pd.Series:
    """True where |actual - forecast| exceeds k times that hour's typical error."""
    resid = (actual - forecast).abs().to_numpy(dtype=float)
    limit = k * scale_by_hour.reindex(actual.index.hour).to_numpy(dtype=float)
    return pd.Series(resid > limit, index=actual.index)


def flat_run_flags(series: pd.Series, min_len: int = 6) -> pd.Series:
    """True for every point in a run of at least min_len identical, non-missing values."""
    run_id = (series != series.shift()).cumsum()
    run_len = series.groupby(run_id).transform("size")
    return (run_len >= min_len) & series.notna()


def detection_report(flags: pd.Series, labels: pd.Series) -> dict:
    """Recall per injected fault type, plus the false-alarm rate on clean ('none') rows."""
    out = {}
    for fault in sorted(set(labels.unique()) - {"none"}):
        out[f"recall_{fault}"] = round(float(flags[labels == fault].mean()), 3)
    out["false_alarm_rate"] = round(float(flags[labels == "none"].mean()), 4)
    out["flagged"] = int(flags.sum())
    return out

def persistent_flags(flags: pd.Series, min_len: int = 3) -> pd.Series:
    """Keep only flagged points that belong to a run of at least min_len consecutive flags."""
    run_id = (flags != flags.shift()).cumsum()
    run_len = flags.groupby(run_id).transform("size")
    return flags & (run_len >= min_len)