"""Route comparison helpers for before/after GTFS feeds."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .analysis import export_route_od


def compare_od_times(old_od_csv: str | Path, new_od_csv: str | Path, output_csv: str | Path) -> pd.DataFrame:
    """Compare OD travel-time tables with from/to stop IDs.

    The input files should contain columns:
    - from_stop_id / to_stop_id / travel_time_min, or
    - from / to / time.
    """
    old = pd.read_csv(old_od_csv, dtype=str)
    new = pd.read_csv(new_od_csv, dtype=str)

    old = _standardise_od_columns(old, "old")
    new = _standardise_od_columns(new, "new")

    merged = old.merge(new, on=["from_stop_id", "to_stop_id"], how="inner")
    merged["travel_time_min_old"] = pd.to_numeric(merged["travel_time_min_old"], errors="coerce")
    merged["travel_time_min_new"] = pd.to_numeric(merged["travel_time_min_new"], errors="coerce")
    merged["difference_min"] = merged["travel_time_min_new"] - merged["travel_time_min_old"]
    merged["time_change_ratio"] = merged["difference_min"] / merged["travel_time_min_old"].replace(0, pd.NA)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return merged


def _standardise_od_columns(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
    rename_map = {}
    if "from" in df.columns:
        rename_map["from"] = "from_stop_id"
    if "to" in df.columns:
        rename_map["to"] = "to_stop_id"
    if "time" in df.columns:
        rename_map["time"] = "travel_time_min"
    df = df.rename(columns=rename_map)
    required = ["from_stop_id", "to_stop_id", "travel_time_min"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"OD table missing columns: {missing}")
    df = df[required].copy()
    return df.rename(columns={"travel_time_min": f"travel_time_min_{suffix}"})
