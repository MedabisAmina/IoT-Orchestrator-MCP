"""
simulation/simulator.py — Real-time sensor data generator with anomaly injection
Member 3 — Data Simulation Engineer | Phase 1

Usage (standalone):
    python simulator.py
    python simulator.py --anomaly
    python simulator.py --interval 3

Imported by:
    api/main.py  →  run_simulator(interval, force_anomaly)
"""

import os
import psycopg2
import random
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load .env from project root (works whether called directly or imported)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── DB Connection ────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB",   "pipeline_db"),
        user=os.getenv("POSTGRES_USER",   "iotuser"),
        password=os.getenv("POSTGRES_PASS", "iotfrontier"),
    )

# ─── Sensor Configuration ─────────────────────────────────────────────────────
SENSORS = {
    "C1": {
        "type": "Pression",    "unit": "bar",
        "normal":  (15, 90),
        "anomaly_low":  5,
        "anomaly_high": 115,
    },
    "C2": {
        "type": "Temperature", "unit": "°C",
        "normal":  (10, 80),
        "anomaly_low":  -5,
        "anomaly_high": 105,
    },
    "C3": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (100, 450),
        "anomaly_low":  20,
        "anomaly_high": 560,
    },
}

# ─── Value generators ─────────────────────────────────────────────────────────
def normal_value(sensor_id: str) -> float:
    lo, hi = SENSORS[sensor_id]["normal"]
    mid = (lo + hi) / 2
    std = (hi - lo) / 6
    value = random.gauss(mid, std)
    return round(max(lo, min(hi, value)), 3)

def anomaly_value(sensor_id: str, direction: str = "high") -> float:
    cfg = SENSORS[sensor_id]
    if direction == "low":
        base = cfg["anomaly_low"]
        return round(base + random.uniform(-abs(base) * 0.1, 0), 3)
    else:
        base = cfg["anomaly_high"]
        return round(base + random.uniform(0, base * 0.1), 3)

# ─── Insert logic ─────────────────────────────────────────────────────────────
def insert_mesure(conn, capteur_id: str, valeur: float):
    ts = datetime.now()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO mesure (capteur_id, valeur, timestamp) VALUES (%s, %s, %s)",
            (capteur_id, valeur, ts)
        )
    conn.commit()
    return ts

def check_last_alerts(conn, limit: int = 5):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT alerte_id, capteur_id, valeur, timestamp, type_alerte, message
            FROM alerte
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()

# ─── Main simulation loop ──────────────────────────────────────────────────────
def run_simulator(interval: int = 5, force_anomaly: bool = False):
    """
    Main loop: inserts one mesure per capteur every `interval` seconds.
    Called directly or imported by api/main.py.
    """
    interval  = int(os.getenv("SIM_INTERVAL", interval))
    force_anomaly = os.getenv("SIM_FORCE_ANOMALY", str(force_anomaly)).lower() == "true" or force_anomaly

    print("🚀 Pipeline Sensor Simulator started")
    print(f"   Interval : {interval}s | Forced anomalies: {force_anomaly}")
    print(f"   Sensors  : {list(SENSORS.keys())}")
    print("─" * 60)

    conn = get_connection()
    cycle, anomaly_count, total_inserts = 0, 0, 0

    try:
        while True:
            cycle += 1
            readings = []

            for capteur_id in SENSORS:
                inject = (force_anomaly and cycle % 10 == 0) or \
                         (not force_anomaly and random.random() < 0.05)

                if inject:
                    direction = random.choice(["high", "low"])
                    value = anomaly_value(capteur_id, direction)
                    tag = "⚠️  ANOMALY"
                    anomaly_count += 1
                else:
                    value = normal_value(capteur_id)
                    tag = "   normal "

                insert_mesure(conn, capteur_id, value)
                total_inserts += 1
                readings.append(
                    f"  [{tag}] {capteur_id} ({SENSORS[capteur_id]['type']:12s}): "
                    f"{value:8.2f} {SENSORS[capteur_id]['unit']}"
                )

            print(f"\n Cycle {cycle:04d}  —  {datetime.now().strftime('%H:%M:%S')}")
            for r in readings:
                print(r)

            if cycle % 10 == 0:
                alerts = check_last_alerts(conn)
                if alerts:
                    print(f"\n🔴 Last alerts ({len(alerts)} shown):")
                    for a in alerts:
                        print(f"   alerte_id={a[0]} | {a[1]} | val={a[2]} | {a[4]} | {a[5]}")
                else:
                    print("\n✅ No alerts yet.")

            print(f"   Total inserts: {total_inserts} | Anomalies: {anomaly_count}")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Simulator stopped.")
        print(f"   Cycles: {cycle} | Inserts: {total_inserts} | Anomalies: {anomaly_count}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline sensor simulator")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--anomaly",  action="store_true")
    args = parser.parse_args()
    run_simulator(interval=args.interval, force_anomaly=args.anomaly)