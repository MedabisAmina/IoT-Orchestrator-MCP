"""
mcp/factory_mcp_server.py — Full-featured MCP server (44 tools)

NEW TOOLS (30-44):
  30. get_alert_frequency_by_sensor   — alerts per sensor, ranked
  31. get_alert_trend_by_day          — daily alert counts over last N days
  32. get_sensor_stats_last_24h       — min/avg/max/stddev per sensor last 24h
  33. get_debit_evolution_by_hour     — hourly avg flow rate last 24h per pipeline
  34. get_pressure_evolution_by_hour  — hourly avg pressure last 24h per pipeline
  35. get_temp_evolution_by_hour      — hourly avg temperature last 24h
  36. get_cost_evolution_by_day       — daily cost totals last 30 days per pipeline
  37. get_mtbf_per_machine            — mean time between failures (alerts)
  38. get_sensor_out_of_range_pct     — % of readings outside thresholds per sensor
  39. get_pipeline_efficiency_score   — composite operational score per pipeline
  40. get_maintenance_frequency       — maintenance count per machine per month
  41. get_alert_resolution_rate       — resolved vs total alert ratio
  42. get_station_cost_ranking        — stations ranked by total cost generated
  43. get_budget_forecast             — linear forecast: days until budget exhausted
  44. get_full_operational_report     — one-shot snapshot: KPIs + alerts + budget
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
        dbname=os.getenv("POSTGRES_DB",   "pipeline_db"),
        user=os.getenv("POSTGRES_USER",   "iotuser"),
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
    """Return machine operational status."""
    sql = """
        SELECT
            m.machine_id, m.type, m.fabricant, m.modele,
            m.status, m.disponibilite, m.mode_controle,
            s.nom_station, p.nom_pipeline, z.nom AS zone
        FROM machine m
        JOIN station  s ON m.station_id  = s.station_id
        JOIN pipeline p ON s.pipeline_id = p.pipeline_id
        JOIN zone     z ON p.zone_id     = z.zone_id
        WHERE (%s = '' OR m.machine_id = %s)
        ORDER BY m.machine_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (machine_id, machine_id))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 2 — GET SENSOR VALUE
# =========================================================

@mcp.tool
def get_sensor_value(capteur_id: str) -> list[dict]:
    """Return latest sensor reading."""
    sql = """
        SELECT c.capteur_id, c.type_mesure, c.unite, d.valeur, d.timestamp
        FROM vue_derniere_mesure d
        JOIN capteur c ON d.capteur_id = c.capteur_id
        WHERE c.capteur_id = %s;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (capteur_id,))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 3 — GET SENSOR HISTORY
# =========================================================

@mcp.tool
def get_sensor_history(capteur_id: str, hours: int = 24) -> list[dict]:
    """Return sensor history for last N hours."""
    sql = """
        SELECT capteur_id, valeur, timestamp
        FROM mesure
        WHERE capteur_id = %s
          AND timestamp > NOW() - (%s * INTERVAL '1 hour')
        ORDER BY timestamp DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (capteur_id, hours))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 4 — ACTIVE ALERTS
# =========================================================

@mcp.tool
def list_active_alerts() -> list[dict]:
    """Return all active alerts."""
    sql = """
        SELECT * FROM vue_alertes_actives
        ORDER BY timestamp DESC LIMIT 100;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 5 — ALERTS BY ZONE
# =========================================================

@mcp.tool
def get_active_alerts_by_zone(zone_id: str) -> list[dict]:
    """Return alerts for a specific zone."""
    sql = """
        SELECT z.zone_id, z.nom AS zone_nom,
               a.alerte_id, a.capteur_id, a.valeur,
               a.timestamp, a.type_alerte, a.message
        FROM alerte a
        JOIN capteur  c ON a.capteur_id  = c.capteur_id
        JOIN machine  m ON c.machine_id  = m.machine_id
        JOIN station  s ON m.station_id  = s.station_id
        JOIN pipeline p ON s.pipeline_id = p.pipeline_id
        JOIN zone     z ON p.zone_id     = z.zone_id
        WHERE z.zone_id = %s
        ORDER BY a.timestamp DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (zone_id,))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 6 — GET PIPELINE INFO
# =========================================================

@mcp.tool
def get_pipeline_info(pipeline_id: str = "") -> list[dict]:
    """Return pipeline information."""
    sql = """
        SELECT pipeline_id, nom_pipeline, type_produit, localisation_geo,
               longueur, diametre, point_debut, point_fin
        FROM pipeline
        WHERE (%s = '' OR pipeline_id = %s)
        ORDER BY pipeline_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (pipeline_id, pipeline_id))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 7 — GET STATION STATUS
# =========================================================

@mcp.tool
def get_station_status() -> list[dict]:
    """Return all station status."""
    sql = """
        SELECT station_id, nom_station, type_station, localisation, status
        FROM station ORDER BY station_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 8 — MAINTENANCE HISTORY
# =========================================================

@mcp.tool
def get_maintenance_history(machine_id: str) -> list[dict]:
    """Return machine maintenance history."""
    sql = """
        SELECT maintenance_id, machine_id, date, type, description
        FROM maintenance WHERE machine_id = %s ORDER BY date DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (machine_id,))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 9 — UPDATE MACHINE STATUS
# =========================================================

@mcp.tool
def update_machine_status(machine_id: str, new_status: str) -> dict:
    """Update machine status."""
    allowed = ["EnMarche", "Arret", "Maintenance", "Alarme"]
    if new_status not in allowed:
        return {"success": False, "error": "Invalid status"}
    sql = "UPDATE machine SET status = %s WHERE machine_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status, machine_id))
            conn.commit()
    return {"success": True, "machine_id": machine_id, "new_status": new_status}

# =========================================================
# TOOL 10 — MACHINES IN ALARM
# =========================================================

@mcp.tool
def get_machines_in_alarm() -> list[dict]:
    """Return machines currently in alarm."""
    sql = "SELECT * FROM vue_machines_alarme;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 11 — RESOLVE ALERT
# =========================================================

@mcp.tool
def resolve_alert(alert_id: int) -> dict:
    """Resolve alert by deleting it."""
    sql = "DELETE FROM alerte WHERE alerte_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (alert_id,))
            conn.commit()
    return {"success": True, "resolved_alert": alert_id}

# =========================================================
# TOOL 12 — ZONE OVERVIEW
# =========================================================

@mcp.tool
def get_zone_overview() -> list[dict]:
    """Overview of all industrial zones."""
    sql = """
        SELECT z.zone_id, z.nom,
               COUNT(DISTINCT p.pipeline_id) AS pipelines,
               COUNT(DISTINCT s.station_id)  AS stations,
               COUNT(DISTINCT m.machine_id)  AS machines,
               COUNT(DISTINCT a.alerte_id)   AS alerts
        FROM zone z
        LEFT JOIN pipeline p ON z.zone_id     = p.zone_id
        LEFT JOIN station  s ON p.pipeline_id = s.pipeline_id
        LEFT JOIN machine  m ON s.station_id  = m.station_id
        LEFT JOIN capteur  c ON m.machine_id  = c.machine_id
        LEFT JOIN alerte   a ON c.capteur_id  = a.capteur_id
        GROUP BY z.zone_id, z.nom ORDER BY z.zone_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 13 — MACHINE AVAILABILITY
# =========================================================

@mcp.tool
def get_machine_availability() -> list[dict]:
    """Machine reliability overview."""
    sql = """
        SELECT machine_id, type, disponibilite, status
        FROM machine ORDER BY disponibilite ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 14 — TOP ALERTED MACHINES
# =========================================================

@mcp.tool
def get_top_alerted_machines() -> list[dict]:
    """Machines generating most alerts."""
    sql = """
        SELECT m.machine_id, m.type, COUNT(a.alerte_id) AS total_alerts
        FROM machine m
        JOIN capteur c ON m.machine_id  = c.machine_id
        JOIN alerte  a ON c.capteur_id  = a.capteur_id
        GROUP BY m.machine_id, m.type
        ORDER BY total_alerts DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 15 — TEMPERATURE ANOMALIES
# =========================================================

@mcp.tool
def get_temperature_anomalies() -> list[dict]:
    """Detect abnormal temperatures (> 90°C)."""
    sql = """
        SELECT m.machine_id, c.capteur_id, d.valeur, d.timestamp
        FROM vue_derniere_mesure d
        JOIN capteur c ON d.capteur_id = c.capteur_id
        JOIN machine m ON c.machine_id = m.machine_id
        WHERE c.type_mesure = 'Temperature' AND d.valeur > 90
        ORDER BY d.valeur DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 16 — PRESSURE TRENDS
# =========================================================

@mcp.tool
def get_pressure_trends() -> list[dict]:
    """Analyze pressure sensor trends (all-time avg/max/min)."""
    sql = """
        SELECT capteur_id,
               ROUND(AVG(valeur)::NUMERIC, 2) AS avg_pressure,
               ROUND(MAX(valeur)::NUMERIC, 2) AS max_pressure,
               ROUND(MIN(valeur)::NUMERIC, 2) AS min_pressure
        FROM mesure
        WHERE capteur_id IN (
            SELECT capteur_id FROM capteur WHERE type_mesure = 'Pression'
        )
        GROUP BY capteur_id
        ORDER BY capteur_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 17 — PIPELINE FLOW RATE
# =========================================================

@mcp.tool
def get_pipeline_flow_rate() -> list[dict]:
    """Pipeline throughput analysis (all-time avg flow)."""
    sql = """
        SELECT p.pipeline_id, p.nom_pipeline,
               ROUND(AVG(ms.valeur)::NUMERIC, 2) AS avg_flow_rate
        FROM pipeline p
        JOIN station  s  ON p.pipeline_id = s.pipeline_id
        JOIN machine  m  ON s.station_id  = m.station_id
        JOIN capteur  c  ON m.machine_id  = c.machine_id
        JOIN mesure   ms ON c.capteur_id  = ms.capteur_id
        WHERE c.type_mesure = 'Debit'
        GROUP BY p.pipeline_id, p.nom_pipeline;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 18 — COMPARE ZONES
# =========================================================

@mcp.tool
def compare_zones() -> list[dict]:
    """Compare operational metrics between zones."""
    sql = """
        SELECT z.zone_id, z.nom,
               COUNT(DISTINCT m.machine_id)         AS machines,
               COUNT(DISTINCT a.alerte_id)           AS alerts,
               ROUND(AVG(m.disponibilite)::NUMERIC, 1) AS avg_disponibilite
        FROM zone z
        LEFT JOIN pipeline p ON z.zone_id     = p.zone_id
        LEFT JOIN station  s ON p.pipeline_id = s.pipeline_id
        LEFT JOIN machine  m ON s.station_id  = m.station_id
        LEFT JOIN capteur  c ON m.machine_id  = c.machine_id
        LEFT JOIN alerte   a ON c.capteur_id  = a.capteur_id
        GROUP BY z.zone_id, z.nom;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 19 — MACHINE HEALTH SCORE
# =========================================================

@mcp.tool
def get_machine_health_score() -> list[dict]:
    """Composite machine health score /100."""
    sql = """
        SELECT machine_id, status, disponibilite,
               CASE
                   WHEN status = 'Alarme'      THEN 20
                   WHEN disponibilite < 50     THEN 40
                   WHEN disponibilite < 75     THEN 70
                   ELSE 95
               END AS health_score
        FROM machine ORDER BY health_score ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 20 — EMERGENCY SHUTDOWN
# =========================================================

@mcp.tool
def emergency_shutdown(machine_id: str) -> dict:
    """Emergency stop for machine."""
    sql = "UPDATE machine SET status = 'Arret' WHERE machine_id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (machine_id,))
            conn.commit()
    return {"success": True, "machine_shutdown": machine_id}

# =========================================================
# TOOL 21 — CREATE MAINTENANCE TICKET
# =========================================================

@mcp.tool
def create_maintenance_ticket(machine_id: str, maintenance_type: str, description: str) -> dict:
    """Create maintenance operation."""
    sql = """
        INSERT INTO maintenance (machine_id, date, type, description)
        VALUES (%s, CURRENT_DATE, %s, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (machine_id, maintenance_type, description))
            conn.commit()
    return {"success": True, "machine_id": machine_id, "maintenance_created": True}

# =========================================================
# TOOL 22 — CUSTOM QUERY
# =========================================================

@mcp.tool
def run_query(sql: str) -> list[dict]:
    """Execute custom SELECT query (read-only)."""
    if not sql.strip().upper().startswith("SELECT"):
        return [{"error": "Only SELECT queries are allowed."}]
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 23 — GET BUDGET STATUS
# =========================================================

@mcp.tool
def get_budget_status(pipeline_id: str = "", periode: str = "") -> list[dict]:
    """Return budget status for pipelines."""
    sql = """
        SELECT b.budget_id, b.pipeline_id, p.nom_pipeline, p.type_produit,
               b.periode, b.budget_alloue, b.cout_total, b.solde,
               ROUND(CASE WHEN b.budget_alloue > 0
                     THEN (b.cout_total / b.budget_alloue * 100)::NUMERIC
                     ELSE 0 END, 2) AS pct_consomme
        FROM budget b
        JOIN pipeline p ON b.pipeline_id = p.pipeline_id
        WHERE (%s = '' OR b.pipeline_id = %s)
          AND (%s = '' OR b.periode = %s)
        ORDER BY b.periode DESC, b.pipeline_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (pipeline_id, pipeline_id, periode, periode))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 24 — GET TARIFS
# =========================================================

@mcp.tool
def get_tarifs(type_produit: str = "", type_mesure: str = "") -> list[dict]:
    """Return pricing tariffs."""
    sql = """
        SELECT tarif_id, type_produit, type_mesure,
               prix_unitaire, unite, date_effet
        FROM tarif
        WHERE (%s = '' OR type_produit = %s)
          AND (%s = '' OR type_mesure  = %s)
        ORDER BY type_produit, type_mesure, date_effet DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (type_produit, type_produit, type_mesure, type_mesure))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 25 — GET TRANSACTION HISTORY
# =========================================================

@mcp.tool
def get_transaction_history(pipeline_id: str = "", station_id: str = "", hours: int = 24) -> list[dict]:
    """Return recent volume transactions with costs."""
    sql = """
        SELECT tv.transaction_id, tv.station_id, st.nom_station,
               pi.pipeline_id, pi.nom_pipeline,
               tv.capteur_id, tv.tarif_id, tv.type_mesure,
               tv.valeur, tv.cout, tv.timestamp
        FROM transaction_volume tv
        JOIN station  st ON tv.station_id  = st.station_id
        JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
        WHERE tv.timestamp > NOW() - (%s * INTERVAL '1 hour')
          AND (%s = '' OR pi.pipeline_id = %s)
          AND (%s = '' OR tv.station_id  = %s)
        ORDER BY tv.timestamp DESC LIMIT 200;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (hours, pipeline_id, pipeline_id, station_id, station_id))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 26 — GET COST SUMMARY BY PIPELINE
# =========================================================

@mcp.tool
def get_cost_summary_by_pipeline(periode: str = "") -> list[dict]:
    """Aggregate cost breakdown per pipeline for a given period."""
    sql = """
        SELECT pi.pipeline_id, pi.nom_pipeline, pi.type_produit,
               TO_CHAR(tv.timestamp, 'YYYY-MM') AS periode,
               COUNT(tv.transaction_id)          AS nb_transactions,
               ROUND(SUM(tv.cout)::NUMERIC, 2)   AS cout_total,
               ROUND(AVG(tv.cout)::NUMERIC, 2)   AS cout_moyen,
               ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Debit')::NUMERIC,      2) AS cout_debit,
               ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Pression')::NUMERIC,   2) AS cout_pression,
               ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure = 'Temperature')::NUMERIC,2) AS cout_temperature
        FROM transaction_volume tv
        JOIN station  st ON tv.station_id  = st.station_id
        JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
        WHERE (%s = '' OR TO_CHAR(tv.timestamp, 'YYYY-MM') = %s)
        GROUP BY pi.pipeline_id, pi.nom_pipeline, pi.type_produit,
                 TO_CHAR(tv.timestamp, 'YYYY-MM')
        ORDER BY periode DESC, cout_total DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (periode, periode))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 27 — GET BUDGET ALERTS
# =========================================================

@mcp.tool
def get_budget_alerts(warning_threshold_pct: float = 80.0) -> list[dict]:
    """Return budgets over warning threshold or exceeded."""
    sql = """
        SELECT b.budget_id, b.pipeline_id, p.nom_pipeline, b.periode,
               b.budget_alloue, b.cout_total, b.solde,
               ROUND((b.cout_total / NULLIF(b.budget_alloue,0) * 100)::NUMERIC, 2) AS pct_consomme,
               CASE
                   WHEN b.cout_total >= b.budget_alloue                       THEN 'Depasse'
                   WHEN b.cout_total >= b.budget_alloue * (%s / 100.0)       THEN 'Alerte'
                   ELSE 'Normal'
               END AS budget_status
        FROM budget b
        JOIN pipeline p ON b.pipeline_id = p.pipeline_id
        WHERE b.cout_total >= b.budget_alloue * (%s / 100.0)
        ORDER BY pct_consomme DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (warning_threshold_pct, warning_threshold_pct))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 28 — UPDATE TARIF
# =========================================================

@mcp.tool
def update_tarif(type_produit: str, type_mesure: str, nouveau_prix: float, unite: str) -> dict:
    """Insert a new tariff entry superseding the previous one."""
    allowed_produits = ["PetroleBrut", "Condensat", "GPL", "GazNaturel"]
    allowed_mesures  = ["Pression", "Debit", "Temperature"]
    if type_produit not in allowed_produits:
        return {"success": False, "error": f"Invalid type_produit: {type_produit}"}
    if type_mesure not in allowed_mesures:
        return {"success": False, "error": f"Invalid type_mesure: {type_mesure}"}
    if nouveau_prix <= 0:
        return {"success": False, "error": "nouveau_prix must be > 0"}
    sql_new_id = """
        SELECT COALESCE(MAX(CAST(SUBSTRING(tarif_id FROM 2) AS INT)), 0) + 1 AS next_id
        FROM tarif WHERE tarif_id ~ '^T[0-9]+$';
    """
    sql_insert = """
        INSERT INTO tarif (tarif_id, type_produit, type_mesure, prix_unitaire, unite, date_effet)
        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
        RETURNING tarif_id, date_effet;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_new_id)
            next_id      = cur.fetchone()["next_id"]
            new_tarif_id = f"T{next_id}"
            cur.execute(sql_insert, (new_tarif_id, type_produit, type_mesure, nouveau_prix, unite))
            result = cur.fetchone()
            conn.commit()
    return {
        "success": True, "tarif_id": result["tarif_id"],
        "type_produit": type_produit, "type_mesure": type_mesure,
        "nouveau_prix": nouveau_prix, "unite": unite,
        "date_effet": str(result["date_effet"])
    }

# =========================================================
# TOOL 29 — SET BUDGET
# =========================================================

@mcp.tool
def set_budget(pipeline_id: str, periode: str, budget_alloue: float) -> dict:
    """Create or update a budget allocation for a pipeline/period."""
    if budget_alloue <= 0:
        return {"success": False, "error": "budget_alloue must be > 0"}
    sql_select = "SELECT budget_id FROM budget WHERE pipeline_id = %s AND periode = %s;"
    sql_insert = """
        INSERT INTO budget (pipeline_id, periode, budget_alloue, cout_total)
        VALUES (%s, %s, %s, 0)
        RETURNING budget_id, pipeline_id, periode, budget_alloue, cout_total, solde;
    """
    sql_update = """
        UPDATE budget SET budget_alloue = %s
        WHERE pipeline_id = %s AND periode = %s
        RETURNING budget_id, pipeline_id, periode, budget_alloue, cout_total, solde;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
        "success": True, "action": action,
        "budget_id":     row["budget_id"],
        "pipeline_id":   row["pipeline_id"],
        "periode":       row["periode"],
        "budget_alloue": float(row["budget_alloue"]),
        "cout_total":    float(row["cout_total"]),
        "solde":         float(row["solde"]),
    }

# =========================================================
# TOOL 30 — ALERT FREQUENCY BY SENSOR
# =========================================================

@mcp.tool
def get_alert_frequency_by_sensor() -> list[dict]:
    """
    Count total alerts per sensor, ranked descending.
    Useful for identifying the noisiest / most problematic sensors.
    """
    sql = """
        SELECT
            a.capteur_id,
            c.type_mesure,
            c.unite,
            COUNT(*)                                                        AS total_alerts,
            COUNT(*) FILTER (WHERE a.type_alerte = 'Critique')             AS critiques,
            COUNT(*) FILTER (WHERE a.type_alerte = 'Avertissement')        AS avertissements,
            COUNT(*) FILTER (WHERE a.type_alerte = 'Resolue')              AS resolues,
            ROUND(AVG(a.valeur::NUMERIC), 2)                               AS avg_valeur
        FROM alerte a
        JOIN capteur c ON a.capteur_id = c.capteur_id
        GROUP BY a.capteur_id, c.type_mesure, c.unite
        ORDER BY total_alerts DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 31 — ALERT TREND BY DAY
# =========================================================

@mcp.tool
def get_alert_trend_by_day(days: int = 14) -> list[dict]:
    """
    Daily alert counts for the last N days, broken down by type.
    Perfect for generating a line/bar trend chart.
    """
    sql = """
        SELECT
            DATE(timestamp)                                                  AS jour,
            COUNT(*)                                                         AS total,
            COUNT(*) FILTER (WHERE type_alerte = 'Critique')                AS critiques,
            COUNT(*) FILTER (WHERE type_alerte = 'Avertissement')           AS avertissements,
            COUNT(*) FILTER (WHERE type_alerte = 'Resolue')                 AS resolues
        FROM alerte
        WHERE timestamp >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY DATE(timestamp)
        ORDER BY jour ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (days,))
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 32 — SENSOR STATS LAST 24H
# =========================================================

@mcp.tool
def get_sensor_stats_last_24h() -> list[dict]:
    """
    Statistical summary per sensor over the last 24 hours:
    min, avg, max, stddev, reading count.
    Helps spot sensors with high variance or drift.
    """
    sql = """
        SELECT
            m.capteur_id,
            c.type_mesure,
            c.unite,
            COUNT(*)                                   AS nb_mesures,
            ROUND(MIN(m.valeur)::NUMERIC,  2)          AS val_min,
            ROUND(AVG(m.valeur)::NUMERIC,  2)          AS val_avg,
            ROUND(MAX(m.valeur)::NUMERIC,  2)          AS val_max,
            ROUND(STDDEV(m.valeur)::NUMERIC, 2)        AS val_stddev
        FROM mesure m
        JOIN capteur c ON m.capteur_id = c.capteur_id
        WHERE m.timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY m.capteur_id, c.type_mesure, c.unite
        ORDER BY m.capteur_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 33 — DEBIT EVOLUTION BY HOUR (last 24h)
# =========================================================

@mcp.tool
def get_debit_evolution_by_hour() -> list[dict]:
    """
    Hourly average flow rate (m³/h) per pipeline over the last 24 hours.
    Use for a line chart showing throughput evolution.
    """
    sql = """
        SELECT
            p.pipeline_id,
            p.nom_pipeline,
            DATE_TRUNC('hour', ms.timestamp)            AS heure,
            ROUND(AVG(ms.valeur)::NUMERIC, 2)           AS debit_moyen
        FROM mesure ms
        JOIN capteur  c  ON ms.capteur_id  = c.capteur_id
        JOIN machine  m  ON c.machine_id   = m.machine_id
        JOIN station  s  ON m.station_id   = s.station_id
        JOIN pipeline p  ON s.pipeline_id  = p.pipeline_id
        WHERE c.type_mesure = 'Debit'
          AND ms.timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY p.pipeline_id, p.nom_pipeline, DATE_TRUNC('hour', ms.timestamp)
        ORDER BY heure ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {**dict(r), "heure": str(r["heure"])}
                for r in rows
            ]

# =========================================================
# TOOL 34 — PRESSURE EVOLUTION BY HOUR (last 24h)
# =========================================================

@mcp.tool
def get_pressure_evolution_by_hour() -> list[dict]:
    """
    Hourly average pressure (bar) per pipeline over the last 24 hours.
    Use for a line chart showing pressure evolution.
    """
    sql = """
        SELECT
            p.pipeline_id,
            p.nom_pipeline,
            DATE_TRUNC('hour', ms.timestamp)            AS heure,
            ROUND(AVG(ms.valeur)::NUMERIC, 2)           AS pression_moyenne
        FROM mesure ms
        JOIN capteur  c  ON ms.capteur_id  = c.capteur_id
        JOIN machine  m  ON c.machine_id   = m.machine_id
        JOIN station  s  ON m.station_id   = s.station_id
        JOIN pipeline p  ON s.pipeline_id  = p.pipeline_id
        WHERE c.type_mesure = 'Pression'
          AND ms.timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY p.pipeline_id, p.nom_pipeline, DATE_TRUNC('hour', ms.timestamp)
        ORDER BY heure ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {**dict(r), "heure": str(r["heure"])}
                for r in rows
            ]

# =========================================================
# TOOL 35 — TEMPERATURE EVOLUTION BY HOUR (last 24h)
# =========================================================

@mcp.tool
def get_temp_evolution_by_hour() -> list[dict]:
    """
    Hourly average temperature (°C) per sensor over the last 24 hours.
    Use for a line chart. Covers all temperature sensors.
    """
    sql = """
        SELECT
            c.capteur_id,
            DATE_TRUNC('hour', ms.timestamp)            AS heure,
            ROUND(AVG(ms.valeur)::NUMERIC, 2)           AS temp_moyenne
        FROM mesure ms
        JOIN capteur c ON ms.capteur_id = c.capteur_id
        WHERE c.type_mesure = 'Temperature'
          AND ms.timestamp >= NOW() - INTERVAL '24 hours'
        GROUP BY c.capteur_id, DATE_TRUNC('hour', ms.timestamp)
        ORDER BY heure ASC, c.capteur_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {**dict(r), "heure": str(r["heure"])}
                for r in rows
            ]

# =========================================================
# TOOL 36 — COST EVOLUTION BY DAY (last 30 days)
# =========================================================

@mcp.tool
def get_cost_evolution_by_day() -> list[dict]:
    """
    Daily total cost (DZD) per pipeline over the last 30 days.
    Perfect for a multi-series line chart showing spending trends.
    """
    sql = """
        SELECT
            pi.pipeline_id,
            pi.nom_pipeline,
            DATE(tv.timestamp)                          AS jour,
            ROUND(SUM(tv.cout)::NUMERIC, 2)             AS cout_journalier,
            COUNT(tv.transaction_id)                    AS nb_transactions
        FROM transaction_volume tv
        JOIN station  st ON tv.station_id  = st.station_id
        JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
        WHERE tv.timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY pi.pipeline_id, pi.nom_pipeline, DATE(tv.timestamp)
        ORDER BY jour ASC, pi.pipeline_id;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {**dict(r), "jour": str(r["jour"])}
                for r in rows
            ]

# =========================================================
# TOOL 37 — MTBF PER MACHINE
# =========================================================

@mcp.tool
def get_mtbf_per_machine() -> list[dict]:
    """
    Mean Time Between Failures (alerts) per machine, in hours.
    Computed as: total monitoring window / number of critical alerts.
    Lower MTBF = more failure-prone machine.
    """
    sql = """
        SELECT
            m.machine_id,
            m.type,
            COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Critique') AS nb_critiques,
            ROUND(
                EXTRACT(EPOCH FROM (MAX(a.timestamp) - MIN(a.timestamp))) / 3600.0
                / NULLIF(COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Critique'), 0)
            , 2) AS mtbf_heures
        FROM machine m
        JOIN capteur c ON m.machine_id = c.machine_id
        LEFT JOIN alerte a ON c.capteur_id = a.capteur_id
        GROUP BY m.machine_id, m.type
        HAVING COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Critique') > 0
        ORDER BY mtbf_heures ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 38 — SENSOR OUT-OF-RANGE PERCENTAGE
# =========================================================

@mcp.tool
def get_sensor_out_of_range_pct() -> list[dict]:
    """
    Percentage of sensor readings that exceeded their configured thresholds
    over all recorded history. High % = consistently problematic sensor.
    """
    sql = """
        SELECT
            ms.capteur_id,
            c.type_mesure,
            c.unite,
            sc.valeur_min,
            sc.valeur_max,
            COUNT(*)                                                         AS total_readings,
            COUNT(*) FILTER (WHERE ms.valeur < sc.valeur_min
                                OR ms.valeur > sc.valeur_max)               AS out_of_range,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ms.valeur < sc.valeur_min
                                          OR ms.valeur > sc.valeur_max)
                / NULLIF(COUNT(*), 0)
            , 2)                                                             AS pct_hors_seuil
        FROM mesure ms
        JOIN capteur       c  ON ms.capteur_id = c.capteur_id
        JOIN seuil_capteur sc ON ms.capteur_id = sc.capteur_id
        GROUP BY ms.capteur_id, c.type_mesure, c.unite, sc.valeur_min, sc.valeur_max
        ORDER BY pct_hors_seuil DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 39 — PIPELINE EFFICIENCY SCORE
# =========================================================

@mcp.tool
def get_pipeline_efficiency_score() -> list[dict]:
    """
    Composite operational efficiency score per pipeline (0-100).
    Formula: avg_machine_availability * (1 - alert_rate_penalty) * uptime_factor.
    Use for high-level KPI dashboard.
    """
    sql = """
        WITH machine_stats AS (
            SELECT
                p.pipeline_id,
                p.nom_pipeline,
                ROUND(AVG(m.disponibilite)::NUMERIC, 1)        AS avg_disponibilite,
                COUNT(DISTINCT m.machine_id)                    AS total_machines,
                COUNT(DISTINCT m.machine_id)
                    FILTER (WHERE m.status = 'EnMarche')        AS machines_en_marche,
                COUNT(DISTINCT m.machine_id)
                    FILTER (WHERE m.status = 'Alarme')          AS machines_alarme
            FROM pipeline p
            JOIN station s ON p.pipeline_id = s.pipeline_id
            JOIN machine m ON s.station_id  = m.station_id
            GROUP BY p.pipeline_id, p.nom_pipeline
        ),
        alert_stats AS (
            SELECT
                p.pipeline_id,
                COUNT(a.alerte_id) AS total_alerts,
                COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Critique') AS critiques
            FROM pipeline p
            JOIN station  s ON p.pipeline_id = s.pipeline_id
            JOIN machine  m ON s.station_id  = m.station_id
            JOIN capteur  c ON m.machine_id  = c.machine_id
            LEFT JOIN alerte a ON c.capteur_id = a.capteur_id
            GROUP BY p.pipeline_id
        )
        SELECT
            ms.pipeline_id,
            ms.nom_pipeline,
            ms.avg_disponibilite,
            ms.machines_en_marche,
            ms.total_machines,
            ms.machines_alarme,
            COALESCE(al.total_alerts, 0)  AS total_alerts,
            COALESCE(al.critiques, 0)     AS critiques,
            ROUND(LEAST(100, GREATEST(0,
                ms.avg_disponibilite
                - (COALESCE(al.machines_alarme, 0) * 10)
                - LEAST(20, COALESCE(al.critiques, 0) * 0.5)
            ))::NUMERIC, 1)               AS efficiency_score
        FROM machine_stats ms
        LEFT JOIN alert_stats al ON ms.pipeline_id = al.pipeline_id
        ORDER BY efficiency_score DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 40 — MAINTENANCE FREQUENCY PER MACHINE
# =========================================================

@mcp.tool
def get_maintenance_frequency() -> list[dict]:
    """
    Monthly maintenance operation count per machine for the last 6 months.
    Useful for spotting machines that need disproportionate attention.
    """
    sql = """
        SELECT
            machine_id,
            TO_CHAR(date, 'YYYY-MM')        AS mois,
            COUNT(*)                         AS nb_maintenances,
            STRING_AGG(DISTINCT type, ', ') AS types
        FROM maintenance
        WHERE date >= NOW() - INTERVAL '6 months'
        GROUP BY machine_id, TO_CHAR(date, 'YYYY-MM')
        ORDER BY machine_id, mois DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 41 — ALERT RESOLUTION RATE
# =========================================================

@mcp.tool
def get_alert_resolution_rate() -> list[dict]:
    """
    Resolution rate per pipeline: ratio of Resolue alerts vs total.
    A low resolution rate indicates alerts are accumulating unaddressed.
    """
    sql = """
        SELECT
            p.pipeline_id,
            p.nom_pipeline,
            COUNT(a.alerte_id)                                              AS total_alertes,
            COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Resolue')    AS resolues,
            COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Critique')   AS critiques,
            COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Avertissement') AS avertissements,
            ROUND(
                100.0 * COUNT(a.alerte_id) FILTER (WHERE a.type_alerte = 'Resolue')
                / NULLIF(COUNT(a.alerte_id), 0)
            , 1) AS taux_resolution_pct
        FROM pipeline p
        JOIN station  s ON p.pipeline_id = s.pipeline_id
        JOIN machine  m ON s.station_id  = m.station_id
        JOIN capteur  c ON m.machine_id  = c.machine_id
        LEFT JOIN alerte a ON c.capteur_id = a.capteur_id
        GROUP BY p.pipeline_id, p.nom_pipeline
        ORDER BY taux_resolution_pct ASC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 42 — STATION COST RANKING
# =========================================================

@mcp.tool
def get_station_cost_ranking() -> list[dict]:
    """
    Stations ranked by total cost generated (all time).
    Identifies which stations are the biggest cost drivers.
    Includes breakdown by sensor type.
    """
    sql = """
        SELECT
            tv.station_id,
            st.nom_station,
            pi.pipeline_id,
            pi.nom_pipeline,
            COUNT(tv.transaction_id)                                         AS nb_transactions,
            ROUND(SUM(tv.cout)::NUMERIC, 2)                                  AS cout_total,
            ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure='Debit')::NUMERIC, 2)      AS cout_debit,
            ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure='Pression')::NUMERIC, 2)   AS cout_pression,
            ROUND(SUM(tv.cout) FILTER (WHERE tv.type_mesure='Temperature')::NUMERIC, 2) AS cout_temperature
        FROM transaction_volume tv
        JOIN station  st ON tv.station_id  = st.station_id
        JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
        GROUP BY tv.station_id, st.nom_station, pi.pipeline_id, pi.nom_pipeline
        ORDER BY cout_total DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]

# =========================================================
# TOOL 43 — BUDGET FORECAST (days until exhaustion)
# =========================================================

@mcp.tool
def get_budget_forecast() -> list[dict]:
    """
    Linear forecast: based on current month's daily spend rate,
    how many days until each pipeline exhausts its budget?
    Returns projected_exhaustion_date and days_remaining.
    Negative days_remaining = already exceeded.
    """
    sql = """
        WITH daily_spend AS (
            SELECT
                pi.pipeline_id,
                pi.nom_pipeline,
                DATE(tv.timestamp)                  AS jour,
                SUM(tv.cout)                        AS cout_jour
            FROM transaction_volume tv
            JOIN station  st ON tv.station_id  = st.station_id
            JOIN pipeline pi ON st.pipeline_id = pi.pipeline_id
            WHERE tv.timestamp >= DATE_TRUNC('month', NOW())
            GROUP BY pi.pipeline_id, pi.nom_pipeline, DATE(tv.timestamp)
        ),
        avg_daily AS (
            SELECT
                pipeline_id, nom_pipeline,
                ROUND(AVG(cout_jour)::NUMERIC, 2)   AS avg_daily_cost,
                COUNT(DISTINCT jour)                 AS days_with_data
            FROM daily_spend
            GROUP BY pipeline_id, nom_pipeline
        ),
        budget_now AS (
            SELECT pipeline_id, budget_alloue, cout_total, solde
            FROM budget
            WHERE periode = TO_CHAR(NOW(), 'YYYY-MM')
        )
        SELECT
            ad.pipeline_id,
            ad.nom_pipeline,
            ad.avg_daily_cost,
            ad.days_with_data,
            bn.budget_alloue,
            bn.cout_total,
            bn.solde,
            CASE
                WHEN ad.avg_daily_cost > 0
                THEN ROUND((bn.solde / ad.avg_daily_cost)::NUMERIC, 1)
                ELSE NULL
            END AS jours_restants,
            CASE
                WHEN ad.avg_daily_cost > 0 AND bn.solde > 0
                THEN (NOW() + ((bn.solde / ad.avg_daily_cost) * INTERVAL '1 day'))::DATE
                ELSE NULL
            END AS date_epuisement
        FROM avg_daily ad
        JOIN budget_now bn ON ad.pipeline_id = bn.pipeline_id
        ORDER BY jours_restants ASC NULLS LAST;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {**dict(r),
                 "date_epuisement": str(r["date_epuisement"]) if r["date_epuisement"] else None}
                for r in rows
            ]

# =========================================================
# TOOL 44 — FULL OPERATIONAL REPORT (one-shot KPI snapshot)
# =========================================================

@mcp.tool
def get_full_operational_report() -> dict:
    """
    Single call that returns a complete operational snapshot:
    - Global KPIs (machines, alerts, budget)
    - Per-pipeline summary
    - Top 3 critical alerts
    - Top 3 machines by alert count
    - Budget status with forecast
    Designed for the daily briefing or dashboard summary card.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # Global KPIs
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM machine)                              AS total_machines,
                    (SELECT COUNT(*) FROM machine WHERE status = 'EnMarche')   AS en_marche,
                    (SELECT COUNT(*) FROM machine WHERE status = 'Alarme')     AS en_alarme,
                    (SELECT COUNT(*) FROM machine WHERE status = 'Arret')      AS a_l_arret,
                    (SELECT COUNT(*) FROM alerte)                              AS total_alertes,
                    (SELECT COUNT(*) FROM alerte WHERE type_alerte='Critique') AS alertes_critiques,
                    (SELECT COUNT(*) FROM capteur)                             AS total_capteurs,
                    (SELECT COUNT(*) FROM mesure WHERE timestamp >= NOW()-INTERVAL '1 hour') AS mesures_last_hour
            """)
            kpis = dict(cur.fetchone())

            # Per-pipeline summary
            cur.execute("""
                SELECT
                    p.pipeline_id, p.nom_pipeline, p.type_produit,
                    COUNT(DISTINCT m.machine_id)                              AS machines,
                    COUNT(DISTINCT a.alerte_id)                               AS alertes,
                    COUNT(DISTINCT a.alerte_id) FILTER
                        (WHERE a.type_alerte='Critique')                      AS critiques,
                    ROUND(AVG(m.disponibilite)::NUMERIC,1)                   AS avg_dispo
                FROM pipeline p
                JOIN station s ON p.pipeline_id = s.pipeline_id
                JOIN machine m ON s.station_id  = m.station_id
                JOIN capteur c ON m.machine_id  = c.machine_id
                LEFT JOIN alerte a ON c.capteur_id = a.capteur_id
                GROUP BY p.pipeline_id, p.nom_pipeline, p.type_produit
                ORDER BY p.pipeline_id;
            """)
            pipelines = [dict(r) for r in cur.fetchall()]

            # Top 3 critical alerts
            cur.execute("""
                SELECT capteur_id, valeur, type_alerte, message, timestamp
                FROM alerte
                WHERE type_alerte = 'Critique'
                ORDER BY timestamp DESC LIMIT 3;
            """)
            top_alerts = [
                {**dict(r), "timestamp": str(r["timestamp"])}
                for r in cur.fetchall()
            ]

            # Top 3 most-alerted machines
            cur.execute("""
                SELECT m.machine_id, m.type, m.status,
                       COUNT(a.alerte_id) AS total_alerts
                FROM machine m
                JOIN capteur c ON m.machine_id  = c.machine_id
                JOIN alerte  a ON c.capteur_id  = a.capteur_id
                GROUP BY m.machine_id, m.type, m.status
                ORDER BY total_alerts DESC LIMIT 3;
            """)
            top_machines = [dict(r) for r in cur.fetchall()]

            # Budget current month
            cur.execute("""
                SELECT b.pipeline_id, p.nom_pipeline,
                       b.budget_alloue, b.cout_total, b.solde,
                       ROUND((b.cout_total/NULLIF(b.budget_alloue,0)*100)::NUMERIC,1) AS pct
                FROM budget b
                JOIN pipeline p ON b.pipeline_id = p.pipeline_id
                WHERE b.periode = TO_CHAR(NOW(),'YYYY-MM')
                ORDER BY b.pipeline_id;
            """)
            budget = [dict(r) for r in cur.fetchall()]

    return {
        "kpis":         kpis,
        "pipelines":    pipelines,
        "top_alerts":   top_alerts,
        "top_machines": top_machines,
        "budget":       budget,
    }

# =========================================================
# RESOURCE — SCHEMA OVERVIEW
# =========================================================

@mcp.resource("pipeline://schema/overview")
def schema_overview() -> str:
    """Industrial Oil & Gas Pipeline Schema"""
    return """
    INDUSTRIAL PIPELINE DATABASE
    ============================
    TABLES: zone, pipeline, station, machine, capteur, mesure,
            seuil_capteur, alerte, maintenance, tarif,
            transaction_volume, budget
    RELATIONS: Zone -> Pipeline -> Station -> Machine -> Sensor
    SENSOR TYPES: Pression, Temperature, Debit
    MACHINE STATUS: EnMarche, Arret, Maintenance, Alarme
    FINANCIAL: tarif (unit prices DZD), transaction_volume (auto cost at TerminalArrivee), budget (monthly)
    """

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    mcp.run()