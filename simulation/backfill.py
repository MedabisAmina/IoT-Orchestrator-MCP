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
# C1, C2, C3   — existing machines M1/M2 (Pompage/Compression stations)
# C5–C14       — new machines on terminal stations S3–S6
SENSORS = {
    # --- Station S1 (Pompage, Pipeline P1) ---
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
    # --- Station S2 (Compression, Pipeline P2) ---
    "C3": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 275,    "daily_amplitude": 80,  "noise_std": 15,
        "threshold": (50, 500)
    },
    # --- Station S3 (TerminalDepart, Pipeline P1) ---
    "C5": {
        "type": "Pression",    "unit": "bar",
        "normal_base": 52,     "daily_amplitude": 18,  "noise_std": 3,
        "threshold": (10, 100)
    },
    "C6": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 270,    "daily_amplitude": 75,  "noise_std": 14,
        "threshold": (50, 500)
    },
    # --- Station S4 (TerminalArrivee, Pipeline P1) — triggers cost calc ---
    "C7": {
        "type": "Pression",    "unit": "bar",
        "normal_base": 48,     "daily_amplitude": 16,  "noise_std": 2,
        "threshold": (10, 100)
    },
    "C8": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 260,    "daily_amplitude": 70,  "noise_std": 13,
        "threshold": (50, 500)
    },
    "C9": {
        "type": "Temperature", "unit": "°C",
        "normal_base": 42,     "daily_amplitude": 12,  "noise_std": 2,
        "threshold": (0, 90)
    },
    # --- Station S5 (TerminalDepart, Pipeline P2) ---
    "C10": {
        "type": "Pression",    "unit": "bar",
        "normal_base": 45,     "daily_amplitude": 15,  "noise_std": 2,
        "threshold": (10, 100)
    },
    "C11": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 220,    "daily_amplitude": 60,  "noise_std": 12,
        "threshold": (50, 500)
    },
    # --- Station S6 (TerminalArrivee, Pipeline P2) — triggers cost calc ---
    "C12": {
        "type": "Pression",    "unit": "bar",
        "normal_base": 40,     "daily_amplitude": 13,  "noise_std": 2,
        "threshold": (10, 100)
    },
    "C13": {
        "type": "Debit",       "unit": "m3/h",
        "normal_base": 210,    "daily_amplitude": 55,  "noise_std": 11,
        "threshold": (50, 500)
    },
    "C14": {
        "type": "Temperature", "unit": "°C",
        "normal_base": 38,     "daily_amplitude": 10,  "noise_std": 2,
        "threshold": (0, 90)
    },
}

# Warning band: 10 % of (max - min) near each threshold boundary.
# Must match WARNING_PCT in check_seuil() in pipeline_db.sql.
WARNING_PCT = 0.10

# Minimum consecutive warning slots needed to trigger the DB Avertissement.
# Must match WARNING_N in check_seuil().
WARNING_N = 3


# ─── Value generation ──────────────────────────────────────────────────────────
def generate_value(
    sensor_id: str,
    ts: datetime,
    anomaly: bool = False,
    warning: bool = False,
) -> float:
    """
    Generate a sensor reading for the given timestamp.

    anomaly=True  → value crosses the threshold   (triggers Critique)
    warning=True  → value inside threshold but within the 10 % danger band
                    (triggers Avertissement after WARNING_N consecutive readings)
    default       → normal operating value
    """
    cfg = SENSORS[sensor_id]
    mn, mx = cfg["threshold"]
    plage = mx - mn

    if anomaly:
        if random.choice(["high", "low"]) == "high":
            return round(mx + random.uniform(0.1 * plage, 0.4 * plage), 3)
        else:
            return round(mn - random.uniform(0.1 * plage, 0.4 * plage), 3)

    if warning:
        margin = plage * WARNING_PCT
        # Pick the low or high danger band (inside the threshold)
        if random.choice(["high", "low"]) == "high":
            # Just below max: [mx - margin, mx]
            return round(random.uniform(mx - margin, mx), 3)
        else:
            # Just above min: [mn, mn + margin]
            return round(random.uniform(mn, mn + margin), 3)

    # ── Normal reading: sinusoidal daily cycle + Gaussian noise ──────────────
    hour = ts.hour + ts.minute / 60
    cycle_phase = math.sin((hour - 2) * math.pi / 12)
    trend = cfg["normal_base"] + cfg["daily_amplitude"] * cycle_phase * 0.5
    noise = random.gauss(0, cfg["noise_std"])
    value = trend + noise
    # Clamp to well inside normal range (avoid accidental near-threshold values)
    inner_lo = mn + plage * (WARNING_PCT + 0.05)
    inner_hi = mx - plage * (WARNING_PCT + 0.05)
    return round(max(inner_lo, min(inner_hi, value)), 3)


# ─── Anomaly & warning scheduling ─────────────────────────────────────────────
def build_event_schedule(
    days: int, interval_minutes: int = 5
) -> tuple[set, set]:
    """
    Returns two sets of (capteur_id, slot) tuples:
      anomaly_slots  — full threshold-crossing events (Critique)
      warning_slots  — warning-band events (Avertissement)

    Warning events are always injected in runs of WARNING_N consecutive slots
    so the DB trigger actually fires.
    """
    total_slots = days * 24 * 60 // interval_minutes
    anomaly_slots: set[tuple] = set()
    warning_slots: set[tuple] = set()

    for capteur_id in SENSORS:
        # ── Critique events ─────────────────────────────────────────────────
        num_crit = random.randint(days // 7, days // 7 * 2 + 1)
        for _ in range(num_crit):
            start_slot = random.randint(0, total_slots - 10)
            duration = random.randint(3, 9)
            for s in range(start_slot, start_slot + duration):
                anomaly_slots.add((capteur_id, s))
        # Sparse single-slot critiques
        for slot in range(total_slots):
            if random.random() < 0.005:
                anomaly_slots.add((capteur_id, slot))

        # ── Avertissement events ─────────────────────────────────────────────
        # Roughly 2× as many warning episodes as critique episodes, each
        # lasting exactly WARNING_N slots so the DB trigger fires once per run.
        num_warn = random.randint(days // 4, days // 3)
        for _ in range(num_warn):
            start_slot = random.randint(0, total_slots - WARNING_N - 1)
            for s in range(start_slot, start_slot + WARNING_N):
                # Don't overlap with a critique slot (critique takes priority)
                if (capteur_id, s) not in anomaly_slots:
                    warning_slots.add((capteur_id, s))

    return anomaly_slots, warning_slots


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
                "INSERT INTO maintenance (machine_id, date, type, description) "
                "VALUES (%s, %s, %s, %s)",
                records
            )
        conn.commit()
        print(f"  ✅ Inserted {len(records)} maintenance records")
    else:
        print("  ℹ️  No maintenance records generated (not enough alerts)")


# ─── Budget period check ───────────────────────────────────────────────────────
def ensure_budget_periods(conn, start_time: datetime, end_time: datetime):
    """Make sure a budget row exists for every month in the backfill range."""
    periods = set()
    current = start_time.replace(day=1)
    while current <= end_time:
        periods.add(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    with conn.cursor() as cur:
        for periode in periods:
            cur.execute("""
                INSERT INTO budget (pipeline_id, periode, budget_alloue, cout_total)
                VALUES ('P1', %s, 500000, 0), ('P2', %s, 300000, 0)
                ON CONFLICT DO NOTHING
            """, (periode, periode))
    conn.commit()
    print(f"  ✅ Budget periods ensured: {sorted(periods)}")


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

    anomaly_slots, warning_slots = build_event_schedule(days, interval_minutes)
    print(f"   Critique slots planned    : {len(anomaly_slots)}")
    print(f"   Avertissement slots planned: {len(warning_slots)}")

    if dry_run:
        print("\n⚠️  Dry run — no data written to DB.")
        return

    conn = get_connection()
    inserted = 0
    critique_readings = 0
    warning_readings  = 0

    try:
        print("\n🗓️  Ensuring budget periods exist...")
        ensure_budget_periods(conn, start_time, now)

        BATCH_SIZE = 500
        batch = []

        for slot in range(total_slots):
            ts = start_time + timedelta(minutes=slot * interval_minutes)
            for capteur_id in SENSORS:
                is_anomaly = (capteur_id, slot) in anomaly_slots
                is_warning = (not is_anomaly) and ((capteur_id, slot) in warning_slots)

                value = generate_value(capteur_id, ts, anomaly=is_anomaly, warning=is_warning)
                batch.append((capteur_id, value, ts))

                if is_anomaly:
                    critique_readings += 1
                elif is_warning:
                    warning_readings += 1

            if len(batch) >= BATCH_SIZE:
                with conn.cursor() as cur:
                    cur.executemany(
                        "INSERT INTO mesure (capteur_id, valeur, timestamp) "
                        "VALUES (%s, %s, %s)",
                        batch
                    )
                conn.commit()
                inserted += len(batch)
                batch = []
                print(
                    f"  ⏳ {inserted:,} rows inserted "
                    f"({slot}/{total_slots} slots)...",
                    end="\r"
                )

        if batch:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO mesure (capteur_id, valeur, timestamp) "
                    "VALUES (%s, %s, %s)",
                    batch
                )
            conn.commit()
            inserted += len(batch)

        print(f"\n  ✅ Inserted {inserted:,} mesure rows")
        print(f"  🔴 Critique readings injected    : {critique_readings:,}")
        print(f"  🟡 Avertissement readings injected: {warning_readings:,}")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT type_alerte, COUNT(*) FROM alerte GROUP BY type_alerte ORDER BY type_alerte"
            )
            rows = cur.fetchall()
            print("\n  🔔 Alerts generated by type:")
            for type_alerte, count in rows:
                icon = "🟡" if type_alerte == "Avertissement" else (
                       "✅" if type_alerte == "Resolue" else "🔴")
                print(f"     {icon} {type_alerte}: {count:,}")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(cout), 0) FROM transaction_volume"
            )
            tx_count, total_cout = cur.fetchone()
            print(f"\n  💰 Transactions : {tx_count:,} (total cost: {total_cout:,.2f} DZD)")

        with conn.cursor() as cur:
            cur.execute(
                "SELECT pipeline_id, periode, cout_total, solde "
                "FROM budget ORDER BY pipeline_id, periode"
            )
            rows = cur.fetchall()
            if rows:
                print("\n  📊 Budget summary:")
                for r in rows:
                    print(
                        f"     Pipeline {r[0]} | {r[1]} | "
                        f"spent: {r[2]:,.2f} | remaining: {r[3]:,.2f} DZD"
                    )

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