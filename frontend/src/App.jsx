import { useState, useEffect, useRef, useCallback } from "react";

// ── CONFIG ──────────────────────────────────────────────────
const CLAUDE_MODEL = "claude-sonnet-4-20250514";
const SYSTEM_PROMPT = `Tu es un assistant expert en monitoring de pipelines pétroliers et gaziers en Algérie.
Tu aides les opérateurs à surveiller leurs machines, interpréter les alertes, et comprendre les coûts.
Le système surveille des pipelines (P1: PetroleBrut Alger→Oran, P2: GazNaturel Hassi Messaoud→Ouargla).
Les capteurs mesurent: Pression (bar), Débit (m3/h), Température (°C).
Les alertes sont déclenchées automatiquement quand une valeur dépasse les seuils.
Réponds en français, de façon concise et professionnelle.`;

const QUICK_CHIPS = [
  "État des machines",
  "Alertes critiques récentes",
  "Résumé du budget pipeline P1",
  "Quelles stations sont en alarme ?",
  "Comment interpréter une alerte de pression ?",
];

// ── ICONS ────────────────────────────────────────────────────
const Icon = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const ChatIcon   = () => <Icon d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />;
const BellIcon   = () => <Icon d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />;
const ChartIcon  = () => <Icon d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />;
const CodeIcon   = () => <Icon d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />;
const SendIcon   = () => <Icon d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />;
const RefreshIcon= () => <Icon d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />;
const DownloadIcon=() => <Icon d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />;
const BulbIcon   = () => <Icon size={24} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />;
const WarnIcon   = () => <Icon size={24} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />;
const OkIcon     = () => <Icon d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />;

// ── STYLES ───────────────────────────────────────────────────
const css = `
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

  .pip-root *, .pip-root *::before, .pip-root *::after { box-sizing: border-box; margin: 0; padding: 0; }

  .pip-root {
    --bg: #0a0e0f; --bg2: #111518; --bg3: #181d20;
    --border: rgba(255,255,255,0.07); --border2: rgba(255,255,255,0.12);
    --text: #e8eaeb; --text2: #8a9299; --text3: #4a5258;
    --accent: #00c896; --accent2: #007a5c;
    --danger: #ff4d4d; --danger2: #8b1a1a;
    --warn: #f59e0b; --info: #3b82f6;
    --font: 'IBM Plex Sans', sans-serif;
    --mono: 'IBM Plex Mono', monospace;
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: grid;
    grid-template-rows: 48px 1fr;
    grid-template-columns: 240px 1fr 300px;
    overflow: hidden;
  }

  /* HEADER */
  .pip-header {
    grid-column: 1 / -1;
    display: flex; align-items: center; gap: 16px;
    padding: 0 20px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .pip-logo { font-family: var(--mono); font-size: 13px; font-weight: 500; color: var(--accent); letter-spacing:.05em; }
  .pip-logo span { color: var(--text2); }
  .pip-divider { width:1px; height:20px; background:var(--border); }
  .pip-sub { font-size:12px; color:var(--text3); font-family:var(--mono); }
  .pip-hstatus { margin-left:auto; display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text2); }
  .pip-dot { width:6px; height:6px; border-radius:50%; background:var(--accent); animation: pip-pulse 2s infinite; }
  .pip-dot.red { background:var(--danger); animation:none; }
  @keyframes pip-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

  /* NAV */
  .pip-nav {
    background: var(--bg2); border-right: 1px solid var(--border);
    padding: 16px 0; display:flex; flex-direction:column; gap:2px; overflow-y:auto;
  }
  .pip-nav-label { font-size:10px; font-weight:500; letter-spacing:.1em; color:var(--text3); padding:12px 16px 6px; text-transform:uppercase; }
  .pip-nav-btn {
    display:flex; align-items:center; gap:10px; padding:8px 16px;
    font-size:13px; color:var(--text2); cursor:pointer; border:none; background:none;
    width:100%; text-align:left; transition:all .15s; font-family:var(--font);
  }
  .pip-nav-btn:hover { background:var(--bg3); color:var(--text); }
  .pip-nav-btn.active { background:rgba(0,200,150,.08); color:var(--accent); border-right:2px solid var(--accent); }
  .pip-badge {
    margin-left:auto; background:var(--danger2); color:var(--danger);
    font-size:10px; font-family:var(--mono); padding:1px 6px; border-radius:10px; min-width:18px; text-align:center;
  }

  /* MAIN */
  .pip-main { overflow:hidden; display:flex; flex-direction:column; }
  .pip-page { display:none; flex-direction:column; height:100%; }
  .pip-page.active { display:flex; }

  /* CHAT */
  .pip-chat-msgs {
    flex:1; overflow-y:auto; padding:24px 28px;
    display:flex; flex-direction:column; gap:20px;
  }
  .pip-chat-msgs::-webkit-scrollbar { width:4px; }
  .pip-chat-msgs::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }

  .pip-msg { display:flex; gap:12px; max-width:800px; }
  .pip-msg.user { flex-direction:row-reverse; align-self:flex-end; }
  .pip-msg-av {
    width:28px; height:28px; border-radius:6px;
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:500; flex-shrink:0; font-family:var(--mono);
  }
  .pip-msg.user .pip-msg-av { background:var(--accent2); color:var(--accent); }
  .pip-msg.ai   .pip-msg-av { background:var(--bg3); color:var(--text2); border:1px solid var(--border2); }
  .pip-msg-bubble {
    padding:10px 14px; border-radius:8px; font-size:14px; line-height:1.6; max-width:640px;
  }
  .pip-msg.user .pip-msg-bubble { background:rgba(0,200,150,.1); border:1px solid rgba(0,200,150,.2); color:var(--text); }
  .pip-msg.ai   .pip-msg-bubble { background:var(--bg3); border:1px solid var(--border); color:var(--text); }

  .pip-input-area { padding:16px 28px 20px; border-top:1px solid var(--border); display:flex; gap:10px; align-items:flex-end; }
  .pip-input {
    flex:1; background:var(--bg3); border:1px solid var(--border2); border-radius:8px;
    padding:10px 14px; color:var(--text); font-family:var(--font); font-size:14px;
    resize:none; outline:none; min-height:42px; max-height:120px; transition:border-color .15s;
  }
  .pip-input:focus { border-color:var(--accent); }
  .pip-input::placeholder { color:var(--text3); }
  .pip-send {
    background:var(--accent); border:none; border-radius:8px;
    width:40px; height:40px; display:flex; align-items:center; justify-content:center;
    cursor:pointer; transition:all .15s; flex-shrink:0; color:var(--bg);
  }
  .pip-send:hover { background:#00e6ad; }
  .pip-send:disabled { background:var(--bg3); cursor:not-allowed; color:var(--text3); }

  /* THINKING DOTS */
  .pip-thinking { display:flex; gap:4px; align-items:center; padding:4px 0; }
  .pip-thinking span { width:6px; height:6px; border-radius:50%; background:var(--text3); animation:pip-blink 1.2s infinite; }
  .pip-thinking span:nth-child(2){animation-delay:.2s}
  .pip-thinking span:nth-child(3){animation-delay:.4s}
  @keyframes pip-blink { 0%,80%,100%{opacity:.3} 40%{opacity:1} }

  /* WELCOME */
  .pip-welcome { display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; gap:12px; padding:40px; text-align:center; }
  .pip-welcome-icon { width:48px; height:48px; background:rgba(0,200,150,.1); border:1px solid rgba(0,200,150,.2); border-radius:12px; display:flex; align-items:center; justify-content:center; color:var(--accent); }
  .pip-welcome h2 { font-size:16px; font-weight:500; color:var(--text); }
  .pip-welcome p { font-size:13px; color:var(--text2); max-width:400px; line-height:1.6; }
  .pip-chips { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:8px; }
  .pip-chip { padding:6px 12px; background:var(--bg3); border:1px solid var(--border2); border-radius:20px; font-size:12px; color:var(--text2); cursor:pointer; transition:all .15s; }
  .pip-chip:hover { border-color:var(--accent); color:var(--accent); background:rgba(0,200,150,.05); }

  /* PAGE HEADER */
  .pip-page-hdr { padding:20px 28px 0; display:flex; align-items:center; justify-content:space-between; }
  .pip-page-title { font-size:16px; font-weight:500; color:var(--text); }
  .pip-page-sub { font-size:12px; color:var(--text2); margin-top:2px; }
  .pip-refresh-btn { display:flex; align-items:center; gap:6px; padding:6px 12px; background:var(--bg3); border:1px solid var(--border2); border-radius:6px; color:var(--text2); font-size:12px; cursor:pointer; font-family:var(--font); transition:all .15s; }
  .pip-refresh-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* ALERTS */
  .pip-alerts-list { flex:1; overflow-y:auto; padding:16px 28px; display:flex; flex-direction:column; gap:8px; }
  .pip-alerts-list::-webkit-scrollbar { width:4px; }
  .pip-alerts-list::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }
  .pip-alert-item { display:grid; grid-template-columns:8px 1fr auto; gap:12px; align-items:start; padding:12px 14px; background:var(--bg3); border:1px solid var(--border); border-radius:8px; transition:border-color .15s; }
  .pip-alert-item:hover { border-color:var(--border2); }
  .pip-alert-item.critique { border-left:2px solid var(--danger); }
  .pip-alert-item.resolue  { border-left:2px solid var(--accent); opacity:.6; }
  .pip-adot { width:8px; height:8px; border-radius:50%; margin-top:4px; }
  .pip-adot.critique { background:var(--danger); box-shadow:0 0 6px rgba(255,77,77,.4); }
  .pip-adot.resolue  { background:var(--accent); }
  .pip-abody { display:flex; flex-direction:column; gap:3px; }
  .pip-atop  { display:flex; align-items:center; gap:8px; }
  .pip-asensor { font-family:var(--mono); font-size:12px; color:var(--accent); background:rgba(0,200,150,.08); padding:1px 6px; border-radius:4px; }
  .pip-atype { font-size:11px; color:var(--danger); font-weight:500; text-transform:uppercase; letter-spacing:.05em; }
  .pip-atype.resolue { color:var(--accent); }
  .pip-amsg  { font-size:13px; color:var(--text2); }
  .pip-aval  { font-family:var(--mono); font-size:13px; font-weight:500; color:var(--text); }
  .pip-atime { font-size:11px; color:var(--text3); }

  /* BUDGET */
  .pip-budget-body { flex:1; overflow-y:auto; padding:16px 28px 28px; display:flex; flex-direction:column; gap:20px; }
  .pip-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; }
  .pip-card { background:var(--bg3); border:1px solid var(--border); border-radius:8px; padding:14px 16px; }
  .pip-card-label { font-size:11px; color:var(--text3); text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
  .pip-card-val { font-family:var(--mono); font-size:20px; font-weight:500; color:var(--text); }
  .pip-card-val.green { color:var(--accent); }
  .pip-card-val.red   { color:var(--danger); }
  .pip-card-val.amber { color:var(--warn); }
  .pip-section-title { font-size:12px; font-weight:500; color:var(--text2); text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }
  .pip-table { width:100%; border-collapse:collapse; font-size:13px; }
  .pip-table th { text-align:left; padding:8px 12px; color:var(--text3); font-size:11px; font-weight:500; text-transform:uppercase; letter-spacing:.06em; border-bottom:1px solid var(--border); }
  .pip-table td { padding:10px 12px; border-bottom:1px solid var(--border); color:var(--text2); font-family:var(--mono); font-size:12px; }
  .pip-table tr:hover td { background:var(--bg3); color:var(--text); }
  .pip-bar { height:4px; background:var(--bg); border-radius:2px; overflow:hidden; margin-top:4px; width:100%; }
  .pip-bar-fill { height:100%; background:var(--accent); border-radius:2px; transition:width .3s; }
  .pip-bar-fill.warn   { background:var(--warn); }
  .pip-bar-fill.danger { background:var(--danger); }
  .pip-dl-btn { display:flex; align-items:center; gap:8px; padding:10px 18px; background:var(--accent); border:none; border-radius:8px; color:var(--bg); font-family:var(--font); font-size:13px; font-weight:500; cursor:pointer; transition:all .15s; }
  .pip-dl-btn:hover { background:#00e6ad; }

  /* RIGHT PANEL */
  .pip-aside { background:var(--bg2); border-left:1px solid var(--border); display:flex; flex-direction:column; overflow:hidden; }
  .pip-panel-hdr { padding:14px 16px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
  .pip-panel-title { font-size:12px; font-weight:500; color:var(--text2); text-transform:uppercase; letter-spacing:.08em; }
  .pip-live-tag { font-size:10px; font-family:var(--mono); color:var(--accent); display:flex; align-items:center; gap:4px; }
  .pip-panel-list { flex:1; overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:6px; }
  .pip-panel-list::-webkit-scrollbar { width:3px; }
  .pip-panel-list::-webkit-scrollbar-thumb { background:var(--border); }
  .pip-palert { padding:8px 10px; background:var(--bg3); border:1px solid var(--border); border-left:2px solid var(--danger); border-radius:6px; font-size:12px; animation:pip-slidein .3s ease; }
  @keyframes pip-slidein { from{opacity:0;transform:translateX(8px)} to{opacity:1;transform:translateX(0)} }
  .pip-palert-top { display:flex; justify-content:space-between; margin-bottom:2px; }
  .pip-palert-sensor { font-family:var(--mono); font-size:11px; color:var(--accent); }
  .pip-palert-time   { font-size:10px; color:var(--text3); }
  .pip-palert-msg    { color:var(--text2); font-size:11px; }
  .pip-palert-val    { font-family:var(--mono); font-weight:500; color:var(--danger); font-size:11px; }

  /* EMPTY STATE */
  .pip-empty { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; color:var(--text3); font-size:12px; padding:20px; text-align:center; }
  .pip-empty svg { opacity:.4; }

  /* CONFIG */
  .pip-config { padding:28px; overflow-y:auto; max-width:560px; display:flex; flex-direction:column; gap:20px; }
  .pip-config-card { background:var(--bg3); border:1px solid var(--border); border-radius:8px; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .pip-label { font-size:12px; color:var(--text2); margin-bottom:4px; }
  .pip-text-input { background:var(--bg2); border:1px solid var(--border2); border-radius:6px; padding:8px 12px; color:var(--text); font-family:var(--mono); font-size:13px; outline:none; width:100%; }
  .pip-btn-sm { padding:7px 14px; background:var(--bg2); border:1px solid var(--border2); border-radius:6px; color:var(--text2); font-family:var(--font); font-size:13px; cursor:pointer; }
  .pip-btn-sm:hover { border-color:var(--accent); color:var(--accent); }
  .pip-btn-accent { padding:7px 14px; background:var(--accent); border:none; border-radius:6px; color:var(--bg); font-family:var(--font); font-size:13px; font-weight:500; cursor:pointer; }
  .pip-code-block { font-family:var(--mono); font-size:12px; color:var(--text2); line-height:2; background:var(--bg2); padding:12px; border-radius:6px; border:1px solid var(--border); }
`;

// ── MAIN COMPONENT ────────────────────────────────────────────
export default function PipelineDashboard() {
  const [page, setPage]           = useState("chat");
  const [messages, setMessages]   = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput]         = useState("");
  const [streaming, setStreaming] = useState(false);
  const [alerts, setAlerts]       = useState([]);
  const [budget, setBudget]       = useState(null);
  const [panelAlerts, setPanelAlerts] = useState([]);
  const [seenIds, setSeenIds]     = useState(new Set());
  const [critCount, setCritCount] = useState(0);
  const [apiUrl, setApiUrl]       = useState("http://localhost:8000");
  const [connResult, setConnResult] = useState("");
  const [copyMsg, setCopyMsg]     = useState(false);

  const msgsRef   = useRef(null);
  const inputRef  = useRef(null);
  const apiUrlRef = useRef(apiUrl);
  apiUrlRef.current = apiUrl;

  // inject CSS once
  useEffect(() => {
    if (!document.getElementById("pip-styles")) {
      const s = document.createElement("style");
      s.id = "pip-styles";
      s.textContent = css;
      document.head.appendChild(s);
    }
  }, []);

  // live poll
  useEffect(() => {
    pollPanel();
    const id = setInterval(pollPanel, 10000);
    return () => clearInterval(id);
  }, []);

  // scroll to bottom on new message
  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [messages]);

  // load data when switching pages
  useEffect(() => {
    if (page === "alerts") loadAlerts();
    if (page === "budget") loadBudget();
  }, [page]);

  // ── API HELPERS ─────────────────────────────────────────────
  async function pollPanel() {
    try {
      const r = await fetch(`${apiUrlRef.current}/alerts/recent?limit=20`);
      const data = await r.json();
      const critiques = data.filter(a => a.type_alerte === "Critique");
      setCritCount(critiques.length);

      setPanelAlerts(prev => {
        const ids = new Set(prev.map(a => a.alerte_id));
        const fresh = data.filter(a => !ids.has(a.alerte_id));
        if (!fresh.length) return prev;
        return [...fresh, ...prev].slice(0, 30);
      });
    } catch { /* API not ready */ }
  }

  async function loadAlerts() {
    try {
      const r = await fetch(`${apiUrl}/alerts/recent?limit=100`);
      setAlerts(await r.json());
    } catch { setAlerts(null); }
  }

  async function loadBudget() {
    try {
      const [sr, tr] = await Promise.all([
        fetch(`${apiUrl}/budget/summary`),
        fetch(`${apiUrl}/budget/transactions?limit=200`),
      ]);
      setBudget({ summary: await sr.json(), transactions: await tr.json() });
    } catch { setBudget(null); }
  }

  // ── CHAT ────────────────────────────────────────────────────
  async function sendMessage(text) {
    const msg = (text || input).trim();
    if (!msg || streaming) return;
    setInput("");
    setStreaming(true);

    const userMsg = { role: "user", content: msg };
    const newHistory = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setMessages(prev => [...prev, { role: "user", text: msg }, { role: "ai", text: null }]);

    try {
      const res = await fetch("/anthropic/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model: CLAUDE_MODEL,
          max_tokens: 1000,
          system: SYSTEM_PROMPT,
          messages: newHistory,
        }),
      });
      const data = await res.json();
      const reply = data.content?.[0]?.text || "Erreur: réponse vide.";
      setChatHistory(h => [...h, { role: "assistant", content: reply }]);
      setMessages(prev => {
        const copy = [...prev];
        copy[copy.length - 1] = { role: "ai", text: reply };
        return copy;
      });
    } catch {
      setMessages(prev => {
        const copy = [...prev];
        copy[copy.length - 1] = { role: "ai", text: "ERROR:Erreur de connexion à l'API Claude." };
        return copy;
      });
    }
    setStreaming(false);
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  // ── CSV DOWNLOAD ─────────────────────────────────────────────
  function downloadCSV() {
    if (!budget) return;
    const { summary, transactions } = budget;
    let csv = "RAPPORT BUDGET PIPELINE\n";
    csv += `Généré le,${new Date().toLocaleString("fr")}\n\nRÉSUMÉ\n`;
    csv += "Pipeline,Période,Alloué,Dépensé,Solde\n";
    summary.forEach(r => { csv += `${r.pipeline_id},${r.periode},${r.budget_alloue},${r.cout_total},${r.solde}\n`; });
    csv += "\nTRANSACTIONS\nID,Station,Capteur,Type,Valeur,Coût,Timestamp\n";
    transactions.forEach(t => { csv += `${t.transaction_id},${t.station_id},${t.capteur_id},${t.type_mesure},${t.valeur},${t.cout},${t.timestamp}\n`; });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `rapport_pipeline_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  }

  // ── TEST CONNECTION ──────────────────────────────────────────
  async function testConnection() {
    setConnResult("Test en cours...");
    try {
      const r = await fetch(`${apiUrl}/health`);
      const d = await r.json();
      setConnResult(`✓ OK — ${JSON.stringify(d)}`);
    } catch (e) {
      setConnResult(`✗ Erreur: ${e.message}`);
    }
  }

  // ── ENDPOINTS CODE ───────────────────────────────────────────
  const endpointsCode = `# Add these routes to api/main.py
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/alerts/recent")
def get_recent_alerts(limit: int = 50):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM alerte ORDER BY timestamp DESC LIMIT %s", (limit,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    for r in rows: r['timestamp'] = r['timestamp'].isoformat()
    return rows

@app.get("/budget/summary")
def get_budget_summary():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM budget ORDER BY pipeline_id, periode")
        cols=[d[0] for d in cur.description]
        rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/budget/transactions")
def get_transactions(limit: int = 200):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM transaction_volume ORDER BY timestamp DESC LIMIT %s", (limit,))
        cols=[d[0] for d in cur.description]
        rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    conn.close()
    for r in rows: r['timestamp'] = r['timestamp'].isoformat()
    return rows

@app.get("/health")
def health(): return {"status": "ok"}`;

  // ── RENDER HELPERS ───────────────────────────────────────────
  const fmtTs = ts => new Date(ts).toLocaleString("fr");
  const fmtTime = ts => new Date(ts).toLocaleTimeString("fr");

  function BudgetView() {
    if (!budget) return (
      <div className="pip-empty" style={{ color: "var(--danger)" }}>
        <WarnIcon />
        Impossible de charger le budget.<br />Vérifiez que l'API tourne sur {apiUrl}
      </div>
    );
    const { summary, transactions } = budget;
    const totalAlloue  = summary.reduce((s, r) => s + (r.budget_alloue || 0), 0);
    const totalDepense = summary.reduce((s, r) => s + (r.cout_total || 0), 0);
    const totalSolde   = totalAlloue - totalDepense;
    const pct = totalAlloue > 0 ? (totalDepense / totalAlloue * 100) : 0;
    const fillCls = pct > 90 ? "danger" : pct > 70 ? "warn" : "";

    return (
      <>
        <div>
          <div className="pip-section-title">Vue globale</div>
          <div className="pip-cards">
            {[
              { label: "Budget total",   val: `${(totalAlloue/1000).toFixed(0)}k DZD`, cls: "" },
              { label: "Dépensé",        val: `${(totalDepense/1000).toFixed(1)}k DZD`, cls: "amber" },
              { label: "Solde",          val: `${(totalSolde/1000).toFixed(1)}k DZD`, cls: totalSolde < 0 ? "red" : "green" },
              { label: "Transactions",   val: transactions.length, cls: "" },
            ].map(c => (
              <div className="pip-card" key={c.label}>
                <div className="pip-card-label">{c.label}</div>
                <div className={`pip-card-val ${c.cls}`}>{c.val}</div>
              </div>
            ))}
          </div>
          <div className="pip-bar" style={{ marginTop: 12 }}>
            <div className={`pip-bar-fill ${fillCls}`} style={{ width: `${Math.min(pct, 100).toFixed(1)}%` }} />
          </div>
          <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 4, fontFamily: "var(--mono)" }}>
            {pct.toFixed(1)}% du budget consommé
          </div>
        </div>
        <div>
          <div className="pip-section-title">Par pipeline & période</div>
          <table className="pip-table">
            <thead><tr><th>Pipeline</th><th>Période</th><th>Alloué</th><th>Dépensé</th><th>Solde</th><th>%</th></tr></thead>
            <tbody>
              {summary.map((r, i) => {
                const p = r.budget_alloue > 0 ? (r.cout_total / r.budget_alloue * 100) : 0;
                const fc = p > 90 ? "danger" : p > 70 ? "warn" : "";
                return (
                  <tr key={i}>
                    <td>{r.pipeline_id}</td>
                    <td>{r.periode}</td>
                    <td>{Number(r.budget_alloue).toLocaleString("fr")}</td>
                    <td>{Number(r.cout_total).toLocaleString("fr")}</td>
                    <td style={{ color: r.solde < 0 ? "var(--danger)" : "var(--accent)" }}>{Number(r.solde).toLocaleString("fr")}</td>
                    <td>
                      <div>{p.toFixed(1)}%</div>
                      <div className="pip-bar"><div className={`pip-bar-fill ${fc}`} style={{ width: `${Math.min(p, 100)}%` }} /></div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div>
          <div className="pip-section-title">Dernières transactions</div>
          <table className="pip-table">
            <thead><tr><th>Station</th><th>Type</th><th>Valeur</th><th>Coût (DZD)</th><th>Timestamp</th></tr></thead>
            <tbody>
              {transactions.slice(0, 50).map((t, i) => (
                <tr key={i}>
                  <td>{t.station_id}</td>
                  <td>{t.type_mesure}</td>
                  <td>{Number(t.valeur).toFixed(2)}</td>
                  <td style={{ color: "var(--warn)" }}>{Number(t.cout).toFixed(2)}</td>
                  <td>{fmtTs(t.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  // ── JSX ──────────────────────────────────────────────────────
  return (
    <div className="pip-root">

      {/* HEADER */}
      <header className="pip-header">
        <div className="pip-logo">PIPELINE<span>_IIoT</span></div>
        <div className="pip-divider" />
        <span className="pip-sub">Algeria O&G Monitoring</span>
        <div className="pip-hstatus">
          <div className="pip-dot" />
          <span>simulator running</span>
          <div className="pip-divider" />
          <span style={{ fontFamily: "var(--mono)" }}>{critCount} alertes critiques</span>
        </div>
      </header>

      {/* NAV */}
      <nav className="pip-nav">
        <div className="pip-nav-label">Navigation</div>
        {[
          { id: "chat",    label: "Assistant IA",   icon: <ChatIcon /> },
          { id: "alerts",  label: "Alertes",        icon: <BellIcon />, badge: critCount },
          { id: "budget",  label: "Budget & Coûts", icon: <ChartIcon /> },
        ].map(n => (
          <button key={n.id} className={`pip-nav-btn ${page === n.id ? "active" : ""}`} onClick={() => setPage(n.id)}>
            {n.icon} {n.label}
            {n.badge !== undefined && <span className="pip-badge">{n.badge}</span>}
          </button>
        ))}

      </nav>

      {/* MAIN */}
      <main className="pip-main">

        {/* CHAT PAGE */}
        <div className={`pip-page ${page === "chat" ? "active" : ""}`}>
          <div className="pip-chat-msgs" ref={msgsRef}>
            {messages.length === 0 && (
              <div className="pip-welcome">
                <div className="pip-welcome-icon"><BulbIcon /></div>
                <h2>Pipeline AI Assistant</h2>
                <p>Posez vos questions sur le système de monitoring, les alertes, les machines ou les coûts.</p>
                <div className="pip-chips">
                  {QUICK_CHIPS.map(c => (
                    <div key={c} className="pip-chip" onClick={() => sendMessage(c)}>{c}</div>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`pip-msg ${m.role}`}>
                <div className="pip-msg-av">{m.role === "user" ? "YOU" : "AI"}</div>
                <div className="pip-msg-bubble">
                  {m.text === null
                    ? <div className="pip-thinking"><span /><span /><span /></div>
                    : m.text.startsWith("ERROR:")
                      ? <span style={{ color: "var(--danger)" }}>{m.text.slice(6)}</span>
                      : m.text.split("\n").map((l, j) => <span key={j}>{l}<br /></span>)
                  }
                </div>
              </div>
            ))}
          </div>
          <div className="pip-input-area">
            <textarea
              ref={inputRef}
              className="pip-input"
              placeholder="Posez votre question sur le pipeline..."
              value={input}
              rows={1}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
            />
            <button className="pip-send" onClick={() => sendMessage()} disabled={streaming}>
              <SendIcon />
            </button>
          </div>
        </div>

        {/* ALERTS PAGE */}
        <div className={`pip-page ${page === "alerts" ? "active" : ""}`}>
          <div className="pip-page-hdr">
            <div>
              <div className="pip-page-title">Alertes système</div>
              <div className="pip-page-sub">
                {alerts === null
                  ? "Erreur de chargement"
                  : alerts.length
                    ? `${alerts.length} alertes — màj ${new Date().toLocaleTimeString("fr")}`
                    : "Chargement..."}
              </div>
            </div>
            <button className="pip-refresh-btn" onClick={loadAlerts}><RefreshIcon /> Actualiser</button>
          </div>
          <div className="pip-alerts-list">
            {alerts === null ? (
              <div className="pip-empty" style={{ color: "var(--danger)" }}>
                <WarnIcon />
                Impossible de charger. Vérifiez l'API sur {apiUrl}
              </div>
            ) : alerts.length === 0 ? (
              <div className="pip-empty"><OkIcon /> Aucune alerte</div>
            ) : alerts.map((a, i) => {
              const cls = (a.type_alerte || "").toLowerCase();
              return (
                <div key={i} className={`pip-alert-item ${cls}`}>
                  <div className={`pip-adot ${cls}`} />
                  <div className="pip-abody">
                    <div className="pip-atop">
                      <span className="pip-asensor">{a.capteur_id}</span>
                      <span className={`pip-atype ${cls}`}>{a.type_alerte}</span>
                    </div>
                    <div className="pip-amsg">{a.message || "Seuil dépassé"}</div>
                    <div className="pip-atime">{fmtTs(a.timestamp)}</div>
                  </div>
                  <div className="pip-aval">{Number(a.valeur).toFixed(2)}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* BUDGET PAGE */}
        <div className={`pip-page ${page === "budget" ? "active" : ""}`}>
          <div className="pip-page-hdr">
            <div>
              <div className="pip-page-title">Budget & Coûts</div>
              <div className="pip-page-sub">Suivi des transactions et consommation budgétaire</div>
            </div>
            <button className="pip-dl-btn" onClick={downloadCSV}><DownloadIcon /> Télécharger CSV</button>
          </div>
          <div className="pip-budget-body">
            {budget === null
              ? <div className="pip-empty" style={{ color: "var(--danger)" }}><WarnIcon />Impossible de charger. Vérifiez l'API.</div>
              : !budget
                ? <div className="pip-empty">Chargement...</div>
                : <BudgetView />
            }
          </div>
        </div>

        {/* CONFIG PAGE */}
        <div className={`pip-page ${page === "config" ? "active" : ""}`} style={{ overflowY: "auto" }}>
          <div className="pip-config">
            <div>
              <div className="pip-page-title" style={{ marginBottom: 6 }}>Configuration</div>
              <div className="pip-page-sub">Connexion backend FastAPI</div>
            </div>
            <div className="pip-config-card">
              <div className="pip-section-title">Backend FastAPI</div>
              <div>
                <div className="pip-label">URL du backend</div>
                <input className="pip-text-input" value={apiUrl} onChange={e => setApiUrl(e.target.value)} />
              </div>
              <button className="pip-btn-sm" onClick={testConnection}>Tester la connexion</button>
              {connResult && (
                <div style={{ fontSize: 12, fontFamily: "var(--mono)", color: connResult.startsWith("✓") ? "var(--accent)" : "var(--danger)" }}>
                  {connResult}
                </div>
              )}
            </div>
            <div className="pip-config-card">
              <div className="pip-section-title">Endpoints requis dans main.py</div>
              <div className="pip-code-block">
                GET /alerts/recent?limit=50<br />
                GET /budget/summary<br />
                GET /budget/transactions?limit=200<br />
                GET /health
              </div>
              <button className="pip-btn-accent" onClick={() => {
                navigator.clipboard.writeText(endpointsCode);
                setCopyMsg(true);
                setTimeout(() => setCopyMsg(false), 3000);
              }}>
                Copier le code des endpoints
              </button>
              {copyMsg && <div style={{ fontSize: 11, color: "var(--accent)" }}>✓ Copié dans le presse-papiers</div>}
            </div>
          </div>
        </div>

      </main>

      {/* RIGHT PANEL */}
      <aside className="pip-aside">
        <div className="pip-panel-hdr">
          <span className="pip-panel-title">Alertes en direct</span>
          <span className="pip-live-tag"><div className="pip-dot" /> LIVE</span>
        </div>
        <div className="pip-panel-list">
          {panelAlerts.length === 0 ? (
            <div className="pip-empty"><OkIcon />En attente d'alertes...</div>
          ) : panelAlerts.map((a, i) => (
            <div key={a.alerte_id || i} className="pip-palert">
              <div className="pip-palert-top">
                <span className="pip-palert-sensor">{a.capteur_id}</span>
                <span className="pip-palert-time">{fmtTime(a.timestamp)}</span>
              </div>
              <div className="pip-palert-msg">{a.message || "Seuil dépassé"}</div>
              <div className="pip-palert-val">val: {Number(a.valeur).toFixed(2)}</div>
            </div>
          ))}
        </div>
      </aside>

    </div>
  );
}