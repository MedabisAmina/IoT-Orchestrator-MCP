-- ============================================================
-- pipeline_db.sql — Run this in pgAdmin Query Tool
-- ============================================================

-- =========================
-- TABLE ZONE
-- =========================
CREATE TABLE zone (
    zone_id VARCHAR PRIMARY KEY,
    nom VARCHAR NOT NULL,
    region VARCHAR,
    type_zone VARCHAR NOT NULL CHECK (type_zone IN ('Nord','Sud','Maritime')),
    description TEXT
);

-- =========================
-- TABLE PIPELINE
-- =========================
CREATE TABLE pipeline (
  pipeline_id VARCHAR PRIMARY KEY,
  nom_pipeline VARCHAR NOT NULL,
  type_produit VARCHAR NOT NULL,
  localisation_geo TEXT,
  date_mise_en_service DATE,
  longueur FLOAT CHECK (longueur > 0),
  diametre FLOAT CHECK (diametre > 0),
  point_debut TEXT,
  point_fin TEXT,
  zone_id VARCHAR NOT NULL,
  FOREIGN KEY (zone_id) REFERENCES zone(zone_id),
  CHECK (type_produit IN ('PetroleBrut', 'Condensat', 'GPL', 'GazNaturel'))
);

-- =========================
-- TABLE STATION
-- =========================
CREATE TABLE station (
  station_id VARCHAR PRIMARY KEY,
  nom_station VARCHAR NOT NULL,
  type_station VARCHAR NOT NULL,
  localisation TEXT,
  status VARCHAR NOT NULL,
  pipeline_id VARCHAR NOT NULL,
  FOREIGN KEY (pipeline_id) REFERENCES pipeline(pipeline_id),
  CHECK (type_station IN ('Pompage', 'Compression')),
  CHECK (status IN ('EnMarche', 'Arret', 'Maintenance', 'Alarme'))
);

-- =========================
-- TABLE MACHINE
-- =========================
CREATE TABLE machine (
  machine_id VARCHAR PRIMARY KEY,
  type VARCHAR NOT NULL,
  fabricant VARCHAR,
  modele VARCHAR,
  capacite_nominale FLOAT CHECK (capacite_nominale > 0),
  date_mise_en_service DATE,
  status VARCHAR NOT NULL,
  disponibilite FLOAT CHECK (disponibilite BETWEEN 0 AND 100),
  mode_controle VARCHAR NOT NULL,
  station_id VARCHAR NOT NULL,
  FOREIGN KEY (station_id) REFERENCES station(station_id),
  CHECK (type IN ('Centrifuge', 'Piston', 'Electrique', 'TurbineGaz')),
  CHECK (status IN ('EnMarche', 'Arret', 'Maintenance', 'Alarme')),
  CHECK (mode_controle IN ('Manuel', 'Auto', 'Distance'))
);

-- =========================
-- TABLE CAPTEUR
-- =========================
CREATE TABLE capteur (
  capteur_id VARCHAR PRIMARY KEY,
  type_mesure VARCHAR NOT NULL,
  unite VARCHAR NOT NULL,
  machine_id VARCHAR NOT NULL,
  FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
  CHECK (type_mesure IN ('Pression', 'Debit', 'Temperature', 'Vibration'))
);

-- =========================
-- TABLE MESURE (temps réel)
-- =========================
CREATE TABLE mesure (
  mesure_id SERIAL PRIMARY KEY,
  capteur_id VARCHAR NOT NULL,
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),
  valeur FLOAT NOT NULL,
  timestamp TIMESTAMP NOT NULL
);

-- =========================
-- TABLE SEUIL CAPTEUR
-- =========================
CREATE TABLE seuil_capteur (
  seuil_id SERIAL PRIMARY KEY,
  capteur_id VARCHAR NOT NULL UNIQUE,
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),
  valeur_min FLOAT,
  valeur_max FLOAT
);

-- =========================
-- TABLE ALERTE
-- =========================
CREATE TABLE alerte (
  alerte_id SERIAL PRIMARY KEY,
  capteur_id VARCHAR NOT NULL,
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),
  valeur FLOAT NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  type_alerte VARCHAR,
  message TEXT
);

-- =========================
-- TABLE MAINTENANCE
-- =========================
CREATE TABLE maintenance (
  maintenance_id SERIAL PRIMARY KEY,
  machine_id VARCHAR NOT NULL,
  FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
  date DATE NOT NULL,
  type VARCHAR,
  description TEXT
);

-- =========================
-- FUNCTION CHECK_SEUIL
-- =========================
CREATE OR REPLACE FUNCTION check_seuil()
RETURNS TRIGGER AS $$
DECLARE
    seuil_min FLOAT;
    seuil_max FLOAT;
BEGIN
    SELECT valeur_min, valeur_max
    INTO seuil_min, seuil_max
    FROM seuil_capteur
    WHERE capteur_id = NEW.capteur_id;

    IF NEW.valeur < seuil_min OR NEW.valeur > seuil_max THEN
        INSERT INTO alerte (capteur_id, valeur, timestamp, type_alerte, message)
        VALUES (
            NEW.capteur_id,
            NEW.valeur,
            NEW.timestamp,
            'Critique',
            'Seuil dépassé'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- TRIGGER TRIGGER_SEUIL
-- =========================
CREATE TRIGGER trigger_seuil
AFTER INSERT ON mesure
FOR EACH ROW
EXECUTE FUNCTION check_seuil();

-- =========================
-- VUE 1 — Alertes actives
-- =========================
CREATE OR REPLACE VIEW vue_alertes_actives AS
SELECT 
    a.alerte_id,
    a.capteur_id,
    c.machine_id,
    a.valeur,
    a.timestamp,
    a.type_alerte,
    a.message
FROM alerte a
JOIN capteur c ON a.capteur_id = c.capteur_id
ORDER BY a.timestamp DESC;

-- =========================
-- VUE 2 — Machines en alarme
-- =========================
CREATE OR REPLACE VIEW vue_machines_alarme AS
SELECT DISTINCT 
    m.machine_id,
    m.type,
    m.status,
    s.nom_station,
    p.nom_pipeline
FROM machine m
JOIN capteur c ON m.machine_id = c.machine_id
JOIN alerte a ON c.capteur_id = a.capteur_id
JOIN station s ON m.station_id = s.station_id
JOIN pipeline p ON s.pipeline_id = p.pipeline_id
WHERE m.status = 'Alarme';

-- =========================
-- VUE 3 — Dernière mesure par capteur (fixed)
-- =========================
CREATE OR REPLACE VIEW vue_derniere_mesure AS
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

-- ============================================================
-- INSERTS
-- ============================================================

INSERT INTO zone (zone_id, nom, region, type_zone, description) VALUES 
('A', 'Zone Nord', 'Alger', 'Nord', 'Zone principale nord'),
('B', 'Zone Sud', 'Hassi Messaoud', 'Sud', 'Zone secondaire sud');

INSERT INTO pipeline (
  pipeline_id, nom_pipeline, type_produit, localisation_geo,
  date_mise_en_service, longueur, diametre, point_debut, point_fin, zone_id
) VALUES 
('P1', 'Pipeline Nord 1', 'PetroleBrut', 'Alger', '2015-06-01', 1200, 30, 'Alger', 'Oran', 'A'),
('P2', 'Pipeline Sud 1', 'GazNaturel', 'Hassi Messaoud', '2018-03-15', 800, 20, 'Hassi Messaoud', 'Ouargla', 'B');

INSERT INTO station (station_id, nom_station, type_station, localisation, status, pipeline_id) VALUES 
('S1', 'Station Nord A', 'Pompage', 'Alger', 'EnMarche', 'P1'),
('S2', 'Station Sud A', 'Compression', 'Hassi Messaoud', 'EnMarche', 'P2');

INSERT INTO machine (
  machine_id, type, fabricant, modele, capacite_nominale,
  date_mise_en_service, status, disponibilite, mode_controle, station_id
) VALUES 
('M1', 'Centrifuge', 'Siemens', 'X100', 500, '2016-01-10', 'EnMarche', 95, 'Auto', 'S1'),
('M2', 'TurbineGaz', 'GE', 'T200', 800, '2019-07-20', 'EnMarche', 90, 'Distance', 'S2');

INSERT INTO capteur (capteur_id, type_mesure, unite, machine_id) VALUES 
('C1', 'Pression', 'bar', 'M1'),
('C2', 'Temperature', 'C', 'M1'),
('C3', 'Debit', 'm3/h', 'M2'),
('C4', 'Vibration', 'mm/s', 'M2');

INSERT INTO seuil_capteur (capteur_id, valeur_min, valeur_max) VALUES
('C1', 10, 100),
('C2', 0, 90),
('C3', 50, 500),
('C4', 0, 20);

INSERT INTO maintenance (machine_id, date, type, description) VALUES
('M1', '2024-01-10', 'Preventive', 'Inspection générale'),
('M2', '2024-02-15', 'Corrective', 'Réparation turbine');

INSERT INTO mesure (capteur_id, valeur, timestamp) VALUES
('C1', 50,  NOW()),
('C2', 85,  NOW()),
('C3', 300, NOW()),
('C4', 10,  NOW());

-- ============================================================
-- VERIFY — run these after to check everything worked
-- ============================================================
SELECT * FROM vue_derniere_mesure;
SELECT * FROM vue_alertes_actives;



SELECT * FROM mesure ORDER BY timestamp DESC LIMIT 20;
SELECT * FROM vue_alertes_actives;
SELECT * FROM maintenance;
SELECT * FROM vue_derniere_mesure;




DELETE FROM seuil_capteur WHERE capteur_id = 'C4';
DELETE FROM mesure WHERE capteur_id = 'C4';
DELETE FROM alerte WHERE capteur_id = 'C4';
DELETE FROM capteur WHERE capteur_id = 'C4';



DELETE FROM alerte;
DELETE FROM mesure;
DELETE FROM maintenance WHERE description LIKE 'Maintenance suite%';




SELECT * FROM vue_alertes_actives LIMIT 10;
SELECT * FROM vue_derniere_mesure;