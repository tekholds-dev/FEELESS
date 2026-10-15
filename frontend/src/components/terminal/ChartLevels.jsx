import { addChartJob } from '../../lib/chartFrame';
import React, { useEffect, useMemo, useRef } from 'react';
import { declutter, distWord, levelRead, spreadAround } from '../../lib/chartLevels';
import '../../styles/chartLevels.css';

// 📏 LIVE LEVELS over the candles (owner, 2026-10-13: "all on-chart stuff needs to be advanced, live styled, no dead lines"). Every row
// is a lit line + a tag; ONE rAF loop (≤ 30fps) places them from the chart's own scale and writes — only when a value changed — the
// distance from the LIVE price (the same eased close the forming candle is drawn with), a `near` heat inside 2.5% and a one-shot
// flash when the price crosses the level. A key level off the visible scale waits at the edge with an arrow. Transforms + text only:
// no React render per frame, no layout property animated, nothing invented between ticks.
const PIN_TOP = 12;   // a key level above the scale waits at the top edge (the vitals badge sits top-LEFT now)

export function ChartLevels({ levels, seriesRef, chartRef, lastBarRef, shownRef, container, fmt }) {
  const rows = useMemo(() => { const seen = new Set(); return declutter((levels || []).filter(l => l && l.px > 0 && !seen.has(l.id) && seen.add(l.id))); }, [levels]);
  const host = useRef(null);
  const key = rows.map(l => `${l.id}:${l.px}`).join('|');
  useEffect(() => {
    const root = host.current;
    if (!root || !rows.length) return undefined;
    const els = rows.map(l => { const el = root.querySelector(`[data-lv="${l.id}"]`); return el ? { el, tag: el.querySelector('.clx-tag'), dist: el.querySelector('em'), y: '', ty: '', txt: '', near: null, off: null, side: null } : null; });
    let axis = -1; let axisAt = 0;
    const step = t => {
      const s = seriesRef.current?.series; const box = container?.current; const bar = lastBarRef.current;
      if (!s || !box) return;
      const top = box.offsetTop || 0; const h = box.clientHeight || 0; const px = shownRef?.current ?? bar?.close ?? bar?.value;
      if (t - axisAt > 1000) { axisAt = t; try { const w = Math.round(chartRef?.current?.priceScale('right').width() || 0); if (w && w !== axis) { axis = w; root.style.setProperty('--clx-axis', `${w}px`); } } catch { /* chart gone */ } }
      const ys = rows.map(l => { try { return s.priceToCoordinate(l.px); } catch { return null; } });
      const lim = Math.max(12, h - 30);
      const shown = ys.map((y, i) => (y == null ? null : y < 6 || y > lim ? (rows[i].key ? Math.max(PIN_TOP, Math.min(lim, y)) : null) : y));
      let pyLive = null; try { pyLive = px > 0 ? s.priceToCoordinate(px) : null; } catch { pyLive = null; }
      const tags = spreadAround(shown.map((y, i) => (rows[i].quiet ? null : y)), lim, [pyLive]);   // a quiet line has no tag to place   // 🧹 never under the live P&L tag / the axis's live price label
      rows.forEach((l, i) => {
        const o = els[i]; if (!o) return;
        const y = shown[i];
        if (y == null) { if (o.y !== 'x') { o.y = 'x'; o.el.style.opacity = '0'; } return; }
        const ys_ = (y + top).toFixed(1);
        if (o.y !== ys_) { o.y = ys_; o.el.style.opacity = '1'; o.el.style.transform = `translate3d(0, ${ys_}px, 0)`; }
        const ty = rows[i].quiet ? '0' : (tags[i] - y).toFixed(0);
        if (o.ty !== ty && o.tag) { o.ty = ty; o.tag.style.transform = `translate3d(0, ${ty}px, 0)`; o.tag.classList.toggle('is-moved', Math.abs(Number(ty)) > 3); }   // a tag moved off its own line says so
        const off = ys[i] < 6 || ys[i] > lim;
        if (o.off !== off) { o.off = off; o.el.classList.toggle('is-off', off); }
        const r = levelRead(l.px, px); if (!r) return;
        const txt = distWord(r.dist);
        if (o.txt !== txt && o.dist) { o.txt = txt; o.dist.textContent = txt; }
        if (o.near !== r.near) { o.near = r.near; o.el.classList.toggle('is-near', r.near); }
        if (o.side !== null && o.side !== r.above) { o.el.classList.remove('is-hit'); void o.el.offsetWidth; o.el.classList.add('is-hit'); }   // the live price just crossed it
        o.side = r.above;
      });
    };
    return addChartJob(container, step);   // ⚡ the shared chart frame: runs only when this chart changed
  }, [key, seriesRef, chartRef, lastBarRef, shownRef, container]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!rows.length) return null;
  return <div className="clx" ref={host} data-testid="chart-levels" aria-hidden="true">
    {rows.map(l => <div key={l.id} className={`clx-row tone-${l.tone} ${l.key ? 'is-key' : ''} ${l.quiet ? 'is-quiet' : ''}`} data-lv={l.id} data-testid={`chart-level-${l.id}`}>
      <i className="clx-line"><i className="clx-run" /></i>
      {l.quiet ? null : <span className="clx-tag"><b>{l.title}</b>{fmt && l.key ? <small>{fmt(l.px)}</small> : null}<em /></span>}
    </div>)}
  </div>;
}
