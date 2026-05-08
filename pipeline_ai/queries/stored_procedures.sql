-- ============================================================
-- MEMBRE 4 — PROCÉDURES STOCKÉES & FONCTIONS
-- Pipeline Monitoring System
-- ============================================================

-- -------------------------------------------------------
-- PROCÉDURE 1 : resolve_alert(alerteID)
-- Met à jour le message de l'alerte pour marquer résolution
-- -------------------------------------------------------
CREATE OR REPLACE PROCEDURE resolve_alert(p_alerte_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE alerte
    SET
        message    = CONCAT('[RÉSOLUE le ', NOW()::TEXT, '] ', message),
        type_alerte = 'Resolue'
    WHERE alerte_id = p_alerte_id;

    -- Mettre la machine en EnMarche si plus aucune alerte critique
    UPDATE machine
    SET status = 'EnMarche'
    WHERE machine_id = (
        SELECT c.machine_id
        FROM capteur c
        JOIN alerte a ON c.capteur_id = a.capteur_id
        WHERE a.alerte_id = p_alerte_id
        LIMIT 1
    )
    AND machine_id NOT IN (
        SELECT DISTINCT c2.machine_id
        FROM alerte a2
        JOIN capteur c2 ON a2.capteur_id = c2.capteur_id
        WHERE a2.type_alerte = 'Critique'
          AND a2.alerte_id != p_alerte_id
    );

    RAISE NOTICE 'Alerte % résolue avec succès.', p_alerte_id;
END;
$$;

-- Usage : CALL resolve_alert(1);


-- -------------------------------------------------------
-- FONCTION 2 : get_machine_summary(zoneID)
-- Retourne le nombre de machines par statut dans une zone
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION get_machine_summary(p_zone_id VARCHAR)
RETURNS TABLE(
    status        VARCHAR,
    nb_machines   BIGINT,
    disponibilite_moy FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        ma.status,
        COUNT(*)::BIGINT                  AS nb_machines,
        ROUND(AVG(ma.disponibilite)::NUMERIC, 2)::FLOAT AS disponibilite_moy
    FROM machine ma
    JOIN station  st ON ma.station_id  = st.station_id
    JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
    WHERE pi.zone_id = p_zone_id
    GROUP BY ma.status
    ORDER BY ma.status;
END;
$$;

-- Usage : SELECT * FROM get_machine_summary('A');


-- -------------------------------------------------------
-- FONCTION 3 : get_alert_history(machineID, nb_jours)
-- Retourne les alertes d'une machine sur N derniers jours
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION get_alert_history(
    p_machine_id VARCHAR,
    p_nb_jours   INT DEFAULT 30
)
RETURNS TABLE(
    alerte_id   INT,
    capteur_id  VARCHAR,
    type_mesure VARCHAR,
    valeur      FLOAT,
    timestamp   TIMESTAMP,
    type_alerte VARCHAR,
    message     TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.alerte_id,
        a.capteur_id,
        c.type_mesure,
        a.valeur,
        a.timestamp,
        a.type_alerte,
        a.message
    FROM alerte a
    JOIN capteur c ON a.capteur_id = c.capteur_id
    WHERE c.machine_id = p_machine_id
      AND a.timestamp >= NOW() - (p_nb_jours || ' days')::INTERVAL
    ORDER BY a.timestamp DESC;
END;
$$;

-- Usage : SELECT * FROM get_alert_history('M1', 7);
