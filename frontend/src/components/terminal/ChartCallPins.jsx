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
  by.forEach(g => { const pri = c => (c.kind === 'agent' ? 1 : 0); const keep = [...g].sort((a, b) => pri(a) - pri(b) || Number(b.at) - Number(a.at)).slice(0, PER_CANDLE);
    const more = g.length - keep.length; keep.forEach((c, i) => out.push(i === keep.length - 1 && more > 0 ? { ...c, more } : c)); });
  return out.sort((a, b) => Number(a.at) - Number(b.at));
}

export function ChartCallPins({ calls, seriesRef, chartRef, container, ratio = 1, mcChart = true, ivSec = 60, nowMc }) {
  const host = useRef(null); const [open, setOpen] = useState(null);
  const list = thinPins((calls || []).filter(c => c && Number(c.cap) > 0 && Number(c.at) > 0), ivSec).slice(-12);
  const key = list.map(c => `${c.id}:${c.cap}`).join('|');
  useEffect(() => {
    const root = host.current; if (!root || !list.length) return undefined;
    const els = list.map(c => ({ el: root.querySelector(`[data-pin="${c.id}"]`), t: pinPlace(c, ivSec), v: mcChart ? Number(c.cap) : Number(c.cap) / (ratio || 1), last: '' }));
    const step = () => {
      const s = seriesRef.current?.series; const ch = chartRef.current; const box = container?.current;
      if (!s || !ch || !box) return;
      const top = box.offsetTop || 0; const h = box.clientHeight || 0; const w = box.clientWidth || 0;
      const slots = [];   // pins on the same candle stack upward instead of covering each other
      els.forEach(o => {
        if (!o.el) return;
        let x = null; let y = null; let yTop = null;
        try {
          x = ch.timeScale().timeToCoordinate(o.t); y = s.priceToCoordinate(o.v);
          const lg = x != null ? ch.timeScale().coordinateToLogical(x) : null; const bar = lg != null && s.dataByIndex ? s.dataByIndex(Math.round(lg)) : null;
          const hi = bar ? Number(bar.high ?? bar.value) : null; yTop = hi > 0 ? s.priceToCoordinate(hi) : null;
        } catch { x = null; }
        const ok = x != null && y != null && x > 8 && x < w - 60 && y > 8 && y < h - 8;
        if (!ok) { if (o.last !== 'x') { o.last = 'x'; o.el.style.opacity = '0'; o.el.style.pointerEvents = 'none'; } return; }
        const n = slots.filter(sx => Math.abs(sx - x) < 16).length; slots.push(x);
        const above = Math.min(y, yTop ?? y) - 16 - n * 22;   // 📍 hover ABOVE the candle's high, a stem down to the call point
        const py = Math.max(12, above); const stem = Math.max(0, y - py - 10);
        const pos = `${x.toFixed(0)},${py.toFixed(0)},${stem.toFixed(0)}`;
        if (pos === o.last) return; o.last = pos;
        o.el.style.opacity = '1'; o.el.style.pointerEvents = 'auto';
        o.el.style.transform = `translate3d(${x.toFixed(0)}px, ${(py + top).toFixed(0)}px, 0)`;
        o.el.style.setProperty('--ccp-stem', `${stem.toFixed(0)}px`);
        o.el.classList.toggle('is-r', x > w * 0.55); o.el.classList.toggle('is-b', py > h * 0.5);   // the card opens toward the free side, inside the chart
      });
    };
    return addChartJob(container, step);
  }, [key, ivSec, ratio, mcChart, seriesRef, chartRef, container]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!list.length) return null;
  const card = list.find(c => c.id === open);
  return <div className="ccp" ref={host} data-testid="chart-call-pins">
    {list.map(c => <button key={c.id} type="button" className={`ccp-pin is-${c.kind || 'user'} ${c.action ? `a-${String(c.action).toLowerCase()}` : ''} ${open === c.id ? 'is-open' : ''}`} data-pin={c.id}
      onMouseEnter={() => setOpen(c.id)} onMouseLeave={() => setOpen(o => (o === c.id ? null : o))} onFocus={() => setOpen(c.id)} onBlur={() => setOpen(o => (o === c.id ? null : o))}
      onClick={() => setOpen(o => (o === c.id ? null : c.id))} aria-label={`${c.who} ${c.action || 'call'}${c.text ? `: ${c.text}` : ''}`} data-testid={`chart-pin-${c.id}`}>
      {c.img ? <img className="ccp-img" src={c.img} alt="" loading="lazy" decoding="async" /> : <i className="ccp-ico">{c.icon || initials(c.who)}</i>}
      {c.more ? <em className="ccp-more">+{c.more}</em> : null}
      {open === c.id && card ? <CallCard c={card} nowMc={nowMc} /> : null}
    </button>)}
  </div>;
}

function CallCard({ c, nowMc }) {
  const l = calloutLive(c.cap, nowMc);
  const ago = Math.max(0, Math.round((Date.now() / 1000 - Number(c.at)) / 60));
  return <span className={`ccp-card is-${l.tone}`} role="tooltip">
    <span className="ccp-head">{c.img ? <img className="ccp-himg" src={c.img} alt="" /> : <i>{c.icon || initials(c.who)}</i>}<b>{c.who}</b><small>{ago < 60 ? `${ago}m` : `${Math.round(ago / 60)}h`}</small>{c.action ? <em className={`ccp-act a-${String(c.action).toLowerCase()}`}>{c.action}</em> : null}</span>
    {c.text ? <span className="ccp-text">{c.text}</span> : null}
    <span className="ccp-row"><small>called at</small><b>{capWord(c.cap)} MC</b></span>
    {l.x != null ? <span className="ccp-row"><small>since</small><b className="ccp-x">{xWord(l.x)} · {l.pct >= 0 ? '+' : ''}{l.pct.toFixed(1)}%</b></span> : null}
    {c.pct != null ? <span className="ccp-row"><small>their seat</small><b className={c.pct >= 0 ? 'm-pos' : 'm-neg'}>{c.pct >= 0 ? '+' : ''}{Number(c.pct).toFixed(1)}%</b></span> : null}
  </span>;
}
