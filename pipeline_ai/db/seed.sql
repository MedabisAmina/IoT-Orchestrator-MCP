-- =========================
-- ZONE
-- =========================
INSERT INTO zone (zone_id, nom, region, type_zone, description) VALUES 
('A', 'Zone Nord', 'Alger', 'Nord', 'Zone principale nord'),
('B', 'Zone Sud', 'Hassi Messaoud', 'Sud', 'Zone secondaire sud');

-- =========================
-- PIPELINE 
-- =========================
INSERT INTO pipeline (
  pipeline_id,
  nom_pipeline,
  type_produit,
  localisation_geo,
  date_mise_en_service,
  longueur,
  diametre,
  point_debut,
  point_fin,
  zone_id
) VALUES 
('P1', 'Pipeline Nord 1', 'PetroleBrut', 'Alger', '2015-06-01', 1200, 30, 'Alger', 'Oran', 'A'),
('P2', 'Pipeline Sud 1', 'GazNaturel', 'Hassi Messaoud', '2018-03-15', 800, 20, 'Hassi Messaoud', 'Ouargla', 'B');

-- =========================
-- STATION
-- =========================
INSERT INTO station (
  station_id,
  nom_station,
  type_station,
  localisation,
  status,
  pipeline_id
) VALUES 
('S1', 'Station Nord A', 'Pompage', 'Alger', 'EnMarche', 'P1'),
('S2', 'Station Sud A', 'Compression', 'Hassi Messaoud', 'EnMarche', 'P2');

-- =========================
-- MACHINE
-- =========================
INSERT INTO machine (
  machine_id,
  type,
  fabricant,
  modele,
  capacite_nominale,
  date_mise_en_service,
  status,
  disponibilite,
  mode_controle,
  station_id
) VALUES 
('M1', 'Centrifuge', 'Siemens', 'X100', 500, '2016-01-10', 'EnMarche', 95, 'Auto', 'S1'),
('M2', 'TurbineGaz', 'GE', 'T200', 800, '2019-07-20', 'EnMarche', 90, 'Distance', 'S2');

-- =========================
-- CAPTEUR
-- =========================
INSERT INTO capteur (
  capteur_id,
  type_mesure,
  unite,
  machine_id
) VALUES 
('C1', 'Pression', 'bar', 'M1'),
('C2', 'Temperature', 'C', 'M1'),
('C3', 'Debit', 'm3/h', 'M2'),
('C4', 'Vibration', 'mm/s', 'M2');

-- =========================
-- SEUIL CAPTEUR
-- =========================
INSERT INTO seuil_capteur (
  capteur_id,
  valeur_min,
  valeur_max
) VALUES
('C1', 10, 100),
('C2', 0, 90),
('C3', 50, 500),
('C4', 0, 20);

-- =========================
-- MAINTENANCE
-- =========================
INSERT INTO maintenance (
  machine_id,
  date,
  type,
  description
) VALUES
('M1', '2024-01-10', 'Preventive', 'Inspection générale'),
('M2', '2024-02-15', 'Corrective', 'Réparation turbine');

-- =========================
-- MESURES
-- =========================
INSERT INTO mesure (
  capteur_id,
  valeur,
  timestamp
) VALUES
('C1', 50, NOW()),
('C2', 85, NOW()),
('C3', 300, NOW()),
('C4', 10, NOW());