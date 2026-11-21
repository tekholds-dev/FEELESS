import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Ic3, IconLook } from '../../lib/icon3d';
import '../../styles/deskLook.css';

// 🖥 THE DESK LOOK (owner 2026-11-20, on the manager's preview v4 — docs/design/agent-desk-approved.html: "OMG!! YES make this the default look for
// Fee, agents and Collective"). One screen: a slim glass bar · [icon rail | widgets · two monitors on stands · vitals · the file cabinet | chat],
// over a background layer. This file is only the shell: every number, row and file comes in from the desk that uses it (real data or "empty").

const LOOK_KEY = 'feeless.deskLook';
export const DESK_BGS = [['smoke', 'Smoke'], ['aurora', 'Aurora'], ['grid', 'Grid'], ['film', 'Film'], ['none', 'Plain']];
export const DESK_THEMES = [['dark', 'Black'], ['light', 'White']];
const DEFAULT_LOOK = { theme: 'dark', bg: 'smoke', classic: false };
export function readDeskLook() { try { return { ...DEFAULT_LOOK, ...JSON.parse(localStorage.getItem(LOOK_KEY) || '{}') }; } catch { return DEFAULT_LOOK; } }
/** → [look, set]: Black / White, the background and the classic-desktop switch, kept for this user on this device. One event keeps every open desk in step. */
export function useDeskLook() {
  const [look, setLook] = useState(readDeskLook);
  useEffect(() => { const on = () => setLook(readDeskLook()); window.addEventListener('feeless:desk-look', on); return () => window.removeEventListener('feeless:desk-look', on); }, []);
  const set = useCallback(patch => { const n = { ...readDeskLook(), ...patch }; try { localStorage.setItem(LOOK_KEY, JSON.stringify(n)); } catch { /* private window: this visit only */ } setLook(n); window.dispatchEvent(new Event('feeless:desk-look')); }, []);
  return [look, set];
}
const calm = () => typeof document !== 'undefined' && (document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches);

// ── value noise for the smoke: slow domain-warped wisps drawn tiny (160×96) and blurred up by CSS. A still fine grain sits over it (never TV static).
const P = (() => { const p = [...Array(256).keys()]; let s = 7; for (let i = 255; i > 0; i -= 1) { s = (s * 16807) % 2147483647; const j = s % (i + 1); [p[i], p[j]] = [p[j], p[i]]; } const o = new Uint8Array(512); for (let i = 0; i < 512; i += 1) o[i] = p[i & 255]; return o; })();
const fade = t => t * t * (3 - 2 * t); const lerp = (a, b, t) => a + (b - a) * t;
function n3(x, y, z) {
  const X = Math.floor(x) & 255; const Y = Math.floor(y) & 255; const Z = Math.floor(z) & 255; x -= Math.floor(x); y -= Math.floor(y); z -= Math.floor(z);
  const u = fade(x); const v = fade(y); const w = fade(z); const h = (a, b, c) => P[P[P[a] + b] + c] / 255;
  return lerp(lerp(lerp(h(X, Y, Z), h(X + 1, Y, Z), u), lerp(h(X, Y + 1, Z), h(X + 1, Y + 1, Z), u), v), lerp(lerp(h(X, Y, Z + 1), h(X + 1, Y, Z + 1), u), lerp(h(X, Y + 1, Z + 1), h(X + 1, Y + 1, Z + 1), u), v), w);
}
export function fbm(x, y, z) { let a = 0; let f = 1; let s = 0.5; for (let o = 0; o < 4; o += 1) { a += s * n3(x * f, y * f, z * f); f *= 2.03; s *= 0.5; } return a; }
const SW = 160; const SH = 96;
function Smoke({ light }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current; const x = c?.getContext?.('2d'); if (!x) return undefined;
    c.width = SW; c.height = SH; const img = x.createImageData(SW, SH); const rgb = light ? [20, 28, 24] : [232, 240, 236];
    const draw = t => { const d = img.data; t *= 0.35;
      for (let y = 0; y < SH; y += 1) for (let X = 0; X < SW; X += 1) { const nx = X / SW * 2.4; const ny = y / SH * 1.5;
        const q = fbm(nx + t * 0.06, ny + t * 0.02, t * 0.05); const v = fbm(nx + q * 2.2 - t * 0.03, ny + q * 1.6 + t * 0.01, t * 0.04);
        let m = Math.max(0, Math.min(1, (v - 0.36) * 3)); m = m * m * (3 - 2 * m); const fall = 0.45 + 0.55 * ((y / SH) ** 1.2); const i = (y * SW + X) * 4;
        d[i] = rgb[0]; d[i + 1] = rgb[1]; d[i + 2] = rgb[2]; d[i + 3] = m * fall * (light ? 90 : 185); }
      x.putImageData(img, 0, 0); };
    draw(3); if (calm()) return undefined;   // fx-lite / reduced motion: one still frame
    let raf = 0; let last = 0; const loop = ts => { raf = requestAnimationFrame(loop); if (document.hidden || ts - last < 66) return; last = ts; draw(ts / 1000); };
    raf = requestAnimationFrame(loop); return () => cancelAnimationFrame(raf);
  }, [light]);
  return <canvas ref={ref} className="dkl-smoke" data-testid="dkl-smoke" />;
}
let GRAIN = '';
function grainUrl() {
  if (GRAIN || typeof document === 'undefined') return GRAIN;
  try { const c = document.createElement('canvas'); c.width = 180; c.height = 180; const x = c.getContext('2d'); if (!x) return ''; const im = x.createImageData(180, 180); const d = im.data;
    let s = 3; const r = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    for (let i = 0; i < d.length; i += 4) { const v = 128 + (r() + r() + r() - 1.5) * 70; d[i] = v; d[i + 1] = v; d[i + 2] = v; d[i + 3] = 255; }
    x.putImageData(im, 0, 0); GRAIN = c.toDataURL(); } catch { GRAIN = ''; }
  return GRAIN;
}
/** The full-page background layer: Smoke, Aurora, Grid, Film or Plain. Transform / opacity only; under fx-lite the smoke holds one frame. */
export function DeskBackdrop({ bg = 'smoke', light = false }) {
  const g = useMemo(grainUrl, []);
  return <div className="dkl-bg" aria-hidden="true" data-bg={bg} data-testid="dkl-bg">
    {bg === 'smoke' ? <Smoke light={light} /> : null}
    {bg === 'aurora' ? <div className="dkl-aurora" /> : null}
    {bg === 'grid' ? <div className="dkl-grid" /> : null}
    <div className="dkl-vignette" />
    {bg === 'smoke' || bg === 'film' ? <div className={`dkl-grain${bg === 'film' ? ' is-film' : ''}`} style={g ? { backgroundImage: `url(${g})` } : undefined} /> : null}
  </div>;
}

// ── small live visuals
/** A sparkline of real points (oldest → newest). Fewer than 2 points draws nothing. Pure SVG, no animation. */
export function Spark({ vals = [], tone = '' }) {
  const pts = (vals || []).map(Number).filter(Number.isFinite); if (pts.length < 2) return <span className="dkl-spark is-none" aria-hidden="true" />;
  const lo = Math.min(...pts); const hi = Math.max(...pts); const span = hi - lo || 1;
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${(i / (pts.length - 1) * 100).toFixed(2)},${(18 - (v - lo) / span * 16 - 1).toFixed(2)}`).join('');
  return <svg className={`dkl-spark${tone ? ` is-${tone}` : ''}`} viewBox="0 0 100 18" preserveAspectRatio="none" aria-hidden="true"><path className="a" d={`${d}L100,18L0,18Z`} /><path className="l" d={d} /></svg>;
}
/** A 0–1 meter. null = no number yet (an empty track, never a made-up fill). */
export function Meter({ v, tone = '' }) {
  const n = v == null || !Number.isFinite(Number(v)) ? null : Math.max(0, Math.min(1, Number(v)));
  return <div className={`dkl-meter${tone ? ` is-${tone}` : ''}${n == null ? ' is-none' : ''}`} aria-hidden="true"><i style={{ transform: `scaleX(${n ?? 0})` }} /></div>;
}
export function Chip({ tone = '', children, tip, testid }) { return <span className={`dkl-chip${tone ? ` is-${tone}` : ''}`} data-tip={tip} data-testid={testid}>{children}</span>; }

// ── click effects: press-down scale is CSS; primary buttons (.dkl-go / .m-go / [data-ripple]) get a ripple at the pointer. One listener per desk.
export function useRipple(ref) {
  useEffect(() => {
    const el = ref.current; if (!el) return undefined;
    const on = e => { const b = e.target.closest?.('.dkl-go, .m-go, [data-ripple]'); if (!b || !el.contains(b) || calm()) return;
      const r = b.getBoundingClientRect(); const s = document.createElement('i'); s.className = 'dkl-ripple'; s.setAttribute('aria-hidden', 'true');
      const size = Math.max(r.width, r.height) * 2; s.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - r.left - size / 2}px;top:${e.clientY - r.top - size / 2}px`;
      if (getComputedStyle(b).position === 'static') b.style.position = 'relative'; b.style.overflow = 'hidden'; b.appendChild(s); setTimeout(() => s.remove(), 560); };
    el.addEventListener('pointerdown', on); return () => el.removeEventListener('pointerdown', on);
  }, [ref]);
}

// ── the file cabinet: drawers with label slots and pulls; the open drawer slides out over a tray of hanging files (or its own panel)
/** drawers: [{ k, e, label, n, lock, files: [{ tab, title, sub, st, onOpen }], body }] */
export function DeskCabinet({ title, who, drawers = [], open: openIn = null, total = null, id = 'desk' }) {
  const key = `feeless.deskCab.${id}`;
  const [open, setOpen] = useState(() => { try { return localStorage.getItem(key) || ''; } catch { return ''; } });
  useEffect(() => { if (openIn?.key) setOpen(openIn.key); }, [openIn?.key, openIn?.at]);   // eslint-disable-line react-hooks/exhaustive-deps
  const cur = drawers.find(x => x.k === open) || drawers[0]; const pick = k => { setOpen(k); try { localStorage.setItem(key, k); } catch { /* this visit only */ } };
  const sum = total ?? drawers.reduce((n, x) => n + (Number(x.n) || 0), 0);
  return <section className="dkl-cab dkl-glass" aria-label="File cabinet" data-testid="dkl-cab">
    <header className="dkl-cab-h"><span className="dkl-k">{title || 'File cabinet'}</span>{who ? <b>{who}</b> : null}<span className="dkl-sp" /><Chip testid="dkl-cab-sum">{Number(sum).toLocaleString()} files</Chip></header>
    <div className="dkl-drawers" role="group" aria-label="Drawers" style={{ '--n': Math.max(1, Math.min(drawers.length, 8)) }}>
      {drawers.map(x => <button key={x.k} type="button" className={`dkl-drawer${x.lock ? ' is-lock' : ''}`} aria-expanded={cur?.k === x.k} onClick={() => pick(x.k)} data-tip={x.tip || x.label} data-testid={`dkl-drawer-${x.k}`}>
        <span className="dkl-slot">{x.e || x.icon ? <Ic3 e={x.e} name={x.icon} size="14px" /> : null}{x.label} <b className="m-num">{Number(x.n || 0).toLocaleString()}</b></span><span className="dkl-pull" /></button>)}
    </div>
    {cur ? <div key={cur.k} className={`dkl-tray${cur.body ? ' is-panel' : ''}`} data-testid={`dkl-tray-${cur.k}`}>
      {cur.body ? cur.body : (cur.files || []).length ? <div className="dkl-hang">{cur.files.map((f, i) => { const Tag = f.onOpen ? 'button' : 'div';
        return <Tag key={`${f.title}-${i}`} {...(f.onOpen ? { type: 'button', onClick: f.onOpen } : {})} className="dkl-file" data-tab={f.tab || ''} style={{ '--i': i }} data-testid={`dkl-file-${cur.k}-${i}`}>
          <span className={`dkl-st${f.st ? ` is-${f.st}` : ''}`} /><b>{f.title}</b>{f.sub ? <small>{f.sub}</small> : null}</Tag>; })}</div>
        : <p className="dkl-empty">{cur.empty || 'Nothing in this drawer yet.'}</p>}
    </div> : null}
  </section>;
}

// ── one monitor on its stand
export function Monitor({ k, kind, title, chips = [], children, onPop, testid }) {
  return <div className="dkl-mon-wrap"><article className="dkl-mon dkl-glass" aria-label={title || kind} data-testid={testid || `dkl-mon-${k}`}>
    <header className="dkl-mon-h">{kind ? <span className="dkl-k">{kind}</span> : null}<span className="dkl-t">{title}</span><span className="dkl-sp" />
      {chips.map((c, i) => <Chip key={i} tone={c.tone}>{c.text}</Chip>)}
      {onPop ? <button type="button" className="dkl-ib" onClick={onPop} aria-label="Pop out" data-tip="Open it in a window" data-testid={`dkl-mon-pop-${k}`}>↗</button> : null}</header>
    <div className="dkl-screen">{children}</div>
  </article><div className="dkl-stand" aria-hidden="true" /></div>;
}

/** The whole desk. Every piece is passed in; nothing here makes up a number. */
export function DeskLook({ id, name, crumb = 'Desk', agents = [], onAgent, pulse = [], rail = [], widgets = [], monitors = [], vitals = [], cabinet = null, chat = null, children = null, barEnd = null, testid = 'dkl', mobileTabs = true }) {
  const [look, setLook] = useDeskLook(); const ref = useRef(null); useRipple(ref);
  const light = look.theme === 'light';
  const [pane, setPane] = useState('desk');   // 📱 a phone shows one part at a time: the desk (monitors swipe), the chat, or the cabinet
  return <IconLook.Provider value="3d"><div ref={ref} className="dkl" data-desk={light ? 'light' : 'dark'} data-pane={pane} data-testid={testid} data-desk-id={id}>
    <DeskBackdrop bg={look.bg} light={light} />
    <div className="dkl-app">
      <header className="dkl-bar dkl-glass">
        <span className="dkl-mark"><i>F</i><span>FEELESS</span></span>
        <span className="dkl-crumb">{crumb} · <b>{name}</b></span>
        {agents.length > 1 ? <span className="dkl-agents" role="group" aria-label="Agent">{agents.map(a => <button key={a.id} type="button" aria-pressed={!!a.on} onClick={() => onAgent?.(a)} data-testid={`dkl-agent-${a.id}`}><span className={`dkl-dot${a.live ? '' : ' is-idle'}`} />{a.name}</button>)}</span> : null}
        <span className="dkl-sp" />
        <span className="dkl-pulse" data-testid="dkl-pulse">{pulse.map(p => <span key={p.k} data-tip={p.tip} data-testid={`dkl-pulse-${p.k}`}>{p.label} <b className="m-num">{p.value}</b>{p.delta ? <b className={`m-num ${p.up ? 'is-up' : 'is-dn'}`}> {p.delta}</b> : null}{p.of ? <small> / {p.of}</small> : null}</span>)}</span>
        <span className="dkl-seg" role="group" aria-label="Desk theme"><span className="dkl-lbl">Desk</span>{DESK_THEMES.map(([k, l]) => <button key={k} type="button" aria-pressed={look.theme === k} onClick={() => setLook({ theme: k })} data-testid={`dkl-theme-${k}`}>{l}</button>)}</span>
        <span className="dkl-seg dkl-bgs" role="group" aria-label="Background"><span className="dkl-lbl">BG</span>{DESK_BGS.map(([k, l]) => <button key={k} type="button" aria-pressed={look.bg === k} onClick={() => setLook({ bg: k })} data-testid={`dkl-bg-${k}`}>{l}</button>)}</span>
        {barEnd}
      </header>
      <div className="dkl-main">
        <nav className="dkl-rail dkl-glass" aria-label="Desk">{rail.map(r => (r.hr ? <hr key={r.k} /> : <button key={r.k} type="button" aria-current={r.current ? 'true' : undefined} onClick={r.onClick} aria-label={r.label} data-testid={`dkl-rail-${r.k}`}>
          <Ic3 e={r.e} name={r.icon} size="22px" />{r.badge ? <em className="m-num">{r.badge}</em> : null}<span className="dkl-tip">{r.label}</span></button>))}</nav>
        <section className="dkl-center">
          {widgets.length ? <div className="dkl-widgets" data-testid="dkl-widgets">{widgets.map((w, i) => { const Tag = w.onOpen ? 'button' : 'div';
            return <Tag key={w.k} {...(w.onOpen ? { type: 'button', onClick: w.onOpen } : {})} className={`dkl-wd dkl-glass${w.hot ? ' is-hot' : ''}`} style={{ '--i': i }} data-testid={`dkl-wd-${w.k}`}>
              <span className="dkl-wd-h"><span className="dkl-k">{w.title}</span><span className="dkl-sp" />{w.chip ? <Chip tone={w.chipTone}>{w.chip}</Chip> : null}</span>{w.body}</Tag>; })}</div> : null}
          {monitors.length ? <div className={`dkl-monitors is-${Math.min(2, monitors.length)}`} data-testid="dkl-monitors">{monitors.map(m => <Monitor key={m.k} {...m}>{m.body}</Monitor>)}</div> : null}
          {vitals.length ? <div className="dkl-vitals dkl-glass" aria-label="Vitals" data-testid="dkl-vitals" style={{ '--n': vitals.length }}>{vitals.map(v => <div key={v.k} className="dkl-vt" data-tip={v.tip} data-testid={`dkl-vt-${v.k}`}>
            <div className="dkl-k">{v.label}</div><div className="dkl-v"><b className="m-num">{v.value ?? '—'}</b>{v.unit ? <small className="m-num">{v.unit}</small> : null}</div>
            {v.spark ? <Spark vals={v.spark} tone={v.tone} /> : <Meter v={v.meter} tone={v.tone} />}</div>)}</div> : null}
          {cabinet}
        </section>
        {chat ? <aside className="dkl-chat dkl-glass" aria-label="Chat" data-testid="dkl-chat">{chat}</aside> : null}
      </div>
      {mobileTabs ? <nav className="dkl-tabs" aria-label="Desk parts">{[['desk', '🖥', 'Desk'], ['chat', '💬', 'Chat'], ['cab', '🗂', 'Cabinet']].map(([k, e, l]) => <button key={k} type="button" aria-pressed={pane === k} onClick={() => setPane(k)} data-testid={`dkl-tab-${k}`}><Ic3 e={e} size="18px" />{l}</button>)}</nav> : null}
    </div>
    {children}
  </div></IconLook.Provider>;
}

/** A panel that springs open over the desk (Motion), e.g. a tool or the proof picker. Esc closes it. */
export function DeskPop({ open, title, onClose, children, wide = false, testid = 'dkl-pop' }) {
  useEffect(() => { if (!open) return undefined; const k = e => { if (e.key === 'Escape') { e.stopPropagation(); onClose?.(); } }; window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [open, onClose]);
  const still = calm();
  return <AnimatePresence>{open ? <motion.div className="dkl-pop-veil" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: still ? 0 : 0.16 }}>
    <motion.section role="dialog" aria-label={title} className={`dkl-pop dkl-glass${wide ? ' is-wide' : ''}`} onClick={e => e.stopPropagation()} data-testid={testid}
      initial={still ? false : { opacity: 0, y: 12, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={still ? { opacity: 0 } : { opacity: 0, y: 8, scale: 0.98 }} transition={still ? { duration: 0 } : { type: 'spring', stiffness: 420, damping: 32 }}>
      <header className="dkl-pop-h"><b>{title}</b><span className="dkl-sp" /><button type="button" className="dkl-ib" onClick={onClose} aria-label="Close" data-testid={`${testid}-close`}>✕</button></header>
      <div className="dkl-pop-b">{children}</div>
    </motion.section></motion.div> : null}</AnimatePresence>;
}

// ── chat pieces shared by every desk chat
const pad = n => String(n).padStart(2, '0');
/** "14:05" today, "Nov 19 14:05" before. at = unix seconds. Pure (now injectable for tests). */
export function stamp(at, now = Date.now()) {
  const t = Number(at); if (!Number.isFinite(t) || t <= 0) return '';
  const d = new Date(t * 1000); const n = new Date(now); const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return d.toDateString() === n.toDateString() ? hm : `${d.toLocaleString('en-US', { month: 'short' })} ${d.getDate()} ${hm}`;
}
/** Safe little markdown → React: **bold**, *italic*, `code`, ```blocks```, [links](https://…), - lists. Never sets HTML. */
export function Md({ text }) {
  const blocks = String(text || '').split(/```/);
  return <>{blocks.map((b, i) => (i % 2 ? <pre key={i} className="dkl-code"><code>{b.replace(/^[a-z0-9]*\n/i, '')}</code></pre> : <MdText key={i} text={b} />))}</>;
}
function MdText({ text }) {
  const lines = text.split('\n'); const out = []; let list = [];
  const flush = k => { if (list.length) { out.push(<ul key={`u${k}`}>{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>); list = []; } };
  lines.forEach((l, i) => { const m = /^\s*[-*•]\s+(.*)$/.exec(l); if (m) { list.push(m[1]); return; } flush(i); if (l.trim()) out.push(<p key={i}>{inline(l)}</p>); });
  flush('end'); return <>{out}</>;
}
function inline(s) {
  const parts = []; const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|\[[^\]]+\]\(https?:\/\/[^)\s]+\))/g; let last = 0; let m; let k = 0;
  while ((m = re.exec(s))) { if (m.index > last) parts.push(s.slice(last, m.index)); const t = m[0];
    if (t.startsWith('**')) parts.push(<b key={k++}>{t.slice(2, -2)}</b>);
    else if (t.startsWith('`')) parts.push(<code key={k++}>{t.slice(1, -1)}</code>);
    else if (t.startsWith('[')) { const mm = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(t); parts.push(<a key={k++} href={mm[2]} target="_blank" rel="noopener noreferrer">{mm[1]}</a>); }
    else parts.push(<em key={k++}>{t.slice(1, -1)}</em>);
    last = m.index + t.length; }
  if (last < s.length) parts.push(s.slice(last)); return parts;
}

/** The image / video generation card: dot-grid shimmer + % while it runs, then a blur-to-sharp reveal with Regenerate / Use / Variations.
 *  md = a media row from the server ({ kind, status: queued|running|done|failed, model|label, usd, url, at, done, why }). Progress is the
 *  time it has run against what this model usually takes (never a fake 100%: it holds at 95% until the server says done). */
export function genPct(md, now = Date.now() / 1000) {
  if (!md) return 0; if (md.status === 'done') return 100; if (md.status === 'failed' || md.status === 'cancelled') return 0;
  const typical = md.kind === 'video' ? 90 : 14; const ran = Math.max(0, now - Number(md.at || now));
  return Math.min(95, Math.round(100 * (1 - Math.exp(-ran / typical))));
}
export function GenCard({ md, src, onCancel, onRegen, onUse, onVariations, useLabel = 'Use' }) {
  const [now, setNow] = useState(() => Date.now() / 1000); const running = md && (md.status === 'queued' || md.status === 'running');
  useEffect(() => { if (!running) return undefined; const t = setInterval(() => setNow(Date.now() / 1000), 500); return () => clearInterval(t); }, [running]);
  const pct = genPct(md, now); const done = md?.status === 'done' && src; const failed = md?.status === 'failed' || md?.status === 'cancelled';
  const stage = md?.status === 'queued' ? 'In the queue' : pct < 40 ? `Generating ${md?.kind === 'video' ? 'video' : 'image'}` : pct < 80 ? 'Adding detail' : 'Finishing up';
  const took = md?.doneAt && md?.at ? `${Math.max(0.1, Number(md.doneAt) - Number(md.at)).toFixed(1)} s` : '';
  return <div className="dkl-gen-wrap" data-testid="dkl-gen">
    <div className={`dkl-gen${done ? ' is-done' : ''}${failed ? ' is-failed' : ''}${md?.kind === 'video' ? ' is-video' : ''}`}>
      {done ? (md.kind === 'video' ? <video src={src} controls muted playsInline preload="metadata" /> : <img src={src} alt={md.prompt || 'Generated image'} loading="lazy" />) : null}
      {!done ? <><div className="dkl-dots is-base" /><div className="dkl-glow" /><div className="dkl-dots" /><div className="dkl-gbar" style={{ transform: `scaleX(${pct / 100})` }} /></> : null}
      <div className="dkl-glbl"><span className="dkl-pill">{running ? <span className="dkl-spin" /> : null}<span>{failed ? (md.why || 'It did not finish') : done ? (md.model || md.label || 'Done') : stage}</span></span><span className="dkl-sp" />
        <span className="dkl-pill m-num" data-testid="dkl-gen-pct">{done ? took || 'ready' : failed ? '—' : `${pct}%`}</span></div>
    </div>
    <div className="dkl-gen-act">
      <small className="m-num">{md?.model || md?.label || ''}{md?.usd != null ? ` · $${Number(md.usd).toFixed(2)}` : ''}</small><span className="dkl-sp" />
      {running && onCancel ? <button type="button" onClick={onCancel} data-testid="dkl-gen-cancel">Cancel</button> : null}
      {!running && onRegen ? <button type="button" onClick={onRegen} data-testid="dkl-gen-regen">Regenerate</button> : null}
      {done && onUse ? <button type="button" className="dkl-go" onClick={onUse} data-testid="dkl-gen-use">{useLabel}</button> : null}
      {done && onVariations ? <button type="button" onClick={onVariations} data-testid="dkl-gen-var">Variations</button> : null}
    </div>
  </div>;
}
