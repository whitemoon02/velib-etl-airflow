-- Zone « gold » : vues analytiques prêtes pour la BI

DROP VIEW IF EXISTS v_latest_status;
CREATE VIEW v_latest_status AS
SELECT s.*, d.name, d.zone, d.capacity, d.lat, d.lon
FROM fact_station_status s
JOIN dim_station d USING (station_id)
WHERE s.snapshot_ts = (SELECT MAX(snapshot_ts) FROM fact_station_status);

DROP VIEW IF EXISTS v_zone_kpis;
CREATE VIEW v_zone_kpis AS
SELECT zone,
       COUNT(*)                                   AS stations,
       SUM(num_bikes_available)                   AS velos_dispo,
       ROUND(100.0 * SUM(ebike) / NULLIF(SUM(num_bikes_available), 0), 1) AS pct_electriques,
       ROUND(100.0 * AVG(fill_rate), 1)           AS taux_remplissage_moyen,
       ROUND(100.0 * AVG(is_empty), 1)            AS pct_stations_vides,
       ROUND(100.0 * AVG(is_full), 1)             AS pct_stations_pleines
FROM v_latest_status
GROUP BY zone;

DROP VIEW IF EXISTS v_hourly_trend;
CREATE VIEW v_hourly_trend AS
SELECT substr(snapshot_ts, 1, 13) AS heure,
       SUM(num_bikes_available)   AS velos_dispo,
       ROUND(100.0 * AVG(is_empty), 1) AS pct_stations_vides
FROM fact_station_status
GROUP BY 1
ORDER BY 1;
