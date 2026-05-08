-- ============================================================
-- MEMBRE 4 — DML QUERIES
-- Pipeline Monitoring System
-- Compatible avec le schéma du Membre 1
-- ============================================================

-- =========================
-- INSERT
-- =========================

-- Insérer une mesure
INSERT INTO mesure (capteur_id, valeur, timestamp)
VALUES ('C1', 75.5, NOW());

-- Insérer une alerte manuellement
INSERT INTO alerte (capteur_id, valeur, timestamp, type_alerte, message)
VALUES ('C1', 120.0, NOW(), 'Critique', 'Seuil max dépassé');

-- Insérer une maintenance
INSERT INTO maintenance (machine_id, date, type, description)
VALUES ('M1', CURRENT_DATE, 'Preventive', 'Vérification capteurs');

-- =========================
-- UPDATE
-- =========================

-- Changer le statut d'une machine
UPDATE machine SET status = 'Alarme'   WHERE machine_id = 'M1';
UPDATE machine SET status = 'EnMarche' WHERE machine_id = 'M1';
UPDATE machine SET status = 'Maintenance' WHERE machine_id = 'M1';
UPDATE machine SET status = 'Arret'    WHERE machine_id = 'M1';

-- Changer le statut d'une station
UPDATE station SET status = 'Alarme'   WHERE station_id = 'S1';
UPDATE station SET status = 'EnMarche' WHERE station_id = 'S1';

-- Mettre à jour un seuil capteur
UPDATE seuil_capteur
SET valeur_min = 5, valeur_max = 120
WHERE capteur_id = 'C1';

-- =========================
-- DELETE
-- =========================

-- Supprimer les mesures de plus de 90 jours
DELETE FROM mesure
WHERE timestamp < NOW() - INTERVAL '90 days';

-- Supprimer les alertes anciennes résolues
DELETE FROM alerte
WHERE timestamp < NOW() - INTERVAL '30 days';
