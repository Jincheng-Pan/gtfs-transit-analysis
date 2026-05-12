"""Geometry utilities for transit routes."""
from __future__ import annotations

import math

import pandas as pd


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def trip_stop_sequence(stop_times: pd.DataFrame, stops: pd.DataFrame, trip_id: str) -> pd.DataFrame:
    """Return ordered stop sequence for a trip with stop coordinates."""
    seq = stop_times[stop_times["trip_id"] == trip_id].sort_values("stop_sequence").copy()
    if seq.empty:
        return seq
    return seq.merge(stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]], on="stop_id", how="left")


def route_length_from_stops(seq: pd.DataFrame) -> float | None:
    """Approximate route length from consecutive stop-to-stop great-circle distances."""
    if len(seq) < 2:
        return None
    total = 0.0
    for i in range(len(seq) - 1):
        a = seq.iloc[i]
        b = seq.iloc[i + 1]
        if pd.isna(a["stop_lat"]) or pd.isna(a["stop_lon"]) or pd.isna(b["stop_lat"]) or pd.isna(b["stop_lon"]):
            return None
        total += haversine_km(a["stop_lat"], a["stop_lon"], b["stop_lat"], b["stop_lon"])
    return total


def direct_distance_from_stops(seq: pd.DataFrame) -> float | None:
    """Straight-line distance between first and last stop."""
    if len(seq) < 2:
        return None
    a = seq.iloc[0]
    b = seq.iloc[-1]
    if pd.isna(a["stop_lat"]) or pd.isna(a["stop_lon"]) or pd.isna(b["stop_lat"]) or pd.isna(b["stop_lon"]):
        return None
    return haversine_km(a["stop_lat"], a["stop_lon"], b["stop_lat"], b["stop_lon"])
