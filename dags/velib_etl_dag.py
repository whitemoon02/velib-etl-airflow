"""DAG Airflow : ETL Vélib' toutes les 15 minutes, avec contrôles qualité entre transformation et chargement.

extract >> transform >> quality_checks >> load
Les DataFrames transitent par des fichiers Parquet (et non par XCom, réservé aux petites métadonnées).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
STAGING = PROJECT / "data" / "staging"

default_args = {
    "owner": "esperance",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
}


@dag(
    dag_id="velib_etl",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["open-data", "etl", "velib"],
)
def velib_etl():

    @task
    def extract_task() -> dict:
        from etl.extract import extract
        import json
        raw = extract()
        STAGING.mkdir(parents=True, exist_ok=True)
        paths = {}
        for feed, data in raw.items():
            p = STAGING / f"{feed}.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            paths[feed] = str(p)
        return paths

    @task
    def transform_task(paths: dict) -> dict:
        import json
        from etl.transform import enrich_status, transform_stations, transform_status
        info = json.loads(Path(paths["station_information"]).read_text(encoding="utf-8"))
        status = json.loads(Path(paths["station_status"]).read_text(encoding="utf-8"))
        stations = transform_stations(info)
        enriched = enrich_status(transform_status(status), stations)
        stations.to_parquet(STAGING / "stations.parquet", index=False)
        enriched.to_parquet(STAGING / "status.parquet", index=False)
        return {"stations": str(STAGING / "stations.parquet"), "status": str(STAGING / "status.parquet")}

    @task
    def quality_task(paths: dict) -> dict:
        import pandas as pd
        from etl.quality import assert_quality
        assert_quality(pd.read_parquet(paths["stations"]), pd.read_parquet(paths["status"]))
        return paths

    @task
    def load_task(paths: dict) -> dict:
        import pandas as pd
        from etl.load import load
        return load(pd.read_parquet(paths["stations"]), pd.read_parquet(paths["status"]))

    load_task(quality_task(transform_task(extract_task())))


velib_etl()
