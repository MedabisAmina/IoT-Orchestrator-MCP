"""
api/main.py — FastAPI entry point
Source: github (teammate) — fixed import path + .env integration

Starts the pipeline REST API and launches the sensor simulator
as a background daemon thread.

Run:
    python api/main.py
    # or from project root:
    uvicorn api.main:app --reload
"""

import os
import sys
import threading
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# ─── Load .env from project root ──────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── Fix import path so simulator.py is found in simulation/ ──────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simulation'))
from simulator import run_simulator

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Pipeline IIoT API",
    description="Industrial pipeline monitoring — Oil & Gas Algeria",
    version="1.0.0",
)

# ─── Startup: launch simulator in background thread ───────────────────────────
@app.on_event("startup")
def start_simulator():
    interval      = int(os.getenv("SIM_INTERVAL", 5))
    force_anomaly = os.getenv("SIM_FORCE_ANOMALY", "false").lower() == "true"

    thread = threading.Thread(
        target=run_simulator,
        kwargs={"interval": interval, "force_anomaly": force_anomaly},
        daemon=True   # thread dies automatically when the main process exits
    )
    thread.start()
    print(f"✅ Simulator thread started (interval={interval}s, anomaly={force_anomaly})")

# ─── Routes ───────────────────────────────────────────────────────────────────
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

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)