"""Contrôles qualité exécutés avant chargement. Un contrôle bloquant en échec arrête le pipeline."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    blocking: bool = True


class DataQualityError(Exception):
    pass


def run_checks(stations: pd.DataFrame, status: pd.DataFrame) -> list[CheckResult]:
    checks = [
        CheckResult("stations_non_vide", len(stations) > 0, f"{len(stations)} stations"),
        CheckResult("station_id_unique", stations.station_id.is_unique,
                    f"{stations.station_id.duplicated().sum()} doublons"),
        CheckResult("coordonnees_ile_de_france",
                    bool(stations.lat.between(48.5, 49.2).all() and stations.lon.between(1.9, 2.8).all()),
                    "lat ∈ [48.5, 49.2], lon ∈ [1.9, 2.8]"),
        CheckResult("velos_non_negatifs",
                    bool((status[["num_bikes_available", "num_docks_available"]] >= 0).all().all()),
                    "aucune valeur négative"),
        CheckResult("types_coherents",
                    bool((status.mechanical + status.ebike == status.num_bikes_available).all()),
                    "mécaniques + électriques = total"),
    ]
    orphans = (~status.station_id.isin(stations.station_id)).sum()
    checks.append(CheckResult("integrite_referentielle", orphans == 0,
                              f"{orphans} statuts sans station", blocking=False))
    return checks


def assert_quality(stations: pd.DataFrame, status: pd.DataFrame) -> list[CheckResult]:
    results = run_checks(stations, status)
    for r in results:
        flag = "✅" if r.passed else ("❌" if r.blocking else "⚠️ ")
        print(f"  {flag} {r.name:28s} {r.detail}")
    failed = [r.name for r in results if r.blocking and not r.passed]
    if failed:
        raise DataQualityError(f"Contrôles bloquants en échec : {failed}")
    return results
