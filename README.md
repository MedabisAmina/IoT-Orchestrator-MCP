# Pipeline IIoT — Oil & Gas Monitoring System

Industrial IoT monitoring platform for Oil & Gas pipeline infrastructure in Algeria. Simulates real-time sensor data (pressure, temperature, flow rate), stores it in PostgreSQL, exposes it via a FastAPI REST API and a full-featured MCP server for AI-assisted operations.

---

## Project Structure

```
PIPELINE_IOT/
├── api/
│   └── main.py                  # FastAPI app + simulator background thread
├── db/
│   └── pipeline_db.sql          # Full DB schema (tables, views, triggers)
├── mcp/
│   └── factory_mcp_server.py    # MCP server — 22 tools for Claude Desktop
├── simulation/
│   ├── simulator.py             # Real-time sensor loop (runs via API)
│   └── backfill.py              # 30-day historical data generator
├── .env                         # DB + API config (see below)
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ (with TimescaleDB optional but present in the schema)
- `pip` (or a virtual environment)

---

## Setup

### 1. Clone & install dependencies

```bash
git clone <your-repo-url>
cd PIPELINE_IOT

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file at the project root:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pipeline_db
POSTGRES_USER=iotuser
POSTGRES_PASS=iotfrontier

# API
API_HOST=0.0.0.0
API_PORT=8000

# Simulator
SIM_INTERVAL=5           # seconds between sensor readings
SIM_FORCE_ANOMALY=false  # set to true to inject anomalies every 10 cycles
```

### 3. Create the database

```bash
psql -U postgres -c "CREATE DATABASE pipeline_db;"
psql -U postgres -c "CREATE USER iotuser WITH PASSWORD 'iotfrontier';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pipeline_db TO iotuser;"

psql -U iotuser -d pipeline_db -f db/pipeline_db.sql
```

### 4. (Optional) Backfill 30 days of historical data

```bash
python simulation/backfill.py               # full 30-day backfill
python simulation/backfill.py --days 7      # shorter run for testing
python simulation/backfill.py --dry-run     # stats only, no DB writes
```

---

## Running the Project

### Start the API (+ real-time simulator)

```bash
python api/main.py
```

Or with uvicorn for development (auto-reload):

```bash
uvicorn api.main:app --reload
```

The simulator starts automatically as a background thread.

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## MCP Server (Claude Desktop)

Connect the MCP server to Claude Desktop by adding this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pipeline-industrial": {
      "command": "python",
      "args": ["mcp/factory_mcp_server.py"]
    }
  }
}
```

Then start the server manually if needed:

```bash
python mcp/factory_mcp_server.py
```

### Available MCP Tools (22)

| # | Tool | Description |
|---|------|-------------|
| 1 | `get_machine_status` | Machine operational status with zone/pipeline context |
| 2 | `get_sensor_value` | Latest reading for a given sensor |
| 3 | `get_sensor_history` | Sensor readings over the last N hours |
| 4 | `list_active_alerts` | All active alerts across all zones |
| 5 | `get_active_alerts_by_zone` | Alerts filtered by zone ID |
| 6 | `get_pipeline_info` | Pipeline metadata (product type, location, length) |
| 7 | `get_station_status` | All station statuses |
| 8 | `get_maintenance_history` | Maintenance records for a machine |
| 9 | `update_machine_status` | Change machine status (EnMarche / Arret / Maintenance / Alarme) |
| 10 | `get_machines_in_alarm` | Machines currently in alarm state |
| 11 | `resolve_alert` | Delete/resolve an alert by ID |
| 12 | `get_zone_overview` | Pipelines, stations, machines and alerts per zone |
| 13 | `get_machine_availability` | Machine reliability sorted by availability % |
| 14 | `get_top_alerted_machines` | Machines generating the most alerts |
| 15 | `get_temperature_anomalies` | Sensors with temperature above 90°C |
| 16 | `get_pressure_trends` | Avg / min / max pressure per sensor |
| 17 | `get_pipeline_flow_rate` | Average flow rate per pipeline |
| 18 | `compare_zones` | Cross-zone operational comparison |
| 19 | `get_machine_health_score` | Rule-based health score per machine |
| 20 | `emergency_shutdown` | Force a machine to Arret immediately |
| 21 | `create_maintenance_ticket` | Log a new maintenance operation |
| 22 | `run_query` | Execute a custom read-only SELECT query |

---

## Database Schema

```
zone → pipeline → station → machine → capteur → mesure
                                              ↘ alerte (via trigger)
                                    ↘ maintenance
```

**Sensor types:** `Pression` (bar) · `Temperature` (°C) · `Debit` (m³/h) · `Vibration`

**Machine statuses:** `EnMarche` · `Arret` · `Maintenance` · `Alarme`

**Key views:**
- `vue_derniere_mesure` — latest reading per sensor
- `vue_alertes_actives` — all current alerts with context
- `vue_machines_alarme` — machines in alarm with station/pipeline

Alerts are generated automatically by a PostgreSQL trigger whenever a measurement crosses a threshold defined in `seuil_capteur`.

---

## Simulator Behavior

The real-time simulator (`simulation/simulator.py`) runs as a daemon thread inside the FastAPI process. Every `SIM_INTERVAL` seconds it:

1. Generates one reading per sensor (`C1`, `C2`, `C3`) using a Gaussian distribution around normal operating ranges.
2. Injects anomalies at ~5% probability per cycle (or every 10 cycles if `SIM_FORCE_ANOMALY=true`).
3. Inserts readings into the `mesure` table — the DB trigger fires and creates alerts automatically for out-of-threshold values.

The backfill script (`simulation/backfill.py`) follows the same logic but for historical timestamps, inserting in batches of 500 rows and generating maintenance records from clustered alert periods.

---

## Requirements

```
psycopg2-binary
fastmcp
fastapi
uvicorn[standard]
python-dotenv
```

## claude desktop config

{
  "mcpServers": {
    "factory-uns": {
      "command": "C:\\projet\\factory_uns\\venv-factory\\Scripts\\python.exe",
      "args": [
        "C:\\projet\\factory_uns\\mcp\\factory_mcp_server.py"
      ],
      "env": {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "pipeline_db",
        "POSTGRES_USER": "iotuser",
        "POSTGRES_PASS": "iotfrontier"
      }
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": false,
    "ccdScheduledTasksEnabled": false,
    "sidebarMode": "chat",
    "coworkWebSearchEnabled": true,
    "epitaxyPrefs": {
      "starred-local-code-sessions": [],
      "starred-cowork-spaces": [],
      "starred-session-groups": [],
      "dframe-local-slice": {
        "pinnedOrder": [],
        "customGroupAssignments": {},
        "customGroupOrder": {}
      }
    }
  }
}