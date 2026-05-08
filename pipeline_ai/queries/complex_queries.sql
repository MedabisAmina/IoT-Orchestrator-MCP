-- ============================================================
-- MEMBRE 4 — REQUÊTES COMPLEXES
-- Pipeline Monitoring System
-- ============================================================

-- -------------------------------------------------------
-- 1. Dernière mesure par capteur
-- -------------------------------------------------------
SELECT DISTINCT ON (m.capteur_id)
    m.capteur_id,
    c.type_mesure,
    c.unite,
    c.machine_id,
    m.valeur,
    m.timestamp
FROM mesure m
JOIN capteur c ON m.capteur_id = c.capteur_id
ORDER BY m.capteur_id, m.timestamp DESC;

-- -------------------------------------------------------
-- 2. Toutes les machines d'une zone donnée (ex: zone 'A')
-- -------------------------------------------------------
SELECT
    ma.machine_id,
    ma.type,
    ma.fabricant,
    ma.modele,
    ma.status,
    ma.disponibilite,
    st.nom_station,
    pi.nom_pipeline,
    zo.nom AS nom_zone
FROM machine ma
JOIN station  st ON ma.station_id  = st.station_id
JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
JOIN zone     zo ON pi.zone_id     = zo.zone_id
WHERE zo.zone_id = 'A'
ORDER BY ma.machine_id;

-- -------------------------------------------------------
-- 3. Historique des alertes d'une machine spécifique
-- -------------------------------------------------------
SELECT
    a.alerte_id,
    a.timestamp,
    a.type_alerte,
    a.valeur,
    a.message,
    c.type_mesure,
    c.unite,
    sc.valeur_min,
    sc.valeur_max
FROM alerte a
JOIN capteur      c  ON a.capteur_id  = c.capteur_id
JOIN seuil_capteur sc ON c.capteur_id = sc.capteur_id
WHERE c.machine_id = 'M1'
ORDER BY a.timestamp DESC;

-- -------------------------------------------------------
-- 4. Machines ayant déclenché le plus d'alertes
-- -------------------------------------------------------
SELECT
    ma.machine_id,
    ma.type,
    ma.fabricant,
    st.nom_station,
    COUNT(a.alerte_id) AS nb_alertes
FROM alerte a
JOIN capteur c  ON a.capteur_id  = c.capteur_id
JOIN machine ma ON c.machine_id  = ma.machine_id
JOIN station st ON ma.station_id = st.station_id
GROUP BY ma.machine_id, ma.type, ma.fabricant, st.nom_station
ORDER BY nb_alertes DESC;

-- -------------------------------------------------------
-- 5. État temps réel de toutes les machines avec dernière mesure
-- -------------------------------------------------------
SELECT
    ma.machine_id,
    ma.type,
    ma.status,
    ma.disponibilite,
    c.capteur_id,
    c.type_mesure,
    c.unite,
    dm.valeur       AS derniere_valeur,
    dm.timestamp    AS derniere_mesure,
    sc.valeur_min,
    sc.valeur_max,
    CASE
        WHEN dm.valeur < sc.valeur_min THEN 'SOUS_SEUIL'
        WHEN dm.valeur > sc.valeur_max THEN 'SEUIL_DEPASSE'
        ELSE 'NORMAL'
    END AS etat_seuil
FROM machine ma
JOIN capteur       c  ON ma.machine_id  = c.machine_id
JOIN seuil_capteur sc ON c.capteur_id   = sc.capteur_id
LEFT JOIN (
    SELECT DISTINCT ON (capteur_id) capteur_id, valeur, timestamp
    FROM mesure
    ORDER BY capteur_id, timestamp DESC
) dm ON c.capteur_id = dm.capteur_id
ORDER BY ma.machine_id, c.type_mesure;

-- -------------------------------------------------------
-- 6. Alertes actives par zone
-- -------------------------------------------------------
SELECT
    zo.zone_id,
    zo.nom AS zone,
    pi.nom_pipeline,
    st.nom_station,
    ma.machine_id,
    c.type_mesure,
    a.valeur,
    a.timestamp,
    a.type_alerte,
    a.message
FROM alerte a
JOIN capteur  c  ON a.capteur_id  = c.capteur_id
JOIN machine  ma ON c.machine_id  = ma.machine_id
JOIN station  st ON ma.station_id = st.station_id
JOIN pipeline pi ON st.pipeline_id= pi.pipeline_id
JOIN zone     zo ON pi.zone_id    = zo.zone_id
ORDER BY a.timestamp DESC;
