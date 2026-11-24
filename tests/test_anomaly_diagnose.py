"""Tests for the false-alarm summary."""
import pandas as pd

from anomaly.diagnose import summarize


def test_summarize_rates_per_group():
    flags = pd.DataFrame(
        {
            "building": ["A", "A", "A", "A", "B", "B"],
            "critical": [True, True, False, False, False, False],
            "warning": [True, False, False, False, False, False],
        }
    )
    out = summarize(flags, "building")
    assert out.loc["A", "hours"] == 4 and out.loc["A", "critical_rate"] == 0.5
    assert out.loc["A", "warning_rate"] == 0.25
    assert out.loc["B", "critical_rate"] == 0.0