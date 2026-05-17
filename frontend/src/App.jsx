import { useState, useEffect, useRef } from "react";
import * as XLSX from "xlsx";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from "recharts";

// ── CONFIG ──────────────────────────────────────────────────
const API_BASE = "http://localhost:8000";

const QUICK_CHIPS = [
  "État général de toutes les machines",
  "Alertes critiques actives — détail complet",
  "Résumé budget pipelines P1 et P2",
  "Quelles stations sont en alarme ?",
  "Tendances de pression par capteur",
  "Y a-t-il des dépassements de budget ?",
  "Anomalies de température détectées",
  "Top machines avec le plus d'alertes",
];

// ── SENSOR METADATA MAP ───────────────────────────────────────
const SENSOR_META = {
  C1:  { pipeline: "P1", station: "Station Nord A (Pompage)",       wilaya: "Alger (16)",         type: "Pression",    unit: "bar",  seuil_min: 10,  seuil_max: 100 },
  C2:  { pipeline: "P1", station: "Station Nord A (Pompage)",       wilaya: "Alger (16)",         type: "Température", unit: "°C",   seuil_min: 0,   seuil_max: 90  },
  C3:  { pipeline: "P2", station: "Station Sud A (Compression)",    wilaya: "Hassi Messaoud (30)",type: "Débit",       unit: "m³/h", seuil_min: 50,  seuil_max: 500 },
  C5:  { pipeline: "P1", station: "Terminal Départ Nord (S3)",      wilaya: "Alger (16)",         type: "Pression",    unit: "bar",  seuil_min: 10,  seuil_max: 100 },
  C6:  { pipeline: "P1", station: "Terminal Départ Nord (S3)",      wilaya: "Alger (16)",         type: "Débit",       unit: "m³/h", seuil_min: 50,  seuil_max: 500 },
  C7:  { pipeline: "P1", station: "Terminal Arrivée Nord (S4)",     wilaya: "Oran (31)",          type: "Pression",    unit: "bar",  seuil_min: 10,  seuil_max: 100 },
  C8:  { pipeline: "P1", station: "Terminal Arrivée Nord (S4)",     wilaya: "Oran (31)",          type: "Débit",       unit: "m³/h", seuil_min: 50,  seuil_max: 500 },
  C9:  { pipeline: "P1", station: "Terminal Arrivée Nord (S4)",     wilaya: "Oran (31)",          type: "Température", unit: "°C",   seuil_min: 0,   seuil_max: 90  },
  C10: { pipeline: "P2", station: "Terminal Départ Sud (S5)",       wilaya: "Hassi Messaoud (30)",type: "Pression",   unit: "bar",  seuil_min: 10,  seuil_max: 100 },
  C11: { pipeline: "P2", station: "Terminal Départ Sud (S5)",       wilaya: "Hassi Messaoud (30)",type: "Débit",      unit: "m³/h", seuil_min: 50,  seuil_max: 500 },
  C12: { pipeline: "P2", station: "Terminal Arrivée Sud (S6)",      wilaya: "Ouargla (30)",       type: "Pression",    unit: "bar",  seuil_min: 10,  seuil_max: 100 },
  C13: { pipeline: "P2", station: "Terminal Arrivée Sud (S6)",      wilaya: "Ouargla (30)",       type: "Débit",       unit: "m³/h", seuil_min: 50,  seuil_max: 500 },
  C14: { pipeline: "P2", station: "Terminal Arrivée Sud (S6)",      wilaya: "Ouargla (30)",       type: "Température", unit: "°C",   seuil_min: 0,   seuil_max: 90  },
};

function getSensorMeta(capteurId) {
  if (!capteurId) return null;
  const key = capteurId.toString().toUpperCase().replace(/\s/g, "");
  return SENSOR_META[key] || null;
}

function buildAlertMessage(a) {
  const meta = getSensorMeta(a.capteur_id);
  if (!meta) return a.message || "Seuil dépassé";
  const val  = Number(a.valeur);
  const diff = Math.abs(val - meta.seuil_max).toFixed(2);
  const direction = val > meta.seuil_max ? "au-dessus du max" : "en-dessous du min";
  return `${meta.type} ${direction} — écart: ${diff} ${meta.unit}`;
}

// ══════════════════════════════════════════════════════════════
// CHART BLOCK RENDERER
// Parses ```chart JSON blocks emitted by Gemini and renders
// them as interactive Recharts bar/line charts.
// ══════════════════════════════════════════════════════════════
function ChartBlock({ spec }) {
  try {
    const { type, title, labels, datasets } = spec;
    if (!labels || !datasets || !datasets.length) return null;

    const data = labels.map((label, idx) => {
      const entry = { name: label };
      datasets.forEach(ds => { entry[ds.label] = ds.data[idx] ?? 0; });
      return entry;
    });

    const colors = datasets.map((ds, i) =>
      ds.color || ["#00c896","#ff4d4d","#f59e0b","#3b82f6","#8b5cf6"][i % 5]
    );

    const axisStyle  = { fill: "#4a5258", fontSize: 10, fontFamily: "IBM Plex Mono" };
    const gridStyle  = { stroke: "rgba(255,255,255,0.05)" };
    const tooltipStyle = {
      contentStyle: { background: "#181d20", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 12 },
      labelStyle: { color: "#e8eaeb" },
    };
    const legendStyle = { fontSize: 11, color: "#8a9299", paddingTop: 6 };
    const margin = { top: 8, right: 12, left: 0, bottom: 44 };

    const renderInner = () => {
      if (type === "line") return (
        <LineChart data={data} margin={margin}>
          <CartesianGrid strokeDasharray="3 3" {...gridStyle} />
          <XAxis dataKey="name" tick={axisStyle} angle={-30} textAnchor="end" interval={0} />
          <YAxis tick={axisStyle} width={60} />
          <Tooltip {...tooltipStyle} />
          <Legend wrapperStyle={legendStyle} />
          {datasets.map((ds, i) => (
            <Line key={ds.label} type="monotone" dataKey={ds.label}
              stroke={colors[i]} strokeWidth={2} dot={{ r: 3, fill: colors[i] }} />
          ))}
        </LineChart>
      );
      return (
        <BarChart data={data} margin={margin}>
          <CartesianGrid strokeDasharray="3 3" {...gridStyle} />
          <XAxis dataKey="name" tick={axisStyle} angle={-20} textAnchor="end" interval={0} />
          <YAxis tick={axisStyle} width={60} />
          <Tooltip {...tooltipStyle} />
          <Legend wrapperStyle={legendStyle} />
          {datasets.map((ds, i) => (
            <Bar key={ds.label} dataKey={ds.label} radius={[3,3,0,0]}>
              {data.map((_, ci) => <Cell key={ci} fill={colors[i]} />)}
            </Bar>
          ))}
        </BarChart>
      );
    };

    return (
      <div className="pip-chart-block">
        {title && <div className="pip-chart-title">{title}</div>}
        <ResponsiveContainer width="100%" height={240}>{renderInner()}</ResponsiveContainer>
      </div>
    );
  } catch { return null; }
}

// ══════════════════════════════════════════════════════════════
// MARKDOWN RENDERER
// Converts Gemini's Markdown response to styled HTML elements.
// Handles: ## headings, **bold**, tables, bullet lists,
//          numbered lists, code/chart blocks, horizontal rules.
// ══════════════════════════════════════════════════════════════
function MarkdownMessage({ text }) {
  const lines  = text.split("\n");
  const output = [];
  let i = 0;

  const inlineFormat = (str) => {
    // **bold**, *italic*, `code`
    return str
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,     '<em>$1</em>')
      .replace(/`([^`]+)`/g,     '<code class="pip-inline-code">$1</code>');
  };

  while (i < lines.length) {
    const line = lines[i];

    // ── Horizontal rule ─────────────────────────────────────
    if (/^---+$/.test(line.trim())) {
      output.push(<hr key={i} className="pip-md-hr" />);
      i++; continue;
    }

    // ── Headings ─────────────────────────────────────────────
    if (line.startsWith("### ")) {
      output.push(
        <h3 key={i} className="pip-md-h3"
          dangerouslySetInnerHTML={{ __html: inlineFormat(line.slice(4)) }} />
      );
      i++; continue;
    }
    if (line.startsWith("## ")) {
      output.push(
        <h2 key={i} className="pip-md-h2"
          dangerouslySetInnerHTML={{ __html: inlineFormat(line.slice(3)) }} />
      );
      i++; continue;
    }
    if (line.startsWith("# ")) {
      output.push(
        <h1 key={i} className="pip-md-h1"
          dangerouslySetInnerHTML={{ __html: inlineFormat(line.slice(2)) }} />
      );
      i++; continue;
    }

    // ── Markdown table ───────────────────────────────────────
    if (line.trimStart().startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].trimStart().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      // Filter separator rows (|---|---|)
      const dataRows = tableLines.filter(l => !/^\s*\|[\s\-|:]+\|\s*$/.test(l));
      if (dataRows.length > 1) {
        const parseRow = (l) =>
          l.split("|").map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        const [headerRow, ...bodyRows] = dataRows;
        const headers = parseRow(headerRow);
        output.push(
          <div key={`tbl-${i}`} className="pip-md-table-wrap">
            <table className="pip-md-table">
              <thead>
                <tr>{headers.map((h, j) => (
                  <th key={j} dangerouslySetInnerHTML={{ __html: inlineFormat(h) }} />
                ))}</tr>
              </thead>
              <tbody>
                {bodyRows.map((row, ri) => (
                  <tr key={ri}>{parseRow(row).map((cell, ci) => (
                    <td key={ci} dangerouslySetInnerHTML={{ __html: inlineFormat(cell) }} />
                  ))}</tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // ── Code block OR Chart block ────────────────────────────
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim().toLowerCase();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      const raw = codeLines.join("\n").trim();

      if (lang === "chart") {
        // Parse JSON spec and render as a real chart
        try {
          const spec = JSON.parse(raw);
          output.push(<ChartBlock key={`chart-${i}`} spec={spec} />);
        } catch {
          // Fallback: show raw JSON as code if parse fails
          output.push(
            <pre key={`code-${i}`} className="pip-md-code"><code>{raw}</code></pre>
          );
        }
      } else {
        output.push(
          <pre key={`code-${i}`} className="pip-md-code">
            <code>{raw}</code>
          </pre>
        );
      }
      i++; continue;
    }

    // ── Bullet list ──────────────────────────────────────────
    if (/^[\-\*] /.test(line)) {
      const items = [];
      while (i < lines.length && /^[\-\*] /.test(lines[i])) {
        items.push(lines[i].slice(2));
        i++;
      }
      output.push(
        <ul key={`ul-${i}`} className="pip-md-ul">
          {items.map((it, j) => (
            <li key={j} dangerouslySetInnerHTML={{ __html: inlineFormat(it) }} />
          ))}
        </ul>
      );
      continue;
    }

    // ── Numbered list ────────────────────────────────────────
    if (/^\d+\. /.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ""));
        i++;
      }
      output.push(
        <ol key={`ol-${i}`} className="pip-md-ol">
          {items.map((it, j) => (
            <li key={j} dangerouslySetInnerHTML={{ __html: inlineFormat(it) }} />
          ))}
        </ol>
      );
      continue;
    }

    // ── Empty line → spacing ─────────────────────────────────
    if (line.trim() === "") {
      output.push(<div key={i} className="pip-md-spacer" />);
      i++; continue;
    }

    // ── Normal paragraph ─────────────────────────────────────
    output.push(
      <p key={i} className="pip-md-p"
        dangerouslySetInnerHTML={{ __html: inlineFormat(line) }} />
    );
    i++;
  }

  return <div className="pip-md-body">{output}</div>;
}

// ── ICONS ────────────────────────────────────────────────────
const Icon = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const ChatIcon    = () => <Icon d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />;
const BellIcon    = () => <Icon d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />;
const ChartIcon   = () => <Icon d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />;
const SendIcon    = () => <Icon d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />;
const RefreshIcon = () => <Icon d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />;
const DownloadIcon= () => <Icon d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />;
const BulbIcon    = () => <Icon size={24} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />;
const WarnIcon    = () => <Icon size={24} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />;
const OkIcon      = () => <Icon d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />;
const MapPinIcon  = () => <Icon size={12} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z" />;
const PipeIcon    = () => <Icon size={12} d="M4 6h16M4 10h16M4 14h16M4 18h16" />;

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
    --gemini: #8b5cf6;
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
  .pip-gemini-badge {
    display:flex; align-items:center; gap:4px;
    font-size:10px; font-family:var(--mono);
    color:var(--gemini);
    background:rgba(139,92,246,.1);
    border:1px solid rgba(139,92,246,.2);
    border-radius:4px; padding:2px 7px;
  }
  .pip-mcp-badge {
    display:flex; align-items:center; gap:4px;
    font-size:10px; font-family:var(--mono);
    color:var(--accent);
    background:rgba(0,200,150,.08);
    border:1px solid rgba(0,200,150,.2);
    border-radius:4px; padding:2px 7px;
  }

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

  .pip-msg { display:flex; gap:12px; max-width:860px; }
  .pip-msg.user { flex-direction:row-reverse; align-self:flex-end; max-width:620px; }
  .pip-msg-av {
    width:28px; height:28px; border-radius:6px;
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:500; flex-shrink:0; font-family:var(--mono);
  }
  .pip-msg.user .pip-msg-av { background:var(--accent2); color:var(--accent); }
  .pip-msg.ai   .pip-msg-av { background:rgba(139,92,246,.15); color:var(--gemini); border:1px solid rgba(139,92,246,.25); }
  .pip-msg-bubble {
    padding:12px 16px; border-radius:8px; font-size:14px; line-height:1.7; flex:1; min-width:0;
  }
  .pip-msg.user .pip-msg-bubble { background:rgba(0,200,150,.1); border:1px solid rgba(0,200,150,.2); color:var(--text); }
  .pip-msg.ai   .pip-msg-bubble { background:var(--bg3); border:1px solid var(--border); color:var(--text); }

  /* ── MARKDOWN STYLES ── */
  .pip-md-body { display:flex; flex-direction:column; gap:0; }
  .pip-md-h1 { font-size:16px; font-weight:600; color:var(--text); margin:14px 0 6px; border-bottom:1px solid var(--border); padding-bottom:4px; }
  .pip-md-h2 { font-size:14px; font-weight:600; color:var(--accent); margin:12px 0 5px; display:flex; align-items:center; gap:6px; }
  .pip-md-h3 { font-size:13px; font-weight:500; color:var(--warn); margin:10px 0 4px; }
  .pip-md-p  { font-size:13px; color:var(--text2); line-height:1.7; margin:2px 0; }
  .pip-md-spacer { height:6px; }
  .pip-md-hr { border:none; border-top:1px solid var(--border); margin:10px 0; }

  .pip-md-ul, .pip-md-ol { padding-left:18px; display:flex; flex-direction:column; gap:3px; margin:4px 0; }
  .pip-md-ul li, .pip-md-ol li { font-size:13px; color:var(--text2); line-height:1.6; }
  .pip-md-ul li::marker { color:var(--accent); }

  .pip-inline-code {
    font-family:var(--mono); font-size:11px; background:var(--bg2);
    border:1px solid var(--border2); border-radius:3px; padding:1px 5px; color:var(--warn);
  }
  .pip-md-code {
    background:var(--bg); border:1px solid var(--border2); border-radius:6px;
    padding:12px 14px; font-family:var(--mono); font-size:12px; color:var(--text2);
    overflow-x:auto; margin:6px 0; white-space:pre;
  }

  /* CHART BLOCKS */
  .pip-chart-block {
    margin: 10px 0; background: var(--bg2); border: 1px solid var(--border2);
    border-radius: 8px; padding: 14px 12px 6px;
  }
  .pip-chart-title {
    font-size: 12px; font-weight: 500; color: var(--text2);
    text-transform: uppercase; letter-spacing: .07em; margin-bottom: 10px;
    padding-bottom: 6px; border-bottom: 1px solid var(--border);
  }

  /* Markdown tables */
  .pip-md-table-wrap { overflow-x:auto; margin:6px 0; border-radius:6px; border:1px solid var(--border2); }
  .pip-md-table { width:100%; border-collapse:collapse; font-size:12px; }
  .pip-md-table th {
    text-align:left; padding:7px 12px; background:rgba(0,200,150,.05);
    color:var(--accent); font-size:11px; font-weight:500; text-transform:uppercase;
    letter-spacing:.05em; border-bottom:1px solid var(--border2); white-space:nowrap;
  }
  .pip-md-table td {
    padding:7px 12px; border-bottom:1px solid var(--border); color:var(--text2);
    font-family:var(--mono); font-size:12px; white-space:nowrap;
  }
  .pip-md-table tr:last-child td { border-bottom:none; }
  .pip-md-table tr:hover td { background:rgba(255,255,255,.02); color:var(--text); }
  .pip-md-table strong { color:var(--text); font-weight:600; }

  /* INPUT */
  .pip-input-area { padding:16px 28px 20px; border-top:1px solid var(--border); display:flex; gap:10px; align-items:flex-end; }
  .pip-input {
    flex:1; background:var(--bg3); border:1px solid var(--border2); border-radius:8px;
    padding:10px 14px; color:var(--text); font-family:var(--font); font-size:14px;
    resize:none; outline:none; min-height:42px; max-height:120px; transition:border-color .15s;
  }
  .pip-input:focus { border-color:var(--gemini); }
  .pip-input::placeholder { color:var(--text3); }
  .pip-send {
    background:var(--gemini); border:none; border-radius:8px;
    width:40px; height:40px; display:flex; align-items:center; justify-content:center;
    cursor:pointer; transition:all .15s; flex-shrink:0; color:#fff;
  }
  .pip-send:hover { background:#7c3aed; }
  .pip-send:disabled { background:var(--bg3); cursor:not-allowed; color:var(--text3); }

  /* THINKING DOTS */
  .pip-thinking { display:flex; gap:4px; align-items:center; padding:4px 0; }
  .pip-thinking span { width:6px; height:6px; border-radius:50%; background:var(--gemini); animation:pip-blink 1.2s infinite; opacity:.4; }
  .pip-thinking span:nth-child(2){animation-delay:.2s}
  .pip-thinking span:nth-child(3){animation-delay:.4s}
  @keyframes pip-blink { 0%,80%,100%{opacity:.2} 40%{opacity:1} }

  /* WELCOME */
  .pip-welcome { display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; gap:12px; padding:40px; text-align:center; }
  .pip-welcome-icon { width:52px; height:52px; background:rgba(139,92,246,.1); border:1px solid rgba(139,92,246,.2); border-radius:14px; display:flex; align-items:center; justify-content:center; color:var(--gemini); }
  .pip-welcome h2 { font-size:17px; font-weight:500; color:var(--text); }
  .pip-welcome p { font-size:13px; color:var(--text2); max-width:440px; line-height:1.7; }
  .pip-welcome-badges { display:flex; gap:8px; flex-wrap:wrap; justify-content:center; }
  .pip-welcome-note { font-size:11px; color:var(--text3); font-family:var(--mono); }
  .pip-chips { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:4px; max-width:600px; }
  .pip-chip { padding:6px 13px; background:var(--bg3); border:1px solid var(--border2); border-radius:20px; font-size:12px; color:var(--text2); cursor:pointer; transition:all .15s; }
  .pip-chip:hover { border-color:var(--gemini); color:var(--gemini); background:rgba(139,92,246,.05); }

  /* PAGE HEADER */
  .pip-page-hdr { padding:20px 28px 0; display:flex; align-items:center; justify-content:space-between; }
  .pip-page-title { font-size:16px; font-weight:500; color:var(--text); }
  .pip-page-sub { font-size:12px; color:var(--text2); margin-top:2px; }
  .pip-refresh-btn { display:flex; align-items:center; gap:6px; padding:6px 12px; background:var(--bg3); border:1px solid var(--border2); border-radius:6px; color:var(--text2); font-size:12px; cursor:pointer; font-family:var(--font); transition:all .15s; }
  .pip-refresh-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* ALERT FILTERS */
  .pip-filter-bar { display:flex; gap:6px; padding:12px 28px 0; flex-wrap:wrap; }
  .pip-filter-btn { padding:4px 12px; border-radius:20px; font-size:11px; font-family:var(--mono); cursor:pointer; border:1px solid var(--border2); background:var(--bg3); color:var(--text2); transition:all .15s; }
  .pip-filter-btn.active-all   { border-color:var(--text2); color:var(--text);   background:rgba(255,255,255,.05); }
  .pip-filter-btn.active-crit  { border-color:var(--danger); color:var(--danger); background:rgba(255,77,77,.07); }
  .pip-filter-btn.active-p1    { border-color:var(--info);   color:var(--info);   background:rgba(59,130,246,.07); }
  .pip-filter-btn.active-p2    { border-color:var(--warn);   color:var(--warn);   background:rgba(245,158,11,.07); }
  .pip-filter-btn.active-warn  { border-color:var(--warn);   color:var(--warn);   background:rgba(245,158,11,.07); }

  /* ALERT STATS BAR */
  .pip-alert-stats { display:flex; gap:16px; padding:12px 28px 0; flex-wrap:wrap; }
  .pip-astat { display:flex; flex-direction:column; gap:1px; }
  .pip-astat-val { font-family:var(--mono); font-size:18px; font-weight:500; color:var(--text); }
  .pip-astat-val.red   { color:var(--danger); }
  .pip-astat-val.green { color:var(--accent); }
  .pip-astat-val.blue  { color:var(--info);   }
  .pip-astat-val.amber { color:var(--warn);   }
  .pip-astat-lbl { font-size:10px; color:var(--text3); text-transform:uppercase; letter-spacing:.08em; }
  .pip-astat-sep { width:1px; background:var(--border); align-self:stretch; margin:0 4px; }

  /* ALERTS LIST */
  .pip-alerts-list { flex:1; overflow-y:auto; padding:12px 28px; display:flex; flex-direction:column; gap:8px; }
  .pip-alerts-list::-webkit-scrollbar { width:4px; }
  .pip-alerts-list::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }

  .pip-alert-item {
    display:grid; grid-template-columns:8px 1fr auto; gap:12px; align-items:start;
    padding:12px 14px; background:var(--bg3); border:1px solid var(--border);
    border-radius:8px; transition:border-color .15s;
    animation: pip-alertin .25s ease;
  }
  @keyframes pip-alertin { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
  .pip-alert-item:hover { border-color:var(--border2); }
  .pip-alert-item.critique      { border-left:2px solid var(--danger); }
  .pip-alert-item.resolue       { border-left:2px solid var(--accent); opacity:.6; }
  .pip-alert-item.avertissement { border-left:2px solid var(--warn); }

  .pip-adot { width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; }
  .pip-adot.critique      { background:var(--danger); box-shadow:0 0 6px rgba(255,77,77,.4); }
  .pip-adot.resolue       { background:var(--accent); }
  .pip-adot.avertissement { background:var(--warn); animation:pip-warn-pulse 2s infinite; }
  @keyframes pip-warn-pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  .pip-abody { display:flex; flex-direction:column; gap:4px; }
  .pip-atop  { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .pip-asensor { font-family:var(--mono); font-size:12px; color:var(--accent); background:rgba(0,200,150,.08); padding:1px 6px; border-radius:4px; }
  .pip-atype { font-size:11px; color:var(--danger); font-weight:500; text-transform:uppercase; letter-spacing:.05em; }
  .pip-atype.resolue       { color:var(--accent); }
  .pip-atype.avertissement { color:var(--warn); }

  .pip-ameta { display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:1px; }
  .pip-aloc  { display:flex; align-items:center; gap:3px; font-size:11px; color:var(--text2); }
  .pip-apipeline {
    display:inline-flex; align-items:center; gap:3px;
    font-size:10px; font-family:var(--mono); padding:1px 6px; border-radius:3px; font-weight:500;
  }
  .pip-apipeline.P1 { color:var(--info); background:rgba(59,130,246,.1); border:1px solid rgba(59,130,246,.2); }
  .pip-apipeline.P2 { color:var(--warn); background:rgba(245,158,11,.1); border:1px solid rgba(245,158,11,.2); }
  .pip-ameastype { font-size:10px; font-family:var(--mono); color:var(--text3); padding:1px 6px; border-radius:3px; background:var(--bg2); border:1px solid var(--border); }
  .pip-amsg  { font-size:12px; color:var(--text2); line-height:1.5; }

  .pip-aval-block { display:flex; flex-direction:column; align-items:flex-end; gap:3px; }
  .pip-aval  { font-family:var(--mono); font-size:14px; font-weight:500; color:var(--text); }
  .pip-aunit { font-size:10px; color:var(--text3); font-family:var(--mono); }
  .pip-atime { font-size:11px; color:var(--text3); }

  /* BUDGET */
  .pip-budget-body { flex:1; overflow-y:auto; padding:16px 28px 28px; display:flex; flex-direction:column; gap:20px; }
  .pip-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; }
  .pip-card { background:var(--bg3); border:1px solid var(--border); border-radius:8px; padding:14px 16px; }
  .pip-card-label { font-size:11px; color:var(--text3); text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
  .pip-card-val { font-family:var(--mono); font-size:20px; font-weight:500; color:var(--text); }
  .pip-card-val.green { color:var(--accent); }
  .pip-card-val.red   { color:var(--danger); }
  .pip-card-val.amber { color:var(--warn);   }
  .pip-section-title { font-size:12px; font-weight:500; color:var(--text2); text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }
  .pip-table { width:100%; border-collapse:collapse; font-size:13px; }
  .pip-table th { text-align:left; padding:8px 12px; color:var(--text3); font-size:11px; font-weight:500; text-transform:uppercase; letter-spacing:.06em; border-bottom:1px solid var(--border); }
  .pip-table td { padding:10px 12px; border-bottom:1px solid var(--border); color:var(--text2); font-family:var(--mono); font-size:12px; }
  .pip-table tr:hover td { background:var(--bg3); color:var(--text); }
  .pip-bar { height:4px; background:var(--bg); border-radius:2px; overflow:hidden; margin-top:4px; width:100%; }
  .pip-bar-fill { height:100%; background:var(--accent); border-radius:2px; transition:width .3s; }
  .pip-bar-fill.warn   { background:var(--warn);   }
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

  .pip-palert               { padding:9px 10px; background:var(--bg3); border:1px solid var(--border); border-left:2px solid var(--danger); border-radius:6px; font-size:12px; animation:pip-slidein .3s ease; }
  .pip-palert.avertissement { border-left-color:var(--warn); }
  .pip-palert.resolue       { border-left-color:var(--accent); opacity:.7; }
  @keyframes pip-slidein { from{opacity:0;transform:translateX(8px)} to{opacity:1;transform:translateX(0)} }
  .pip-palert-top  { display:flex; justify-content:space-between; margin-bottom:3px; }
  .pip-palert-sensor { font-family:var(--mono); font-size:11px; color:var(--accent); }
  .pip-palert-time   { font-size:10px; color:var(--text3); }
  .pip-palert-loc  { font-size:10px; color:var(--text3); margin-bottom:2px; display:flex; align-items:center; gap:3px; }
  .pip-palert-msg  { color:var(--text2); font-size:11px; margin-bottom:2px; }
  .pip-palert-val  { font-family:var(--mono); font-weight:500; color:var(--danger); font-size:11px; }
  .pip-palert-tags { display:flex; gap:4px; margin-top:4px; }
  .pip-ptag        { font-size:9px; font-family:var(--mono); padding:1px 5px; border-radius:3px; }
  .pip-ptag.P1     { color:var(--info); background:rgba(59,130,246,.12); }
  .pip-ptag.P2     { color:var(--warn); background:rgba(245,158,11,.12); }
  .pip-ptag.type   { color:var(--text3); background:var(--bg2); }

  /* EMPTY STATE */
  .pip-empty { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; color:var(--text3); font-size:12px; padding:20px; text-align:center; }
  .pip-empty svg { opacity:.4; }
`;

// ── MAIN COMPONENT ────────────────────────────────────────────
export default function PipelineDashboard() {
  const [page, setPage]               = useState("chat");
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState("");
  const [streaming, setStreaming]     = useState(false);
  const [alerts, setAlerts]           = useState([]);
  const [alertFilter, setAlertFilter] = useState("all");
  const [budget, setBudget]           = useState(null);
  const [panelAlerts, setPanelAlerts] = useState([]);
  const [totalAlertCount, setTotalAlertCount] = useState(0);
  const [critAlertCount,  setCritAlertCount]  = useState(0);

  const msgsRef   = useRef(null);
  const inputRef  = useRef(null);

  // ── Inject CSS once ─────────────────────────────────────────
  useEffect(() => {
    if (!document.getElementById("pip-styles")) {
      const s = document.createElement("style");
      s.id = "pip-styles";
      s.textContent = css;
      document.head.appendChild(s);
    }
  }, []);

  // ── Live poll every 10 s ─────────────────────────────────────
  useEffect(() => {
    pollPanel();
    const id = setInterval(pollPanel, 10000);
    return () => clearInterval(id);
  }, []);

  // ── Auto-scroll chat ─────────────────────────────────────────
  useEffect(() => {
    if (msgsRef.current) msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
  }, [messages]);

  // ── Load page data on nav ────────────────────────────────────
  useEffect(() => {
    if (page === "alerts") {
      loadAlerts();
      const id = setInterval(loadAlerts, 10000);
      return () => clearInterval(id);
    }
    if (page === "budget") loadBudget();
  }, [page]);

  // ── API HELPERS ──────────────────────────────────────────────
  async function pollPanel() {
    try {
      const [panelRes, countRes] = await Promise.all([
        fetch(`${API_BASE}/alerts/recent?limit=20`),
        fetch(`${API_BASE}/alerts/recent?limit=10000`),
      ]);
      const panelData = await panelRes.json();
      const countData = await countRes.json();
      setTotalAlertCount(countData.length);
      setCritAlertCount(countData.filter(a => a.type_alerte === "Critique").length);
      setPanelAlerts(prev => {
        const ids = new Set(prev.map(a => a.alerte_id));
        const fresh = panelData.filter(a => !ids.has(a.alerte_id));
        if (!fresh.length) return prev;
        return [...fresh, ...prev].slice(0, 30);
      });
    } catch { /* API not ready */ }
  }

  async function loadAlerts() {
    try {
      const r    = await fetch(`${API_BASE}/alerts/recent?limit=10000`);
      const data = await r.json();
      setAlerts(data);
      setTotalAlertCount(data.length);
      setCritAlertCount(data.filter(a => a.type_alerte === "Critique").length);
    } catch { setAlerts(null); }
  }

  async function loadBudget() {
    try {
      const [sr, tr] = await Promise.all([
        fetch(`${API_BASE}/budget/summary`),
        fetch(`${API_BASE}/budget/transactions?limit=200`),
      ]);
      setBudget({ summary: await sr.json(), transactions: await tr.json() });
    } catch { setBudget(null); }
  }

  // ── CHAT → Gemini via FastAPI /chat ──────────────────────────
  async function sendMessage(text) {
    const msg = (text || input).trim();
    if (!msg || streaming) return;
    setInput("");
    setStreaming(true);
    setMessages(prev => [...prev, { role: "user", text: msg }, { role: "ai", text: null }]);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message: msg }),
      });
      const data  = await res.json();
      const reply = data.reply || "Erreur : réponse vide.";
      setMessages(prev => {
        const copy = [...prev];
        copy[copy.length - 1] = { role: "ai", text: reply };
        return copy;
      });
    } catch {
      setMessages(prev => {
        const copy = [...prev];
        copy[copy.length - 1] = { role: "ai", text: "ERROR:Erreur de connexion à l'API." };
        return copy;
      });
    }
    setStreaming(false);
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  // ── CSV DOWNLOAD ─────────────────────────────────────────────
function downloadXLSX() {
  if (!budget) return;
  const { summary, transactions } = budget;
  const wb = XLSX.utils.book_new();

  const STATION_INFO = {
    S4: { pipeline: "P1", nom: "Terminal Arrivée Nord", wilaya: "Oran" },
    S6: { pipeline: "P2", nom: "Terminal Arrivée Sud",  wilaya: "Ouargla" },
  };
  const CAPTEUR_INFO = {
    C8:  { type: "Débit", unite: "m³/h" },
    C13: { type: "Débit", unite: "m³/h" },
  };

  const enriched = [...transactions]
    .sort((a, b) => a.transaction_id - b.transaction_id)
    .map(t => {
      const si = STATION_INFO[t.station_id] || {};
      const ci = CAPTEUR_INFO[t.capteur_id] || {};
      const ts = (t.timestamp || "").slice(0, 19).replace("T", " ");
      return {
        ...t,
        pipeline:    si.pipeline    || "—",
        station_nom: si.nom         || t.station_id,
        wilaya:      si.wilaya      || "—",
        mesure_type: ci.type        || t.type_mesure,
        ts_clean:    ts,
        date:        ts.slice(0, 10),
        time:        ts.slice(11, 19),
      };
    });

  const totalAlloue  = summary.reduce((s, r) => s + Number(r.budget_alloue || 0), 0);
  const totalDepense = summary.reduce((s, r) => s + Number(r.cout_total    || 0), 0);
  const totalSolde   = totalAlloue - totalDepense;
  const totalPct     = totalAlloue > 0 ? (totalDepense / totalAlloue * 100) : 0;

  // ── SHEET 1: Résumé Budget ────────────────────────────────────────────────
  const s1rows = [];

  s1rows.push(["RAPPORT BUDGET PIPELINE", "", "", "", "", "", ""]);
  s1rows.push([`Généré le ${new Date().toLocaleString("fr")}  —  P1 (Alger → Oran)  &  P2 (Hassi Messaoud → Ouargla)`, "", "", "", "", "", ""]);
  s1rows.push([]);
  s1rows.push(["RÉSUMÉ PAR PIPELINE ET PÉRIODE", "", "", "", "", "", ""]);
  s1rows.push(["Pipeline", "Période", "Alloué (DZD)", "Dépensé (DZD)", "Solde (DZD)", "Taux consommé", "Statut"]);

  summary.forEach(r => {
    const alloue  = Number(r.budget_alloue || 0);
    const depense = Number(r.cout_total    || 0);
    const solde   = alloue - depense;
    const pct     = alloue > 0 ? depense / alloue : 0;
    const status  = pct > 1 ? "Dépassement" : pct > 0.8 ? "Attention" : pct > 0 ? "Normal" : "Sans données";
    s1rows.push([r.pipeline_id, r.periode, alloue, depense, solde, pct, status]);
  });

  s1rows.push(["TOTAL", "", totalAlloue, totalDepense, totalSolde, totalPct / 100, ""]);
  s1rows.push([]);
  s1rows.push(["ANALYSE PAR PIPELINE", "", "", "", "", "", ""]);

  [["P1", "C8", "P1 — Pétrole Brut (Alger → Oran)"], ["P2", "C13", "P2 — Gaz Naturel (Hassi Messaoud → Ouargla)"]].forEach(([pip, capteur, label]) => {
    const rows    = summary.filter(x => x.pipeline_id === pip);
    const pipTxns = enriched.filter(t => t.capteur_id === capteur);
    const a       = rows.reduce((s, x) => s + Number(x.budget_alloue || 0), 0);
    const d       = rows.reduce((s, x) => s + Number(x.cout_total    || 0), 0);
    const coutTxn = pipTxns.reduce((s, t) => s + Number(t.cout || 0), 0);

    s1rows.push([label, "", "", "", "", "", ""]);
    s1rows.push(["", "Budget alloué",           a,                   "", "", "", ""]);
    s1rows.push(["", "Total dépensé",            d,                   "", "", "", ""]);
    s1rows.push(["", "Solde",                    a - d,               "", "", "", ""]);
    s1rows.push(["", "Taux de consommation",     a > 0 ? d / a : 0,   "", "", "", ""]);
    s1rows.push(["", "Nombre de transactions",   pipTxns.length,      "", "", "", ""]);
    s1rows.push(["", "Coût total transactions",  coutTxn,             "", "", "", ""]);
    s1rows.push([]);
  });

  const ws1 = XLSX.utils.aoa_to_sheet(s1rows);

  // Column widths
  ws1["!cols"] = [
    { wch: 10 }, { wch: 14 }, { wch: 22 }, { wch: 22 }, { wch: 22 }, { wch: 16 }, { wch: 14 }
  ];

  // Number formats
  const fmtDZD = '#,##0.00 "DZD"';
  const fmtPct = "0.0%";
  const dataStartRow = 5; // 0-indexed row of first data row (after header)
  s1rows.forEach((row, ri) => {
    if (ri < dataStartRow) return;
    [2, 3, 4].forEach(ci => {
      const addr = XLSX.utils.encode_cell({ r: ri, c: ci });
      if (ws1[addr] && typeof ws1[addr].v === "number") {
        ws1[addr].z = fmtDZD;
      }
    });
    const pctAddr = XLSX.utils.encode_cell({ r: ri, c: 5 });
    if (ws1[pctAddr] && typeof ws1[pctAddr].v === "number") {
      ws1[pctAddr].z = fmtPct;
    }
  });

  // Merges: title rows
  ws1["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 6 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 6 } },
    { s: { r: 3, c: 0 }, e: { r: 3, c: 6 } },
  ];

  XLSX.utils.book_append_sheet(wb, ws1, "Résumé Budget");

  // ── SHEET 2: Historique Transactions ─────────────────────────────────────
  const s2rows = [];

  s2rows.push([`Historique des Transactions — ${enriched.length} enregistrements`, "", "", "", "", "", "", "", ""]);
  s2rows.push([`Tri chronologique (plus ancien → plus récent)`, "", "", "", "", "", "", "", ""]);
  s2rows.push([]);
  s2rows.push(["#", "Date", "Heure", "Pipeline", "Station", "Capteur", "Mesure", "Débit (m³/h)", "Coût (DZD)"]);

  let prevDate = null;
  enriched.forEach(t => {
    if (t.date !== prevDate) {
      if (prevDate !== null) s2rows.push([]);
      s2rows.push([`── ${t.date} ──`, "", "", "", "", "", "", "", ""]);
      prevDate = t.date;
    }
    s2rows.push([
      t.transaction_id,
      t.date,
      t.time,
      t.pipeline,
      `${t.station_id} — ${t.station_nom}`,
      t.capteur_id,
      t.mesure_type,
      Number(t.valeur),
      Number(t.cout),
    ]);
  });

  s2rows.push([]);
  s2rows.push([
    `TOTAL (${enriched.length} transactions)`, "", "", "", "", "", "",
    enriched.reduce((s, t) => s + Number(t.valeur || 0), 0),
    enriched.reduce((s, t) => s + Number(t.cout   || 0), 0),
  ]);

  const ws2 = XLSX.utils.aoa_to_sheet(s2rows);
  ws2["!cols"] = [
    { wch: 12 }, { wch: 12 }, { wch: 10 }, { wch: 10 },
    { wch: 36 }, { wch: 10 }, { wch: 10 }, { wch: 16 }, { wch: 20 }
  ];
  ws2["!freeze"] = { xSplit: 0, ySplit: 4 };

  s2rows.forEach((row, ri) => {
    if (ri < 4) return;
    const valAddr  = XLSX.utils.encode_cell({ r: ri, c: 7 });
    const coutAddr = XLSX.utils.encode_cell({ r: ri, c: 8 });
    if (ws2[valAddr]  && typeof ws2[valAddr].v  === "number") ws2[valAddr].z  = "0.000";
    if (ws2[coutAddr] && typeof ws2[coutAddr].v === "number") ws2[coutAddr].z = fmtDZD;
  });

  ws2["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 8 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 8 } },
  ];

  XLSX.utils.book_append_sheet(wb, ws2, "Historique Transactions");

  // ── SHEET 3: Analyse Stations ─────────────────────────────────────────────
  const s3rows = [];
  s3rows.push(["Analyse des Transactions par Station", "", "", ""]);
  s3rows.push([`Statistiques agrégées — Stations S4 (P1) et S6 (P2)`, "", "", ""]);
  s3rows.push([]);

  Object.entries(STATION_INFO).forEach(([station, si]) => {
    const txns  = enriched.filter(t => t.station_id === station);
    const couts = txns.map(t => Number(t.cout   || 0));
    const vals  = txns.map(t => Number(t.valeur || 0));
    const avg   = arr => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    s3rows.push([`Station ${station} — ${si.nom}  |  ${si.pipeline}  |  ${si.wilaya}`, "", "", ""]);
    s3rows.push(["", "Nombre de transactions",      txns.length,             ""]);
    s3rows.push(["", "Coût total",                  couts.reduce((a,b)=>a+b,0), ""]);
    s3rows.push(["", "Coût moyen / transaction",    avg(couts),              ""]);
    s3rows.push(["", "Coût maximum",                Math.max(...couts),      ""]);
    s3rows.push(["", "Coût minimum",                Math.min(...couts),      ""]);
    s3rows.push(["", "Débit moyen (m³/h)",          avg(vals),               ""]);
    s3rows.push(["", "Débit maximum (m³/h)",        Math.max(...vals),        ""]);
    s3rows.push(["", "Débit minimum (m³/h)",        Math.min(...vals),        ""]);
    s3rows.push(["", "Première transaction",         txns[0]?.ts_clean        || "—", ""]);
    s3rows.push(["", "Dernière transaction",         txns[txns.length-1]?.ts_clean || "—", ""]);
    s3rows.push([]);
  });

  const ws3 = XLSX.utils.aoa_to_sheet(s3rows);
  ws3["!cols"] = [{ wch: 4 }, { wch: 30 }, { wch: 28 }, { wch: 4 }];

  s3rows.forEach((row, ri) => {
    const addr = XLSX.utils.encode_cell({ r: ri, c: 2 });
    if (ws3[addr] && typeof ws3[addr].v === "number" && row[1] && row[1].includes("Coût")) {
      ws3[addr].z = fmtDZD;
    }
  });

  ws3["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 3 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 3 } },
  ];

  XLSX.utils.book_append_sheet(wb, ws3, "Analyse Stations");

  // ── Download ──────────────────────────────────────────────────────────────
  XLSX.writeFile(wb, `rapport_pipeline_${new Date().toISOString().slice(0, 10)}.xlsx`);
}

  // ── RENDER HELPERS ───────────────────────────────────────────
  const fmtTs   = ts => new Date(ts).toLocaleString("fr");
  const fmtTime = ts => new Date(ts).toLocaleTimeString("fr");

  const filteredAlerts = Array.isArray(alerts) ? alerts.filter(a => {
    if (alertFilter === "critique")      return (a.type_alerte || "").toLowerCase() === "critique";
    if (alertFilter === "avertissement") return (a.type_alerte || "").toLowerCase() === "avertissement";
    if (alertFilter === "P1" || alertFilter === "P2")
      return getSensorMeta(a.capteur_id)?.pipeline === alertFilter;
    return true;
  }) : [];

  const critCount    = Array.isArray(alerts) ? alerts.filter(a => (a.type_alerte||"").toLowerCase() === "critique").length      : 0;
  const avertCount   = Array.isArray(alerts) ? alerts.filter(a => (a.type_alerte||"").toLowerCase() === "avertissement").length  : 0;
  const resolueCount = Array.isArray(alerts) ? alerts.filter(a => (a.type_alerte||"").toLowerCase() === "resolue").length        : 0;
  const p1Count      = Array.isArray(alerts) ? alerts.filter(a => getSensorMeta(a.capteur_id)?.pipeline === "P1").length         : 0;
  const p2Count      = Array.isArray(alerts) ? alerts.filter(a => getSensorMeta(a.capteur_id)?.pipeline === "P2").length         : 0;

  // ── Budget sub-component ─────────────────────────────────────
  function BudgetView() {
    if (!budget) return (
      <div className="pip-empty" style={{ color: "var(--danger)" }}>
        <WarnIcon />Impossible de charger le budget.<br />Vérifiez que l'API tourne sur {API_BASE}
      </div>
    );
    const { summary, transactions } = budget;
    const totalAlloue  = summary.reduce((s, r) => s + (r.budget_alloue || 0), 0);
    const totalDepense = summary.reduce((s, r) => s + (r.cout_total    || 0), 0);
    const totalSolde   = totalAlloue - totalDepense;
    const pct    = totalAlloue > 0 ? (totalDepense / totalAlloue * 100) : 0;
    const fillCls = pct > 90 ? "danger" : pct > 70 ? "warn" : "";
    return (
      <>
        <div>
          <div className="pip-section-title">Vue globale</div>
          <div className="pip-cards">
            {[
              { label: "Budget total", val: `${(totalAlloue/1000).toFixed(0)}k DZD`,  cls: "" },
              { label: "Dépensé",      val: `${(totalDepense/1000).toFixed(1)}k DZD`, cls: "amber" },
              { label: "Solde",        val: `${(totalSolde/1000).toFixed(1)}k DZD`,   cls: totalSolde < 0 ? "red" : "green" },
              { label: "Transactions", val: transactions.length, cls: "" },
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
                const p  = r.budget_alloue > 0 ? (r.cout_total / r.budget_alloue * 100) : 0;
                const fc = p > 90 ? "danger" : p > 70 ? "warn" : "";
                return (
                  <tr key={i}>
                    <td>{r.pipeline_id}</td><td>{r.periode}</td>
                    <td>{Number(r.budget_alloue).toLocaleString("fr")}</td>
                    <td>{Number(r.cout_total).toLocaleString("fr")}</td>
                    <td style={{ color: r.solde < 0 ? "var(--danger)" : "var(--accent)" }}>{Number(r.solde).toLocaleString("fr")}</td>
                    <td>
                      <div>{p.toFixed(1)}%</div>
                      <div className="pip-bar"><div className={`pip-bar-fill ${fc}`} style={{ width: `${Math.min(p,100)}%` }} /></div>
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
                  <td>{t.station_id}</td><td>{t.type_mesure}</td>
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
        <span className="pip-sub">Algeria O&amp;G Monitoring</span>
        <div className="pip-hstatus">
          <div className="pip-dot" />
          <span>simulator running</span>
          <div className="pip-divider" />
          <span style={{ fontFamily: "var(--mono)" }}>{critAlertCount} alertes critiques</span>
          <div className="pip-divider" />
        </div>
      </header>

      {/* NAV */}
      <nav className="pip-nav">
        <div className="pip-nav-label">Navigation</div>
        {[
          { id: "chat",   label: "Assistant IA",  icon: <ChatIcon /> },
          { id: "alerts", label: "Alertes",        icon: <BellIcon />, badge: totalAlertCount },
          { id: "budget", label: "Budget & Coûts", icon: <ChartIcon /> },
        ].map(n => (
          <button
            key={n.id}
            className={`pip-nav-btn ${page === n.id ? "active" : ""}`}
            onClick={() => setPage(n.id)}
          >
            {n.icon} {n.label}
            {n.badge !== undefined && n.badge > 0 && (
              <span className="pip-badge">{n.badge}</span>
            )}
          </button>
        ))}
      </nav>

      {/* MAIN */}
      <main className="pip-main">

        {/* ── CHAT PAGE ──────────────────────────────────────── */}
        <div className={`pip-page ${page === "chat" ? "active" : ""}`}>
          <div className="pip-chat-msgs" ref={msgsRef}>
            {messages.length === 0 && (
              <div className="pip-welcome">
                <div className="pip-welcome-icon">
                  <BulbIcon />
                </div>
                <h2>Pipeline AI Assistant</h2>
                <p>
                  Posez vos questions sur le monitoring, les alertes, les machines
                  ou les coûts. L'assistant consulte la base de données en temps réel
                  via les outils MCP et répond avec des tableaux et analyses détaillées.
                </p>

                <div className="pip-welcome-note">Les réponses incluent tableaux, tendances et recommandations</div>
                <div className="pip-chips">
                  {QUICK_CHIPS.map(c => (
                    <div key={c} className="pip-chip" onClick={() => sendMessage(c)}>{c}</div>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`pip-msg ${m.role}`}>
                <div className="pip-msg-av">{m.role === "user" ? "YOU" : "✦"}</div>
                <div className="pip-msg-bubble">
                  {m.text === null
                    ? <div className="pip-thinking"><span /><span /><span /></div>
                    : m.text.startsWith("ERROR:")
                      ? <span style={{ color: "var(--danger)" }}>{m.text.slice(6)}</span>
                      : <MarkdownMessage text={m.text} />
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

        {/* ── ALERTS PAGE ────────────────────────────────────── */}
        <div className={`pip-page ${page === "alerts" ? "active" : ""}`}>
          <div className="pip-page-hdr">
            <div>
              <div className="pip-page-title">Alertes système</div>
              <div className="pip-page-sub">
                {alerts === null
                  ? "Erreur de chargement"
                  : Array.isArray(alerts) && alerts.length
                    ? `${alerts.length} alertes — màj ${new Date().toLocaleTimeString("fr")}`
                    : "Chargement..."}
              </div>
            </div>
            <button className="pip-refresh-btn" onClick={loadAlerts}><RefreshIcon /> Actualiser</button>
          </div>

          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="pip-alert-stats">
              {[
                { val: alerts.length, lbl: "Total",       cls: "" },
                { val: critCount,     lbl: "Critiques",   cls: "red" },
                { val: avertCount,    lbl: "Avert.",       cls: "amber" },
                { val: resolueCount,  lbl: "Résolues",    cls: "green" },
                { val: p1Count,       lbl: "Pipeline P1", cls: "blue" },
                { val: p2Count,       lbl: "Pipeline P2", cls: "amber" },
              ].map((s, i, arr) => (
                <>
                  <div className="pip-astat" key={s.lbl}>
                    <div className={`pip-astat-val ${s.cls}`}>{s.val}</div>
                    <div className="pip-astat-lbl">{s.lbl}</div>
                  </div>
                  {i < arr.length - 1 && <div className="pip-astat-sep" key={`sep-${i}`} />}
                </>
              ))}
            </div>
          )}

          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="pip-filter-bar">
              {[
                { id: "all",           label: `Toutes (${alerts.length})`,      cls: "active-all"  },
                { id: "critique",      label: `Critiques (${critCount})`,        cls: "active-crit" },
                { id: "avertissement", label: `Avertissements (${avertCount})`,  cls: "active-warn" },
                { id: "P1",            label: `P1 – Alger→Oran (${p1Count})`,   cls: "active-p1"   },
                { id: "P2",            label: `P2 – HM→Ouargla (${p2Count})`,   cls: "active-p2"   },
              ].map(f => (
                <button
                  key={f.id}
                  className={`pip-filter-btn ${alertFilter === f.id ? f.cls : ""}`}
                  onClick={() => setAlertFilter(f.id)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}

          <div className="pip-alerts-list">
            {alerts === null ? (
              <div className="pip-empty" style={{ color: "var(--danger)" }}>
                <WarnIcon />Impossible de charger. Vérifiez l'API sur {API_BASE}
              </div>
            ) : !Array.isArray(alerts) || alerts.length === 0 ? (
              <div className="pip-empty"><OkIcon /> Aucune alerte</div>
            ) : filteredAlerts.length === 0 ? (
              <div className="pip-empty"><OkIcon /> Aucune alerte dans cette catégorie</div>
            ) : filteredAlerts.map((a, i) => {
              const cls  = (a.type_alerte || "").toLowerCase();
              const meta = getSensorMeta(a.capteur_id);
              const val  = Number(a.valeur);
              return (
                <div key={i} className={`pip-alert-item ${cls}`}>
                  <div className={`pip-adot ${cls}`} />
                  <div className="pip-abody">
                    <div className="pip-atop">
                      <span className="pip-asensor">{a.capteur_id}</span>
                      <span className={`pip-atype ${cls}`}>{a.type_alerte}</span>
                    </div>
                    {meta && (
                      <div className="pip-ameta">
                        <span className={`pip-apipeline ${meta.pipeline}`}>
                          <PipeIcon /> {meta.pipeline}
                        </span>
                        <span className="pip-aloc">
                          <MapPinIcon /> {meta.station}
                        </span>
                        <span className="pip-ameastype">{meta.type}</span>
                      </div>
                    )}
                    <div className="pip-amsg">{buildAlertMessage(a)}</div>
                    <div className="pip-atime">{fmtTs(a.timestamp)}</div>
                  </div>
                  <div className="pip-aval-block">
                    <div className="pip-aval">{isNaN(val) ? "—" : val.toFixed(2)}</div>
                    {meta && <div className="pip-aunit">{meta.unit}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── BUDGET PAGE ────────────────────────────────────── */}
        <div className={`pip-page ${page === "budget" ? "active" : ""}`}>
          <div className="pip-page-hdr">
            <div>
              <div className="pip-page-title">Budget & Coûts</div>
              <div className="pip-page-sub">Suivi des transactions et consommation budgétaire</div>
            </div>
            <button className="pip-dl-btn" onClick={downloadXLSX}>
              <DownloadIcon /> Télécharger XLSX
            </button>
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

      </main>

      {/* RIGHT PANEL — Live alerts */}
      <aside className="pip-aside">
        <div className="pip-panel-hdr">
          <span className="pip-panel-title">Alertes en direct</span>
          <span className="pip-live-tag"><div className="pip-dot" /> LIVE</span>
        </div>
        <div className="pip-panel-list">
          {panelAlerts.length === 0 ? (
            <div className="pip-empty"><OkIcon />En attente d'alertes...</div>
          ) : panelAlerts.map((a, i) => {
            const meta = getSensorMeta(a.capteur_id);
            const val  = Number(a.valeur);
            const cls  = (a.type_alerte || "").toLowerCase();
            return (
              <div key={a.alerte_id || i} className={`pip-palert ${cls}`}>
                <div className="pip-palert-top">
                  <span className="pip-palert-sensor">{a.capteur_id}</span>
                  <span className="pip-palert-time">{fmtTime(a.timestamp)}</span>
                </div>
                {meta && (
                  <div className="pip-palert-loc">
                    <MapPinIcon /> {meta.station}
                  </div>
                )}
                <div className="pip-palert-msg">
                  {cls === "avertissement" ? "Valeur proche du seuil" : "Seuil dépassé"}
                </div>
                <div className="pip-palert-val">
                  {isNaN(val) ? "—" : val.toFixed(2)}{meta ? ` ${meta.unit}` : ""}
                </div>
                {meta && (
                  <div className="pip-palert-tags">
                    <span className={`pip-ptag ${meta.pipeline}`}>{meta.pipeline}</span>
                    <span className="pip-ptag type">{meta.type}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

    </div>
  );
}