# Pipeline IIoT — Oil & Gas Monitoring System

An Industrial IoT monitoring platform for Oil & Gas pipeline infrastructure, specifically designed for the Edge-Fog continuum. This system bridges the "semantic gap" between raw sensor data and strategic decision-making using a Context-Aware Microservices Orchestration approach.

It simulates real-time telemetry from Algerian pipeline networks, stores data in PostgreSQL, and exposes a high-level Model Context Protocol (MCP) server to enable AI Agents (like Claude , Gemini) to perform natural language operations. A React-based dashboard provides a unified operator interface with live alerts, budget tracking, and an embedded AI assistant.

---

## Project Structure

```
PIPELINE_IOT/
├── api/
│   └── main.py                  # FastAPI app + simulator background thread
├── db/
│   └── pipeline_db.sql          # Full DB schema (tables, views, triggers)
├── frontend/
│   └── PipelineDashboard.jsx    # React dashboard (chat · alerts · budget)
├── mcp/
│   └── factory_mcp_server.py    # MCP server — 29 tools for Claude Desktop
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
- Node.js 18+ (for the React frontend)
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

## Frontend Dashboard

The React dashboard (`frontend/PipelineDashboard.jsx`) provides a single-page operator interface with three panels:

| Panel | Description |
|---|---|
| **Assistant IA** | Conversational interface powered by Claude. Maintains full chat history and supports quick-action chips for common queries. |
| **Alertes** | Full alert log with severity coloring, sensor ID, value, and timestamp. Live badge count in the sidebar. Auto-refreshes every 10 s via the right panel. |
| **Budget & Coûts** | Budget vs. actual spend per pipeline, progress bars, transaction table, and CSV export. |

A live alert feed in the right-hand panel polls `/alerts/recent` every 10 seconds and surfaces new `Critique` alerts as they arrive.

### Required API endpoints

The dashboard expects these four routes on the FastAPI backend. Add them to `api/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/alerts/recent")
def get_recent_alerts(limit: int = 50):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM alerte ORDER BY timestamp DESC LIMIT %s", (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    for r in rows: r['timestamp'] = r['timestamp'].isoformat()
    return rows

@app.get("/budget/summary")
def get_budget_summary():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM budget ORDER BY pipeline_id, periode")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/budget/transactions")
def get_transactions(limit: int = 200):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM transaction_volume ORDER BY timestamp DESC LIMIT %s", (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    for r in rows: r['timestamp'] = r['timestamp'].isoformat()
    return rows

@app.get("/health")
def health(): return {"status": "ok"}
```

### Running the frontend

The component is a self-contained React artifact (single `.jsx` file, no build step required). Drop it into your existing React app or serve it via Claude's artifact renderer.

If you want a standalone dev server:

```bash
cd frontend
npm create vite@latest . -- --template react
# replace src/App.jsx content with PipelineDashboard.jsx
npm install
npm run dev
```

The dashboard will be available at http://localhost:5173. Set the backend URL in the **Configuration** panel (default: `http://localhost:8000`).

---

## MCP Server (Claude Desktop)

Connect the MCP server to Claude Desktop by adding this to your `claude_desktop_config.json`:

```json
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
  }
}
```

Then start the server manually if needed:

```bash
python mcp/factory_mcp_server.py
```

### Available MCP Tools (29)

#### Operational Tools

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

#### Financial Tools

| # | Tool | Description |
|---|------|-------------|
| 23 | `get_budget_status` | Budget vs. actual spend per pipeline/period with % consumed |
| 24 | `get_tarifs` | Browse unit price tariffs, filterable by product and measure type |
| 25 | `get_transaction_history` | Recent cost transactions, filterable by pipeline or station |
| 26 | `get_cost_summary_by_pipeline` | Monthly cost rollup broken down by Débit / Pression / Température |
| 27 | `get_budget_alerts` | Budgets above a configurable warning threshold (default 80%) |
| 28 | `update_tarif` | Insert a new tariff superseding the previous price |
| 29 | `set_budget` | Create or update a monthly budget allocation for a pipeline |

---

## Database Schema

```
zone → pipeline → station → machine → capteur → mesure
                                              ↘ alerte (via trigger: check_seuil)
                                              ↘ transaction_volume (via trigger: calc_cout)
                                    ↘ maintenance
pipeline → budget
tarif ──────────────────────────────↗ transaction_volume
```

**Sensor types:** `Pression` (bar) · `Temperature` (°C) · `Debit` (m³/h)

**Machine statuses:** `EnMarche` · `Arret` · `Maintenance` · `Alarme`

**Key views:**
- `vue_derniere_mesure` — latest reading per sensor
- `vue_alertes_actives` — all current alerts with context
- `vue_machines_alarme` — machines in alarm with station/pipeline

**Triggers:**
- `trigger_seuil` — fires on every `mesure` INSERT; creates an `alerte` row if the value is outside the bounds defined in `seuil_capteur`
- `trigger_cout` — fires on every `mesure` INSERT at a `TerminalArrivee` station; looks up the applicable tariff, computes cost, inserts a `transaction_volume` row, and updates the monthly `budget`

---

## Simulator Behavior

The real-time simulator (`simulation/simulator.py`) runs as a daemon thread inside the FastAPI process. Every `SIM_INTERVAL` seconds it:

1. Generates one reading per sensor (`C1`, `C2`, `C3`) using a Gaussian distribution around normal operating ranges.
2. Injects anomalies at ~5% probability per cycle (or every 10 cycles if `SIM_FORCE_ANOMALY=true`).
3. Inserts readings into the `mesure` table — the DB triggers fire automatically for threshold violations and cost calculation.

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
