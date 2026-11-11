import { ProChart } from './ProChart';
import '../../styles/boosts.css';
import React, { createContext, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Ic3, Ic3Text } from '../../lib/icon3d';
import '../../styles/deskShell.css';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';

// 🖥 ONE DESKTOP SHELL (owner 2026-11-04: "the same as the general agent gets"): every agent's desktop and the owner's two are built from these pieces.

// Apps an agent's page hands to whichever desktop opens from it (its wallet, its limits).
export const DeskExtras = createContext([]);

// 💡 A lamp over its monitors: our own take on a conic lamp, drawn in CSS. Two light cones and a bar, opacity and transform only, in its accent colour.
// 💡 The lamp over its monitors (owner 2026-11-04): on while its agents work, out when they finish, and the tube catches static every 5, 23 and 45 seconds. Turning off is a last burst of static.
export function Lamp({ active = false }) {
  const [lit, setLit] = useState(active); const [zap, setZap] = useState(0);
  useEffect(() => {
    if (active) { setLit(true); setZap(n => n + 1); const t = [5000, 23000, 45000].map(ms => setInterval(() => { if (!document.hidden) setZap(n => n + 1); }, ms)); return () => t.forEach(clearInterval); }
    setZap(n => n + 1); const t = setTimeout(() => setLit(false), 650); return () => clearTimeout(t);
  }, [active]);
  return <div className={`lamp${lit ? ' is-on' : ''}${active ? '' : ' is-dying'}`} aria-hidden="true" data-testid="kd-lamp" data-on={lit ? '1' : '0'}>
    <div key={zap} className="lamp-zap"><div className="lamp-light"><i className="lamp-l" /><i className="lamp-r" /><u className="lamp-core" /><u className="lamp-hot" /></div><b className="lamp-bar" /></div></div>;
}

// 🧱 A folder's wall: big clickable vitals that fill whatever its list leaves empty, so no folder opens as a small box in a big window. Every number is the folder's own.
export function VitalsWall({ tiles, onCommand, onOpen, children }) {
  const [said, setSaid] = useState('');
  const hit = async t => {
    if (t.to) { onOpen?.(t.to); return; }
    if (!t.cmd) return;
    if (onCommand) { onCommand(t.cmd); setSaid(`“${t.cmd}” is in its chat box`); return; }
    try { await navigator.clipboard.writeText(t.cmd); setSaid(`Copied “${t.cmd}”. Paste it in its chat`); } catch { setSaid(`Type “${t.cmd}” in its chat`); }
  };
  return <div className="dfw" data-testid="dsk-wall"><div className="dfw-wall">{tiles.map((t, i) => { const can = t.to || t.cmd; const Tag = can ? 'button' : 'div'; return <Tag key={t.label} {...(can ? { type: 'button', onClick: () => hit(t) } : {})} className={`dfw-tile${can ? ' is-go' : ''}${t.tone ? ` is-${t.tone}` : ''}`} style={{ '--i': i }} data-tip={t.tip} data-testid={`dfw-${String(t.label).toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}>
      <i aria-hidden="true"><Ic3 e={t.ic} size="100%" /></i><b className="m-num">{t.value}</b><small>{t.label}</small>{can ? <em>{t.to ? 'Open' : 'Put in chat'}</em> : null}</Tag>; })}</div>
    {said ? <small className="dfw-said" role="status">{said}</small> : null}
    {children ? <div className="dfw-in">{children}</div> : null}</div>;
}

// 🚀 The dot on every Desktop button: how many setup asks are left. Lit until they are done. Only its owner gets a number from the server.
export function SetupDot({ id, left = null }) {
  const [n, setN] = useState(left);
  useEffect(() => { setN(left); }, [left]);
  useEffect(() => { const on = e => { if (e.detail?.id === id) setN(e.detail.left); }; window.addEventListener('feeless:setup-left', on); return () => window.removeEventListener('feeless:setup-left', on); }, [id]);
  return n > 0 ? <b className="dsk-lit m-num" data-tip={`${n} setup ask${n === 1 ? '' : 's'} left in its Manual folder`} data-testid="setup-dot">{n}</b> : null;
}

// 🎓 First time on a desktop: 12 steps that point at the real icons. Never opens an app or moves anything.
const TOUR_KEY = 'feeless.dsk.tour.v1';
export const TOUR = [
  { t: 'Its own computer', x: 'Every tool it has is a folder here. Drag them anywhere.', e: '🖥' },
  { at: 'perf-glass', t: 'Results at a glance', x: 'Tap this glass for the full chart of its proofs.', e: '📈' },
  { at: 'dsk-vault', t: 'The Vault', x: 'Logins, sign-ins and recovery files, sealed for this agent.', e: '🔐' },
  { at: 'dsk-ico-wallet', t: 'Fund it', x: 'Add SOL here. Keep site accounts funded from your own wallet: it is easier and costs less.', e: '👛' },
  { at: 'dsk-ico-limits', t: 'Your limits', x: 'What it may spend and trade. It can only ever trade less.', e: '🎚' },
  { at: 'dsk-ico-pow', t: 'PoW', x: 'Real research, a small real buy, a hold, a filed folder. Type a site at the top to use it first.', e: '⛏' },
  { at: 'dsk-ico-pop', t: 'PoP', x: 'Both minds call perps blind. It runs on paper at true prices.', e: '📉' },
  { at: 'dsk-ico-bids', t: 'PoB', x: 'Ask anything: "file a pob best NFL picks". It reads ESPN and others and keeps snapshots.', e: '🎲' },
  { at: 'dsk-ico-browser', t: 'Browser and Sources', x: 'Its browser. A tab inside shows every site it has used, and you can sign it in there.', e: '🌐' },
  { at: 'dsk-ico-browser', t: 'Its email', x: 'Also a tab in Browser: its own mailbox, so it can sign up and read its codes.', e: '📧' },
  { at: 'dsk-ico-manual', t: 'Commands', x: 'A tab in the Manual, with its terms and desktop settings: everything it understands.', e: '⌘' },
  { at: 'dsk-ico-manual', t: 'The Manual', x: 'How each part works, with this tour one click away.', e: '📖' },
];
export const tourSeen = () => { try { return !!localStorage.getItem(TOUR_KEY); } catch { return true; } };
export function DeskTour({ onDone }) {
  const [at, setAt] = useState(0); const [box, setBox] = useState(null); const s = TOUR[at];
  const done = useCallback(() => { try { localStorage.setItem(TOUR_KEY, '1'); } catch { /* private window */ } onDone(); }, [onDone]);
  useEffect(() => {
    const place = () => { const el = s.at ? document.querySelector(`[data-testid="${s.at}"]`) : null; const r = el?.getBoundingClientRect(); setBox(r && r.width ? { x: r.left - 6, y: r.top - 6, w: r.width + 12, h: r.height + 12 } : null); };
    place(); window.addEventListener('resize', place); return () => window.removeEventListener('resize', place);
  }, [s.at]);
  useEffect(() => { const k = e => { if (e.key === 'Escape') { e.stopPropagation(); done(); } else if (e.key === 'ArrowRight') setAt(n => Math.min(TOUR.length - 1, n + 1)); else if (e.key === 'ArrowLeft') setAt(n => Math.max(0, n - 1)); }; window.addEventListener('keydown', k, true); return () => window.removeEventListener('keydown', k, true); }, [done]);
  const W = 300; const vw = typeof window !== 'undefined' ? window.innerWidth : 1200; const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
  const card = box ? { left: Math.max(10, Math.min(vw - W - 10, box.x + box.w + 18 + W > vw ? box.x - W - 18 : box.x + box.w + 18)), top: Math.max(10, Math.min(vh - 250, box.y)) } : { left: Math.max(10, vw / 2 - W / 2), top: Math.max(10, vh / 2 - 120) };
  const last = at === TOUR.length - 1;
  return <div className="dtr" role="dialog" aria-modal="true" aria-label="Desktop tour" data-testid="desk-tour">
    {box ? <i className="dtr-ring" style={{ width: box.w, height: box.h, transform: `translate(${box.x}px, ${box.y}px)` }} aria-hidden="true" /> : <i className="dtr-veil" aria-hidden="true" />}
    <section key={at} className="dtr-card" style={{ ...card, width: Math.min(W, vw - 20) }}>
      <Ic3 e={s.e} size="54px" className="dtr-ic" /><em className="m-num">{at + 1} OF {TOUR.length}</em><b>{s.t}</b><p>{s.x}</p>
      <u className="dtr-bar" aria-hidden="true"><i style={{ transform: `scaleX(${(at + 1) / TOUR.length})` }} /></u>
      <span className="dtr-nav"><button type="button" className="m-btn" onClick={done} data-testid="tour-skip">Skip</button><span><button type="button" className="m-btn" disabled={!at} onClick={() => setAt(at - 1)} aria-label="Back" data-testid="tour-back">←</button>
        <button type="button" className="m-btn m-go" onClick={() => (last ? done() : setAt(at + 1))} data-testid="tour-next">{last ? 'Done' : 'Next'}</button></span></span></section></div>;
}

// 🌌 A live wall: one small shader, drawn at a third of the screen's size and 24 fps. It stops when hidden or off-screen and holds one frame under fx-lite or reduced motion.
const MOODS = {
  agent: { a: [0.012, 0.05, 0.03], b: [0.03, 0.27, 0.155], c: [0.08, 0.82, 0.42], hex: 0 },
  fee: { a: [0.035, 0.018, 0.085], b: [0.2, 0.09, 0.5], c: [0.7, 0.53, 1], hex: 0 },
  colony: { a: [0.012, 0.02, 0.07], b: [0.07, 0.13, 0.42], c: [0.42, 0.55, 1], hex: 0 },
  ember: { a: [0.07, 0.02, 0.012], b: [0.42, 0.12, 0.05], c: [1, 0.55, 0.2], hex: 0 },
  mono: { a: [0.03, 0.03, 0.035], b: [0.16, 0.16, 0.18], c: [0.72, 0.74, 0.8], hex: 0 },
  rose: { a: [0.07, 0.015, 0.05], b: [0.4, 0.08, 0.28], c: [1, 0.45, 0.72], hex: 0 },
};
export const WALLS = [['agent', 'Green', '#9b6bff'], ['colony', 'Blue', '#6b8cff'], ['fee', 'Violet', '#b388ff'], ['ember', 'Ember', '#ff8c33'], ['rose', 'Rose', '#ff73b8'], ['mono', 'Steel', '#b8bcc8']];
export const DESK_DEFAULTS = { wall: null, motion: 'full', light: 100, print: true, title: true, glass: true, iconSort: 'groups', iconFlow: 'columns', iconSide: 'left', iconSize: 'm', iconLabels: true, autoFit: false, hidden: [], winOpen: 'beside', clock: '24' };
const prefKey = id => `feeless.deskPrefs.${id}`;
export function useDeskPrefs(id) {
  const [p, setP] = useState(() => { try { return { ...DESK_DEFAULTS, ...JSON.parse(localStorage.getItem(prefKey(id)) || '{}') }; } catch { return DESK_DEFAULTS; } });
  const set = patch => setP(x => { const n = { ...x, ...patch }; try { localStorage.setItem(prefKey(id), JSON.stringify(n)); } catch { /* it still works for this visit */ } return n; });
  return [p, set];
}
// 🗂 Folders by what they are for. Each group starts its own column or row when you fit the desktop.
export const ICON_GROUPS = [['Proofs', ['pow', 'pop', 'bids', 'poc', 'postatic', 'poe', 'proofs', 'print']], ['Money', ['vault', 'wallet', 'boost', 'honey', 'limits']], ['Work', ['features', 'character', 'browser', 'sources', 'jobs', 'github', 'mail', 'minds', 'cmds']], ['Help', ['manual', 'terms', 'deskset']]];
const groupOf = k => { const i = ICON_GROUPS.findIndex(g => g[1].includes(k)); return i < 0 ? ICON_GROUPS.length : i; };
export const ICON_CELL = { s: 80, m: 96, l: 118 };
// 🧭 Every folder in its place, on this screen. Never overlaps, never runs off the edge: a full column or row wraps to the next one.
export function fitIcons(apps, o = {}, vw = 1280, vh = 800) {
  const cell = ICON_CELL[o.iconSize] || 96; const rows = o.iconFlow === 'rows'; const right = o.iconSide === 'right';
  const top = right && !rows ? 150 : 0; const maxMain = Math.max(2, Math.floor(((rows ? vw - 32 : vh - 110 - top)) / cell));   // the right side starts under its results glass
  const list = [...apps]; const label = a => String(a[2] || a[0]).toLowerCase();
  if (o.iconSort === 'az') list.sort((a, b) => label(a).localeCompare(label(b)));
  else if (o.iconSort !== 'keep') list.sort((a, b) => groupOf(a[0]) - groupOf(b[0]));
  const out = {}; let main = 0; let line = 0; let was = null;
  list.forEach(a => {
    const g = groupOf(a[0]); if (o.iconSort === 'groups' && was !== null && g !== was && main) { main = 0; line += 1; } was = g;
    if (main >= maxMain) { main = 0; line += 1; }
    const x = rows ? main * cell : line * cell; const y = rows ? line * cell : main * cell;
    out[a[0]] = { x: right ? Math.max(0, vw - 32 - cell - x) : x, y: y + top }; main += 1;
  });
  return out;
}
const snapTo = (p, cell) => ({ x: Math.max(0, Math.round(p.x / cell)) * cell, y: Math.max(0, Math.round(p.y / cell)) * cell });
// ▦ A true grid: every folder in one cell, never two in the same cell. Saved spots stay where they are; anything new takes the next free cell.
export function toGrid(keys, saved, height, cell = 96) {
  const rows = Math.max(3, Math.floor((height - 110) / cell)); const used = new Set(); const out = {}; const id = p => `${p.x},${p.y}`;
  keys.filter(k => saved?.[k]).forEach(k => { const p = snapTo(saved[k], cell); if (!used.has(id(p))) { used.add(id(p)); out[k] = p; } });
  let n = 0; keys.filter(k => !out[k]).forEach(k => { let p; do { p = { x: Math.floor(n / rows) * cell, y: (n % rows) * cell }; n += 1; } while (used.has(id(p))); used.add(id(p)); out[k] = p; });
  return out;
}
// 🧲 Every folder stays on the page, above the taskbar. A saved spot past the edge shows in the nearest free cell, and comes back if the window grows.
const ICON_W = 116; const ICON_H = 162;   // the folder, its label, the page margin and the taskbar
export function iconsOnPage(pos, vw, vh, cell = 96) {
  const maxX = Math.max(0, Math.floor((vw - ICON_W) / cell)) * cell; const maxY = Math.max(0, Math.floor((vh - ICON_H) / cell)) * cell; const out = {}; const late = [];
  Object.keys(pos).forEach(k => { const p = pos[k]; if (p && p.x >= 0 && p.y >= 0 && p.x <= maxX && p.y <= maxY) out[k] = p; else if (p) late.push(k); });
  const taken = c => Object.values(out).some(q => Math.abs(q.x - c.x) < cell * 0.8 && Math.abs(q.y - c.y) < cell * 0.8);
  late.forEach(k => { const want = pos[k]; let best = null; let far = Infinity; for (let x = 0; x <= maxX; x += cell) for (let y = 0; y <= maxY; y += cell) { const d = (x - want.x) ** 2 + (y - want.y) ** 2; if (d < far && !taken({ x, y })) { far = d; best = { x, y }; } } out[k] = best || { x: Math.min(want.x, maxX), y: Math.min(want.y, maxY) }; });
  return out;
}
// ◧ Half and half. Taking a side sends the other open window to the other side, and the next folder you open fills an empty half.
export function deskSet(all, k, p) {
  const others = Object.keys(all).filter(x => x !== k && all[x]?.open && !all[x].min); const me = { ...all[k], ...p }; const next = { ...all, [k]: me }; const was = all[k] || {};
  if (p.max || p.open === false) me.tile = null;
  if (p.tile) {
    const opp = p.tile === 'left' ? 'right' : 'left'; me.max = false;
    others.filter(x => all[x].tile === p.tile).forEach(x => { next[x] = { ...all[x], tile: null }; });
    if (!others.some(x => all[x].tile === opp)) { const mate = [...others].reverse().find(x => !all[x].tile); if (mate) next[mate] = { ...all[mate], tile: opp, max: false }; }
  } else if (p.open && !was.open && !me.tile) {
    const held = others.filter(x => all[x].tile);
    if (held.length === 1) { me.tile = all[held[0]].tile === 'left' ? 'right' : 'left'; me.max = false; }
  } else if (p.min === false && me.tile && others.some(x => all[x].tile === me.tile)) me.tile = null;
  return next;
}
// A folder dropped on another swaps places with it.
export function dropOnGrid(pos, k, p, cell = 96) {
  const to = snapTo(p, cell); const from = pos[k]; const other = Object.keys(pos).find(x => x !== k && pos[x].x === to.x && pos[x].y === to.y);
  return { ...pos, [k]: to, ...(other && from ? { [other]: from } : {}) };
}
// 🖥 Where its folders sit: on a grid, yours where you dragged them, or fitted to this screen. Kept on this device and, for an agent, with the agent, so a refresh or a full browser never loses it.
export function useDeskIcons(id, apps, prefs, { load, store, onDrag } = {}) {
  const shown = apps.filter(a => !(prefs.hidden || []).includes(a[0])); const names = shown.map(a => a[0]).join(); const cell = ICON_CELL[prefs.iconSize] || 96; const allKeys = apps.map(a => a[0]).join();
  const key = `feeless.dsk.icons.${id}`; const pushT = useRef(0);
  // 🔁 A spot the agent's copy has not taken yet is marked `.dirty`: on the next load it is pushed up, never overwritten by the older copy (2026-11-11: a save lost to a restart came back wrong).
  const dirty = `${key}.dirty`; const mark = on => { try { if (on) localStorage.setItem(dirty, '1'); else localStorage.removeItem(dirty); } catch { /* private */ } };
  const push = n => Promise.resolve(store?.(n)).then(() => mark(false)).catch(() => {});
  const save = n => { try { localStorage.setItem(key, JSON.stringify(n)); } catch { /* full or private: the agent's copy still holds it */ } if (store) { mark(true); clearTimeout(pushT.current); pushT.current = setTimeout(() => push(n), 400); } };
  const [stored, setPos] = useState(() => { let s = {}; try { s = JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch { /* private window */ } return prefs.autoFit ? fitIcons(shown, prefs, window.innerWidth, window.innerHeight) : toGrid(apps.map(a => a[0]), s, window.innerHeight, cell); });
  // A folder can arrive after the first paint (the owner's come from a read). It has its place in that same render, never one frame without one.
  const pos = useMemo(() => (allKeys.split(',').some(k => k && !stored[k]) ? toGrid(allKeys.split(','), stored, window.innerHeight, cell) : stored), [stored, allKeys, cell]);
  useEffect(() => { if (!load || prefs.autoFit) return undefined; let on = true; load().then(j => { if (!on) return; const got = j?.pos || {}; let mine = null; try { mine = localStorage.getItem(dirty) && JSON.parse(localStorage.getItem(key) || 'null'); } catch { /* private */ } if (mine && Object.keys(mine).length) { push(mine); return; } if (Object.keys(got).length) { const n = toGrid(allKeys.split(','), got, window.innerHeight, cell); setPos(n); try { localStorage.setItem(key, JSON.stringify(n)); } catch { /* full */ } } else { let had = null; try { had = localStorage.getItem(key); } catch { /* private */ } if (had) store?.(JSON.parse(had)); } }).catch(() => {}); return () => { on = false; }; }, [id]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setPos(x => { const missing = allKeys.split(',').some(k => !x[k]); return missing ? toGrid(allKeys.split(','), x, window.innerHeight, cell) : x; }); }, [allKeys, cell]);
  const [page, setPage] = useState(() => [window.innerWidth, window.innerHeight]); useEffect(() => { let t = 0; const on = () => { clearTimeout(t); t = setTimeout(() => setPage([window.innerWidth, window.innerHeight]), 120); }; window.addEventListener('resize', on); return () => { clearTimeout(t); window.removeEventListener('resize', on); }; }, []);
  const seen = useMemo(() => iconsOnPage(pos, page[0], page[1], cell), [pos, page, cell]);
  const moveIcon = (k, p) => { if (prefs.autoFit) onDrag?.(); setPos(x => { const n = dropOnGrid(iconsOnPage(x, window.innerWidth, window.innerHeight, cell), k, p, cell); const m = iconsOnPage(n, window.innerWidth, window.innerHeight, cell); save(m); return m; }); };
  const fit = useCallback(o => { const n = fitIcons(shown, o || prefs, window.innerWidth, window.innerHeight); setPos(x => { const m = { ...x, ...n }; save(m); return m; }); }, [names, prefs.iconSort, prefs.iconFlow, prefs.iconSide, prefs.iconSize]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!prefs.autoFit) return undefined; fit(); let t = 0; const on = () => { clearTimeout(t); t = setTimeout(() => fit(), 150); }; window.addEventListener('resize', on); return () => { clearTimeout(t); window.removeEventListener('resize', on); }; }, [prefs.autoFit, fit]);
  return { pos: seen, moveIcon, fit, shown };
}
// ⚡ A desktop covers the whole page, so the page under it stops painting. It comes back where you left it.
let deskCount = 0;
export function useDeskOverPage() {
  useEffect(() => { const y = window.scrollY; deskCount += 1; document.body.classList.add('dsk-open'); return () => { deskCount -= 1; if (!deskCount) { document.body.classList.remove('dsk-open'); requestAnimationFrame(() => window.scrollTo(0, y)); } }; }, []);
}
const PRESETS = [['Proofs first', { iconSort: 'groups', iconFlow: 'columns', iconSide: 'left' }, 'Each kind of folder gets its own column, proofs first'], ['Right side', { iconSort: 'groups', iconFlow: 'columns', iconSide: 'right' }, 'Folders on the right, the left stays clear for windows'], ['Top rows', { iconSort: 'groups', iconFlow: 'rows', iconSide: 'left' }, 'Rows across the top'], ['A to Z', { iconSort: 'az', iconFlow: 'columns', iconSide: 'left' }, 'One list in name order']];
const Seg = ({ label, k, rows, prefs, set }) => <section><h4>{label}</h4><span className="m-seg" role="group" aria-label={label}>{rows.map(([v, l, tip]) => <button key={v} type="button" className={prefs[k] === v ? 'active' : ''} aria-pressed={prefs[k] === v} onClick={() => set({ [k]: v })} data-tip={tip} data-testid={`dset-${k}-${v}`}>{l}</button>)}</span></section>;
// ⚙ How its desktop looks. A look only: it is saved in this browser, and nothing here touches the agent.
export function DeskSettings({ prefs, set, mood, apps = [], onFit }) {
  const wall = prefs.wall || mood; const shown = apps.filter(a => !(prefs.hidden || []).includes(a[0])); const vw = typeof window !== 'undefined' ? window.innerWidth : 1280; const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
  const map = useMemo(() => fitIcons(shown, prefs, vw, vh), [shown.length, prefs.iconSort, prefs.iconFlow, prefs.iconSide, prefs.iconSize, vw, vh]);   // eslint-disable-line react-hooks/exhaustive-deps
  const look = patch => { set(patch); onFit?.({ ...prefs, ...patch }); };
  return <div className="dset" data-testid="dsk-settings"><h3>Its desktop</h3>
    {apps.length ? <><section className="dset-fit" data-testid="dset-fit"><h4>Folders</h4><div className="dset-map" role="img" aria-label="Where its folders will sit" style={{ aspectRatio: `${vw} / ${vh}` }}>{shown.map(a => <i key={a[0]} className={`is-g${groupOf(a[0])}`} data-tip={a[2]} style={{ left: `${((map[a[0]]?.x || 0) / vw) * 100}%`, top: `${((map[a[0]]?.y || 0) / vh) * 100}%` }} />)}</div>
      <span className="dset-presets">{PRESETS.map(([l, o, tip]) => <button key={l} type="button" className="m-btn" onClick={() => look(o)} data-tip={tip} data-testid={`dset-preset-${l.toLowerCase().replace(/\W+/g, '-')}`}>{l}</button>)}</span>
      <button type="button" className="m-btn m-go" onClick={() => onFit?.(prefs)} data-tip="Puts every folder in its place on this screen" data-testid="dset-fit-now">Fit to screen</button></section>
      <Seg label="Widgets" k="widgets" rows={[[true, 'Show', 'Dashboard, CRM and finances on the wall'], [false, 'Hide', 'Just folders']]} prefs={prefs} set={o => look(o)} />
      <Seg label="Folder size" k="iconSize" rows={[['s', 'Small', 'Fits the most'], ['m', 'Medium', 'The usual size'], ['l', 'Large', 'Easier to hit']]} prefs={prefs} set={o => look(o)} />
      <section>{[['autoFit', 'Keep it fitted', 'Folders refit themselves when the window changes size'], ['iconLabels', 'Folder names', 'The name under each folder']].map(([k, l, t]) => <label key={k} className="dset-row" data-tip={t}><span>{l}</span><input type="checkbox" checked={!!prefs[k]} onChange={e => set({ [k]: e.target.checked })} data-testid={`dset-${k}`} /></label>)}</section>
      <details className="dset-hide"><summary data-testid="dset-hide">Hide folders{prefs.hidden?.length ? ` · ${prefs.hidden.length} hidden` : ''}</summary><div>{apps.filter(a => a[0] !== 'deskset').map(a => <label key={a[0]} className="dset-row"><span>{a[2]}</span><input type="checkbox" checked={!(prefs.hidden || []).includes(a[0])} onChange={e => set({ hidden: e.target.checked ? (prefs.hidden || []).filter(x => x !== a[0]) : [...(prefs.hidden || []), a[0]] })} data-testid={`dset-show-${a[0]}`} /></label>)}</div></details>
      <Seg label="New windows open" k="winOpen" rows={[['beside', 'Beside folders', 'Keeps its folders in view'], ['center', 'Centered', 'In the middle of the screen'], ['max', 'Full screen', 'Fills the desktop']]} prefs={prefs} set={set} /></> : null}
    <section><h4>Background color</h4><div className="dset-walls" role="radiogroup" aria-label="Background color">{WALLS.map(([k, l, c]) => <button key={k} type="button" role="radio" aria-checked={wall === k} className={wall === k ? 'is-on' : ''} style={{ '--c': c }} onClick={() => set({ wall: k })} data-tip={`A ${l.toLowerCase()} desktop`} data-testid={`dset-wall-${k}`}><i aria-hidden="true" /><span>{l}</span></button>)}</div></section>
    <section><h4>Background animation</h4><span className="m-seg" role="group" aria-label="Background animation">{[['full', 'Alive'], ['still', 'Still'], ['off', 'Off']].map(([k, l]) => <button key={k} type="button" className={prefs.motion === k ? 'active' : ''} aria-pressed={prefs.motion === k} onClick={() => set({ motion: k })} data-tip={k === 'full' ? 'It moves' : k === 'still' ? 'One frozen frame, lightest on the machine' : 'A plain dark wall'} data-testid={`dset-motion-${k}`}>{l}</button>)}</span></section>
    <section><label className="dset-row" data-tip="How bright the background is"><span>Brightness</span><input type="range" min="30" max="130" step="5" value={prefs.light} aria-label="Brightness" onChange={e => set({ light: Number(e.target.value) })} data-testid="dset-light" /><b className="m-num">{prefs.light}%</b></label></section>
    <section><h4>On the wall</h4>{[['print', 'Its Proofprint', 'The big fingerprint behind the icons'], ['title', 'Its name', 'The name written on the wall'], ['glass', 'Its results', 'The small results glass in the corner']].map(([k, l, t]) => <label key={k} className="dset-row" data-tip={t}><span>{l}</span><input type="checkbox" checked={!!prefs[k]} onChange={e => set({ [k]: e.target.checked })} data-testid={`dset-${k}`} /></label>)}</section>
    <Seg label="Clock" k="clock" rows={[['24', '24 hour', '15:30'], ['12', '12 hour', '3:30 PM']]} prefs={prefs} set={set} />
    <button type="button" className="m-btn" onClick={() => set({ ...DESK_DEFAULTS })} data-testid="dset-reset">Back to how it started</button></div>;
}
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
gl_FragColor=vec4(col,1.);}`;

function still() {
  return document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

export function ShaderWall({ mood = 'agent', className = '', frozen = false, style }) {
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
    const tick = now => { raf = 0; if (document.hidden || !seen) return; if (now - last >= 41) { last = now; draw(now); } if (!still() && !frozen) raf = requestAnimationFrame(tick); };
    const go = () => { if (!raf && !document.hidden && seen) raf = requestAnimationFrame(tick); };
    const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(es => { seen = es[0].isIntersecting; go(); }) : null; io?.observe(cv);
    const lost = () => { cv.style.opacity = '0'; };   // the browser took the context back: the gradient under it stays
    cv.addEventListener('webglcontextlost', lost);
    cv.style.opacity = '1'; draw(0); go(); document.addEventListener('visibilitychange', go);
    return () => { cancelAnimationFrame(raf); io?.disconnect(); document.removeEventListener('visibilitychange', go); cv.removeEventListener('webglcontextlost', lost); };
  }, [mood, frozen]);
  return <canvas ref={ref} className={`dsw ${className}`.trim()} style={style} aria-hidden="true" data-mood={mood} />;
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
// 🪙 the owner's Collective Boost coin. `earning` makes it pulse while real money is counting.
export function BoostCoin({ earning = false }) {
  return <span className={`bst-coinart${earning ? ' is-earning' : ''}`} aria-hidden="true"><img src="/coin/boost-coin-160.webp" alt="" draggable="false" /></span>;
}
// ▦ The grid it snaps to, faint on the wall; the cell a dragged folder will land in lights up. Spots are saved, so a refresh keeps them.
export const DeskGrid = () => <i className="dsk-grid" aria-hidden="true" data-testid="dsk-grid"><b /></i>;
export function DeskIcon({ k, ic, label, at, onMove, onOpen, tip, badge = null, testid, earn = false, earning = false }) {
  const g = useRef(null); const dragged = useRef(false);
  const down = e => { if (e.button !== 0) return; dragged.current = false; g.current = { x: e.clientX, y: e.clientY, ox: at.x, oy: at.y, px: at.x, py: at.y }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { const d = g.current; if (!d) return; const dx = e.clientX - d.x, dy = e.clientY - d.y; if (Math.abs(dx) + Math.abs(dy) > 4) dragged.current = true; if (dragged.current) { const nav = e.currentTarget.parentElement; const c = ICON_CELL[nav?.dataset.size] || 96; nav?.classList.add('is-drag'); nav?.style.setProperty('--tx', `${Math.round(d.px / c) * c}px`); nav?.style.setProperty('--ty', `${Math.round(d.py / c) * c}px`); d.px = Math.min(Math.max(0, d.ox + dx), Math.max(0, window.innerWidth - ICON_W)); d.py = Math.min(Math.max(0, d.oy + dy), Math.max(0, window.innerHeight - ICON_H)); e.currentTarget.style.transform = `translate(${d.px}px, ${d.py}px)`; } };
  const up = e => { e?.currentTarget?.parentElement?.classList.remove('is-drag'); const d = g.current; g.current = null; if (d && dragged.current) onMove(k, { x: d.px, y: d.py }); };
  return <button type="button" className={`dsk-ico is-${k}`} style={{ transform: `translate(${at.x}px, ${at.y}px)` }} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
    onClick={() => { if (!dragged.current) onOpen(k); dragged.current = false; }} data-tip={tip} data-testid={testid || `dsk-${k === 'vault' ? 'vault' : `ico-${k}`}`}>
    <i className="dsk-ico-art" aria-hidden="true">{k === 'pop' ? <PopFolderArt /> : k === 'boost' ? <BoostCoin /> : <em><Ic3 e={ic} size="30px" /></em>}{earn ? <u className="bst-earn"><BoostCoin earning={earning} /></u> : null}{badge ? <b className={`dsk-pop-roe m-num ${badge.lit ? 'is-lit' : badge.up ? 'is-up' : 'is-dn'}`}>{badge.text}</b> : null}</i><span>{label}</span></button>;
}

const leadOf = t => (String(t || '').match(/^\p{Extended_Pictographic}/u) || [''])[0];
const WIN_TILES = [['max', 'Fill the screen'], ['left', 'Left half of the screen'], ['right', 'Right half of the screen']];
export function DeskWin({ k, title, s, top, set, onTop, onClose, tools, dock = null, children }) {
  const drag = useRef(null); const box = useRef(null);
  const down = e => { onTop(); if (s.max || e.button !== 0 || e.target.closest('button, a') || !box.current) return; const r = box.current.getBoundingClientRect(); const d = box.current.querySelector(':scope > .bwr-dock:not(.is-fold)'); const side = d ? d.getBoundingClientRect().width + 8 : 0; const isLeft = d?.classList.contains('is-left'); drag.current = { x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, h: r.height, l: isLeft ? side : 0, r: isLeft ? 0 : side }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { const g = drag.current; if (!g) return; g.px = Math.max(g.l, Math.min(e.clientX - g.x, window.innerWidth - g.w - g.r)); g.py = Math.max(0, Math.min(e.clientY - g.y, window.innerHeight - 46 - g.h)); if (box.current) box.current.style.transform = `translate(${g.px}px, ${g.py}px)`; };   // only this window moves, and only inside the page; nothing re-renders until the drop
  const up = () => { const g = drag.current; drag.current = null; if (g && g.px != null) set(k, { x: g.px, y: g.py, tile: null }); };
  const onPage = `clamp(0px, ${s.x}px, calc(100vw - 320px))`; const downPage = `clamp(0px, ${s.y}px, calc(100dvh - 400px))`;   // a saved spot from before, or from a bigger window, comes back onto the page
  const place = s.max ? undefined : s.tile ? { transform: `translateX(${s.tile === 'right' ? '50vw' : '0'})` } : { transform: `translate(${onPage}, ${downPage})`, '--wx': onPage, '--wy': downPage };
  const now = s.max ? 'max' : s.tile || '';
  return <section ref={box} className={`dsk-win${s.max ? ' is-max' : ''}${s.tile && !s.max ? ' is-tile' : ''}${top ? ' is-top' : ''}`} style={place} onPointerDown={onTop} aria-label={title} data-testid={`dsk-win-${k}`}>
    <header className="dsk-title" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onDoubleClick={() => set(k, s.tile ? { tile: null } : { max: !s.max })}>
      <span className="dsk-dots"><button type="button" className="is-x" onClick={onClose} aria-label={`Close ${title}`} data-tip="Close" />
        <button type="button" className="is-min" onClick={() => set(k, { min: true })} aria-label={`Minimize ${title}`} data-tip="Minimize — it waits in the taskbar" data-testid={`dsk-min-${k}`} />
        <span className="dsk-fit"><button type="button" className="is-max" onClick={() => set(k, s.tile ? { tile: null } : { max: !s.max })} aria-label={s.max || s.tile ? 'Restore' : 'Maximize'} data-testid={`dsk-max-${k}`} />
          <span className="dsk-tiles" role="group" aria-label={`Arrange ${title}`}>{WIN_TILES.map(([t, tip]) => <button key={t} type="button" className={`is-${t}-tile${now === t ? ' is-on' : ''}`} onClick={() => set(k, t === 'max' ? { max: true } : { tile: t })} aria-label={tip} aria-pressed={now === t} data-tip={tip} data-testid={`dsk-tile-${t}-${k}`}><i aria-hidden="true" /></button>)}</span></span></span>
      <b><Ic3Text text={title} /></b><span className="dsk-tools">{tools}</span></header>
    <i className="dsk-water" aria-hidden="true"><Ic3 e={leadOf(title)} size="100%" /></i>
    <div className="dsk-body">{children}</div>{dock}</section>;
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
    {path ? <svg viewBox="-2 -2 124 38" aria-hidden="true" preserveAspectRatio="none"><path d={path} fill="none" stroke={up || tone === '' ? '#b48cff' : '#ff8fa3'} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" /></svg> : <svg viewBox="0 0 124 38" aria-hidden="true"><path d="M0 19H124" stroke="#ffffff2e" strokeDasharray="3 5" /></svg>}
  </Tag>;
}
export function glassOf(s) {
  const k = s.pow.length ? 'pow' : s.pop.length ? 'pop' : s.pob.length ? 'pob' : 'pow'; const rows = running(s[k]); const u = UNITS[k]; const end = rows.length ? rows[rows.length - 1].sum : 0;
  const won = s[k].filter(r => r.v > 0).length;
  return { title: `${u.label} RESULT`, value: rows.length ? `${u.fmt(end)} ${u.unit}` : 'No results yet', sub: rows.length ? `${won} of ${rows.length} won` : 'File a proof to start', tone: !rows.length ? '' : end >= 0 ? 'up' : 'dn', vals: rows.map(r => r.sum) };
}

function when(at) { return at ? new Date(at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''; }
function LineChart({ rows, u }) {
  return <div className="pfd-plot" data-testid="pfd-line"><ProChart rows={rows.map(r => ({ ...r, v: r.sum }))} height={240} testid="pfd-pro" label={`Running total, ${u.unit}`} fmt={v => u.fmt(v)} tip={r => `${r.name}${r.sub ? ` ${r.sub}` : ''}`} /></div>;
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
export function AppDesktop({ id, title, sub, mood = 'agent', apps: appsIn, glass, onClose }) {
  useDeskOverPage(); const [prefs, setPrefs] = useDeskPrefs(id); const appsRef = useRef(null); const fitRef = useRef(null);
  const apps = useMemo(() => [...appsIn, { k: 'deskset', ic: '⚙', label: 'Desktop settings', tip: 'Fit its folders, sizes and how it looks', body: <DeskSettings prefs={prefs} set={setPrefs} mood={mood} apps={appsRef.current || []} onFit={o => fitRef.current?.(o)} /> }], [appsIn, prefs, mood]);   // eslint-disable-line react-hooks/exhaustive-deps
  appsRef.current = apps.map(a => [a.k, a.ic, a.label]); const icons = useDeskIcons(id, appsRef.current, prefs); fitRef.current = icons.fit;
  const [w, setW] = useState(() => Object.fromEntries(apps.map((a, i) => [a.k, { open: false, min: false, max: false, x: 140 + i * 16, y: 34 + i * 12 }])));
  const [top, setTop] = useState(''); const [now, setNow] = useState(Date.now());
  const { pos, moveIcon } = icons;
  const set = useCallback((k, p) => setW(x => deskSet({ ...x, [k]: { max: false, min: false, x: 150, y: 40, ...x[k] } }, k, p)), []);   // a folder may appear after this desktop opened
  const open = k => { set(k, { open: true, min: false }); setTop(k); };
  useEffect(() => { const go = e => { set(e.detail, { open: true, min: false }); setTop(e.detail); }; window.addEventListener('feeless:open-win', go); return () => window.removeEventListener('feeless:open-win', go); }, [set]);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(t); }, []);
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  const tasks = apps.filter(a => w[a.k]?.open);
  return createPortal(<div className="dsk dsk-app" role="dialog" aria-modal="true" aria-label={title} data-testid={`dsk-app-${id}`}>
    <ShaderWall mood={mood} />
    <div className="dsk-wall" aria-hidden="true"><b>{title}</b><small>{sub}</small></div>
    <nav className="dsk-icons" aria-label="Desktop" data-size={prefs.iconSize} data-labels={prefs.iconLabels ? undefined : 'off'}><DeskGrid />{apps.filter(a => !(prefs.hidden || []).includes(a.k)).map(a => <DeskIcon key={a.k} k={a.k} ic={a.ic} label={a.label} at={pos[a.k]} onMove={moveIcon} onOpen={open} tip={a.tip} badge={a.badge} testid={`app-ico-${a.k}`} />)}</nav>
    {glass ? <PerfGlass {...glass} onOpen={() => open(glass.app)} /> : null}
    {apps.map(a => (w[a.k]?.open && !w[a.k].min ? <DeskWin key={a.k} k={a.k} title={`${a.ic} ${a.label}`} s={w[a.k]} top={top === a.k} set={set} onTop={() => setTop(a.k)} onClose={() => set(a.k, { open: false })}>{a.body}</DeskWin> : null))}
    <footer className="dsk-bar"><span className="dsk-start"><i aria-hidden="true" />FEELESS</span>
      {tasks.map(a => <button key={a.k} type="button" className={`dsk-task${!w[a.k].min && top === a.k ? ' is-on' : ''}`} onClick={() => { if (w[a.k].min || top !== a.k) { set(a.k, { min: false }); setTop(a.k); } else set(a.k, { min: true }); }} data-testid={`dsk-task-${a.k}`}><Ic3 e={a.ic} /> {a.label}</button>)}
      <time className="m-num">{prefs.clock === '12' ? new Date(now).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : new Date(now).toTimeString().slice(0, 5)}</time>
      <button type="button" className="m-btn dsk-exit" onClick={onClose} data-tip="Back (Esc)" data-testid="dsk-app-close">Exit desktop</button></footer>
  </div>, document.body);
}


// 🔔 The desk's notification bar (owner 2026-11-10: "a noti bar for desktop for when stuff is done or agents see potential"): what this agent
// finished (filed · graded · reviewed · a picture or clip ready) or thinks is worth a look (a plan waiting, a failed review), newest first.
// One poll every 20 s while the desk is open and the tab is visible; the newest one also slides in as a toast. Seen = per agent, this device.
const BELL_KEY = id => `feeless:bell:${id}`;
const bellSeen = id => { try { return Number(localStorage.getItem(BELL_KEY(id)) || 0); } catch { return 0; } };
const ago = at => { const s = Math.max(1, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
export function DeskBell({ catId, onOpen }) {
  const [rows, setRows] = useState([]); const [open, setOpen] = useState(false); const [seen, setSeen] = useState(() => bellSeen(catId)); const [toast, setToast] = useState(null); const newest = useRef(0);
  useEffect(() => {
    if (!catId) return undefined; let live = true;
    const pull = () => { if (document.hidden) return; fetch(apiUrl(`/api/cats/${encodeURIComponent(catId)}/feed?${agentAuthQuery()}`)).then(r => (r.ok ? r.json() : { rows: [] })).then(j => {
      if (!live) return; const got = Array.isArray(j?.rows) ? j.rows : []; setRows(got);
      const top = got[0]; if (top && newest.current && top.at > newest.current) { setToast(top); setTimeout(() => live && setToast(t => (t === top ? null : t)), 6000); }
      if (top) newest.current = Math.max(newest.current, top.at); }).catch(() => {}); };
    pull(); const t = setInterval(pull, 20000); return () => { live = false; clearInterval(t); };
  }, [catId]);
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  const unread = rows.filter(r => r.at > seen).length;
  const flip = () => { setOpen(o => !o); if (rows[0]) { const at = rows[0].at; setSeen(at); try { localStorage.setItem(BELL_KEY(catId), String(at)); } catch { /* private window */ } } };
  return <span className="dbl">
    <button type="button" className={`dbl-btn${unread ? ' has-new' : ''}${open ? ' is-on' : ''}`} onClick={flip} aria-expanded={open} aria-label={unread ? `${unread} new` : 'Notifications'} data-tip="What your agent finished or thinks is worth a look" data-testid="desk-bell">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a6 6 0 0 0-6 6v3.6L4.3 16h15.4L18 12.6V9a6 6 0 0 0-6-6Zm0 18a2.6 2.6 0 0 0 2.5-2h-5A2.6 2.6 0 0 0 12 21Z" /></svg>{unread ? <em>{unread > 9 ? '9+' : unread}</em> : null}</button>
    {open ? <div className="dbl-pop" role="dialog" aria-label="Notifications" data-testid="desk-bell-list"><header><b>Your agent</b><small>{rows.length ? `${rows.filter(r => r.tone === 'done').length} done · ${rows.filter(r => r.tone === 'look').length} worth a look` : 'nothing yet'}</small></header>
      {rows.length ? <ol>{rows.map((r, i) => <li key={`${r.at}-${i}`} className={`is-${r.tone}${r.at > seen ? ' is-new' : ''}`} style={{ '--i': i }}><button type="button" onClick={() => { setOpen(false); onOpen?.(r); }} data-testid={`desk-bell-${i}`}>
        <i aria-hidden="true">{r.tone === 'done' ? '✓' : '👀'}</i><span><b>{r.text}</b><small>{r.kind} · {ago(r.at)} ago</small></span></button></li>)}</ol>
        : <p className="dbl-none">When your agent files, grades, reviews or finishes a picture or clip, it shows up here.</p>}</div> : null}
    {toast && !open ? <button type="button" className={`dbl-toast is-${toast.tone}`} onClick={() => { setToast(null); flip(); }} role="status" data-testid="desk-bell-toast"><i aria-hidden="true">{toast.tone === 'done' ? '✓' : '👀'}</i><span><b>{toast.text}</b><small>{toast.kind} · just now</small></span></button> : null}
  </span>;
}
