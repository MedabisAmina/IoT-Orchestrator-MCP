

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



SELECT machine_id, type, status, disponibilite FROM machine;

SELECT * FROM vue_derniere_mesure WHERE capteur_id = 'C1';

SELECT * FROM vue_alertes_actives;





ALTER TABLE station
DROP CONSTRAINT station_type_station_check;

ALTER TABLE station
ADD CONSTRAINT station_type_station_check
CHECK (type_station IN ('Pompage', 'Compression', 'TerminalDepart', 'TerminalArrivee'));






INSERT INTO station (station_id, nom_station, type_station, localisation, status, pipeline_id) VALUES
('S3', 'Terminal Départ Nord', 'TerminalDepart', 'Alger', 'EnMarche', 'P1'),
('S4', 'Terminal Arrivée Nord', 'TerminalArrivee', 'Oran', 'EnMarche', 'P1'),
('S5', 'Terminal Départ Sud', 'TerminalDepart', 'Hassi Messaoud', 'EnMarche', 'P2'),
('S6', 'Terminal Arrivée Sud', 'TerminalArrivee', 'Ouargla', 'EnMarche', 'P2');





-- =========================
-- TABLE TARIF
-- =========================
CREATE TABLE tarif (
  tarif_id VARCHAR PRIMARY KEY,
  type_produit VARCHAR NOT NULL,
  type_mesure VARCHAR NOT NULL,
  prix_unitaire FLOAT NOT NULL CHECK (prix_unitaire > 0),
  unite VARCHAR NOT NULL,
  date_effet DATE NOT NULL,
  CHECK (type_produit IN ('PetroleBrut', 'Condensat', 'GPL', 'GazNaturel')),
  CHECK (type_mesure IN ('Pression', 'Debit', 'Temperature'))
);

-- =========================
-- TABLE TRANSACTION_VOLUME
-- =========================
CREATE TABLE transaction_volume (
  transaction_id SERIAL PRIMARY KEY,
  station_id VARCHAR NOT NULL,
  capteur_id VARCHAR NOT NULL,
  tarif_id VARCHAR NOT NULL,
  type_mesure VARCHAR NOT NULL,
  valeur FLOAT NOT NULL,
  cout FLOAT NOT NULL CHECK (cout > 0),
  timestamp TIMESTAMP NOT NULL,
  FOREIGN KEY (station_id) REFERENCES station(station_id),
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),
  FOREIGN KEY (tarif_id) REFERENCES tarif(tarif_id)
);

-- =========================
-- TABLE BUDGET
-- =========================
CREATE TABLE budget (
  budget_id SERIAL PRIMARY KEY,
  pipeline_id VARCHAR NOT NULL,
  periode VARCHAR NOT NULL,
  budget_alloue FLOAT NOT NULL CHECK (budget_alloue > 0),
  cout_total FLOAT DEFAULT 0,
  solde FLOAT GENERATED ALWAYS AS (budget_alloue - cout_total) STORED,
  FOREIGN KEY (pipeline_id) REFERENCES pipeline(pipeline_id)
);

-- =========================
-- FUNCTION CALC_COUT
-- =========================
CREATE OR REPLACE FUNCTION calc_cout()
RETURNS TRIGGER AS $$
DECLARE
  v_station_type VARCHAR;
  v_type_mesure  VARCHAR;
  v_type_produit VARCHAR;
  v_tarif_id     VARCHAR;
  v_prix         FLOAT;
  v_cout         FLOAT;
  v_station_id   VARCHAR;
  v_pipeline_id  VARCHAR;
BEGIN
  SELECT c.type_mesure, m.station_id
  INTO v_type_mesure, v_station_id
  FROM capteur c
  JOIN machine m ON c.machine_id = m.machine_id
  WHERE c.capteur_id = NEW.capteur_id;

  SELECT type_station, pipeline_id
  INTO v_station_type, v_pipeline_id
  FROM station WHERE station_id = v_station_id;

  -- Only TerminalArrivee, skip Vibration
  IF v_station_type = 'TerminalArrivee' AND v_type_mesure != 'Vibration' THEN

    SELECT p.type_produit INTO v_type_produit
    FROM pipeline p WHERE p.pipeline_id = v_pipeline_id;

    SELECT tarif_id, prix_unitaire INTO v_tarif_id, v_prix
    FROM tarif
    WHERE type_produit = v_type_produit
      AND type_mesure  = v_type_mesure
    ORDER BY date_effet DESC LIMIT 1;

    IF v_tarif_id IS NULL THEN
      RETURN NEW;
    END IF;

    v_cout := NEW.valeur * v_prix;

    INSERT INTO transaction_volume (
      station_id, capteur_id, tarif_id, type_mesure, valeur, cout, timestamp
    ) VALUES (
      v_station_id, NEW.capteur_id, v_tarif_id,
      v_type_mesure, NEW.valeur, v_cout, NEW.timestamp
    );

    UPDATE budget
    SET cout_total = cout_total + v_cout
    WHERE pipeline_id = v_pipeline_id
      AND periode = TO_CHAR(NEW.timestamp, 'YYYY-MM');

  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================
-- TRIGGER TRIGGER_COUT
-- =========================
CREATE TRIGGER trigger_cout
AFTER INSERT ON mesure
FOR EACH ROW
EXECUTE FUNCTION calc_cout();

-- =========================
-- INSERTS — TARIFS
-- =========================
INSERT INTO tarif (tarif_id, type_produit, type_mesure, prix_unitaire, unite, date_effet) VALUES
('T1', 'PetroleBrut', 'Debit',       45.50, 'DZD/m3',  '2024-01-01'),
('T2', 'PetroleBrut', 'Pression',     2.10, 'DZD/bar', '2024-01-01'),
('T3', 'PetroleBrut', 'Temperature',  1.50, 'DZD/C',   '2024-01-01'),
('T4', 'GazNaturel',  'Debit',       12.75, 'DZD/m3',  '2024-01-01'),
('T5', 'GazNaturel',  'Pression',     1.80, 'DZD/bar', '2024-01-01'),
('T6', 'GazNaturel',  'Temperature',  0.90, 'DZD/C',   '2024-01-01');

-- =========================
-- INSERTS — BUDGET
-- =========================
INSERT INTO budget (pipeline_id, periode, budget_alloue, cout_total) VALUES
('P1', '2025-05', 500000, 0),
('P2', '2025-05', 300000, 0);