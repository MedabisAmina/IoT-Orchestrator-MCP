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
# C1, C2, C3  — existing machines M1/M2 (Pompage/Compression stations)
# C5–C14      — new machines M3–M6 on terminal stations S3–S6
#
# WARNING_PCT = 10 % proximity band applied inside the [lo, hi] normal range.
# A warning value lands in  [lo, lo + 10%·range]  or  [hi - 10%·range, hi].

SENSORS = {
    # --- Station S1 (Pompage, Pipeline P1) ---
    "C1": {
        "type": "Pression",    "unit": "bar",
        "normal":  (15, 90),
        "anomaly_low":  5,     "anomaly_high": 115,
    },
    "C2": {
        "type": "Temperature", "unit": "°C",
        "normal":  (10, 80),
        "anomaly_low":  -5,    "anomaly_high": 105,
    },
    # --- Station S2 (Compression, Pipeline P2) ---
    "C3": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (100, 450),
        "anomaly_low":  20,    "anomaly_high": 560,
    },
    # --- Station S3 (TerminalDepart, Pipeline P1) ---
    "C5": {
        "type": "Pression",    "unit": "bar",
        "normal":  (20, 85),
        "anomaly_low":  5,     "anomaly_high": 110,
    },
    "C6": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (120, 430),
        "anomaly_low":  30,    "anomaly_high": 540,
    },
    # --- Station S4 (TerminalArrivee, Pipeline P1) — triggers cost calc ---
    "C7": {
        "type": "Pression",    "unit": "bar",
        "normal":  (18, 82),
        "anomaly_low":  4,     "anomaly_high": 108,
    },
    "C8": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (110, 420),
        "anomaly_low":  25,    "anomaly_high": 530,
    },
    "C9": {
        "type": "Temperature", "unit": "°C",
        "normal":  (12, 75),
        "anomaly_low":  -3,    "anomaly_high": 100,
    },
    # --- Station S5 (TerminalDepart, Pipeline P2) ---
    "C10": {
        "type": "Pression",    "unit": "bar",
        "normal":  (15, 78),
        "anomaly_low":  4,     "anomaly_high": 105,
    },
    "C11": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (80, 380),
        "anomaly_low":  20,    "anomaly_high": 490,
    },
    # --- Station S6 (TerminalArrivee, Pipeline P2) — triggers cost calc ---
    "C12": {
        "type": "Pression",    "unit": "bar",
        "normal":  (12, 75),
        "anomaly_low":  3,     "anomaly_high": 100,
    },
    "C13": {
        "type": "Debit",       "unit": "m3/h",
        "normal":  (70, 360),
        "anomaly_low":  15,    "anomaly_high": 470,
    },
    "C14": {
        "type": "Temperature", "unit": "°C",
        "normal":  (10, 70),
        "anomaly_low":  -2,    "anomaly_high": 95,
    },
}

# Warning band: 10 % of the normal range near each boundary
WARNING_PCT = 0.10


# ─── Value generators ─────────────────────────────────────────────────────────
def normal_value(sensor_id: str) -> float:
    """Random value well inside the normal operating band."""
    lo, hi = SENSORS[sensor_id]["normal"]
    mid = (lo + hi) / 2
    std = (hi - lo) / 6
    value = random.gauss(mid, std)
    return round(max(lo, min(hi, value)), 3)


def warning_value(sensor_id: str, direction: str = "high") -> float:
    """
    Value that is inside the normal [lo, hi] band but within the 10 % warning
    margin near one of the boundaries — enough to trigger the DB's Avertissement
    logic after WARNING_N consecutive readings.
    """
    lo, hi = SENSORS[sensor_id]["normal"]
    margin = (hi - lo) * WARNING_PCT
    if direction == "low":
        # Near the lower boundary: [lo, lo + margin]
        return round(random.uniform(lo, lo + margin), 3)
    else:
        # Near the upper boundary: [hi - margin, hi]
        return round(random.uniform(hi - margin, hi), 3)


def anomaly_value(sensor_id: str, direction: str = "high") -> float:
    """Value that crosses the threshold — triggers a Critique alert."""
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


def check_last_transactions(conn, limit: int = 3):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT transaction_id, station_id, type_mesure, valeur, cout, timestamp
            FROM transaction_volume
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


# ─── Main simulation loop ──────────────────────────────────────────────────────
def run_simulator(interval: int = 5, force_anomaly: bool = False):
    interval      = int(os.getenv("SIM_INTERVAL", interval))
    force_anomaly = (
        os.getenv("SIM_FORCE_ANOMALY", str(force_anomaly)).lower() == "true"
        or force_anomaly
    )

    print("🚀 Pipeline Sensor Simulator started")
    print(f"   Interval : {interval}s | Forced anomalies: {force_anomaly}")
    print(f"   Sensors  : {list(SENSORS.keys())}")
    print("─" * 60)

    conn = get_connection()
    cycle, anomaly_count, warning_count, total_inserts = 0, 0, 0, 0

    # Per-sensor consecutive warning counter — mirrors the DB's WARNING_N = 3 logic
    # so the simulator can emit 3 warning readings in a row to guarantee a DB alert.
    warning_streak: dict[str, int] = {sid: 0 for sid in SENSORS}
    WARNING_N = 3  # must match check_seuil() in pipeline_db.sql

    try:
        while True:
            cycle += 1
            readings = []

            for capteur_id in SENSORS:
                # --- Decide reading type for this cycle ---
                roll = random.random()

                if force_anomaly and cycle % 10 == 0:
                    # Forced anomaly every 10 cycles
                    direction = random.choice(["high", "low"])
                    value = anomaly_value(capteur_id, direction)
                    tag = "⚠️  ANOMALY "
                    anomaly_count += 1
                    warning_streak[capteur_id] = 0

                elif not force_anomaly and roll < 0.05:
                    # ~5 % chance of a full Critique anomaly
                    direction = random.choice(["high", "low"])
                    value = anomaly_value(capteur_id, direction)
                    tag = "⚠️  ANOMALY "
                    anomaly_count += 1
                    warning_streak[capteur_id] = 0

                elif not force_anomaly and roll < 0.20:
                    # ~15 % chance of a warning-zone reading (5–20 % band)
                    # We keep injecting until we've sent WARNING_N in a row,
                    # which is what the DB trigger needs to fire Avertissement.
                    direction = random.choice(["high", "low"])
                    value = warning_value(capteur_id, direction)
                    warning_streak[capteur_id] += 1
                    tag = f"🟡 WARNING  ({warning_streak[capteur_id]}/{WARNING_N})"
                    if warning_streak[capteur_id] >= WARNING_N:
                        warning_count += 1
                        warning_streak[capteur_id] = 0  # reset after trigger
                else:
                    value = normal_value(capteur_id)
                    tag = "   normal  "
                    warning_streak[capteur_id] = 0

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
                        type_label = a[4] or "?"
                        icon = "🟡" if type_label == "Avertissement" else (
                               "✅" if type_label == "Resolue" else "🔴")
                        print(
                            f"   {icon} alerte_id={a[0]} | {a[1]} | "
                            f"val={a[2]} | {type_label} | {a[5]}"
                        )
                else:
                    print("\n✅ No alerts yet.")

                transactions = check_last_transactions(conn)
                if transactions:
                    print(f"\n💰 Last cost transactions ({len(transactions)} shown):")
                    for t in transactions:
                        print(
                            f"   tx_id={t[0]} | station={t[1]} | {t[2]} | "
                            f"val={t[3]} | cout={t[4]:.2f} DZD"
                        )

            print(
                f"   Total inserts: {total_inserts} | "
                f"Critiques: {anomaly_count} | "
                f"Avertissements déclenchés: {warning_count}"
            )
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⛔ Simulator stopped.")
        print(
            f"   Cycles: {cycle} | Inserts: {total_inserts} | "
            f"Critiques: {anomaly_count} | Avertissements: {warning_count}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline sensor simulator")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--anomaly",  action="store_true")
    args = parser.parse_args()
    run_simulator(interval=args.interval, force_anomaly=args.anomaly)