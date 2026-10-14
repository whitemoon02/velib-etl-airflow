"""Extraction des flux GBFS publics de Vélib' Métropole (open data, sans clé d'API)."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole"
FEEDS = ("station_information", "station_status")
ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"
RAW_DIR = ROOT / "data" / "raw"


def fetch(feed: str, retries: int = 3, timeout: int = 20) -> dict:
    url = f"{BASE_URL}/{feed}.json"
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as exc:  # réseau, HTTP, JSON
            if attempt == retries:
                raise RuntimeError(f"Échec de l'extraction de {url}") from exc
            time.sleep(2 ** attempt)  # backoff exponentiel
    raise AssertionError("unreachable")


def extract(offline: bool = False) -> dict[str, dict]:
    """Retourne les deux flux bruts et les archive dans data/raw/ (zone « bronze »)."""
    if offline:
        payloads = {f: json.loads((SAMPLE_DIR / f"{f}.json").read_text(encoding="utf-8")) for f in FEEDS}
    else:
        payloads = {f: fetch(f) for f in FEEDS}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for feed, data in payloads.items():
        (RAW_DIR / f"{feed}_{stamp}.json").write_text(json.dumps(data), encoding="utf-8")
    return payloads
