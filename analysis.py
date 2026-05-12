"""Core GTFS analysis functions."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .geometry import direct_distance_from_stops, route_length_from_stops, trip_stop_sequence
from .io import load_gtfs, minutes_to_hhmm
from .services import select_representative_weekday_trips


def build_first_departures(stop_times: pd.DataFrame, trips: pd.DataFrame) -> pd.DataFrame:
    """Build one row per trip using first-stop departure/arrival time."""
    first = (
        stop_times.sort_values(["trip_id", "stop_sequence"])
        .groupby("trip_id", as_index=False)
        .first()
    )
    cols = ["trip_id", "event_min"]
    dep = first[cols].rename(columns={"event_min": "departure_min"})
    merge_cols = [c for c in ["trip_id", "route_id", "service_id", "trip_headsign", "direction_id", "shape_id"] if c in trips.columns]
    return dep.merge(trips[merge_cols], on="trip_id", how="inner")


def choose_representative_trip(stop_times: pd.DataFrame, trip_ids: Iterable[str]) -> str | None:
    """Choose the trip with the largest number of stops as representative."""
    trip_ids = list(trip_ids)
    if not trip_ids:
        return None
    lengths = stop_times[stop_times["trip_id"].isin(trip_ids)].groupby("trip_id").size()
    if lengths.empty:
        return None
    return lengths.idxmax()


def compute_in_vehicle_time(stop_times: pd.DataFrame, trip_id: str) -> float | None:
    seq = stop_times[stop_times["trip_id"] == trip_id].sort_values("stop_sequence")
    if len(seq) < 2:
        return None
    start = seq.iloc[0]["event_min"]
    end = seq.iloc[-1]["arrival_min"] if "arrival_min" in seq.columns else seq.iloc[-1]["event_min"]
    if pd.isna(start) or pd.isna(end):
        return None
    return float(end - start)


def _headway_from_span(first_time: float, last_time: float, n_trips: int) -> float | None:
    if n_trips <= 1:
        return None
    return float((last_time - first_time) / (n_trips - 1))


def _window_stats(df: pd.DataFrame, start_min: float, end_min: float) -> tuple[int, float | None]:
    window = df[(df["departure_min"] >= start_min) & (df["departure_min"] < end_min)]
    n = len(window)
    span = end_min - start_min
    headway = span / n if n > 0 else None
    return n, headway


def analyse_feed(feed_path: str | Path, output_csv: str | Path | None = None) -> pd.DataFrame:
    """Analyse a GTFS feed by route and trip_headsign.

    Output includes service span, daily/peak trips, headways, approximate geometry,
    in-vehicle time, and average travel time.
    """
    feed = load_gtfs(feed_path)
    routes = feed["routes"]
    trips = feed["trips"]
    stop_times = feed["stop_times"]
    stops = feed["stops"]
    calendar = feed["calendar"]

    filtered_trips, selected_services = select_representative_weekday_trips(trips, calendar)
    departures = build_first_departures(stop_times, filtered_trips)

    if "trip_headsign" not in departures.columns:
        departures["trip_headsign"] = departures.get("direction_id", "unknown")
    departures["trip_headsign"] = departures["trip_headsign"].fillna("unknown")

    route_names = routes[["route_id", "route_short_name"]].drop_duplicates("route_id") if "route_short_name" in routes.columns else routes[["route_id"]].assign(route_short_name=None)
    service_lookup = selected_services[["route_id", "service_id"]].rename(columns={"service_id": "selected_service_id"})

    results: list[dict] = []
    for route_id, route_df in departures.groupby("route_id"):
        for headsign, dir_df in route_df.groupby("trip_headsign"):
            dir_df = dir_df.dropna(subset=["departure_min"]).sort_values("departure_min")
            if dir_df.empty:
                continue

            first_time = float(dir_df["departure_min"].iloc[0])
            last_time = float(dir_df["departure_min"].iloc[-1])
            n_daily = len(dir_df)
            headway_daily = _headway_from_span(first_time, last_time, n_daily)

            trips_am, headway_am = _window_stats(dir_df, 7 * 60, 9 * 60)
            trips_pm, headway_pm = _window_stats(dir_df, 16 * 60, 18 * 60)

            rep_trip = choose_representative_trip(stop_times, dir_df["trip_id"])
            route_length = direct_dist = circuity = in_vehicle = avg_travel = None
            if rep_trip is not None:
                seq = trip_stop_sequence(stop_times, stops, rep_trip)
                route_length = route_length_from_stops(seq)
                direct_dist = direct_distance_from_stops(seq)
                if route_length is not None and direct_dist and direct_dist > 0:
                    circuity = route_length / direct_dist
                in_vehicle = compute_in_vehicle_time(stop_times, rep_trip)
                if in_vehicle is not None and headway_daily is not None:
                    avg_travel = in_vehicle + headway_daily / 2

            route_name_match = route_names.loc[route_names["route_id"] == route_id, "route_short_name"]
            route_name = route_name_match.iloc[0] if not route_name_match.empty else route_id
            selected_service_match = service_lookup.loc[service_lookup["route_id"] == route_id, "selected_service_id"]
            selected_service = selected_service_match.iloc[0] if not selected_service_match.empty else None

            results.append({
                "route_id": route_id,
                "route_name": route_name,
                "direction_headsign": headsign,
                "selected_service_id": selected_service,
                "representative_trip_id": rep_trip,
                "first_departure": minutes_to_hhmm(first_time),
                "last_departure": minutes_to_hhmm(last_time),
                "trips_daily": n_daily,
                "headway_daily_min": round(headway_daily, 2) if headway_daily is not None else None,
                "trips_am_peak": trips_am,
                "headway_am_peak_min": round(headway_am, 2) if headway_am is not None else None,
                "trips_pm_peak": trips_pm,
                "headway_pm_peak_min": round(headway_pm, 2) if headway_pm is not None else None,
                "route_length_km_approx": round(route_length, 2) if route_length is not None else None,
                "direct_distance_km": round(direct_dist, 2) if direct_dist is not None else None,
                "circuity": round(circuity, 2) if circuity is not None else None,
                "in_vehicle_time_min": round(in_vehicle, 2) if in_vehicle is not None else None,
                "avg_travel_time_min": round(avg_travel, 2) if avg_travel is not None else None,
            })

    out = pd.DataFrame(results).sort_values(["route_name", "route_id", "direction_headsign"]).reset_index(drop=True)
    if output_csv is not None:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return out


def export_route_od(feed_path: str | Path, route_short_name: str, direction_id: str | None, output_csv: str | Path) -> pd.DataFrame:
    """Export all upstream-downstream stop-pair travel times for one representative route trip."""
    feed = load_gtfs(feed_path)
    routes, trips, stop_times, stops = feed["routes"], feed["trips"], feed["stop_times"], feed["stops"]
    route_ids = routes.loc[routes["route_short_name"] == str(route_short_name), "route_id"].tolist()
    if not route_ids:
        raise ValueError(f"Route short name not found: {route_short_name}")
    route_trips = trips[trips["route_id"].isin(route_ids)].copy()
    if direction_id is not None and "direction_id" in route_trips.columns:
        route_trips = route_trips[route_trips["direction_id"] == str(direction_id)]
    rep_trip = choose_representative_trip(stop_times, route_trips["trip_id"])
    if rep_trip is None:
        raise ValueError("No representative trip found.")
    seq = trip_stop_sequence(stop_times, stops, rep_trip).reset_index(drop=True)
    rows = []
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            rows.append({
                "from_stop_id": seq.loc[i, "stop_id"],
                "from_stop_name": seq.loc[i, "stop_name"],
                "to_stop_id": seq.loc[j, "stop_id"],
                "to_stop_name": seq.loc[j, "stop_name"],
                "travel_time_min": float(seq.loc[j, "arrival_min"] - seq.loc[i, "arrival_min"]),
                "representative_trip_id": rep_trip,
            })
    od = pd.DataFrame(rows)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    od.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return od
