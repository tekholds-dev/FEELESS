import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Ic3, Ic3Text } from '../../lib/icon3d';
import '../../styles/deskShell.css';

// 🖥 ONE DESKTOP SHELL (owner 2026-11-04: "the same as the general agent gets"): every agent's desktop and the owner's two are built from these pieces.

// 🌌 A live wall: one small shader, drawn at a third of the screen's size and 24 fps. It stops when hidden or off-screen and holds one frame under fx-lite or reduced motion.
const MOODS = {
  agent: { a: [0.012, 0.05, 0.03], b: [0.03, 0.27, 0.155], c: [0.08, 0.82, 0.42], hex: 0 },
  fee: { a: [0.035, 0.018, 0.085], b: [0.2, 0.09, 0.5], c: [0.7, 0.53, 1], hex: 0 },
  colony: { a: [0.06, 0.032, 0.01], b: [0.3, 0.165, 0.02], c: [1, 0.71, 0.28], hex: 1 },
};
const VERT = 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
const FRAG = `precision mediump float;uniform float t;uniform vec2 r;uniform vec3 a,b,c;uniform float h;
void main(){vec2 u=gl_FragCoord.xy/r;vec2 p=u*vec2(r.x/r.y,1.)*2.4;
float w=sin(p.x*1.1+t*.13)+sin(p.y*1.3-t*.1)+sin((p.x+p.y)*.8+t*.07);
vec2 q=p+.35*vec2(sin(p.y*1.7+t*.11+w),cos(p.x*1.4-t*.09+w));
float f=.5+.5*sin(q.x*1.3+q.y*1.1+w);float g=.5+.5*sin(q.y*2.1-q.x*.7-t*.12);
vec3 col=mix(a,b,smoothstep(.1,.9,f));col=mix(col,c,pow(g,2.)*.5);
float ribbon=pow(max(0.,1.-abs(sin(q.x*.9+q.y*.6+w*.5+t*.05)-.2)),10.);col+=c*ribbon*.55;
vec2 sg=floor(p*22.);vec2 sf=fract(p*22.)-.5;float sn=fract(sin(dot(sg,vec2(12.9,78.2)))*43758.5);
if(sn>.965){float tw=.5+.5*sin(t*(1.+sn*3.)+sn*40.);col+=mix(c,vec3(1.),.6)*tw*smoothstep(.16,.0,length(sf))*.85;}
col*=.5+.5*(1.-smoothstep(.1,1.35,length(u-vec2(.62,.68))));
if(h>.5){vec2 s=vec2(1.,1.732);vec2 hp=p*5.;vec2 ha=mod(hp,s)-s*.5;vec2 hb=mod(hp-s*.5,s)-s*.5;vec2 g2=dot(ha,ha)<dot(hb,hb)?ha:hb;vec2 id=hp-g2;
float e=max(abs(g2.x),dot(abs(g2),normalize(s)));float pu=pow(.5+.5*sin(id.x*1.7+id.y*2.3+t*.6),12.);
col+=c*(smoothstep(.43,.49,e)*.2+pu*.16*(1.-e*1.6));}
gl_FragColor=vec4(col,1.);}`;

function still() {
  return document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

export function ShaderWall({ mood = 'agent', className = '' }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current; const gl = cv?.getContext?.('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' });
    if (!gl) return undefined;
    const sh = (kind, src) => { const s = gl.createShader(kind); gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FRAG)); gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) return undefined;
    gl.useProgram(pr); gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer()); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const at = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(at); gl.vertexAttribPointer(at, 2, gl.FLOAT, false, 0, 0);
    const m = MOODS[mood] || MOODS.agent; const U = n => gl.getUniformLocation(pr, n);
    gl.uniform3fv(U('a'), m.a); gl.uniform3fv(U('b'), m.b); gl.uniform3fv(U('c'), m.c); gl.uniform1f(U('h'), m.hex);
    const uT = U('t'); const uR = U('r'); let raf = 0; let last = 0; let seen = true;
    const size = () => { const w = Math.max(64, Math.round(cv.clientWidth / 3)); const h = Math.max(64, Math.round(cv.clientHeight / 3)); if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; } gl.viewport(0, 0, w, h); gl.uniform2f(uR, w, h); };   // set every frame: a second run on the same canvas has a new program with no size yet
    const draw = now => { size(); gl.uniform1f(uT, now / 1000 + 40); gl.drawArrays(gl.TRIANGLES, 0, 3); };
    const tick = now => { raf = 0; if (document.hidden || !seen) return; if (now - last >= 41) { last = now; draw(now); } if (!still()) raf = requestAnimationFrame(tick); };
    const go = () => { if (!raf && !document.hidden && seen) raf = requestAnimationFrame(tick); };
    const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(es => { seen = es[0].isIntersecting; go(); }) : null; io?.observe(cv);
    const lost = () => { cv.style.opacity = '0'; };   // the browser took the context back: the gradient under it stays
    cv.addEventListener('webglcontextlost', lost);
    cv.style.opacity = '1'; draw(0); go(); document.addEventListener('visibilitychange', go);
    return () => { cancelAnimationFrame(raf); io?.disconnect(); document.removeEventListener('visibilitychange', go); cv.removeEventListener('webglcontextlost', lost); };
  }, [mood]);
  return <canvas ref={ref} className={`dsw ${className}`.trim()} aria-hidden="true" data-mood={mood} />;
}

// 🧭 an icon nobody has moved takes the first free slot, a new column once the screen is full: a saved layout from before a new icon existed can never stack two on one spot
export function placeFor(keys, saved, height) {
  const rows = Math.max(3, Math.floor((height - 110) / 96)); const taken = Object.values(saved); let n = 0;
  const hits = p => taken.some(q => Math.abs(q.x - p.x) < 84 && Math.abs(q.y - p.y) < 84);   // a dragged icon sits off the grid: anything touching it counts as taken
  const free = () => { for (;;) { const p = { x: Math.floor(n / rows) * 96, y: (n % rows) * 96 }; n += 1; if (!hits(p)) { taken.push(p); return p; } } };
  return Object.fromEntries(keys.map(k => [k, saved[k] || free()]));
}

// 📉 the PoP folder's face: drawn candles breathing under a light sweep; an open PoP adds its live paper return
function PopFolderArt() {
  return <svg className="dsk-pop-art" viewBox="0 0 40 26"><g>{[[5, 12, 8, 1], [13, 8, 10, 0], [21, 10, 9, 1], [29, 4, 14, 1]].map(([x, y, h, up], i) => <g key={x} className="dsk-pop-c" style={{ '--i': i }}><line x1={x + 2} x2={x + 2} y1={y - 3} y2={y + h + 2} className="dsk-pop-w" /><rect x={x} y={y} width="4" height={h} rx="1" className={up ? 'is-up' : 'is-dn'} /></g>)}</g><rect className="dsk-pop-sweep" x="-14" y="0" width="10" height="26" /></svg>;
}
// 🖱 desktop icons you can drag anywhere (positions kept on this device); a tap without a drag opens it
export function DeskIcon({ k, ic, label, at, onMove, onOpen, tip, badge = null, testid }) {
  const g = useRef(null); const dragged = useRef(false);
  const down = e => { if (e.button !== 0) return; dragged.current = false; g.current = { x: e.clientX, y: e.clientY, ox: at.x, oy: at.y }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { const d = g.current; if (!d) return; const dx = e.clientX - d.x, dy = e.clientY - d.y; if (Math.abs(dx) + Math.abs(dy) > 4) dragged.current = true; if (dragged.current) onMove(k, { x: Math.max(0, d.ox + dx), y: Math.max(0, d.oy + dy) }); };
  return <button type="button" className={`dsk-ico is-${k}`} style={{ transform: `translate(${at.x}px, ${at.y}px)` }} onPointerDown={down} onPointerMove={move} onPointerUp={() => { g.current = null; }}
    onClick={() => { if (!dragged.current) onOpen(k); dragged.current = false; }} data-tip={tip} data-testid={testid || `dsk-${k === 'vault' ? 'vault' : `ico-${k}`}`}>
    <i className="dsk-ico-art" aria-hidden="true">{k === 'pop' ? <PopFolderArt /> : <em><Ic3 e={ic} size="30px" /></em>}{badge ? <b className={`dsk-pop-roe m-num ${badge.up ? 'is-up' : 'is-dn'}`}>{badge.text}</b> : null}</i><span>{label}</span></button>;
}

export function DeskWin({ k, title, s, top, set, onTop, onClose, tools, children }) {
  const drag = useRef(null);
  const down = e => { onTop(); if (s.max || e.button !== 0 || e.target.closest('button, a')) return; drag.current = { x: e.clientX - s.x, y: e.clientY - s.y }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { if (drag.current) set(k, { x: e.clientX - drag.current.x, y: Math.max(0, e.clientY - drag.current.y) }); };
  return <section className={`dsk-win${s.max ? ' is-max' : ''}${top ? ' is-top' : ''}`} style={s.max ? undefined : { transform: `translate(${s.x}px, ${s.y}px)`, '--wx': `${s.x}px`, '--wy': `${s.y}px` }} onPointerDown={onTop} aria-label={title} data-testid={`dsk-win-${k}`}>
    <header className="dsk-title" onPointerDown={down} onPointerMove={move} onPointerUp={() => { drag.current = null; }} onDoubleClick={() => set(k, { max: !s.max })}>
      <span className="dsk-dots"><button type="button" className="is-x" onClick={onClose} aria-label={`Close ${title}`} data-tip="Close" />
        <button type="button" className="is-min" onClick={() => set(k, { min: true })} aria-label={`Minimize ${title}`} data-tip="Minimize — it waits in the taskbar" data-testid={`dsk-min-${k}`} />
        <button type="button" className="is-max" onClick={() => set(k, { max: !s.max })} aria-label={s.max ? 'Restore' : 'Maximize'} data-tip={s.max ? 'Restore' : 'Maximize'} /></span>
      <b><Ic3Text text={title} /></b><span className="dsk-tools">{tools}</span></header>
    <div className="dsk-body">{children}</div></section>;
}

// 📈 What an agent's filed proofs did. Each proof kind keeps its own unit and is never added to another: real SOL, paper %, free chips.
const UNITS = { pow: { label: 'PoW', unit: 'SOL', tip: 'Real trades, at pool prices. Fees are on the receipt, not here', fmt: v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(4)}` }, pop: { label: 'PoP', unit: '% paper', tip: 'Paper trades on true prices. Each return added up', fmt: v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}` }, pob: { label: 'PoB', unit: 'free chips', tip: 'Free chips on the bid board', fmt: v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(0)}` } };
export function perfSeries(d) {
  const by = rows => rows.filter(r => Number.isFinite(r.v)).sort((a, b) => a.at - b.at);
  return {
    pow: by((d?.powFolders || []).filter(f => f.pnlSol != null).map(f => ({ at: Number(f.soldAt || f.at) || 0, v: Number(f.pnlSol), name: f.name || 'PoW', sub: f.sym ? `$${f.sym}` : '' }))),
    pop: by((d?.popFolders || []).filter(f => f.roePct != null && !f.noTrade).map(f => ({ at: Number(f.closedAt || f.at) || 0, v: Number(f.roePct), name: f.n ? `PoP #${f.n}` : 'PoP', sub: f.market || '' }))),
    pob: by((d?.pobFolders || []).filter(f => f.net != null && f.status === 'closed').map(f => ({ at: Number(f.closedAt || f.at) || 0, v: Number(f.net), name: f.n ? `PoB #${f.n}` : 'PoB', sub: f.q || '' }))),
  };
}
const running = rows => { let s = 0; return rows.map(r => { s += r.v; return { ...r, sum: s }; }); };
function sparkPath(vals, w, h) {
  if (vals.length < 2) return '';
  const lo = Math.min(0, ...vals); const hi = Math.max(0, ...vals); const span = hi - lo || 1;
  return vals.map((v, i) => `${i ? 'L' : 'M'}${((i / (vals.length - 1)) * w).toFixed(1)} ${(h - ((v - lo) / span) * h).toFixed(1)}`).join(' ');
}

// 🫧 the small glass on a desktop. Tap it for the chart.
export function PerfGlass({ title, value, sub, tone = '', vals = [], onOpen, testid = 'perf-glass', style }) {
  const up = tone === 'up'; const path = useMemo(() => sparkPath(vals, 120, 34), [vals]);
  const Tag = onOpen ? 'button' : 'span'; const act = onOpen ? { type: 'button', onClick: onOpen, 'data-tip': 'Open its performance chart' } : {};
  return <Tag className="pfg" style={style} {...act} data-testid={testid}>
    <span className="pfg-top"><em>{title}</em><i aria-hidden="true" /></span>
    <b className={`m-num ${tone === 'up' ? 'is-up' : tone === 'dn' ? 'is-dn' : ''}`} key={value}>{value}</b>
    <small className="m-num">{sub}</small>
    {path ? <svg viewBox="-2 -2 124 38" aria-hidden="true" preserveAspectRatio="none"><path d={path} fill="none" stroke={up || tone === '' ? '#45e486' : '#ff8fa3'} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" /></svg> : <svg viewBox="0 0 124 38" aria-hidden="true"><path d="M0 19H124" stroke="#ffffff2e" strokeDasharray="3 5" /></svg>}
  </Tag>;
}
export function glassOf(s) {
  const k = s.pow.length ? 'pow' : s.pop.length ? 'pop' : s.pob.length ? 'pob' : 'pow'; const rows = running(s[k]); const u = UNITS[k]; const end = rows.length ? rows[rows.length - 1].sum : 0;
  const won = s[k].filter(r => r.v > 0).length;
  return { title: `${u.label} RESULT`, value: rows.length ? `${u.fmt(end)} ${u.unit}` : 'No results yet', sub: rows.length ? `${won} of ${rows.length} won` : 'File a proof to start', tone: !rows.length ? '' : end >= 0 ? 'up' : 'dn', vals: rows.map(r => r.sum) };
}

const CW = 640; const CH = 210; const PAD = { l: 8, r: 8, t: 12, b: 20 };
function when(at) { return at ? new Date(at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''; }
function LineChart({ rows, u }) {
  const [hover, setHover] = useState(null); const box = useRef(null);
  const vals = rows.map(r => r.sum); const lo = Math.min(0, ...vals); const hi = Math.max(0, ...vals); const span = hi - lo || 1;
  const X = i => PAD.l + (rows.length > 1 ? (i / (rows.length - 1)) * (CW - PAD.l - PAD.r) : (CW - PAD.l - PAD.r) / 2);
  const Y = v => PAD.t + (1 - (v - lo) / span) * (CH - PAD.t - PAD.b);
  const line = rows.map((r, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(r.sum).toFixed(1)}`).join(' ');
  const onMove = e => { const b = box.current.getBoundingClientRect(); const fx = ((e.clientX - b.left) / b.width) * CW; const i = rows.length > 1 ? Math.round(((fx - PAD.l) / (CW - PAD.l - PAD.r)) * (rows.length - 1)) : 0; setHover(Math.max(0, Math.min(rows.length - 1, i))); };
  const h = hover != null ? rows[hover] : null;
  return <div className="pfd-plot" ref={box} onPointerMove={onMove} onPointerLeave={() => setHover(null)} data-testid="pfd-line">
    <svg viewBox={`0 0 ${CW} ${CH}`} role="img" aria-label={`Running total, ${u.unit}`}>
      <line x1={PAD.l} x2={CW - PAD.r} y1={Y(0)} y2={Y(0)} className="pfd-zero" />
      <path className="pfd-line" d={line} pathLength="1" />
      {h ? <><line x1={X(hover)} x2={X(hover)} y1={PAD.t} y2={CH - PAD.b} className="pfd-cross" /><circle cx={X(hover)} cy={Y(h.sum)} r="5" className="pfd-dot" /></> : null}
      <text x={PAD.l} y={CH - 5} className="pfd-axis">{when(rows[0]?.at)}</text><text x={CW - PAD.r} y={CH - 5} textAnchor="end" className="pfd-axis">{when(rows[rows.length - 1]?.at)}</text>
    </svg>
    {h ? <div className="pfd-tip" style={{ left: `${Math.min(70, (X(hover) / CW) * 100)}%` }} role="status" data-testid="pfd-tip"><b>{h.name}</b>{h.sub ? <small>{h.sub}</small> : null}<span className="m-num">{u.fmt(h.v)} {u.unit}</span><em className="m-num">total {u.fmt(h.sum)}</em></div> : null}
  </div>;
}
export function PerfDiagram({ series }) {
  const firstKey = series.pow.length ? 'pow' : series.pop.length ? 'pop' : series.pob.length ? 'pob' : 'pow';
  const [k, setK] = useState(firstKey); const [view, setView] = useState('chart'); const u = UNITS[k]; const rows = running(series[k]);
  const won = rows.filter(r => r.v > 0).length; const end = rows.length ? rows[rows.length - 1].sum : 0; const most = Math.max(1e-9, ...rows.map(r => Math.abs(r.v)));
  return <div className="pfd" data-testid="perf-diagram">
    <div className="pfd-bar"><div className="m-seg" role="group" aria-label="Which proofs">{Object.entries(UNITS).map(([x, v]) => <button key={x} type="button" className={k === x ? 'active' : ''} aria-pressed={k === x} onClick={() => setK(x)} data-tip={v.tip} data-testid={`pfd-k-${x}`}>{v.label} <small className="m-num">{series[x].length}</small></button>)}</div>
      <div className="m-seg" role="group" aria-label="View">{[['chart', 'Chart'], ['table', 'Table']].map(([v, l]) => <button key={v} type="button" className={view === v ? 'active' : ''} aria-pressed={view === v} onClick={() => setView(v)} data-testid={`pfd-v-${v}`}>{l}</button>)}</div></div>
    <div className="pfd-kpis"><span><em>TOTAL</em><b className={`m-num ${end > 0 ? 'is-up' : end < 0 ? 'is-dn' : ''}`}>{rows.length ? `${u.fmt(end)} ${u.unit}` : '—'}</b></span><span><em>WON</em><b className="m-num">{rows.length ? `${won} of ${rows.length}` : '—'}</b></span><span><em>BEST</em><b className="m-num">{rows.length ? u.fmt(Math.max(...rows.map(r => r.v))) : '—'}</b></span><span><em>WORST</em><b className="m-num">{rows.length ? u.fmt(Math.min(...rows.map(r => r.v))) : '—'}</b></span></div>
    {!rows.length ? <p className="pfd-empty" data-testid="pfd-empty">No {u.label} has a result yet.</p> : view === 'table'
      ? <div className="pfd-table"><table data-testid="pfd-table"><thead><tr><th>Proof</th><th>Date</th><th className="is-n">{u.unit}</th><th className="is-n">Total</th></tr></thead><tbody>{rows.map((r, i) => <tr key={`${r.at}${i}`}><td>{r.name}{r.sub ? <small> {r.sub}</small> : null}</td><td>{when(r.at)}</td><td className="is-n m-num">{u.fmt(r.v)}</td><td className="is-n m-num">{u.fmt(r.sum)}</td></tr>)}</tbody></table></div>
      : <><LineChart key={k} rows={rows} u={u} />
        <ul className="pfd-bars" aria-label="Each proof" data-testid="pfd-bars">{rows.slice(-24).map((r, i) => <li key={`${r.at}${i}`} className={r.v >= 0 ? 'is-up' : 'is-dn'} style={{ '--i': i, '--v': Math.max(0.05, Math.abs(r.v) / most) }} data-tip={`${r.name}: ${u.fmt(r.v)} ${u.unit}`} tabIndex={0}><i /></li>)}</ul></>}
  </div>;
}

// Each agent side by side, for the Agents desktop: their own numbers, in SOL only.
export function AgentsDiagram({ agents = [] }) {
  const most = Math.max(1e-9, ...agents.map(a => Math.abs(Number(a.pnlSol) || 0)));
  return <div className="pfd" data-testid="agents-diagram">
    {!agents.length ? <p className="pfd-empty">No agents yet.</p> : <ul className="pfa">{agents.map((a, i) => { const v = Number(a.pnlSol) || 0; return <li key={a.id} style={{ '--i': i, '--v': v ? Math.max(0.02, Math.abs(v) / most) : 0 }} className={v >= 0 ? 'is-up' : 'is-dn'}>
      <b>{a.name}</b><small>{a.kind === 'general' ? 'General' : 'Trader'} · {a.proofs} proofs · won {a.won} of {a.trades}</small><u aria-hidden="true"><i /></u><em className="m-num">{v ? `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(4)} SOL` : 'No result yet'}</em></li>; })}</ul>}
  </div>;
}

// 🖥 A desktop from a list of apps. Used by the owner's Agents desktop; AgentDesktop adds its Vault and live window around the same pieces.
export function AppDesktop({ id, title, sub, mood = 'agent', apps, glass, onClose }) {
  const keys = apps.map(a => a.k);
  const [w, setW] = useState(() => Object.fromEntries(apps.map((a, i) => [a.k, { open: false, min: false, max: false, x: 140 + i * 16, y: 34 + i * 12 }])));
  const [top, setTop] = useState(''); const [now, setNow] = useState(Date.now());
  const [pos, setPos] = useState(() => { let s = {}; try { s = JSON.parse(localStorage.getItem(`feeless.dsk.icons.${id}`) || '{}') || {}; } catch { /* private window */ } return placeFor(keys, s, window.innerHeight); });
  const moveIcon = (k, p) => setPos(x => { const n = { ...x, [k]: p }; try { localStorage.setItem(`feeless.dsk.icons.${id}`, JSON.stringify(n)); } catch { /* private window */ } return n; });
  const set = useCallback((k, p) => setW(x => ({ ...x, [k]: { ...x[k], ...p } })), []);
  const open = k => { set(k, { open: true, min: false }); setTop(k); };
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(t); }, []);
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  const tasks = apps.filter(a => w[a.k]?.open);
  return createPortal(<div className="dsk dsk-app" role="dialog" aria-modal="true" aria-label={title} data-testid={`dsk-app-${id}`}>
    <ShaderWall mood={mood} />
    <div className="dsk-wall" aria-hidden="true"><b>{title}</b><small>{sub}</small></div>
    <nav className="dsk-icons" aria-label="Desktop">{apps.map(a => <DeskIcon key={a.k} k={a.k} ic={a.ic} label={a.label} at={pos[a.k]} onMove={moveIcon} onOpen={open} tip={a.tip} badge={a.badge} testid={`app-ico-${a.k}`} />)}</nav>
    {glass ? <PerfGlass {...glass} onOpen={() => open(glass.app)} /> : null}
    {apps.map(a => (w[a.k]?.open && !w[a.k].min ? <DeskWin key={a.k} k={a.k} title={`${a.ic} ${a.label}`} s={w[a.k]} top={top === a.k} set={set} onTop={() => setTop(a.k)} onClose={() => set(a.k, { open: false })}>{a.body}</DeskWin> : null))}
    <footer className="dsk-bar"><span className="dsk-start"><i aria-hidden="true" />FEELESS</span>
      {tasks.map(a => <button key={a.k} type="button" className={`dsk-task${!w[a.k].min && top === a.k ? ' is-on' : ''}`} onClick={() => { if (w[a.k].min || top !== a.k) { set(a.k, { min: false }); setTop(a.k); } else set(a.k, { min: true }); }} data-testid={`dsk-task-${a.k}`}><Ic3 e={a.ic} /> {a.label}</button>)}
      <time className="m-num">{new Date(now).toTimeString().slice(0, 5)}</time>
      <button type="button" className="m-btn dsk-exit" onClick={onClose} data-tip="Back (Esc)" data-testid="dsk-app-close">Exit desktop</button></footer>
  </div>, document.body);
}
