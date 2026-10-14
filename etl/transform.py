"""Transformation : aplatissement du JSON GBFS, typage, enrichissement (zone « silver »)."""
from __future__ import annotations

import pandas as pd

# Centre de Paris (Notre-Dame) pour calculer la distance au centre
CENTER_LAT, CENTER_LON = 48.8530, 2.3499


def _bike_types(types: list[dict] | None) -> tuple[int, int]:
    mech = ebike = 0
    for t in types or []:
        mech += int(t.get("mechanical", 0))
        ebike += int(t.get("ebike", 0))
    return mech, ebike


def transform_stations(info: dict) -> pd.DataFrame:
    df = pd.DataFrame(info["data"]["stations"])
    df = df.rename(columns={"stationCode": "station_code"})
    df["station_id"] = df["station_id"].astype("int64")
    df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce").fillna(0).astype(int)
    # distance approximative (équirectangulaire) en km
    lat_km = (df.lat - CENTER_LAT) * 111.0
    lon_km = (df.lon - CENTER_LON) * 111.0 * 0.656
    df["dist_center_km"] = ((lat_km ** 2 + lon_km ** 2) ** 0.5).round(2)
    df["zone"] = pd.cut(df.dist_center_km, [-1, 3, 6, 100], labels=["Centre", "Paris périphérique", "Banlieue"]).astype(str)
    return df[["station_id", "station_code", "name", "lat", "lon", "capacity", "dist_center_km", "zone"]]


def transform_status(status: dict) -> pd.DataFrame:
    df = pd.DataFrame(status["data"]["stations"])
    df["station_id"] = df["station_id"].astype("int64")
    types = df["num_bikes_available_types"].apply(_bike_types)
    df["mechanical"] = types.str[0]
    df["ebike"] = types.str[1]
    df["snapshot_ts"] = pd.to_datetime(status["lastUpdatedOther"], unit="s", utc=True).isoformat()
    df["last_reported"] = pd.to_datetime(df["last_reported"], unit="s", utc=True).astype(str)
    for col in ("is_installed", "is_renting", "is_returning"):
        df[col] = df[col].astype(int)
    return df[["snapshot_ts", "station_id", "num_bikes_available", "mechanical", "ebike",
               "num_docks_available", "is_installed", "is_renting", "is_returning", "last_reported"]]


def enrich_status(status: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Taux de remplissage et indicateur de station vide / pleine."""
    df = status.merge(stations[["station_id", "capacity"]], on="station_id", how="left")
    df["fill_rate"] = (df.num_bikes_available / df.capacity.where(df.capacity > 0)).clip(0, 1).round(3)
    df["is_empty"] = (df.num_bikes_available == 0).astype(int)
    df["is_full"] = (df.num_docks_available == 0).astype(int)
    return df.drop(columns="capacity")
