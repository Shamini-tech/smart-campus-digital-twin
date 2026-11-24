"""Tests for the fault injection used to score the anomaly detectors."""
import numpy as np
import pandas as pd

from anomaly.evaluate import inject_into_meters


def test_faults_are_injected_only_from_the_start_date():
    idx = pd.date_range("2017-11-01", periods=96, freq="h", name="time")
    meters = pd.DataFrame(
        {"B01": np.arange(96) + 100.0, "B02": np.arange(96) + 200.0}, index=idx
    )
    faulty, labels = inject_into_meters(
        meters, "2017-11-03", n_stuck=1, n_spikes=3, stuck_hours=6
    )
    before = meters.index < "2017-11-03"
    assert faulty[before].equals(meters[before])
    assert (labels == "spike").to_numpy().sum() == 3
    assert (labels == "stuck_meter").to_numpy().sum() == 6
    spikes = (labels == "spike").stack()
    for (ts, dev), is_spike in spikes.items():
        if is_spike:
            assert faulty.loc[ts, dev] == 3 * meters.loc[ts, dev]