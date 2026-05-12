"""Service calendar selection utilities."""
from __future__ import annotations

import pandas as pd

WEEKDAY_COLS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
WEEKEND_COLS = ["saturday", "sunday"]


def get_weekday_service_ids(calendar: pd.DataFrame) -> list[str]:
    """Return service_ids operating Monday-Friday only.

    The strict definition avoids combining weekday and weekend service patterns.
    """
    if calendar.empty:
        raise ValueError("calendar.txt is required to identify weekday service_ids.")
    required = ["service_id", *WEEKDAY_COLS, *WEEKEND_COLS]
    missing = [c for c in required if c not in calendar.columns]
    if missing:
        raise ValueError(f"calendar.txt missing required columns: {missing}")

    mask = calendar[WEEKDAY_COLS].eq(1).all(axis=1) & calendar[WEEKEND_COLS].eq(0).all(axis=1)
    return calendar.loc[mask, "service_id"].astype(str).tolist()


def select_representative_weekday_trips(trips: pd.DataFrame, calendar: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each route, keep its most frequent weekday service_id.

    This avoids the common problem where choosing one global service_id removes
    trains, ferries, regional routes, or special sub-networks.
    """
    weekday_ids = get_weekday_service_ids(calendar)
    weekday_trips = trips[trips["service_id"].isin(weekday_ids)].copy()
    if weekday_trips.empty:
        raise ValueError("No weekday trips found. Check calendar.txt and trips.txt.")

    counts = (
        weekday_trips.groupby(["route_id", "service_id"])
        .size()
        .reset_index(name="trip_count")
        .sort_values(["route_id", "trip_count"], ascending=[True, False])
    )
    selected = counts.drop_duplicates("route_id", keep="first").copy()
    selected_map = dict(zip(selected["route_id"], selected["service_id"]))

    keep_mask = weekday_trips.apply(lambda r: r["service_id"] == selected_map.get(r["route_id"]), axis=1)
    filtered = weekday_trips.loc[keep_mask].copy()
    return filtered, selected
