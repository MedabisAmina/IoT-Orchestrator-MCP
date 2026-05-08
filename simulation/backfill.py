"""
simulation/backfill.py — 30-day historical sensor data generator
Member 3 — Data Simulation Engineer | Phase 2

Usage:
    python backfill.py              # full 30-day backfill
    python backfill.py --days 7     # shorter run for testing
    python backfill.py --dry-run    # print stats only, no DB writes
"""

import os
import psycopg2
import random
import argparse
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─── DB Connection ─────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB",   "pipeline_db"),
        user=os.getenv("POSTGRES_USER",   "iotuser"),
        password=os.getenv("POSTGRES_PASS", "iotfrontier"),
    )

# ─── Sensor Configuration ──────────────────────────────────────────────────────
SENSORS = {
    "C1": {
        "type": "Pression",    "unit": "bar",
        "normal_base": 55,     "daily_amplitude": 20,  "noise_std": 3,
        "threshold": (10, 100)
    },
    "C2": {
        "type": "Temperature", "unit": "°C",
        "normal_base": 45,     "daily_amplitude": 15,  "noise_std": 2,
        "threshold": (0, 90)
    },
    "C3": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 275,    "daily_amplitude": 80,  "noise_std": 15,
        "threshold": (50, 500)
    },
}

# ─── Value generation ──────────────────────────────────────────────────────────
def generate_value(sensor_id: str, ts: datetime, anomaly: bool = False) -> float:
    cfg = SENSORS[sensor_id]
    hour = ts.hour + ts.minute / 60
    cycle_phase = math.sin((hour - 2) * math.pi / 12)
    trend = cfg["normal_base"] + cfg["daily_amplitude"] * cycle_phase * 0.5
    noise = random.gauss(0, cfg["noise_std"])
    value = trend + noise

    if anomaly:
        mn, mx = cfg["threshold"]
        plage = mx - mn
        if random.choice(["high", "low"]) == "high":
            value = mx + random.uniform(0.1 * plage, 0.4 * plage)
        else:
            value = mn - random.uniform(0.1 * plage, 0.4 * plage)

    return round(value, 3)

# ─── Anomaly scheduling ────────────────────────────────────────────────────────
def build_anomaly_schedule(days: int, interval_minutes: int = 5) -> set:
    total_slots = days * 24 * 60 // interval_minutes
    anomaly_slots = set()
    for capteur_id in SENSORS:
        num_events = random.randint(days // 7, days // 7 * 2 + 1)
        for _ in range(num_events):
            start_slot = random.randint(0, total_slots - 10)
            duration = random.randint(3, 9)
            for s in range(start_slot, start_slot + duration):
                anomaly_slots.add((capteur_id, s))
        for slot in range(total_slots):
            if random.random() < 0.005:
                anomaly_slots.add((capteur_id, slot))
    return anomaly_slots

# ─── Maintenance generation ────────────────────────────────────────────────────
def generate_maintenance_records(conn):
    records = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.machine_id, MIN(a.timestamp) as first_alert, COUNT(*) as n_alerts
            FROM alerte a
            JOIN capteur c ON a.capteur_id = c.capteur_id
            GROUP BY c.machine_id
            HAVING COUNT(*) > 5
            ORDER BY n_alerts DESC
        """)
        rows = cur.fetchall()

    for machine_id, first_alert, n_alerts in rows:
        maint_date  = (first_alert + timedelta(days=random.randint(1, 3))).date()
        maint_type  = "Corrective" if n_alerts > 20 else "Preventive"
        description = (
            f"Maintenance suite à {n_alerts} alertes détectées. "
            f"Première anomalie le {first_alert.strftime('%Y-%m-%d %H:%M')}."
        )
        records.append((machine_id, maint_date, maint_type, description))

    if records:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO maintenance (machine_id, date, type, description) VALUES (%s, %s, %s, %s)",
                records
            )
        conn.commit()
        print(f"  ✅ Inserted {len(records)} maintenance records")
    else:
        print("  ℹ️  No maintenance records generated (not enough alerts)")

# ─── Main backfill ─────────────────────────────────────────────────────────────
def run_backfill(days: int = 30, interval_minutes: int = 5, dry_run: bool = False):
    now        = datetime.now().replace(second=0, microsecond=0)
    start_time = now - timedelta(days=days)
    total_slots = days * 24 * 60 // interval_minutes

    print("📦 Historical Backfill")
    print(f"   Period      : {start_time.strftime('%Y-%m-%d')} → {now.strftime('%Y-%m-%d')}")
    print(f"   Interval    : every {interval_minutes} minutes")
    print(f"   Slots/sensor: {total_slots}")
    print(f"   Total rows  : ~{total_slots * len(SENSORS):,} mesure rows")
    print(f"   Dry run     : {dry_run}")
    print("─" * 60)

    anomaly_slots = build_anomaly_schedule(days, interval_minutes)
    print(f"   Anomaly slots planned: {len(anomaly_slots)}")

    if dry_run:
        print("\n⚠️  Dry run — no data written to DB.")
        return

    conn = get_connection()
    inserted, anomalies = 0, 0

    try:
        BATCH_SIZE = 500
        batch = []

        for slot in range(total_slots):
            ts = start_time + timedelta(minutes=slot * interval_minutes)
            for capteur_id in SENSORS:
                is_anomaly = (capteur_id, slot) in anomaly_slots
                value = generate_value(capteur_id, ts, anomaly=is_anomaly)
                batch.append((capteur_id, value, ts))
                if is_anomaly:
                    anomalies += 1

            if len(batch) >= BATCH_SIZE:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO mesure (capteur_id, valeur, timestamp) VALUES (%s, %s, %s)",
                        batch
                    )
                conn.commit()
                inserted += len(batch)
                batch = []
                print(f"  ⏳ {inserted:,} rows inserted ({slot}/{total_slots} slots)...", end="\r")

        if batch:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO mesure (capteur_id, valeur, timestamp) VALUES (%s, %s, %s)",
                    batch
                )
            conn.commit()
            inserted += len(batch)

        print(f"\n  ✅ Inserted {inserted:,} mesure rows")
        print(f"  ⚠️  Anomalous readings : {anomalies:,}")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM alerte")
            print(f"  🔴 Alerts generated   : {cur.fetchone()[0]:,}")

        print("\n🔧 Generating maintenance records...")
        generate_maintenance_records(conn)

    finally:
        conn.close()

    print("\n✅ Backfill complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Historical sensor data backfill")
    parser.add_argument("--days",     type=int, default=30)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()
    run_backfill(days=args.days, interval_minutes=args.interval, dry_run=args.dry_run)