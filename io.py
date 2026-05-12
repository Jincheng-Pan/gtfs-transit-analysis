"""Input/output utilities for GTFS feeds."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

GTFS_TABLES = ["agency", "routes", "trips", "stop_times", "stops", "calendar", "calendar_dates", "shapes"]


def _read_table(feed_path: Path, table_name: str, required: bool = False) -> pd.DataFrame:
    file_path = feed_path / f"{table_name}.txt"
    if not file_path.exists():
        if required:
            raise FileNotFoundError(f"Required GTFS file not found: {file_path}")
        return pd.DataFrame()
    return pd.read_csv(file_path, dtype=str, low_memory=False)


def load_gtfs(feed_path: str | Path) -> Dict[str, pd.DataFrame]:
    """Load common GTFS text files as string-typed pandas DataFrames.

    GTFS identifiers are read as strings to avoid merge errors such as int64/object
    mismatches on fields like stop_id, route_id, service_id, and trip_id.
    """
    path = Path(feed_path)
    if not path.exists():
        raise FileNotFoundError(f"GTFS folder does not exist: {path}")

    feed = {name: _read_table(path, name, required=name in {"routes", "trips", "stop_times", "stops"}) for name in GTFS_TABLES}
    clean_gtfs(feed)
    return feed


def clean_gtfs(feed: Dict[str, pd.DataFrame]) -> None:
    """Strip whitespace and convert selected numeric fields."""
    for df in feed.values():
        if df.empty:
            continue
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()

    stop_times = feed.get("stop_times", pd.DataFrame())
    if not stop_times.empty:
        if "stop_sequence" in stop_times.columns:
            stop_times["stop_sequence"] = pd.to_numeric(stop_times["stop_sequence"], errors="coerce")
        if "arrival_time" in stop_times.columns:
            stop_times["arrival_min"] = stop_times["arrival_time"].map(time_to_minutes)
        if "departure_time" in stop_times.columns:
            stop_times["departure_min"] = stop_times["departure_time"].map(time_to_minutes)
            stop_times["event_min"] = stop_times["departure_min"].fillna(stop_times.get("arrival_min"))
        elif "arrival_min" in stop_times.columns:
            stop_times["departure_min"] = stop_times["arrival_min"]
            stop_times["event_min"] = stop_times["arrival_min"]

    stops = feed.get("stops", pd.DataFrame())
    if not stops.empty:
        for col in ["stop_lat", "stop_lon"]:
            if col in stops.columns:
                stops[col] = pd.to_numeric(stops[col], errors="coerce")

    calendar = feed.get("calendar", pd.DataFrame())
    if not calendar.empty:
        for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if col in calendar.columns:
                calendar[col] = pd.to_numeric(calendar[col], errors="coerce").fillna(0).astype(int)


def time_to_minutes(value: str | float | int | None) -> float:
    """Convert GTFS HH:MM:SS to minutes after service-day midnight.

    Supports GTFS times beyond 24:00:00.
    """
    if value is None or pd.isna(value):
        return float("nan")
    text = str(value).strip()
    try:
        h, m, s = map(int, text.split(":"))
        return h * 60 + m + s / 60
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid GTFS time value: {value!r}") from exc


def minutes_to_hhmm(minutes: float | None) -> str | None:
    """Format minutes after service-day midnight as HH:MM."""
    if minutes is None or pd.isna(minutes):
        return None
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"
