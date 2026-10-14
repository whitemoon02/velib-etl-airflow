"""Chargement : référentiel des stations en upsert, statuts en historique append-only (idempotent)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "warehouse.db"

DDL = """
CREATE TABLE IF NOT EXISTS dim_station (
    station_id INTEGER PRIMARY KEY, station_code TEXT, name TEXT, lat REAL, lon REAL,
    capacity INTEGER, dist_center_km REAL, zone TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS fact_station_status (
    snapshot_ts TEXT, station_id INTEGER, num_bikes_available INTEGER, mechanical INTEGER, ebike INTEGER,
    num_docks_available INTEGER, is_installed INTEGER, is_renting INTEGER, is_returning INTEGER,
    last_reported TEXT, fill_rate REAL, is_empty INTEGER, is_full INTEGER,
    PRIMARY KEY (snapshot_ts, station_id)
);
"""


def load(stations: pd.DataFrame, status: pd.DataFrame, db_path: Path | str = DEFAULT_DB) -> dict[str, int]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(DDL)
        cols = list(stations.columns)
        con.executemany(
            f"INSERT INTO dim_station ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
            f"ON CONFLICT(station_id) DO UPDATE SET "
            + ", ".join(f"{c}=excluded.{c}" for c in cols if c != "station_id")
            + ", updated_at=CURRENT_TIMESTAMP",
            stations.itertuples(index=False, name=None),
        )
        cols = list(status.columns)
        before = con.total_changes
        # INSERT OR IGNORE : relancer le même snapshot ne crée pas de doublon
        con.executemany(
            f"INSERT OR IGNORE INTO fact_station_status ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            status.itertuples(index=False, name=None),
        )
        inserted = con.total_changes - before
        con.executescript((ROOT / "sql" / "views.sql").read_text(encoding="utf-8"))
    return {"stations": len(stations), "status_inserted": inserted}
