import React, { useEffect, useRef, useState } from 'react';
import { addChartJob } from '../../lib/chartFrame';
import { calloutLive, xWord, capWord } from '../../lib/callout';
import '../../styles/chartCallPins.css';

// 📍 CALL PINS ON THE CHART (owner, 2026-10-16, Pump's chart as the reference: "lil bubbles and cards like this on chart"): one small avatar
// pin at the candle + market cap of each call; hover / tap opens a card (who · when · what they said · cap at the call · × since). Pins are
// placed by the shared chart frame (transform only, only when the chart moved). `calls` = [{id, at (s), cap, who, text, kind, action}].
const initials = w => String(w || '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?';
export function pinPlace(call, ivSec) { const t = Number(call?.at); return t > 0 && ivSec > 0 ? t - (t % ivSec) : null; }

// 🧹 one candle carries at most PER_CANDLE pins (models first, then the newest agent), one per author; the rest fold into "+N" on the last
export const PER_CANDLE = 2;
export function thinPins(calls, ivSec) {
  const by = new Map();
  (calls || []).forEach(c => { const t = pinPlace(c, ivSec); if (t == null) return; const g = by.get(t) || []; if (!g.some(x => x.who === c.who)) g.push(c); by.set(t, g); });
  const out = [];
  by.forEach(g => { const pri = c => (c.kind === 'wallet' ? 2 : c.kind === 'agent' ? 1 : 0); const keep = [...g].sort((a, b) => pri(a) - pri(b) || Number(b.at) - Number(a.at)).slice(0, PER_CANDLE);
    const rest = g.filter(c => !keep.includes(c)); const more = rest.length;
    keep.forEach((c, i) => out.push(i === keep.length - 1 && more > 0 ? { ...c, more, folded: rest.sort((a, b) => Number(b.at) - Number(a.at)).slice(0, 6) } : c)); });   // 📜 the folded comments stay readable in the card
  return out.sort((a, b) => Number(a.at) - Number(b.at));
}

export const MAX_PINS = 60;   // 📜 the whole comment history the chart was handed (≤ 60, folded per candle) — owner: "full comment bubble history"

// 🫧 STACKS (owner, 2026-10-18: "cooler ways to see all bubbles on chart without clutter"): pins whose candles sit within STACK_GAP px of
// each other on screen merge into ONE stack — the lead's avatar with the others fanned behind it and a count. Tap / hover = the whole
// thread for those candles. Zoom in and the stack splits by itself (it is measured in pixels, every frame the chart moved).
export const STACK_GAP = 28;
const PRI = { ai: 0, talk: 1, user: 1, agent: 2, wallet: 3 };
export function clusterPins(pts, gap = STACK_GAP) {
  const out = []; let cur = null;
  [...(pts || [])].sort((a, b) => a.x - b.x).forEach(p => {
    if (!cur || p.x - cur.x0 > gap) { cur = { x0: p.x, members: [] }; out.push(cur); }
    cur.members.push(p);
  });
  return out.map(g => { const lead = [...g.members].sort((a, b) => (PRI[a.kind] ?? 4) - (PRI[b.kind] ?? 4) || Number(b.at) - Number(a.at))[0];
    return { lead: lead.id, ids: g.members.map(m => m.id), top: Math.min(...g.members.map(m => m.top)) }; });
}

// 🎛 who shows on the chart — tap a group to hide / show it (remembered on this browser)
export const PIN_LENSES = [['models', '🔁 Models', k => k === 'ai' || k === 'talk'], ['agents', '🤖 Agents', k => k === 'agent'], ['wallets', '🐋 Wallets', k => k === 'wallet'], ['fee', '🐱 Fee', k => k === 'feecat'], ['you', '👤 You', k => k === 'user']];
export const lensOf = kind => (PIN_LENSES.find(l => l[2](kind || 'user')) || PIN_LENSES[PIN_LENSES.length - 1])[0];
const LENS_KEY = 'feeless.pinLens';

// 🧵 TRAILS (owner, 2026-10-18: "I wanna see agents and AI trail on chart"): each voice's calls joined in time order — OSSY, G4 and the
// agents each get one faint line through the exact candle + cap they called at (dots on the calls). Wallets / your own lines get none.
export function trailKey(c) {
  if (!c) return null;
  if (c.kind === 'agent') return 'agents';
  if (c.kind === 'feecat') return 'fee';
  if (c.kind === 'ai' || c.kind === 'talk') { const w = String(c.who || '').toUpperCase(); return w === 'OSSY' || w === 'G4' || w === 'REAPER' ? w.toLowerCase() : null; }
  return null;
}
export function trailPaths(pts) {
  const by = {};
  (pts || []).forEach(p => { const k = trailKey(p); if (k) (by[k] = by[k] || []).push(p); });
  const out = {};
  Object.entries(by).forEach(([k, a]) => { if (a.length < 2) return; a.sort((x, y) => x.x - y.x);
    const hd = a[a.length - 1];
    out[k] = { line: a.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(0)} ${p.y.toFixed(0)}`).join(''), dots: a.map(p => `M${p.x.toFixed(0)} ${p.y.toFixed(0)}h0`).join(''), head: `translate(${hd.x.toFixed(0)} ${hd.y.toFixed(0)})` }; });
  return out;
}
// 🔥 a HOT message (owner, 2026-10-19: "on-chart dot path more vital and live — see the hot messages"): said in the last 5 min, a BUY / SELL /
// TRIM, or a call already 10%+ off where it was made. Hot pins wear a beating ring; each trail's newest point is its live head.
export const isHot = (c, now = Date.now() / 1000) => !!c && (now - Number(c.at) < 300 || /^(BUY|SELL|TRIM)$/i.test(String(c.action || '')) || Math.abs(Number(c.pct) || 0) >= 10);
const readHidden = () => { try { return new Set(JSON.parse(localStorage.getItem(LENS_KEY) || '[]')); } catch { return new Set(); } };

export function ChartCallPins({ calls, seriesRef, chartRef, container, ratio = 1, mcChart = true, ivSec = 60, nowMc }) {
  const host = useRef(null); const [open, setOpen] = useState(null);
  const [hidden, setHidden] = useState(readHidden);
  const [stacks, setStacks] = useState({});   // lead id → [member ids]; members not leading are hidden
  const trailRef = useRef(null);
  const valid = (calls || []).filter(c => c && Number(c.cap) > 0 && Number(c.at) > 0);
  const counts = {}; valid.forEach(c => { const l = lensOf(c.kind); counts[l] = (counts[l] || 0) + 1; });
  const list = thinPins(valid.filter(c => !hidden.has(lensOf(c.kind))), ivSec).slice(-MAX_PINS);
  const key = list.map(c => `${c.id}:${c.cap}`).join('|');
  const flip = l => setHidden(h => { const n = new Set(h); n.has(l) ? n.delete(l) : n.add(l); try { localStorage.setItem(LENS_KEY, JSON.stringify([...n])); } catch { /* private window */ } return n; });
  useEffect(() => {
    const root = host.current; if (!root || !list.length) return undefined;
    const els = list.map(c => ({ id: c.id, kind: c.kind, who: c.who, at: c.at, el: root.querySelector(`[data-pin="${c.id}"]`), t: pinPlace(c, ivSec), v: mcChart ? Number(c.cap) : Number(c.cap) / (ratio || 1), last: '' }));
    let lastGroups = ''; let lastTrail = '';
    const hide = o => { if (o.last !== 'x') { o.last = 'x'; o.el.style.opacity = '0'; o.el.style.pointerEvents = 'none'; } };
    const step = () => {
      const s = seriesRef.current?.series; const ch = chartRef.current; const box = container?.current;
      if (!s || !ch || !box) return;
      const top = box.offsetTop || 0; const h = box.clientHeight || 0; const w = box.clientWidth || 0;
      const pts = [];
      els.forEach(o => {
        if (!o.el) return;
        let x = null; let y = null; let yTop = null;
        try {
          x = ch.timeScale().timeToCoordinate(o.t); y = s.priceToCoordinate(o.v);
          const lg = x != null ? ch.timeScale().coordinateToLogical(x) : null; const bar = lg != null && s.dataByIndex ? s.dataByIndex(Math.round(lg)) : null;
          const hi = bar ? Number(bar.high ?? bar.value) : null; yTop = hi > 0 ? s.priceToCoordinate(hi) : null;
        } catch { x = null; }
        if (x != null && y != null && x > 8 && x < w - 60 && y > 8 && y < h - 8) pts.push({ id: o.id, kind: o.kind, who: o.who, at: o.at, x, y, top: Math.min(y, yTop ?? y), o }); else hide(o);
      });
      const svg = trailRef.current;
      if (svg) { const tp = trailPaths(pts); const tk = `${top},${w},${h}|${JSON.stringify(tp)}`;
        if (tk !== lastTrail) { lastTrail = tk; svg.style.transform = `translate3d(0, ${top}px, 0)`; svg.setAttribute('width', w); svg.setAttribute('height', h);
          svg.querySelectorAll('[data-trail]').forEach(g => { const t = tp[g.dataset.trail]; g.querySelector('.ccp-tl').setAttribute('d', t ? t.line : ''); g.querySelector('.ccp-td').setAttribute('d', t ? t.dots : ''); const hg = g.querySelector('.ccp-hg'); if (hg) { hg.setAttribute('transform', t ? t.head : 'translate(-99 -99)'); } }); } }
      const groups = clusterPins(pts);
      const gk = groups.map(g => `${g.lead}:${g.ids.join(',')}`).join('|');
      if (gk !== lastGroups) { lastGroups = gk; const m = {}; groups.forEach(g => { m[g.lead] = g.ids; }); setStacks(m); }
      const byId = new Map(pts.map(p => [p.id, p]));
      groups.forEach(g => {
        g.ids.forEach(id => { if (id !== g.lead) hide(byId.get(id).o); });
        const p = byId.get(g.lead); const o = p.o;
        const py = Math.max(12, g.top - 30); const stem = Math.max(0, p.y - py - 10);   // 📍 above the stack's highest candle, a stem to the call point
        const pos = `${p.x.toFixed(0)},${py.toFixed(0)},${stem.toFixed(0)}`;
        if (pos === o.last) return; o.last = pos;
        o.el.style.opacity = '1'; o.el.style.pointerEvents = 'auto';
        o.el.style.transform = `translate3d(${p.x.toFixed(0)}px, ${(py + top).toFixed(0)}px, 0)`;
        o.el.style.setProperty('--ccp-stem', `${stem.toFixed(0)}px`);
        o.el.classList.toggle('is-r', p.x > w * 0.55); o.el.classList.toggle('is-b', py > h * 0.5);   // the card opens toward the free side, inside the chart
      });
    };
    return addChartJob(container, step);
  }, [key, ivSec, ratio, mcChart, seriesRef, chartRef, container]); // eslint-disable-line react-hooks/exhaustive-deps
  const lenses = PIN_LENSES.filter(l => counts[l[0]]);
  if (!valid.length) return null;
  const byId = new Map(list.map(c => [c.id, c]));
  const trails = [...new Set(list.map(trailKey).filter(Boolean))];
  return <div className="ccp" ref={host} data-testid="chart-call-pins">
    {trails.length ? <svg ref={trailRef} className="ccp-trails" aria-hidden="true" data-testid="chart-trails">{trails.map(k =>
      <g key={k} data-trail={k} className={`ccp-trail t-${k}`}><path className="ccp-tl" d="" /><path className="ccp-td" d="" /><g className="ccp-hg" transform="translate(-99 -99)"><circle className="ccp-head" r="4" /></g></g>)}</svg> : null}
    {lenses.length > 1 || hidden.size ? <div className="ccp-lens" data-testid="chart-pin-lens">{lenses.map(([k, word]) =>
      <button key={k} type="button" className={`ccp-lb ${hidden.has(k) ? 'is-off' : ''}`} aria-pressed={!hidden.has(k)} onClick={() => flip(k)} data-testid={`chart-pin-lens-${k}`}>{word}<b>{counts[k]}</b></button>)}</div> : null}
    {list.map(c => { const mates = (stacks[c.id] || [c.id]).map(id => byId.get(id)).filter(Boolean); const n = mates.length; const fan = mates.filter(m => m.id !== c.id).slice(0, 2);
      const total = mates.reduce((a, m) => a + 1 + (m.more || 0), 0);
      return <button key={c.id} type="button" className={`ccp-pin is-${c.kind || 'user'} ${c.action ? `a-${String(c.action).toLowerCase()}` : ''} ${open === c.id ? 'is-open' : ''} ${n > 1 ? 'is-stack' : ''} ${mates.some(m => isHot(m)) ? 'is-hot' : ''}`} data-pin={c.id}
        onMouseEnter={() => setOpen(c.id)} onMouseLeave={() => setOpen(o => (o === c.id ? null : o))} onFocus={() => setOpen(c.id)} onBlur={() => setOpen(o => (o === c.id ? null : o))}
        onClick={() => setOpen(o => (o === c.id ? null : c.id))} aria-label={n > 1 ? `${total} comments here` : `${c.who} ${c.action || 'call'}${c.text ? `: ${c.text}` : ''}`} data-testid={`chart-pin-${c.id}`}>
        {fan.map((m, i) => <span key={m.id} className={`ccp-fan ${['f0', 'f1'][i]} is-${m.kind || 'user'}`} aria-hidden="true">{m.img ? <img src={m.img} alt="" loading="lazy" decoding="async" /> : <i>{m.icon || initials(m.who)}</i>}</span>)}
        {c.img ? <img className="ccp-img" src={c.img} alt="" loading="lazy" decoding="async" /> : <i className="ccp-ico">{c.icon || initials(c.who)}</i>}
        {total > 1 ? <em className="ccp-more">{total}</em> : null}
        {open === c.id ? (n > 1 ? <StackCard list={mates} nowMc={nowMc} /> : <CallCard c={c} nowMc={nowMc} />) : null}
      </button>; })}
  </div>;
}

const agoWord = at => { const m = Math.max(0, Math.round((Date.now() / 1000 - Number(at)) / 60)); return m < 60 ? `${m}m` : `${Math.round(m / 60)}h`; };

// 🧵 one stack = one thread: every comment on those candles, newest first, each with what it has done since
function StackCard({ list, nowMc }) {
  const rows = list.flatMap(c => [c, ...(c.folded || [])]).sort((a, b) => Number(b.at) - Number(a.at));
  return <span className="ccp-card ccp-thread" role="tooltip" data-testid="chart-pin-thread">
    <span className="ccp-th-head"><b>{rows.length} comments</b><small>{agoWord(rows[rows.length - 1].at)} → {agoWord(rows[0].at)} ago · zoom in to split</small></span>
    {rows.map(c => { const l = calloutLive(c.cap, nowMc); return <span key={c.id} className={`ccp-tr is-${c.kind || 'user'}`}>
      {c.img ? <img className="ccp-himg" src={c.img} alt="" /> : <i className="ccp-tri">{c.icon || initials(c.who)}</i>}
      <span className="ccp-trb"><span className="ccp-trh"><b>{c.who}</b>{c.action ? <em className={`ccp-act a-${String(c.action).toLowerCase()}`}>{c.action}</em> : null}<small>{agoWord(c.at)}</small>
        {l.x != null ? <small className={l.pct >= 0 ? 'm-pos' : 'm-neg'}>{l.pct >= 0 ? '+' : ''}{l.pct.toFixed(0)}% since</small> : null}</span>
        {c.text ? <span className="ccp-trt">{c.text}</span> : null}</span>
    </span>; })}
  </span>;
}

function CallCard({ c, nowMc }) {
  const l = calloutLive(c.cap, nowMc);
  return <span className={`ccp-card is-${l.tone}`} role="tooltip">
    <span className="ccp-head">{c.img ? <img className="ccp-himg" src={c.img} alt="" /> : <i>{c.icon || initials(c.who)}</i>}<b>{c.who}</b><small>{agoWord(c.at)}</small>{c.action ? <em className={`ccp-act a-${String(c.action).toLowerCase()}`}>{c.action}</em> : null}</span>
    {c.text ? <span className="ccp-text">{c.text}</span> : null}
    <span className="ccp-row"><small>called at</small><b>{capWord(c.cap)} MC</b></span>
    {l.x != null ? <span className="ccp-row"><small>since</small><b className="ccp-x">{xWord(l.x)} · {l.pct >= 0 ? '+' : ''}{l.pct.toFixed(1)}%</b></span> : null}
    {c.rep > 1 ? <span className="ccp-row"><small>said it</small><b>×{c.rep} in a row</b></span> : null}
    {(c.folded || []).map(f => <span key={f.id} className="ccp-fold"><b>{f.who}</b>{f.action ? <em className={`ccp-act a-${String(f.action).toLowerCase()}`}>{f.action}</em> : null}<small>{String(f.text || '').slice(0, 90)}</small></span>)}
    {c.pct != null ? <span className="ccp-row"><small>their seat</small><b className={c.pct >= 0 ? 'm-pos' : 'm-neg'}>{c.pct >= 0 ? '+' : ''}{Number(c.pct).toFixed(1)}%</b></span> : null}
  </span>;
}
