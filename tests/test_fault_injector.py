"""Tests for the fault injector."""
import numpy as np
import pandas as pd

from simulator.fault_injector import inject_faults


def _readings():
    ts = pd.date_range("2016-09-01", periods=72, freq="h")
    meter = pd.DataFrame(
        {"timestamp": ts, "device_id": "meter-01", "device_type": "energy_meter",
         "value": 100.0 + np.arange(72)}
    )
    ac = pd.DataFrame(
        {"timestamp": ts, "device_id": "ac-01", "device_type": "hvac",
         "value": [5.0 if 8 <= t.hour < 18 else 1.0 for t in ts]}
    )
    df = pd.concat([meter, ac]).sort_values(["timestamp", "device_id"], ignore_index=True)
    return df


def _run(**kw):
    return inject_faults(_readings(), n_ac=1, n_stuck=1, n_spikes=3, stuck_hours=6, **kw)


def test_input_is_not_modified():
    df = _readings()
    inject_faults(df, n_ac=1, n_stuck=1, n_spikes=3, stuck_hours=6)
    assert "fault_label" not in df.columns
    assert df["value"].equals(_readings()["value"])


def test_labels_and_effects():
    out = _run()
    counts = out["fault_label"].value_counts()
    assert counts["spike"] == 3
    assert counts["stuck_meter"] == 6
    assert counts["ac_overnight"] == 8
    stuck = out[out["fault_label"] == "stuck_meter"]
    assert stuck["value"].nunique() == 1
    ac = out[out["fault_label"] == "ac_overnight"]
    assert (ac["value"] == 3.0).all()  # 60% of the 5.0 peak


def test_same_seed_gives_same_result():
    assert _run().equals(_run())

def test_short_window_skips_faults_that_do_not_fit():
    one_day = _readings().iloc[:48]
    out = inject_faults(one_day, n_ac=1, n_stuck=1, n_spikes=3, stuck_hours=6)
    labels = set(out["fault_label"])
    assert "ac_overnight" not in labels
    assert (out["fault_label"] == "spike").sum() == 3