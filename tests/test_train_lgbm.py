"""Tests for the LightGBM training helpers."""
import numpy as np
import pandas as pd

from forecasting.metrics import score
from forecasting.train_lgbm import chronological_split, train_model


def _data():
    idx = pd.date_range("2016-01-01", "2016-04-30 23:00", freq="h")
    y = pd.Series(100 + 20 * np.sin(2 * np.pi * idx.hour / 24), index=idx)
    y.iloc[5] = np.nan
    X = pd.DataFrame({"hour": idx.hour}, index=idx)
    return X, y


def test_split_is_chronological_non_overlapping_and_drops_missing_targets():
    X, y = _data()
    s = chronological_split(X, y, "2016-03-01", "2016-04-01")
    assert s["train"][0].index.max() < s["val"][0].index.min()
    assert s["val"][0].index.max() < s["test"][0].index.min()
    assert len(s["train"][0]) + len(s["val"][0]) + len(s["test"][0]) == len(y) - 1


def test_model_learns_a_simple_daily_pattern():
    X, y = _data()
    s = chronological_split(X, y, "2016-03-01", "2016-04-01")
    model = train_model(s)
    Xs, ys = s["test"]
    pred = pd.Series(model.predict(Xs), index=Xs.index)
    assert score(ys, pred)["wape"] < 0.1