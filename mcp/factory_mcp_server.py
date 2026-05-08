"""
mcp/factory_mcp_server.py — Full-featured MCP server (22 tools)
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
        "measurements, alerts, maintenance history and industrial infrastructure data. "
        "Use the available tools to answer operational questions."
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

    RELATIONS:
    Zone -> Pipeline -> Station -> Machine -> Sensor

    SENSOR TYPES:
    - Pression
    - Temperature
    - Debit
    - Vibration

    MACHINE STATUS:
    - EnMarche
    - Arret
    - Maintenance
    - Alarme

    FEATURES:
    - Real-time industrial measurements
    - Automatic alerts via trigger
    - Maintenance history
    - Industrial monitoring
    - Oil & Gas infrastructure analytics

    """

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    mcp.run()