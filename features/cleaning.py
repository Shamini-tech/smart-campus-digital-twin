"""Cleaning for hourly electricity readings.

Raw data in data/raw/ is never modified. Rules (see docs/decisions.md):
- exact zeros are treated as missing (a building does not draw exactly 0 kWh);
- flat runs (same value for min_flat_hours or more) are treated as stuck-meter data and masked;
- gaps of up to max_gap hours are filled by linear interpolation and marked "imputed";
- longer gaps stay empty and are marked "missing".
"""
from __future__ import annotations

import pandas as pd

from features.data_quality import find_flat_runs, load_electricity
from features.weather_client import fill_short_gaps


def clean_series(series: pd.Series, max_gap: int = 3, min_flat_hours: int = 24) -> pd.DataFrame:
    """Return a DataFrame with the cleaned value and a status for every hour."""
    masked = series.where(series != 0)
    for run in find_flat_runs(series, min_flat_hours).itertuples(index=False):
        masked.loc[run.start : run.end] = float("nan")
    filled = fill_short_gaps(masked, max_gap)
    status = pd.Series("ok", index=series.index)
    status[masked.isna() & filled.notna()] = "imputed"
    status[filled.isna()] = "missing"
    return pd.DataFrame({"value": filled, "status": status})


def clean_frame(
    df: pd.DataFrame, max_gap: int = 3, min_flat_hours: int = 24
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean every building; return (values, statuses) as wide DataFrames."""
    parts = {b: clean_series(df[b], max_gap, min_flat_hours) for b in df.columns}
    values = pd.DataFrame({b: p["value"] for b, p in parts.items()})
    statuses = pd.DataFrame({b: p["status"] for b, p in parts.items()})
    return values, statuses


def main() -> None:
    from config.settings import BASE_DIR

    mapping = pd.read_csv(BASE_DIR / "config" / "building_mapping.csv")
    df = load_electricity(
        BASE_DIR / "data" / "raw" / "electricity.csv", mapping["building_id"].tolist()
    )
    values, statuses = clean_frame(df)
    out_dir = BASE_DIR / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    values.to_csv(out_dir / "electricity_clean.csv")
    statuses.to_csv(out_dir / "electricity_status.csv")
    print(f"Wrote cleaned data to {out_dir}")
    print(statuses.apply(pd.Series.value_counts).fillna(0).astype(int).to_string())


if __name__ == "__main__":
    main()