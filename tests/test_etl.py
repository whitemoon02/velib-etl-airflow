import json
import sqlite3
from pathlib import Path

import pandas as pd

from etl.load import load
from etl.quality import DataQualityError, assert_quality
from etl.transform import enrich_status, transform_stations, transform_status

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample"


def _sample():
    info = json.loads((SAMPLE / "station_information.json").read_text(encoding="utf-8"))
    status = json.loads((SAMPLE / "station_status.json").read_text(encoding="utf-8"))
    stations = transform_stations(info)
    return stations, enrich_status(transform_status(status), stations)


def test_transform_flattens_bike_types():
    stations, status = _sample()
    assert (status.mechanical + status.ebike == status.num_bikes_available).all()
    assert status.fill_rate.between(0, 1).all()
    assert set(stations.zone) <= {"Centre", "Paris périphérique", "Banlieue"}


def test_quality_passes_on_sample():
    stations, status = _sample()
    assert_quality(stations, status)


def test_quality_blocks_duplicates():
    stations, status = _sample()
    try:
        assert_quality(pd.concat([stations, stations.iloc[:1]]), status)
    except DataQualityError:
        return
    raise AssertionError("Le doublon aurait dû bloquer le pipeline")


def test_load_is_idempotent(tmp_path):
    stations, status = _sample()
    db = tmp_path / "w.db"
    first = load(stations, status, db)
    second = load(stations, status, db)
    assert first["status_inserted"] == len(status)
    assert second["status_inserted"] == 0
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM v_zone_kpis").fetchone()[0] >= 1
