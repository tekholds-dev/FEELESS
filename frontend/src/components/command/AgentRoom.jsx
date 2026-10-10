import React, { Suspense, lazy, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import '../../styles/agentRoom.css';

// 🏢 THE AGENT OFFICE (owner, 2026-10-09: "real cartoon robots and places, looks like a game but it isn't one — an actual animated office with
// robots working on real tasks"). One SVG scene, everything on it is the last REAL pass of the desk:
//   · four robots at their desks (Tally → Sherlock → Trigger → Devil), each typing at the speed of its REAL work this pass (its ms), its
//     speech bubble = its live task, its monitor = its real output (Tally's bars = coins it read, green / pink by 5-min move · Sherlock's
//     screen = the reasons it weighed most · Trigger's scope = its real ENTER calls · Devil's docket = its real verdicts)
//   · the pneumatic tube carries this pass's real coins desk to desk as paper slips, stamped by how they ended (🟢 GO · ✕ objected · ⏳ · ⛔);
//     GO slips land in the "→ YOUR CARD" tray, objections in the shredder
//   · status is on the robot: ⚠ probation = amber antenna + a sweat drop · ☠ scrap = red antenna, X eyes, flicker
//   · the wall board = the pass: coins read, GO, market temperature, when
// Click a robot → its task, ACTUAL rules (served from the code), last rulings, record, history, inherited lesson. Pop out = full screen.
// Transform + opacity only; `.agr` is an fxPause surface; fx-lite / reduced motion freeze the motion (the data stays).
const Office3D = lazy(() => import('./AgentOffice3D'));   // 🧊 the real 3D office (own chunk: three.js never ships in the app bundle)
// WebGL here? (jsdom / no GPU → the SVG office below stands in)
export const has3D = () => { try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); } catch (e) { return false; } };
export const AGENTS = [['tally', '📊', 'Tally', 'numbers'], ['sherlock', '🔍', 'Sherlock', 'why'], ['trigger', '⏱', 'Trigger', 'when'], ['devil', '⚖', 'Devil', 'argues']];
export const packetsOf = table => (table || []).slice(0, 8).map(x => ({ k: x.mint, sym: x.symbol,
  end: x.go ? 'go' : x.trigger?.[0] === 'enter' ? 'obj' : x.trigger?.[0] === 'skip' ? 'skip' : 'wait' }));
const END = { go: '🟢', obj: '✕', wait: '⏳', skip: '⛔' };
const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - t)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
// a typing speed for each robot: more real ms this pass → busier hands, bounded so it never strobes
export const spinSec = ms => Math.max(1.2, Math.min(8, 8 - Math.log10(1 + Math.max(0, Number(ms) || 0)) * 3));
// SVG text via createElement, never JSX children: the dev server's visual-edits plugin wraps a JSX `{expr}` in a <span>, which SVG can't draw
const T = ({ s, ...p }) => React.createElement('text', p, String(s ?? ''));
const cut = (s, n) => { const t = String(s || ''); return t.length > n ? `${t.slice(0, n - 1)}…` : t; };
// what each monitor shows — straight from the pass (pure, tested)
export const screensOf = d => { const t = d?.table || []; const freq = {};
  t.forEach(x => (x.why?.drivers || []).slice(0, 3).forEach(dd => { freq[dd[2]] = (freq[dd[2]] || 0) + 1; }));
  const enters = t.filter(x => x.trigger?.[0] === 'enter');
  return { bars: t.slice(0, 10).map(x => ({ k: x.mint, v: Number(x.nums?.d5) || 0 })), tags: Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 3),
    enters: enters.length, waits: t.filter(x => x.trigger?.[0] === 'wait').length,
    verdicts: enters.slice(0, 3).map(x => ({ sym: x.symbol, ok: x.devil?.[0] === 'agree', go: x.go })), go: t.filter(x => x.go).length, n: t.length }; };

const COL = { tally: ['#1fd178', '#0e7a46'], sherlock: ['#a07bff', '#5a3fb0'], trigger: ['#f5c451', '#a87b12'], devil: ['#ff6b86', '#a8263f'] };
const X = [128, 376, 624, 872];   // desk centres across the 1000-wide office

function Screen({ k, s }) {   // a 64 × 42 monitor face
  if (k === 'tally') return <g>{s.bars.map((b, i) => { const h = Math.max(2, Math.min(30, Math.abs(b.v) * 3));
    return <rect key={b.k || i} x={4 + i * 5.8} y={36 - h} width="4" height={h} rx="1" className={b.v >= 0 ? 'agr-up' : 'agr-dn'} />; })}
    <T x="4" y="8" className="agr-scr-t" s={(s.n) + ' READ'} /></g>;
  if (k === 'sherlock') return <g><text x="4" y="9" className="agr-scr-t">WHY</text>{s.tags.map(([w, n], i) => <T key={w} x="4" y={19 + i * 9} className="agr-scr-s" s={(cut(w, 11)) + ' ×' + (n)} />)}
    {!s.tags.length && <text x="4" y="22" className="agr-scr-s">no clues</text>}</g>;
  if (k === 'trigger') return <g><circle cx="20" cy="22" r="12" className="agr-scope" /><path d="M20 6v32M4 22h32" className="agr-scope" />
    <circle cx="20" cy="22" r="3" className={s.enters ? 'agr-up' : 'agr-dim'} /><T x="38" y="18" className="agr-scr-b" s={(s.enters)} /><text x="38" y="28" className="agr-scr-s">ENTER</text></g>;
  return <g><text x="4" y="9" className="agr-scr-t">DOCKET</text>{s.verdicts.map((v, i) => <T key={v.sym + i} x="4" y={19 + i * 9} className={`agr-scr-s ${v.ok ? 'is-ok' : 'is-no'}`} s={(v.ok ? (v.go ? '● GO' : '✓') : '✕') + ' $' + (cut(v.sym, 7))} />)}
    {!s.verdicts.length && <text x="4" y="22" className="agr-scr-s">nothing to argue</text>}</g>;
}

function Robot({ k, i, d, s, sel, onPick }) {
  const l = d?.life?.[k] || {}; const st = l.status || 'alive'; const [c1, c2] = COL[k]; const ms = d?.perf?.[k];
  const task = cut((d?.tasks?.[k] || 'waiting for the first pass').split(' · ')[0], 30); const name = AGENTS[i][2];
  const pick = () => onPick(k);
  return <g className={`agr-st is-${k} is-${st} ${sel ? 'is-sel' : ''}`} transform={`translate(${X[i]} 268)`} style={{ '--spin': `${spinSec(ms)}s`, '--x': i }}
    role="button" tabIndex={0} aria-pressed={sel} aria-label={`${name}: ${d?.tasks?.[k] || ''}`} data-testid={`agr-st-${k}`}
    onClick={pick} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), pick())}>
    <ellipse cx="0" cy="118" rx="104" ry="14" className="agr-shadow" />
    {sel && <ellipse cx="-22" cy="112" rx="58" ry="10" className="agr-selring" />}
    {/* chair */}<rect x="-58" y="-6" width="72" height="84" rx="14" className="agr-chair" />
    <g className="agr-bot">
      <g className="agr-bob">
        <line x1="-22" y1="-70" x2="-22" y2="-56" className="agr-ant-l" /><circle cx="-22" cy="-74" r="5.5" className={`agr-ant is-${st}`} />
        <rect x="-52" y="-56" width="60" height="46" rx="15" fill={c1} stroke={c2} strokeWidth="2.5" />
        {k === 'sherlock' && <path d="M-56 -48 Q-22 -78 12 -48 Z M-22 -63 l-8 -10 h16 Z" className="agr-hat" />}
        {k === 'devil' && <path d="M-48 -50 l-6 -16 l14 10 Z M4 -50 l6 -16 l-14 10 Z" className="agr-horn" />}
        {k === 'trigger' && <path d="M-56 -34 a34 34 0 0 1 68 0" className="agr-headset" />}
        <rect x="-45" y="-47" width="46" height="26" rx="10" className="agr-visor" />
        {st === 'scrap' ? <g className="agr-xeyes"><path d="M-35 -39l8 8M-27 -39l-8 8M-17 -39l8 8M-9 -39l-8 8" /></g>
          : <g className="agr-eyes"><circle cx="-31" cy="-35" r="4.5" /><circle cx="-13" cy="-35" r="4.5" /></g>}
        {k === 'tally' && <g className="agr-specs"><circle cx="-31" cy="-35" r="7.5" /><circle cx="-13" cy="-35" r="7.5" /><path d="M-23.5 -35h3" /></g>}
        <path d={st === 'alive' ? 'M-30 -18 q8 6 16 0' : 'M-30 -14 q8 -6 16 0'} className="agr-mouth" />
        {st === 'probation' && <path d="M10 -46 q-5 8 0 11 q5 -3 0 -11 Z" className="agr-sweat" />}
      </g>
      <rect x="-30" y="-8" width="16" height="8" fill={c2} />
      <rect x="-50" y="-2" width="56" height="50" rx="13" fill={c1} stroke={c2} strokeWidth="2.5" />
      <rect x="-36" y="10" width="28" height="16" rx="4" className="agr-chest" /><circle cx="-22" cy="18" r="3.5" className="agr-chestlight" />
      <g className="agr-arm is-l"><rect x="-62" y="2" width="12" height="40" rx="6" fill={c1} stroke={c2} strokeWidth="2" /></g>
      <g className="agr-arm is-r"><rect x="6" y="2" width="12" height="40" rx="6" fill={c1} stroke={c2} strokeWidth="2" />
        {k === 'sherlock' && <g className="agr-glass"><circle cx="22" cy="46" r="8" /><path d="M16 52 l-8 8" /></g>}
        {k === 'devil' && <g className="agr-gavel"><rect x="14" y="36" width="18" height="9" rx="2" /><path d="M23 45v14" /></g>}</g>
    </g>
    {/* desk + keyboard + monitor */}
    <rect x="-96" y="44" width="192" height="13" rx="4" className="agr-desk-top" />
    <rect x="-90" y="57" width="180" height="56" rx="4" className="agr-desk" />
    <rect x="-46" y="38" width="44" height="7" rx="2" className="agr-kbd" />
    <g transform="translate(18 -14)"><rect x="-4" y="-4" width="72" height="50" rx="6" className="agr-mon" />
      <rect x="0" y="0" width="64" height="42" rx="3" className="agr-scr" /><Screen k={k} s={s} /><rect x="0" y="0" width="64" height="42" rx="3" className="agr-scan" />
      <rect x="28" y="46" width="8" height="12" className="agr-mon" /></g>
    <g className="agr-plate"><rect x="-60" y="74" width="120" height="22" rx="5" /><T x="0" y="89" textAnchor="middle" s={(name.toUpperCase()) + ' · GEN ' + (l.gen || 1) + (st === 'probation' ? ' ⚠' : st === 'scrap' ? ' ☠' : '')} /></g>
    {/* speech bubble = its live task (pops in fresh each pass) */}
    <g className="agr-say" key={d?.perf?.at || 0}><rect x="-104" y="-122" width="208" height="30" rx="12" /><path d="M-30 -92 l6 10 l6 -10 Z" />
      <T x="0" y="-102" textAnchor="middle" s={(task)} /></g>
  </g>;
}

export function AgentDetail({ d, agent }) {
  const card = (d?.agents || []).find(a => a.key === agent) || {}; const life = d?.life?.[agent] || {};
  const lines = (d?.thoughts || []).filter(l => l.who === agent).slice(0, 6);
  return <div className="agr-detail" data-testid={`agr-detail-${agent}`}>
    <b>{card.icon} {card.name} <small>gen {life.gen || 1} · {life.status || 'alive'} · {d?.perf?.[agent] != null ? `${d.perf[agent]} ms this pass` : '—'}</small></b>
    <p className="agr-now">⚙ {d?.tasks?.[agent] || 'waiting for the first pass'}</p>
    <h6>📏 RULES IT RUNS ON (from the code)</h6><ul>{(d?.rules?.[agent] || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
    <h6>🗯 LAST RULINGS</h6><ul>{lines.length ? lines.map((l, i) => <li key={i}><small>{ago(l.at)}</small> {l.text}</li>) : <li className="m-dim">nothing said yet</li>}</ul>
    <h6>📈 RECORD · this life</h6><p>{card.n ? `${card.n} judged · ${card.med >= 0 ? '+' : ''}${card.med}% typical${card.right != null ? ` · ${card.right}% right` : ''}` : 'no judged calls yet'}</p>
    <Spark hist={d?.hist} agent={agent} />
    {(d?.lessons?.[agent]?.words || []).length > 0 && <><h6>🧬 CARRIES FROM ITS LAST LIFE</h6><p>{d.lessons[agent].words.join(' · ')}</p></>}
  </div>;
}
function Spark({ hist, agent }) {
  const pts = (hist || []).map(h => h[agent]).filter(Boolean).map(h => (h.right != null ? Number(h.right) : h.med != null ? 50 + Number(h.med) * 5 : null)).filter(v => v != null);
  if (pts.length < 2) return <small className="m-dim">history fills in every 30 min</small>;
  const w = 220, h = 44; const lo = Math.min(...pts, 40), hi = Math.max(...pts, 60); const y50 = h - ((50 - lo) / Math.max(1, hi - lo)) * h;
  const xy = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${h - ((v - lo) / Math.max(1, hi - lo)) * h}`).join(' ');
  return <svg className="agr-spark" viewBox={`0 0 ${w} ${h}`} data-testid={`spark-${agent}`}><line x1="0" x2={w} y1={y50} y2={y50} className="agr-spark-mid" /><polyline points={xy} /></svg>;
}

function Office({ d, sel, setSel }) {
  const s = screensOf(d); const pk = packetsOf(d?.table); const at = d?.perf?.at || 0; const rg = d?.perf?.regime || {};
  return <svg className="agr-office" viewBox="0 0 1000 420" role="group" aria-label="The agent office">
    <defs>
      <linearGradient id="agrWall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0d1f2e" /><stop offset="1" stopColor="#132a24" /></linearGradient>
      <linearGradient id="agrFloor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1a2b3a" /><stop offset="1" stopColor="#0b1520" /></linearGradient>
      <linearGradient id="agrSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1b1446" /><stop offset="1" stopColor="#7a3a7a" /></linearGradient>
    </defs>
    <rect x="0" y="0" width="1000" height="250" fill="url(#agrWall)" className="agr-wall" />
    {[70, 760].map((wx, wi) => <g key={wx} transform={`translate(${wx} 26)`}><rect width="170" height="96" rx="6" fill="url(#agrSky)" className="agr-win" />
      {[[8, 50, 22], [34, 34, 18], [56, 58, 26], [86, 40, 20], [110, 28, 24], [138, 52, 22]].map(([bx, by, bw], j) => <rect key={j} x={bx} y={by} width={bw} height={96 - by} className="agr-city" />)}
      {[0, 1, 2, 3, 4, 5].map(j => <rect key={j} x={14 + j * 26} y={62 + (j % 3) * 8} width="3" height="3" className="agr-lit" style={{ '--i': j + wi * 3 }} />)}
      <path d="M85 0v96M0 48h170" className="agr-frame" /></g>)}
    {/* the wall board = the pass */}
    <g transform="translate(320 18)" className="agr-board" data-testid="agr-board"><rect width="360" height="84" rx="10" />
      <T x="180" y="24" textAnchor="middle" className="agr-board-h" s={'🤖 THE AGENT DESK · ' + (at ? `pass ${ago(at)} ago` : 'starting')} />
      <T x="22" y="54" className="agr-board-n" s={(s.n)} /><text x="22" y="72" className="agr-board-l">COINS READ</text>
      <T x="140" y="54" className="agr-board-n is-go" s={(s.go)} /><text x="140" y="72" className="agr-board-l">GO</text>
      <T x="220" y="54" className={`agr-board-n is-${rg.word || 'unknown'}`} s={(rg.green != null ? `${rg.green}%` : '—')} /><T x="220" y="72" className="agr-board-l" s={'GREEN · ' + (String(rg.word || 'unknown').toUpperCase())} />
      <circle cx="338" cy="20" r="5" className="agr-rec" /></g>
    {/* plant + water cooler, for the humans that never come */}
    <g transform="translate(18 170)"><rect x="6" y="40" width="26" height="32" rx="4" className="agr-pot" /><path d="M19 42 q-18 -30 -6 -48 M19 42 q14 -28 4 -44 M19 42 q2 -30 0 -50" className="agr-leaf" /></g>
    <rect x="0" y="244" width="1000" height="176" fill="url(#agrFloor)" />
    {[0, 1, 2, 3, 4, 5, 6, 7, 8].map(j => <path key={j} d={`M${-200 + j * 175} 420 L${300 + j * 50} 246`} className="agr-tile" />)}
    {[290, 330, 380].map(y => <path key={y} d={`M0 ${y}H1000`} className="agr-tile" />)}
    {/* the pneumatic tube: real coins travel desk to desk */}
    <path d="M60 126 H955" className="agr-tube" /><path d="M60 126 H955" className="agr-tube-in" />
    {X.map(x => <path key={x} d={`M${x + 50} 126 V232`} className="agr-tube is-drop" />)}
    <g className="agr-slips" key={`p${at}`} aria-hidden>{pk.map((p, i) => <g key={p.k} className={`agr-slip is-${p.end}`} style={{ '--i': i }}>
      <rect x="40" y="116" width="78" height="20" rx="4" /><T x="79" y="130" textAnchor="middle" s={(END[p.end]) + ' $' + (cut(p.sym, 8))} /></g>)}</g>
    <g transform="translate(948 138)"><rect x="-26" y="0" width="44" height="26" rx="4" className="agr-tray" /><text x="-4" y="17" textAnchor="middle" className="agr-tray-t">→ CARD</text>
      <rect x="-24" y="34" width="40" height="40" rx="5" className="agr-bin" /><text x="-4" y="58" textAnchor="middle" className="agr-tray-t">✂</text></g>
    {AGENTS.map(([k], i) => <Robot key={k} k={k} i={i} d={d} s={s} sel={sel === k} onPick={setSel} />)}
  </svg>;
}

export function AgentRoom({ d }) {
  const [sel, setSel] = useState('tally'); const [pop, setPop] = useState(false);
  useEffect(() => { if (!pop) return undefined; const k = e => e.key === 'Escape' && setPop(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [pop]);
  const at = d?.perf?.at || 0; const [gl] = useState(has3D);
  const room = big => <div className={`agr ${big ? 'is-big' : ''}`} data-testid={big ? 'agr-pop' : 'agr'}>
    <div className="agr-stage">{gl ? <Suspense fallback={<div className="agr3 is-boot">booting the office…</div>}><Office3D d={d} sel={sel} setSel={setSel} paused={!big && pop} /></Suspense> : <Office d={d} sel={sel} setSel={setSel} />}
      {gl && <div className="m-seg agr-who" role="group" aria-label="Pick a robot">{AGENTS.map(([k, ic, name]) => <button key={k} type="button" className={sel === k ? 'active' : ''} onClick={() => setSel(k)} data-testid={`agr-pick-${k}`}>{ic} {name}</button>)}</div>}</div>
    <AgentDetail d={d} agent={sel} />
  </div>;
  return <section className="agr-wrap" data-testid="agent-room"><div className="agr-head"><b>🏢 THE AGENT OFFICE · live</b><small>last pass {at ? `${ago(at)} ago` : '—'} · tap a robot</small>
    <button type="button" className="m-btn agr-out" onClick={() => setPop(true)} data-testid="agr-popout">⤢ Pop out</button></div>
    {room(false)}
    {pop && createPortal(<div className="agr-shade" onClick={e => e.target === e.currentTarget && setPop(false)} role="dialog" aria-label="The agent office">
      <div className="agr-modal"><button type="button" className="agr-x" onClick={() => setPop(false)} aria-label="Close" data-testid="agr-close">✕</button>{room(true)}</div></div>, document.body)}
  </section>;
}
