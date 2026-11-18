"""Tests for the weather loader."""
import numpy as np
import pandas as pd

from features.weather_client import fill_short_gaps, load_site_weather, relative_humidity


def test_relative_humidity_known_values():
    assert abs(relative_humidity(20.0, 20.0) - 100.0) < 0.1
    assert abs(relative_humidity(30.0, 10.0) - 28.9) < 0.5


def test_fill_short_gaps_only_fills_short_runs():
    s = pd.Series([1.0, np.nan, np.nan, 4.0, 5.0, np.nan, np.nan, np.nan, np.nan, np.nan, 11.0])
    out = fill_short_gaps(s, max_gap=3)
    assert out.iloc[1] == 2.0 and out.iloc[2] == 3.0
    assert out.iloc[5:10].isna().all()


def test_load_site_weather_fills_missing_hour(tmp_path):
    csv = tmp_path / "w.csv"
    csv.write_text(
        "timestamp,site_id,airTemperature,dewTemperature,windSpeed\n"
        "2016-01-01 00:00:00,Fox,10,0,2\n"
        "2016-01-01 02:00:00,Fox,14,4,4\n"
        "2016-01-01 00:00:00,Other,99,99,99\n"
    )
    df = load_site_weather(csv, "Fox")
    assert len(df) == 3
    assert df["air_temp_c"].iloc[1] == 12.0
    assert "rel_humidity_pct" in df.columns