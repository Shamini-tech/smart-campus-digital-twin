"""Load the cleaned BDG2 consumption profiles and map them to campus buildings."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import BASE_DIR


def load_profiles(
    values_path: str | Path | None = None,
    status_path: str | Path | None = None,
    mapping_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (values, statuses) with BDG2 building ids renamed to campus ids (B01-B05)."""
    values_path = values_path or BASE_DIR / "data" / "processed" / "electricity_clean.csv"
    status_path = status_path or BASE_DIR / "data" / "processed" / "electricity_status.csv"
    mapping_path = mapping_path or BASE_DIR / "config" / "building_mapping.csv"

    mapping = pd.read_csv(mapping_path)
    rename = dict(zip(mapping["building_id"], mapping["campus_building"]))
    values = pd.read_csv(values_path, index_col=0, parse_dates=True)
    statuses = pd.read_csv(status_path, index_col=0, parse_dates=True)
    return (
        values.rename(columns=rename).sort_index(axis=1),
        statuses.rename(columns=rename).sort_index(axis=1),
    )