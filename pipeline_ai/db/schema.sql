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
create table pipeline (
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
create table station (
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
create table machine (
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
create table capteur (
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
create table mesure (
  mesure_id SERIAL PRIMARY KEY,

  capteur_id VARCHAR NOT NULL,
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),

  valeur FLOAT NOT NULL,
  timestamp TIMESTAMP NOT NULL
);

-- =========================
-- TABLE SEUIL CAPTEUR
-- =========================
create table seuil_capteur (
  seuil_id SERIAL PRIMARY KEY,

  capteur_id VARCHAR NOT NULL UNIQUE,
  FOREIGN KEY (capteur_id) REFERENCES capteur(capteur_id),

  valeur_min FLOAT,
  valeur_max FLOAT
);

-- =========================
-- TABLE ALERTE
-- =========================
create table alerte (
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
create table maintenance (
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

    -- récupérer le seuil du capteur
    SELECT valeur_min, valeur_max
    INTO seuil_min, seuil_max
    FROM seuil_capteur
    WHERE capteur_id = NEW.capteur_id;

    -- vérifier dépassement
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


-- ===========================
-- VUE 2 — Machines en alarme
-- ===========================
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

-- ======================================
-- VUE 3 — Dernière mesure par capteur
-- ======================================
CREATE OR REPLACE VIEW vue_derniere_mesure AS
SELECT DISTINCT ON (capteur_id)
    capteur_id,
    valeur,
    timestamp
FROM mesure
ORDER BY capteur_id, timestamp DESC;