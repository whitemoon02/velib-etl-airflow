# 🚲 Vélib' ETL — pipeline open data orchestré avec Airflow

Pipeline ETL de production qui collecte toutes les 15 minutes la disponibilité des ~1 500 stations
Vélib' Métropole (API GBFS publique), fiabilise les données et alimente un entrepôt avec historique
pour analyser la tension du réseau (stations vides / pleines, part de vélos électriques).

## 🧱 Architecture médaillon

```
 API GBFS Vélib'          BRONZE              SILVER                    GOLD
 ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────────────┐
 │ station_    │──►│ JSON bruts   │──►│ Pandas : typage, │──►│ dim_station (upsert) │
 │ information │   │ horodatés    │   │ aplatissement,   │   │ fact_station_status  │
 │ station_    │   │ data/raw/    │   │ enrichissement   │   │ (historique)         │
 │ status      │   └──────────────┘   └────────┬─────────┘   │ vues KPI             │
 └─────────────┘                               │             └──────────────────────┘
                                     contrôles qualité
                                    (bloquants / alertes)

 Airflow : extract_task >> transform_task >> quality_task >> load_task   (toutes les 15 min)
```

## ✨ Points techniques

- **Orchestration Airflow** (TaskFlow API) : retries avec backoff exponentiel, `max_active_runs=1`, `catchup=False`.
- **Échanges entre tâches en Parquet**, XCom réservé aux chemins (bonne pratique Airflow).
- **Qualité des données** : unicité, coordonnées dans l'Île-de-France, valeurs non négatives, cohérence
  mécaniques + électriques = total, intégrité référentielle (alerte non bloquante).
- **Chargement idempotent** : upsert du référentiel, `INSERT OR IGNORE` sur la clé (snapshot, station) →
  relancer un run ne crée aucun doublon (testé).
- **Zone gold** : vues SQL `v_zone_kpis`, `v_latest_status`, `v_hourly_trend` prêtes pour Power BI.
- **CI GitHub Actions** : lint (ruff), tests, exécution de bout en bout hors-ligne.

## 🚀 Lancer le projet

```bash
pip install -r requirements.txt
python -m etl.run              # données live
python -m etl.run --offline    # échantillon versionné (sans réseau)
pytest -v
```

Avec Airflow :

```bash
docker compose up    # http://localhost:8080 → activer le DAG « velib_etl »
```

## 📊 Exemple de sortie (`v_zone_kpis`, échantillon hors-ligne)

| zone | stations | vélos dispo | % électriques | remplissage moyen | % stations vides |
|---|---|---|---|---|---|
| Centre | 43 | 445 | 54,4 % | 34,6 % | 48,8 % |
| Paris périphérique | 24 | 370 | 60,3 % | 42,8 % | 37,5 % |
| Banlieue | 13 | 208 | 59,1 % | 51,8 % | 15,4 % |

## 🛠️ Stack

Python · Pandas · Apache Airflow · SQL (SQLite, portable PostgreSQL) · Parquet · Docker · GitHub Actions

## 🔭 Pistes d'évolution

- Cible PostgreSQL / BigQuery, modélisation dbt
- Prévision de la disponibilité par station (séries temporelles)
- Carte de chaleur Power BI des stations en tension

Source des données : [Vélib' Métropole — open data](https://www.velib-metropole.fr/donnees-open-data-gbfs-du-service-velib-metropole) (licence ouverte).

---
👤 **Espérance DAYE** — Data Engineer · [LinkedIn](https://linkedin.com/in/Esperance-DAYE)
