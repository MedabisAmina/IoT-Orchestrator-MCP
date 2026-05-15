"""
mcp/factory_mcp_server.py — Full-featured MCP server (29 tools)
Source: github (teammate) — fixed to use shared .env

Connect via Claude Desktop:
  {
    "mcpServers": {
      "pipeline-industrial": {
        "command": "python",
        "args": ["mcp/factory_mcp_server.py"]
      }
    }
  }
"""

import os
import psycopg2
import psycopg2.extras
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "pipeline_db"),
        user=os.getenv("POSTGRES_USER", "iotuser"),
        password=os.getenv("POSTGRES_PASS", "iotfrontier"),
    )

# =========================================================
# MCP SERVER
# =========================================================

mcp = FastMCP(
    name="pipeline-industrial-mcp",
    instructions=(
        "You are an Industrial Oil & Gas IoT assistant. "
        "The database contains pipelines, stations, machines, sensors, "
        "measurements, alerts, maintenance history, tariffs, transactions, "
        "budgets and industrial infrastructure data. "
        "Use the available tools to answer operational and financial questions."
    ),
)

# =========================================================
# TOOL 1 — GET MACHINE STATUS
# =========================================================

@mcp.tool
def get_machine_status(machine_id: str = "") -> list[dict]:

    """
    Return machine operational status.
    """

    sql = """
        SELECT
            m.machine_id,
            m.type,
            m.fabricant,
            m.modele,
            m.status,
            m.disponibilite,
            m.mode_controle,
            s.nom_station,
            p.nom_pipeline,
            z.nom AS zone
        FROM machine m
        JOIN station s
            ON m.station_id = s.station_id
        JOIN pipeline p
            ON s.pipeline_id = p.pipeline_id
        JOIN zone z
            ON p.zone_id = z.zone_id
        WHERE (%s = '' OR m.machine_id = %s)
        ORDER BY m.machine_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (machine_id, machine_id))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 2 — GET SENSOR VALUE
# =========================================================

@mcp.tool
def get_sensor_value(capteur_id: str) -> list[dict]:

    """
    Return latest sensor reading.
    """

    sql = """
        SELECT
            c.capteur_id,
            c.type_mesure,
            c.unite,
            d.valeur,
            d.timestamp
        FROM vue_derniere_mesure d
        JOIN capteur c
            ON d.capteur_id = c.capteur_id
        WHERE c.capteur_id = %s;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (capteur_id,))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 3 — GET SENSOR HISTORY
# =========================================================

@mcp.tool
def get_sensor_history(
    capteur_id: str,
    hours: int = 24
) -> list[dict]:

    """
    Return sensor history for last N hours.
    """

    sql = """
        SELECT
            capteur_id,
            valeur,
            timestamp
        FROM mesure
        WHERE capteur_id = %s
        AND timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY timestamp DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (capteur_id, hours))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 4 — ACTIVE ALERTS
# =========================================================

@mcp.tool
def list_active_alerts() -> list[dict]:

    """
    Return all active alerts.
    """

    sql = """
        SELECT *
        FROM vue_alertes_actives
        ORDER BY timestamp DESC
        LIMIT 100;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 5 — ALERTS BY ZONE
# =========================================================

@mcp.tool
def get_active_alerts_by_zone(
    zone_id: str
) -> list[dict]:

    """
    Return alerts for a specific zone.
    """

    sql = """
        SELECT
            z.zone_id,
            z.nom AS zone_nom,
            a.alerte_id,
            a.capteur_id,
            a.valeur,
            a.timestamp,
            a.type_alerte,
            a.message
        FROM alerte a

        JOIN capteur c
            ON a.capteur_id = c.capteur_id

        JOIN machine m
            ON c.machine_id = m.machine_id

        JOIN station s
            ON m.station_id = s.station_id

        JOIN pipeline p
            ON s.pipeline_id = p.pipeline_id

        JOIN zone z
            ON p.zone_id = z.zone_id

        WHERE z.zone_id = %s

        ORDER BY a.timestamp DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (zone_id,))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 6 — GET PIPELINE INFO
# =========================================================

@mcp.tool
def get_pipeline_info(
    pipeline_id: str = ""
) -> list[dict]:

    """
    Return pipeline information.
    """

    sql = """
        SELECT
            pipeline_id,
            nom_pipeline,
            type_produit,
            localisation_geo,
            longueur,
            diametre,
            point_debut,
            point_fin
        FROM pipeline
        WHERE (%s = '' OR pipeline_id = %s)
        ORDER BY pipeline_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (pipeline_id, pipeline_id))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 7 — GET STATION STATUS
# =========================================================

@mcp.tool
def get_station_status() -> list[dict]:

    """
    Return all station status.
    """

    sql = """
        SELECT
            station_id,
            nom_station,
            type_station,
            localisation,
            status
        FROM station
        ORDER BY station_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 8 — MAINTENANCE HISTORY
# =========================================================

@mcp.tool
def get_maintenance_history(
    machine_id: str
) -> list[dict]:

    """
    Return machine maintenance history.
    """

    sql = """
        SELECT
            maintenance_id,
            machine_id,
            date,
            type,
            description
        FROM maintenance
        WHERE machine_id = %s
        ORDER BY date DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (machine_id,))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 9 — UPDATE MACHINE STATUS
# =========================================================

@mcp.tool
def update_machine_status(
    machine_id: str,
    new_status: str
) -> dict:

    """
    Update machine status.
    """

    allowed = [
        "EnMarche",
        "Arret",
        "Maintenance",
        "Alarme"
    ]

    if new_status not in allowed:

        return {
            "success": False,
            "error": "Invalid status"
        }

    sql = """
        UPDATE machine
        SET status = %s
        WHERE machine_id = %s
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql, (
                new_status,
                machine_id
            ))

            conn.commit()

    return {
        "success": True,
        "machine_id": machine_id,
        "new_status": new_status
    }

# =========================================================
# TOOL 10 — MACHINES IN ALARM
# =========================================================

@mcp.tool
def get_machines_in_alarm() -> list[dict]:

    """
    Return machines currently in alarm.
    """

    sql = """
        SELECT *
        FROM vue_machines_alarme;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 11 — RESOLVE ALERT
# =========================================================

@mcp.tool
def resolve_alert(
    alert_id: int
) -> dict:

    """
    Resolve alert by deleting it.
    """

    sql = """
        DELETE FROM alerte
        WHERE alerte_id = %s
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql, (alert_id,))

            conn.commit()

    return {
        "success": True,
        "resolved_alert": alert_id
    }

# =========================================================
# TOOL 12 — ZONE OVERVIEW
# =========================================================

@mcp.tool
def get_zone_overview() -> list[dict]:

    """
    Overview of all industrial zones.
    """

    sql = """
        SELECT
            z.zone_id,
            z.nom,

            COUNT(DISTINCT p.pipeline_id) AS pipelines,
            COUNT(DISTINCT s.station_id) AS stations,
            COUNT(DISTINCT m.machine_id) AS machines,
            COUNT(DISTINCT a.alerte_id) AS alerts

        FROM zone z

        LEFT JOIN pipeline p
            ON z.zone_id = p.zone_id

        LEFT JOIN station s
            ON p.pipeline_id = s.pipeline_id

        LEFT JOIN machine m
            ON s.station_id = m.station_id

        LEFT JOIN capteur c
            ON m.machine_id = c.machine_id

        LEFT JOIN alerte a
            ON c.capteur_id = a.capteur_id

        GROUP BY z.zone_id, z.nom

        ORDER BY z.zone_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 13 — MACHINE AVAILABILITY
# =========================================================

@mcp.tool
def get_machine_availability() -> list[dict]:

    """
    Machine reliability overview.
    """

    sql = """
        SELECT
            machine_id,
            type,
            disponibilite,
            status
        FROM machine
        ORDER BY disponibilite ASC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 14 — TOP ALERTED MACHINES
# =========================================================

@mcp.tool
def get_top_alerted_machines() -> list[dict]:

    """
    Machines generating most alerts.
    """

    sql = """
        SELECT
            m.machine_id,
            m.type,
            COUNT(a.alerte_id) AS total_alerts

        FROM machine m

        JOIN capteur c
            ON m.machine_id = c.machine_id

        JOIN alerte a
            ON c.capteur_id = a.capteur_id

        GROUP BY m.machine_id, m.type

        ORDER BY total_alerts DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 15 — TEMPERATURE ANOMALIES
# =========================================================

@mcp.tool
def get_temperature_anomalies() -> list[dict]:

    """
    Detect abnormal temperatures.
    """

    sql = """
        SELECT
            m.machine_id,
            c.capteur_id,
            d.valeur,
            d.timestamp

        FROM vue_derniere_mesure d

        JOIN capteur c
            ON d.capteur_id = c.capteur_id

        JOIN machine m
            ON c.machine_id = m.machine_id

        WHERE c.type_mesure = 'Temperature'
        AND d.valeur > 90

        ORDER BY d.valeur DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 16 — PRESSURE TRENDS
# =========================================================

@mcp.tool
def get_pressure_trends() -> list[dict]:

    """
    Analyze pressure sensor trends.
    """

    sql = """
        SELECT
            capteur_id,
            AVG(valeur) AS avg_pressure,
            MAX(valeur) AS max_pressure,
            MIN(valeur) AS min_pressure

        FROM mesure

        WHERE capteur_id IN (
            SELECT capteur_id
            FROM capteur
            WHERE type_mesure = 'Pression'
        )

        GROUP BY capteur_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 17 — PIPELINE FLOW RATE
# =========================================================

@mcp.tool
def get_pipeline_flow_rate() -> list[dict]:

    """
    Pipeline throughput analysis.
    """

    sql = """
        SELECT
            p.pipeline_id,
            p.nom_pipeline,
            AVG(ms.valeur) AS avg_flow_rate

        FROM pipeline p

        JOIN station s
            ON p.pipeline_id = s.pipeline_id

        JOIN machine m
            ON s.station_id = m.station_id

        JOIN capteur c
            ON m.machine_id = c.machine_id

        JOIN mesure ms
            ON c.capteur_id = ms.capteur_id

        WHERE c.type_mesure = 'Debit'

        GROUP BY p.pipeline_id, p.nom_pipeline;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 18 — COMPARE ZONES
# =========================================================

@mcp.tool
def compare_zones() -> list[dict]:

    """
    Compare operational metrics between zones.
    """

    sql = """
        SELECT
            z.zone_id,
            z.nom,

            COUNT(DISTINCT m.machine_id) AS machines,

            COUNT(DISTINCT a.alerte_id) AS alerts,

            AVG(m.disponibilite) AS avg_disponibilite

        FROM zone z

        LEFT JOIN pipeline p
            ON z.zone_id = p.zone_id

        LEFT JOIN station s
            ON p.pipeline_id = s.pipeline_id

        LEFT JOIN machine m
            ON s.station_id = m.station_id

        LEFT JOIN capteur c
            ON m.machine_id = c.machine_id

        LEFT JOIN alerte a
            ON c.capteur_id = a.capteur_id

        GROUP BY z.zone_id, z.nom;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 19 — MACHINE HEALTH SCORE
# =========================================================

@mcp.tool
def get_machine_health_score() -> list[dict]:

    """
    AI-style machine health score.
    """

    sql = """
        SELECT
            machine_id,
            status,
            disponibilite,

            CASE
                WHEN status = 'Alarme' THEN 20
                WHEN disponibilite < 50 THEN 40
                WHEN disponibilite < 75 THEN 70
                ELSE 95
            END AS health_score

        FROM machine

        ORDER BY health_score ASC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 20 — EMERGENCY SHUTDOWN
# =========================================================

@mcp.tool
def emergency_shutdown(
    machine_id: str
) -> dict:

    """
    Emergency stop for machine.
    """

    sql = """
        UPDATE machine
        SET status = 'Arret'
        WHERE machine_id = %s
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql, (machine_id,))

            conn.commit()

    return {
        "success": True,
        "machine_shutdown": machine_id
    }

# =========================================================
# TOOL 21 — CREATE MAINTENANCE TICKET
# =========================================================

@mcp.tool
def create_maintenance_ticket(
    machine_id: str,
    maintenance_type: str,
    description: str
) -> dict:

    """
    Create maintenance operation.
    """

    sql = """
        INSERT INTO maintenance (
            machine_id,
            date,
            type,
            description
        )
        VALUES (
            %s,
            CURRENT_DATE,
            %s,
            %s
        )
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(sql, (
                machine_id,
                maintenance_type,
                description
            ))

            conn.commit()

    return {
        "success": True,
        "machine_id": machine_id,
        "maintenance_created": True
    }

# =========================================================
# TOOL 22 — CUSTOM QUERY
# =========================================================

@mcp.tool
def run_query(sql: str) -> list[dict]:

    """
    Execute custom SELECT query.
    """

    if not sql.strip().upper().startswith("SELECT"):

        return [{
            "error": "Only SELECT queries are allowed."
        }]

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql)

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 23 — GET BUDGET STATUS
# =========================================================

@mcp.tool
def get_budget_status(
    pipeline_id: str = "",
    periode: str = ""
) -> list[dict]:

    """
    Return budget status for pipelines.
    Optionally filter by pipeline_id and/or periode (format: YYYY-MM).
    Shows budget_alloue, cout_total, solde and consumption percentage.
    """

    sql = """
        SELECT
            b.budget_id,
            b.pipeline_id,
            p.nom_pipeline,
            p.type_produit,
            b.periode,
            b.budget_alloue,
            b.cout_total,
            b.solde,
            ROUND(
                CASE
                    WHEN b.budget_alloue > 0
                    THEN (b.cout_total / b.budget_alloue * 100)::NUMERIC
                    ELSE 0
                END, 2
            ) AS pct_consomme
        FROM budget b
        JOIN pipeline p ON b.pipeline_id = p.pipeline_id
        WHERE (%s = '' OR b.pipeline_id = %s)
          AND (%s = '' OR b.periode = %s)
        ORDER BY b.periode DESC, b.pipeline_id;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (
                pipeline_id, pipeline_id,
                periode, periode
            ))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 24 — GET TARIFS
# =========================================================

@mcp.tool
def get_tarifs(
    type_produit: str = "",
    type_mesure: str = ""
) -> list[dict]:

    """
    Return pricing tariffs.
    Optionally filter by type_produit (PetroleBrut, Condensat, GPL, GazNaturel)
    and/or type_mesure (Pression, Debit, Temperature).
    Returns the most recent tariff per product/measure combination first.
    """

    sql = """
        SELECT
            tarif_id,
            type_produit,
            type_mesure,
            prix_unitaire,
            unite,
            date_effet
        FROM tarif
        WHERE (%s = '' OR type_produit = %s)
          AND (%s = '' OR type_mesure  = %s)
        ORDER BY type_produit, type_mesure, date_effet DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (
                type_produit, type_produit,
                type_mesure,  type_mesure
            ))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 25 — GET TRANSACTION HISTORY
# =========================================================

@mcp.tool
def get_transaction_history(
    pipeline_id: str = "",
    station_id: str = "",
    hours: int = 24
) -> list[dict]:

    """
    Return recent volume transactions with costs.
    Optionally filter by pipeline_id or station_id.
    Default window is the last 24 hours.
    """

    sql = """
        SELECT
            tv.transaction_id,
            tv.station_id,
            st.nom_station,
            pi.pipeline_id,
            pi.nom_pipeline,
            tv.capteur_id,
            tv.tarif_id,
            tv.type_mesure,
            tv.valeur,
            tv.cout,
            tv.timestamp
        FROM transaction_volume tv
        JOIN station   st ON tv.station_id   = st.station_id
        JOIN pipeline  pi ON st.pipeline_id  = pi.pipeline_id
        WHERE tv.timestamp > NOW() - (%s || ' hours')::INTERVAL
          AND (%s = '' OR pi.pipeline_id = %s)
          AND (%s = '' OR tv.station_id  = %s)
        ORDER BY tv.timestamp DESC
        LIMIT 200;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (
                hours,
                pipeline_id, pipeline_id,
                station_id,  station_id
            ))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 26 — GET COST SUMMARY BY PIPELINE
# =========================================================

@mcp.tool
def get_cost_summary_by_pipeline(
    periode: str = ""
) -> list[dict]:

    """
    Aggregate cost breakdown per pipeline for a given period (YYYY-MM).
    If no period is specified, uses the current month.
    Shows total cost, number of transactions, average cost per transaction,
    and cost split by measure type.
    """

    sql = """
        SELECT
            pi.pipeline_id,
            pi.nom_pipeline,
            pi.type_produit,
            TO_CHAR(tv.timestamp, 'YYYY-MM') AS periode,
            COUNT(tv.transaction_id)          AS nb_transactions,
            ROUND(SUM(tv.cout)::NUMERIC, 2)   AS cout_total,
            ROUND(AVG(tv.cout)::NUMERIC, 2)   AS cout_moyen,
            ROUND(
                SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Debit')::NUMERIC,
                2
            ) AS cout_debit,
            ROUND(
                SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Pression')::NUMERIC,
                2
            ) AS cout_pression,
            ROUND(
                SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Temperature')::NUMERIC,
                2
            ) AS cout_temperature
        FROM transaction_volume tv
        JOIN station  st ON tv.station_id  = st.station_id
        JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
        WHERE (%s = '' OR TO_CHAR(tv.timestamp, 'YYYY-MM') = %s)
        GROUP BY pi.pipeline_id, pi.nom_pipeline, pi.type_produit,
                 TO_CHAR(tv.timestamp, 'YYYY-MM')
        ORDER BY periode DESC, cout_total DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (periode, periode))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 27 — GET BUDGET ALERTS (OVERSPEND / NEAR LIMIT)
# =========================================================

@mcp.tool
def get_budget_alerts(
    warning_threshold_pct: float = 80.0
) -> list[dict]:

    """
    Return budgets that are over the warning threshold or already exceeded.
    Default threshold is 80% consumption.
    Returns status: 'Depasse' if over 100%, 'Alerte' if over the threshold,
    'Normal' otherwise.
    """

    sql = """
        SELECT
            b.budget_id,
            b.pipeline_id,
            p.nom_pipeline,
            b.periode,
            b.budget_alloue,
            b.cout_total,
            b.solde,
            ROUND(
                (b.cout_total / NULLIF(b.budget_alloue, 0) * 100)::NUMERIC,
                2
            ) AS pct_consomme,
            CASE
                WHEN b.cout_total >= b.budget_alloue
                    THEN 'Depasse'
                WHEN b.cout_total >= b.budget_alloue * (%s / 100.0)
                    THEN 'Alerte'
                ELSE 'Normal'
            END AS budget_status
        FROM budget b
        JOIN pipeline p ON b.pipeline_id = p.pipeline_id
        WHERE b.cout_total >= b.budget_alloue * (%s / 100.0)
        ORDER BY pct_consomme DESC;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql, (
                warning_threshold_pct,
                warning_threshold_pct
            ))

            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 28 — UPDATE TARIF
# =========================================================

@mcp.tool
def update_tarif(
    type_produit: str,
    type_mesure: str,
    nouveau_prix: float,
    unite: str
) -> dict:

    """
    Insert a new tariff entry that supersedes the previous one
    for a given product/measure combination.
    type_produit: PetroleBrut | Condensat | GPL | GazNaturel
    type_mesure : Pression | Debit | Temperature
    nouveau_prix: positive float (price per unit)
    unite       : e.g. 'DZD/m3', 'DZD/bar', 'DZD/C'
    """

    allowed_produits = ["PetroleBrut", "Condensat", "GPL", "GazNaturel"]
    allowed_mesures  = ["Pression", "Debit", "Temperature"]

    if type_produit not in allowed_produits:
        return {"success": False, "error": f"Invalid type_produit: {type_produit}"}

    if type_mesure not in allowed_mesures:
        return {"success": False, "error": f"Invalid type_mesure: {type_mesure}"}

    if nouveau_prix <= 0:
        return {"success": False, "error": "nouveau_prix must be > 0"}

    # Build a new tarif_id from the current max numeric suffix
    sql_new_id = """
        SELECT COALESCE(MAX(CAST(SUBSTRING(tarif_id FROM 2) AS INT)), 0) + 1
        AS next_id
        FROM tarif
        WHERE tarif_id ~ '^T[0-9]+$';
    """

    sql_insert = """
        INSERT INTO tarif (tarif_id, type_produit, type_mesure,
                           prix_unitaire, unite, date_effet)
        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
        RETURNING tarif_id, date_effet;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql_new_id)
            next_id = cur.fetchone()["next_id"]
            new_tarif_id = f"T{next_id}"

            cur.execute(sql_insert, (
                new_tarif_id,
                type_produit,
                type_mesure,
                nouveau_prix,
                unite
            ))

            result = cur.fetchone()
            conn.commit()

    return {
        "success":     True,
        "tarif_id":    result["tarif_id"],
        "type_produit": type_produit,
        "type_mesure":  type_mesure,
        "nouveau_prix": nouveau_prix,
        "unite":        unite,
        "date_effet":   str(result["date_effet"])
    }

# =========================================================
# TOOL 29 — SET BUDGET
# =========================================================

@mcp.tool
def set_budget(
    pipeline_id: str,
    periode: str,
    budget_alloue: float
) -> dict:

    """
    Create or update a budget allocation for a pipeline/period.
    pipeline_id  : existing pipeline (e.g. 'P1')
    periode      : month string in YYYY-MM format (e.g. '2025-06')
    budget_alloue: positive float — allocated budget in DZD
    If a budget already exists for that pipeline+period it is updated;
    otherwise a new row is inserted.
    """

    if budget_alloue <= 0:
        return {"success": False, "error": "budget_alloue must be > 0"}

    sql_upsert = """
        INSERT INTO budget (pipeline_id, periode, budget_alloue, cout_total)
        VALUES (%s, %s, %s, 0)
        ON CONFLICT (pipeline_id, periode)
        DO UPDATE SET budget_alloue = EXCLUDED.budget_alloue
        RETURNING budget_id, pipeline_id, periode, budget_alloue, cout_total, solde;
    """

    # budget table has no unique constraint on (pipeline_id, periode) by default
    # so we do a manual upsert with SELECT + INSERT/UPDATE
    sql_select = """
        SELECT budget_id FROM budget
        WHERE pipeline_id = %s AND periode = %s;
    """

    sql_insert = """
        INSERT INTO budget (pipeline_id, periode, budget_alloue, cout_total)
        VALUES (%s, %s, %s, 0)
        RETURNING budget_id, pipeline_id, periode, budget_alloue, cout_total, solde;
    """

    sql_update = """
        UPDATE budget
        SET budget_alloue = %s
        WHERE pipeline_id = %s AND periode = %s
        RETURNING budget_id, pipeline_id, periode, budget_alloue, cout_total, solde;
    """

    with get_connection() as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(sql_select, (pipeline_id, periode))
            existing = cur.fetchone()

            if existing:
                cur.execute(sql_update, (budget_alloue, pipeline_id, periode))
                action = "updated"
            else:
                cur.execute(sql_insert, (pipeline_id, periode, budget_alloue))
                action = "created"

            row = cur.fetchone()
            conn.commit()

    return {
        "success":       True,
        "action":        action,
        "budget_id":     row["budget_id"],
        "pipeline_id":   row["pipeline_id"],
        "periode":       row["periode"],
        "budget_alloue": row["budget_alloue"],
        "cout_total":    row["cout_total"],
        "solde":         row["solde"]
    }

# =========================================================
# RESOURCE — SCHEMA OVERVIEW
# =========================================================

@mcp.resource("pipeline://schema/overview")
def schema_overview() -> str:

    """
    Industrial Oil & Gas Pipeline Schema
    """

    return """

    INDUSTRIAL PIPELINE DATABASE
    ============================

    TABLES:
    - zone
    - pipeline
    - station
    - machine
    - capteur
    - mesure
    - seuil_capteur
    - alerte
    - maintenance
    - tarif
    - transaction_volume
    - budget

    RELATIONS:
    Zone -> Pipeline -> Station -> Machine -> Sensor

    SENSOR TYPES:
    - Pression
    - Temperature
    - Debit

    MACHINE STATUS:
    - EnMarche
    - Arret
    - Maintenance
    - Alarme

    FINANCIAL:
    - tarif         : unit prices per product/measure (DZD)
    - transaction_volume : auto-generated cost records at TerminalArrivee
    - budget        : monthly allocated vs. consumed budget per pipeline

    FEATURES:
    - Real-time industrial measurements
    - Automatic alerts via trigger
    - Automatic cost calculation via trigger (calc_cout)
    - Maintenance history
    - Industrial monitoring
    - Budget tracking and overspend alerts
    - Oil & Gas infrastructure analytics

    """

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    mcp.run()