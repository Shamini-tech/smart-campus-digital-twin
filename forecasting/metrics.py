"""Forecast error metrics. Pairs where either value is missing are ignored."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _valid(actual: pd.Series, forecast: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    both = pd.concat([actual, forecast], axis=1, keys=["a", "f"]).dropna()
    return both["a"].to_numpy(dtype=float), both["f"].to_numpy(dtype=float)


def mae(actual: pd.Series, forecast: pd.Series) -> float:
    a, f = _valid(actual, forecast)
    return float(np.mean(np.abs(a - f))) if len(a) else float("nan")


def rmse(actual: pd.Series, forecast: pd.Series) -> float:
    a, f = _valid(actual, forecast)
    return float(np.sqrt(np.mean((a - f) ** 2))) if len(a) else float("nan")


def wape(actual: pd.Series, forecast: pd.Series) -> float:
    """Weighted absolute percentage error: sum|error| / sum|actual| (0.1 = 10%)."""
    a, f = _valid(actual, forecast)
    return float(np.sum(np.abs(a - f)) / np.sum(np.abs(a))) if len(a) else float("nan")


def score(actual: pd.Series, forecast: pd.Series) -> dict:
    a, _ = _valid(actual, forecast)
    return {
        "wape": wape(actual, forecast),
        "mae": mae(actual, forecast),
        "rmse": rmse(actual, forecast),
        "n": int(len(a)),
    }