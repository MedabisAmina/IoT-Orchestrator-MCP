"""
api/main.py — FastAPI entry point

Starts the pipeline REST API, runs the 30-day historical backfill ONCE
(only if mesure table is empty), then launches the real-time simulator
as a background daemon thread.

MCP tools from factory_mcp_server.py are imported directly and called
as Python functions to build structured live context for the Gemini prompt.

Run:
    python api/main.py
    # or from project root:
    uvicorn api.main:app --reload
"""

import os
import sys
import json
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

# ─── Fix import paths ─────────────────────────────────────────────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simulation'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'mcp'))

from simulator import run_simulator
from backfill  import run_backfill

# ─── Import MCP tools directly so we can call them as Python functions ────────
from factory_mcp_server import (
    get_machine_status,
    get_sensor_value,
    list_active_alerts,
    get_pipeline_info,
    get_station_status,
    get_maintenance_history,
    get_machines_in_alarm,
    get_zone_overview,
    get_machine_availability,
    get_top_alerted_machines,
    get_temperature_anomalies,
    get_pressure_trends,
    get_pipeline_flow_rate,
    get_budget_status,
    get_tarifs,
    get_transaction_history,
    get_cost_summary_by_pipeline,
    get_budget_alerts,
    get_machine_health_score,
)

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Pipeline IIoT API",
    description="Industrial pipeline monitoring — Oil & Gas Algeria",
    version="1.0.0",
)

# ─── Gemini setup ─────────────────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DB helper (kept for alert/budget REST endpoints) ─────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB",   "pipeline_db"),
        user=os.getenv("POSTGRES_USER",   "iotuser"),
        password=os.getenv("POSTGRES_PASS", "iotfrontier"),
    )

# ─── Helper: check if backfill already ran ────────────────────────────────────
def _mesure_table_empty() -> bool:
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
# MCP-POWERED LIVE CONTEXT  (calls the actual MCP tool functions)
# ══════════════════════════════════════════════════════════════════════════════

def _safe(fn, *args, **kwargs):
    """Call an MCP tool function and return its result, or [] on failure."""
    try:
        result = fn(*args, **kwargs)
        # Serialise datetimes / Decimals to strings so json.dumps works
        return json.loads(json.dumps(result, default=str))
    except Exception as e:
        print(f"⚠️  MCP tool {fn.__name__} failed: {e}")
        return []


def get_pipeline_context() -> str:
    """
    Call the real MCP tool functions to build a rich, structured context
    block that is injected into the Gemini system prompt.
    """
    sections: list[str] = []

    # ── 1. Zone overview ────────────────────────────────────────────────────
    zones = _safe(get_zone_overview)
    if zones:
        sections.append("## VUE PAR ZONE")
        for z in zones:
            sections.append(
                f"| Zone | Pipelines | Stations | Machines | Alertes |"
            )
            sections.append("|------|-----------|----------|----------|---------|")
            sections.append(
                f"| {z.get('nom')} ({z.get('zone_id')}) "
                f"| {z.get('pipelines')} | {z.get('stations')} "
                f"| {z.get('machines')} | {z.get('alerts')} |"
            )
        sections.append("")

    # ── 2. Pipeline info ────────────────────────────────────────────────────
    pipelines = _safe(get_pipeline_info)
    if pipelines:
        sections.append("## PIPELINES")
        sections.append("| ID | Nom | Produit | Début | Fin | Long. (km) | Diam. (mm) |")
        sections.append("|----|-----|---------|-------|-----|------------|------------|")
        for p in pipelines:
            sections.append(
                f"| {p.get('pipeline_id')} | {p.get('nom_pipeline')} "
                f"| {p.get('type_produit')} | {p.get('point_debut')} "
                f"| {p.get('point_fin')} | {p.get('longueur')} | {p.get('diametre')} |"
            )
        sections.append("")

    # ── 3. Station status ───────────────────────────────────────────────────
    stations = _safe(get_station_status)
    if stations:
        sections.append("## STATIONS")
        sections.append("| ID | Nom | Type | Localisation | Statut |")
        sections.append("|----|-----|------|--------------|--------|")
        for s in stations:
            sections.append(
                f"| {s.get('station_id')} | {s.get('nom_station')} "
                f"| {s.get('type_station')} | {s.get('localisation')} "
                f"| {s.get('status')} |"
            )
        sections.append("")

    # ── 4. Machine status ───────────────────────────────────────────────────
    machines = _safe(get_machine_status)
    if machines:
        sections.append("## ÉTAT DES MACHINES")
        sections.append("| Machine | Type | Statut | Dispo % | Station | Pipeline |")
        sections.append("|---------|------|--------|---------|---------|----------|")
        for m in machines:
            sections.append(
                f"| {m.get('machine_id')} | {m.get('type')} "
                f"| {m.get('status')} | {m.get('disponibilite')} "
                f"| {m.get('nom_station')} | {m.get('nom_pipeline')} |"
            )
        sections.append("")

    # ── 5. Machine health scores ────────────────────────────────────────────
    health = _safe(get_machine_health_score)
    if health:
        sections.append("## SCORES DE SANTÉ MACHINES")
        sections.append("| Machine | Statut | Dispo % | Score /100 |")
        sections.append("|---------|--------|---------|------------|")
        for h in health:
            score = h.get('health_score', '?')
            emoji = "🔴" if score < 50 else "🟡" if score < 80 else "🟢"
            sections.append(
                f"| {h.get('machine_id')} | {h.get('status')} "
                f"| {h.get('disponibilite')} | {emoji} {score} |"
            )
        sections.append("")

    # ── 6. Machines en alarme ───────────────────────────────────────────────
    alarms = _safe(get_machines_in_alarm)
    if alarms:
        sections.append("## ⚠️  MACHINES EN ALARME")
        for a in alarms:
            sections.append(f"- **{a.get('machine_id')}** ({a.get('type')}) — {a.get('nom_station')}")
        sections.append("")

    # ── 7. Active alerts ────────────────────────────────────────────────────
    alerts = _safe(list_active_alerts)
    if alerts:
        critique  = [a for a in alerts if a.get('type_alerte') == 'Critique']
        avert     = [a for a in alerts if a.get('type_alerte') == 'Avertissement']
        sections.append(f"## 🚨 ALERTES ACTIVES ({len(alerts)} total — {len(critique)} critiques, {len(avert)} avertissements)")
        sections.append("| Capteur | Type | Valeur | Message | Timestamp |")
        sections.append("|---------|------|--------|---------|-----------|")
        for a in alerts[:30]:  # cap at 30 rows for prompt length
            sections.append(
                f"| {a.get('capteur_id')} | **{a.get('type_alerte')}** "
                f"| {a.get('valeur')} | {str(a.get('message',''))[:60]} "
                f"| {a.get('timestamp')} |"
            )
        sections.append("")

    # ── 8. Top alerted machines ─────────────────────────────────────────────
    top_alert = _safe(get_top_alerted_machines)
    if top_alert:
        sections.append("## TOP MACHINES PAR NOMBRE D'ALERTES")
        sections.append("| Machine | Type | Total Alertes |")
        sections.append("|---------|------|---------------|")
        for t in top_alert[:10]:
            sections.append(
                f"| {t.get('machine_id')} | {t.get('type')} | {t.get('total_alerts')} |"
            )
        sections.append("")

    # ── 9. Pressure trends ──────────────────────────────────────────────────
    pressure = _safe(get_pressure_trends)
    if pressure:
        sections.append("## TENDANCES PRESSION (toutes périodes)")
        sections.append("| Capteur | Moy (bar) | Max (bar) | Min (bar) |")
        sections.append("|---------|-----------|-----------|-----------|")
        for p in pressure:
            sections.append(
                f"| {p.get('capteur_id')} "
                f"| {round(float(p.get('avg_pressure') or 0), 2)} "
                f"| {round(float(p.get('max_pressure') or 0), 2)} "
                f"| {round(float(p.get('min_pressure') or 0), 2)} |"
            )
        sections.append("")

    # ── 10. Flow rates ──────────────────────────────────────────────────────
    flow = _safe(get_pipeline_flow_rate)
    if flow:
        sections.append("## DÉBITS MOYENS PAR PIPELINE")
        sections.append("| Pipeline | Nom | Débit moyen (m³/h) |")
        sections.append("|----------|-----|--------------------|")
        for f in flow:
            sections.append(
                f"| {f.get('pipeline_id')} | {f.get('nom_pipeline')} "
                f"| {round(float(f.get('avg_flow_rate') or 0), 2)} |"
            )
        sections.append("")

    # ── 11. Temperature anomalies ───────────────────────────────────────────
    temps = _safe(get_temperature_anomalies)
    if temps:
        sections.append("## 🌡️  ANOMALIES TEMPÉRATURE (> 90 °C)")
        for t in temps:
            sections.append(
                f"- Capteur **{t.get('capteur_id')}** sur machine **{t.get('machine_id')}** "
                f"→ {t.get('valeur')} °C @ {t.get('timestamp')}"
            )
        sections.append("")

    # ── 12. Budget status ───────────────────────────────────────────────────
    budgets = _safe(get_budget_status)
    if budgets:
        sections.append("## BUDGET PAR PIPELINE & PÉRIODE")
        sections.append("| Pipeline | Nom | Période | Alloué (DZD) | Dépensé (DZD) | Solde (DZD) | % |")
        sections.append("|----------|-----|---------|-------------|---------------|-------------|---|")
        for b in budgets:
            pct = float(b.get('pct_consomme') or 0)
            flag = "🔴" if pct >= 90 else "🟡" if pct >= 70 else "🟢"
            sections.append(
                f"| {b.get('pipeline_id')} | {b.get('nom_pipeline')} "
                f"| {b.get('periode')} "
                f"| {float(b.get('budget_alloue') or 0):,.0f} "
                f"| {float(b.get('cout_total') or 0):,.0f} "
                f"| {float(b.get('solde') or 0):,.0f} "
                f"| {flag} {pct:.1f}% |"
            )
        sections.append("")

    # ── 13. Budget alerts ───────────────────────────────────────────────────
    budget_alerts = _safe(get_budget_alerts, 70.0)
    if budget_alerts:
        sections.append("## ⚡ ALERTES BUDGET (> 70%)")
        for b in budget_alerts:
            sections.append(
                f"- **{b.get('pipeline_id')}** ({b.get('nom_pipeline')}) "
                f"| {b.get('periode')} | {b.get('pct_consomme')}% consommé "
                f"— statut: **{b.get('budget_status')}**"
            )
        sections.append("")

    # ── 14. Cost summary ────────────────────────────────────────────────────
    costs = _safe(get_cost_summary_by_pipeline)
    if costs:
        sections.append("## COÛTS PAR PIPELINE & MOIS")
        sections.append("| Pipeline | Mois | Transactions | Coût total (DZD) | Débit | Pression | Temp. |")
        sections.append("|----------|------|-------------|------------------|-------|----------|-------|")
        for c in costs[:20]:  # cap
            sections.append(
                f"| {c.get('pipeline_id')} | {c.get('periode')} "
                f"| {c.get('nb_transactions')} "
                f"| {float(c.get('cout_total') or 0):,.2f} "
                f"| {float(c.get('cout_debit') or 0):,.2f} "
                f"| {float(c.get('cout_pression') or 0):,.2f} "
                f"| {float(c.get('cout_temperature') or 0):,.2f} |"
            )
        sections.append("")

    # ── 15. Tariffs ─────────────────────────────────────────────────────────
    tarifs = _safe(get_tarifs)
    if tarifs:
        sections.append("## TARIFS EN VIGUEUR")
        sections.append("| ID | Produit | Mesure | Prix/Unité (DZD) | Unité | Effet |")
        sections.append("|----|---------|--------|-----------------|-------|-------|")
        for t in tarifs:
            sections.append(
                f"| {t.get('tarif_id')} | {t.get('type_produit')} "
                f"| {t.get('type_mesure')} "
                f"| {float(t.get('prix_unitaire') or 0):,.4f} "
                f"| {t.get('unite')} | {t.get('date_effet')} |"
            )
        sections.append("")

    # ── 16. Recent transactions ─────────────────────────────────────────────
    txns = _safe(get_transaction_history, hours=6)
    if txns:
        sections.append(f"## TRANSACTIONS RÉCENTES (6 dernières heures — {len(txns)} entrées)")
        sections.append("| Station | Pipeline | Type | Valeur | Coût (DZD) | Timestamp |")
        sections.append("|---------|----------|------|--------|------------|-----------|")
        for t in txns[:20]:
            sections.append(
                f"| {t.get('station_id')} | {t.get('pipeline_id')} "
                f"| {t.get('type_mesure')} | {t.get('valeur')} "
                f"| {float(t.get('cout') or 0):.2f} | {t.get('timestamp')} |"
            )
        sections.append("")

    return "\n".join(sections) if sections else "[Aucune donnée MCP disponible]"


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    return {"status": "Pipeline API running", "docs": "/docs", "redoc": "/redoc"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# ─── Alerts ───────────────────────────────────────────────────────────────────
@app.get("/alerts/recent", tags=["Alerts"])
def get_recent_alerts(limit: int = 50):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM alerte ORDER BY timestamp DESC LIMIT %s", (limit,)
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("timestamp"):
                r["timestamp"] = r["timestamp"].isoformat()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Budget ───────────────────────────────────────────────────────────────────
@app.get("/budget/summary", tags=["Budget"])
def get_budget_summary():
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM budget ORDER BY pipeline_id, periode")
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if "solde" not in r:
                r["solde"] = round(float(r.get("budget_alloue") or 0) - float(r.get("cout_total") or 0), 2)
            for key in ("budget_alloue", "cout_total", "solde"):
                if key in r:
                    r[key] = float(r[key])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/budget/transactions", tags=["Budget"])
def get_transactions(limit: int = 200):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM transaction_volume ORDER BY timestamp DESC LIMIT %s", (limit,)
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        for r in rows:
            if r.get("timestamp"):
                r["timestamp"] = r["timestamp"].isoformat()
            for key in ("valeur", "cout"):
                if key in r:
                    r[key] = float(r[key])
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Chat — Gemini with full MCP context ──────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """Tu es un système expert de monitoring de pipelines O&G en Algérie. Tu fournis des analyses opérationnelles et financières directes, sans introduction ni formule de politesse.

INFRASTRUCTURE:
- **P1** — PétroleBrut | Alger → Oran | Stations: S1, S3, S4
- **P2** — GazNaturel | Hassi Messaoud → Ouargla | Stations: S2, S5, S6
- Capteurs: Pression (bar), Débit (m³/h), Température (°C)
- Alertes: Critique | Avertissement | Résolue
- Finances: Tarifs DZD → Transactions → Budget mensuel

DONNÉES TEMPS RÉEL (MCP):
{mcp_context}

RÈGLES STRICTES:

1. **INTERDICTIONS ABSOLUES**:
   - JAMAIS de "Bonjour", "En tant qu'assistant", "Je vous fournis", "Bien sûr", "Certainement" ou toute formule d'introduction
   - JAMAIS de conclusion du type "N'hésitez pas à me poser d'autres questions"
   - Commencer DIRECTEMENT par le titre de la première section ou la donnée la plus importante

2. **FORMAT OBLIGATOIRE**:
   - Tableaux Markdown pour toute donnée tabulaire
   - Titres `##` et `###` pour structurer
   - **Gras** pour valeurs critiques et IDs
   - Émojis de statut: 🔴 critique, 🟡 attention, 🟢 OK, ⚡ financier, 🌡️ temp, 💧 débit

3. **GRAPHIQUES** — Pour budgets, comparaisons et tendances, TOUJOURS inclure un bloc CHART après le tableau:
   - Budget/pourcentage → type `bar`
   - Évolution temporelle → type `line`  
   - Répartition → type `bar` horizontal
   
   Format EXACT (JSON strict, une seule ligne après ```chart):
   ```chart
   {{"type":"bar","title":"Titre","labels":["A","B"],"datasets":[{{"label":"Série","data":[10,20],"color":"#ff4d4d"}}]}}
   ```
   
   Couleurs: #ff4d4d (rouge/critique), #f59e0b (orange/alerte), #00c896 (vert/OK), #3b82f6 (bleu/info), #8b5cf6 (violet)
   
   Exemples de charts utiles:
   - Budget alloué vs dépensé par pipeline → bar groupé
   - Alertes par type (Critique/Avert/Résolue) → bar
   - Score de santé machines → bar horizontal
   - Coûts par mois → line

4. **ALERTES CRITIQUES** → tableau en premier si présentes, avec capteur, valeur, écart au seuil

5. **BUDGET > 80%** → signaler avec chart de consommation obligatoire

6. **RECOMMANDATIONS** → terminer par `### 🎯 Actions` avec bullets actionnables

Langue: français professionnel, concis, orienté opérateur terrain."""


@app.post("/chat", tags=["Chat"])
def chat(req: ChatRequest):
    """
    Send a question to Gemini. Live MCP tool data is injected as structured
    Markdown tables into the system prompt for maximum context quality.
    """
    try:
        mcp_context = get_pipeline_context()

        full_prompt = SYSTEM_PROMPT.format(mcp_context=mcp_context)
        full_prompt += f"\n\n---\n**Question de l'opérateur:** {req.message}"

        response = model.generate_content(full_prompt)
        return {"reply": response.text}

    except Exception as e:
        print("GEMINI ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)