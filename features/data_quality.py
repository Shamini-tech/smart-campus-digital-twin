"""Data-quality checks for hourly energy readings.

The functions take a wide DataFrame (hourly timestamp index, one column per
building) and return plain results, so they can be tested and reused by the
notebook, the cleaning step and the report.

Run as a script to write docs/data_quality_report.md:
    python -m features.data_quality
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_electricity(path: str | Path, buildings: list[str] | None = None) -> pd.DataFrame:
    """Load a BDG2-style wide CSV: first column is the timestamp, one column per building."""
    if buildings is None:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    wanted = set(buildings)
    df = pd.read_csv(
        path,
        usecols=lambda c: c == "timestamp" or c in wanted,
        index_col="timestamp",
        parse_dates=True,
    )
    return df[buildings]


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Percentage of missing and zero readings per building."""
    return pd.DataFrame(
        {
            "missing_pct": df.isna().mean() * 100,
            "zero_pct": (df == 0).mean() * 100,
        }
    ).round(3)


def find_flat_runs(series: pd.Series, min_hours: int = 24) -> pd.DataFrame:
    """Find stretches where the value stays exactly the same (possible stuck meter)."""
    run_id = (~series.eq(series.shift())).cumsum()
    idx = series.index.to_series()
    runs = pd.DataFrame(
        {
            "start": idx.groupby(run_id).first(),
            "end": idx.groupby(run_id).last(),
            "hours": idx.groupby(run_id).size(),
            "value": series.groupby(run_id).first(),
        }
    )
    runs = runs[(runs["hours"] >= min_hours) & runs["value"].notna()]
    return runs.reset_index(drop=True)


def find_simultaneous_dips(
    df: pd.DataFrame,
    threshold: float = 0.5,
    min_buildings: int = 4,
    window: int = 24 * 7,
) -> pd.DatetimeIndex:
    """Hours where many buildings fall far below their normal level at once."""
    ratio = df / df.rolling(window, center=True, min_periods=24).median()
    mask = (ratio < threshold).sum(axis=1) >= min_buildings
    return df.index[mask]


def find_outliers(series: pd.Series, window: int = 24 * 7, k: float = 6.0) -> pd.DatetimeIndex:
    """Readings far from the local median, measured in robust (MAD) units."""
    med = series.rolling(window, center=True, min_periods=24).median()
    dev = (series - med).abs()
    mad = dev.rolling(window, center=True, min_periods=24).median()
    flagged = dev > k * mad.where(mad > 0)
    return series.index[flagged.to_numpy()]


def _md_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(["building"] + [str(c) for c in df.columns]) + " |"
    divider = "|" + "---|" * (len(df.columns) + 1)
    rows = [
        "| " + " | ".join([str(i)] + [str(v) for v in r]) + " |"
        for i, r in zip(df.index, df.itertuples(index=False))
    ]
    return "\n".join([header, divider] + rows)


def build_report(df: pd.DataFrame, min_flat_hours: int = 24) -> str:
    """Build a markdown data-quality report for the given buildings."""
    summary = missing_summary(df)
    flat = {b: find_flat_runs(df[b], min_flat_hours) for b in df.columns}
    summary["flat_hours"] = [int(flat[b]["hours"].sum()) for b in df.columns]
    summary["outliers"] = [len(find_outliers(df[b])) for b in df.columns]
    dips = find_simultaneous_dips(df, min_buildings=max(2, len(df.columns) - 1))

    lines = [
        "# Data quality report",
        "",
        f"Period: {df.index.min()} to {df.index.max()} "
        f"({len(df)} hourly rows, {df.shape[1]} buildings).",
        "",
        "## Per-building summary",
        "",
        _md_table(summary),
        "",
        f"## Flat runs (same value for {min_flat_hours}+ hours)",
        "",
    ]
    found = False
    for building, runs in flat.items():
        for r in runs.itertuples(index=False):
            found = True
            lines.append(f"- {building}: {r.start} to {r.end} ({r.hours} hours, value {r.value})")
    if not found:
        lines.append("- None found.")
    lines += [
        "",
        "## Site-wide dips",
        "",
        f"{len(dips)} hours where nearly all buildings fall below 50% of normal at once.",
        "",
    ]
    lines += [f"- {t}" for t in dips[:20]]
    lines += ["", "Results are descriptive. Review flagged periods before removing or filling anything."]
    return "\n".join(lines) + "\n"


def main() -> None:
    from config.settings import BASE_DIR

    mapping = pd.read_csv(BASE_DIR / "config" / "building_mapping.csv")
    df = load_electricity(
        BASE_DIR / "data" / "raw" / "electricity.csv", mapping["building_id"].tolist()
    )
    out = BASE_DIR / "docs" / "data_quality_report.md"
    out.write_text(build_report(df), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
