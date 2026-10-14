"""Exécution du pipeline complet en ligne de commande.

Usage :
    python -m etl.run            # données live de l'API Vélib'
    python -m etl.run --offline  # échantillon versionné dans data/sample/
"""
import argparse
import sqlite3
import time

import pandas as pd

from etl.extract import extract
from etl.load import DEFAULT_DB, load
from etl.quality import assert_quality
from etl.transform import enrich_status, transform_stations, transform_status


def run(offline: bool = False, db_path=DEFAULT_DB) -> dict:
    t0 = time.perf_counter()
    print("1/4 Extraction…")
    raw = extract(offline=offline)
    print("2/4 Transformation…")
    stations = transform_stations(raw["station_information"])
    status = enrich_status(transform_status(raw["station_status"]), stations)
    print("3/4 Contrôles qualité :")
    assert_quality(stations, status)
    print("4/4 Chargement…")
    stats = load(stations, status, db_path)
    print(f"Terminé en {time.perf_counter() - t0:.1f}s : {stats}")
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    run(offline=args.offline)
    with sqlite3.connect(DEFAULT_DB) as con:
        print("\nIndicateurs par zone :")
        print(pd.read_sql("SELECT * FROM v_zone_kpis", con).to_string(index=False))
