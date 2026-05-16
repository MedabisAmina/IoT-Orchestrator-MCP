"""
api/main.py — FastAPI entry point

Starts the pipeline REST API, runs the 30-day historical backfill ONCE
(only if mesure table is empty), then launches the real-time simulator
as a background daemon thread.

Run:
    python api/main.py
    # or from project root:
    uvicorn api.main:app --reload
"""

import os
import sys
import threading
import psycopg2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel

# ─── Load .env from project root ──────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── Fix import path so simulator.py / backfill.py are found in simulation/ ───
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simulation'))
from simulator import run_simulator
from backfill  import run_backfill

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Pipeline IIoT API",
    description="Industrial pipeline monitoring — Oil & Gas Algeria",
    version="1.0.0",
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

# ─── CORS — allow all origins so the React frontend can reach the API ─────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DB helper ────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB",   "pipeline_db"),
        user=os.getenv("POSTGRES_USER",   "postgres"),
        password=os.getenv("POSTGRES_PASS", "malak2004"),
    )

# ─── Helper: check if backfill already ran ────────────────────────────────────
def _mesure_table_empty() -> bool:
    """Returns True if the mesure table has no rows."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mesure")
            count = cur.fetchone()[0]
        conn.close()
        return count == 0
    except Exception as e:
        print(f"⚠️  Could not check mesure table: {e}")
        return False

# ─── Background thread: backfill once, then simulate forever ──────────────────
def _backfill_then_simulate(interval: int, force_anomaly: bool):
    if _mesure_table_empty():
        print("📦 mesure table is empty — running 30-day backfill first...")
        try:
            run_backfill(days=30, interval_minutes=5)
            print("✅ Backfill complete — starting real-time simulator...")
        except Exception as e:
            print(f"❌ Backfill failed: {e} — starting simulator anyway...")
    else:
        print("⏭️  mesure table already has data — skipping backfill.")
        print("🚀 Starting real-time simulator...")

    run_simulator(interval=interval, force_anomaly=force_anomaly)

# ─── Startup event ────────────────────────────────────────────────────────────
@app.on_event("startup")
def start_background_worker():
    interval      = int(os.getenv("SIM_INTERVAL", 5))
    force_anomaly = os.getenv("SIM_FORCE_ANOMALY", "false").lower() == "true"

    thread = threading.Thread(
        target=_backfill_then_simulate,
        kwargs={"interval": interval, "force_anomaly": force_anomaly},
        daemon=True,
    )
    thread.start()
    print(f"✅ Background worker started (interval={interval}s, anomaly={force_anomaly})")

# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "Pipeline API running",
        "docs":   "/docs",
        "redoc":  "/redoc",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ─── Alerts ───────────────────────────────────────────────────────────────────
@app.get("/alerts/recent", tags=["Alerts"])
def get_recent_alerts(limit: int = 50):
    """
    Return the most recent alerts ordered by timestamp DESC.
    Query param: limit (default 50)
    """
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM alerte ORDER BY timestamp DESC LIMIT %s",
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        # Serialize datetime objects to ISO strings
        for r in rows:
            if r.get("timestamp"):
                r["timestamp"] = r["timestamp"].isoformat()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Budget ───────────────────────────────────────────────────────────────────
@app.get("/budget/summary", tags=["Budget"])
def get_budget_summary():
    """
    Return budget rows per pipeline and period, including computed solde.
    Adds a 'solde' column (budget_alloue - cout_total) if not already present.
    """
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM budget ORDER BY pipeline_id, periode")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        # Compute solde if the column isn't already in the table
        for r in rows:
            if "solde" not in r:
                alloue = float(r.get("budget_alloue") or 0)
                depense = float(r.get("cout_total") or 0)
                r["solde"] = round(alloue - depense, 2)
            # Cast Decimal → float so JSON serialises cleanly
            for key in ("budget_alloue", "cout_total", "solde"):
                if key in r:
                    r[key] = float(r[key])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/budget/transactions", tags=["Budget"])
def get_transactions(limit: int = 200):
    """
    Return the most recent cost transactions ordered by timestamp DESC.
    Query param: limit (default 200)
    """
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM transaction_volume ORDER BY timestamp DESC LIMIT %s",
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("timestamp"):
                r["timestamp"] = r["timestamp"].isoformat()
            # Cast Decimal → float
            for key in ("valeur", "cout"):
                if key in r:
                    r[key] = float(r[key])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        response = model.generate_content(f"""
        Tu es un assistant expert en monitoring de pipelines pétroliers et gaziers.

        Question utilisateur:
        {req.message}
        """)

        return {
            "reply": response.text
        }

    except Exception as e:
        print("GEMINI ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)