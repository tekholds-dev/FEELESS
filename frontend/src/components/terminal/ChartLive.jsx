import { addChartJob } from '../../lib/chartFrame';
import React, { useEffect, useRef } from 'react';
import '../../styles/chartLive.css';

// 🟢 THE TRADE, ON THE CANDLES (owner, 2026-10-12: "meta styled buy and live moving pnl that moves with the current candle"). Two things
// drawn over the plot from the chart's OWN scale: a BUY chip pinned at the entry (its price level, at the buy's candle when it is on
// screen) and a P&L tag that RIDES THE LIVE CANDLE — it sits at the price the forming candle shows right now (the same eased value the
// candle body is drawn with) and moves with every real tick. One rAF loop at ≤ 30fps that writes transforms + text straight to the DOM:
// no React render per frame, nothing invented between ticks.
const GAP = 28;   // px between the forming candle and the live P&L tag (a dotted leader joins them)
export const liveRead = (entry, px, usd) => {
  const e = Number(entry); const p = Number(px);
  if (!(e > 0) || !(p > 0)) return null;
  const pct = (p / e - 1) * 100; const cost = Number(usd);
  return { pct, usd: cost > 0 ? cost * (p / e - 1) : null, up: pct >= 0 };
};
export const pctWord = v => (Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2)}%`);
export const usdWord = v => (v == null ? '' : `${v >= 0 ? '+' : '−'}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(Math.abs(v) < 1 ? 3 : 2)}`);

// 🫀 THE ENTRY VITAL (owner, 2026-10-19: "better buy indicator — a small vital that plays out based on data when entered"): a 16px ring at
// the entry whose arc fills with the move since the buy (full = ±50%), green / pink, its core beating while the trade is live; beside it
// the move and how long it has been held. Pure helpers below; the frame writes the arc + text straight to the DOM.
export const RING = 2 * Math.PI * 6;
export const ringFill = pct => Math.max(0.04, Math.min(1, Math.abs(Number(pct) || 0) / 50));
export const heldWord = (at, now = Date.now() / 1000) => { const s = Math.max(0, now - (Number(at) || now)); return s < 3600 ? `${Math.floor(s / 60)}m` : `${(s / 3600).toFixed(1)}h`; };

export function ChartLive({ seriesRef, chartRef, lastBarRef, shownRef, container, ratio = 1, entry, usd = null, at = null, label = 'YOU', entryWord = null }) {
  const tag = useRef(null); const lead = useRef(null); const buy = useRef(null); const pctEl = useRef(null); const usdEl = useRef(null); const line = useRef(null); const arc = useRef(null); const vit = useRef(null);
  useEffect(() => {
    if (!(Number(entry) > 0)) return undefined;
    let lastTxt = ''; let lastUp = null; let axis = 62; let axisAt = 0; let tagW = 90;
    const step = t => {
      const s = seriesRef.current?.series; const bar = lastBarRef.current; const el = tag.current; const be = buy.current;
      if (!s || !bar || !el || !be) return;
      const px = shownRef?.current ?? bar.close ?? bar.value; const e = Number(entry) * ratio; const top = container?.current?.offsetTop || 0; const h = container?.current?.clientHeight || 0;
      let y = null; let ye = null; let x = null;
      try { y = s.priceToCoordinate(px); ye = s.priceToCoordinate(e); if (at && chartRef?.current) x = chartRef.current.timeScale().timeToCoordinate(at); } catch { return; }
      const clamp = v => Math.max(10, Math.min(Math.max(10, h - 34), v));
      // 🕯 the tag sits RIGHT BESIDE the forming candle (owner, 2026-10-14: "live pnl beside the latest candle"), never past the price axis
      if (t - axisAt > 1000) { axisAt = t; try { axis = Math.round(chartRef?.current?.priceScale('right').width() || axis); } catch { /* chart gone */ } }
      const w = container?.current?.clientWidth || 0; const maxX = Math.max(0, w - axis - tagW - 4);
      let xc = null; try { xc = chartRef?.current?.timeScale().timeToCoordinate(bar.time); } catch { xc = null; }
      const xt = Math.max(0, Math.min(maxX, xc != null ? xc + GAP : maxX));   // 📍 off the candle (owner, 2026-10-14: "too close to the current candle")
      if (lead.current) { const x0 = xc != null ? xc + 4 : xt; lead.current.style.transform = `translate3d(${x0.toFixed(0)}px, ${(clamp(y ?? 0) + top + 8).toFixed(1)}px, 0) scaleX(${Math.max(0, xt - x0).toFixed(0)})`; }
      if (y != null) { el.style.transform = `translate3d(${xt.toFixed(0)}px, ${(clamp(y) + top).toFixed(1)}px, 0)`; el.style.opacity = '1'; }
      if (ye != null) {
        const off = ye < 10 || ye > h - 34;   // the entry is off the visible scale: the chip waits at the edge and says which way
        let yb = clamp(ye) + top;
        if (!(x != null && x > 40)) {   // 📌 pinned at the left edge: never under the vitals badge (the BUY chip sat on it)
          const vb = container?.current?.querySelector?.('.cpl'); const cb = container?.current?.getBoundingClientRect?.();
          if (vb && cb) { const r0 = vb.getBoundingClientRect(); const t0 = r0.top - cb.top; const b0 = r0.bottom - cb.top; if (yb + 18 > t0 && yb < b0) yb = b0 + 4; }
        }
        be.style.transform = `translate3d(${x != null && x > 40 ? Math.round(x) : 0}px, ${yb.toFixed(1)}px, 0)`; be.style.opacity = '1';
        be.classList.toggle('is-off', off); be.classList.toggle('is-pinned', !(x != null && x > 40));
        if (line.current && y != null) { const a = clamp(ye) + top; const b = clamp(y) + top; line.current.style.transform = `translate3d(${Math.max(0, xt - 4).toFixed(0)}px, ${Math.min(a, b).toFixed(1)}px, 0) scaleY(${Math.max(1, Math.abs(b - a)).toFixed(1)})`; }
      }
      const r = liveRead(e, px, usd); if (!r) return;
      const txt = `${pctWord(r.pct)}|${usdWord(r.usd)}`;
      if (txt !== lastTxt) { if (arc.current) arc.current.style.strokeDashoffset = (RING * (1 - ringFill(r.pct))).toFixed(1); if (vit.current) vit.current.textContent = `${pctWord(r.pct)}${at ? ` · ${heldWord(at)}` : ''}`; be.classList.toggle('is-dn', !r.up); lastTxt = txt; if (pctEl.current) pctEl.current.textContent = pctWord(r.pct); if (usdEl.current) usdEl.current.textContent = usdWord(r.usd); tagW = el.offsetWidth || tagW; }
      if (r.up !== lastUp) { lastUp = r.up; el.classList.toggle('is-up', r.up); el.classList.toggle('is-dn', !r.up); if (line.current) { line.current.classList.toggle('is-up', r.up); line.current.classList.toggle('is-dn', !r.up); } }
    };
    return addChartJob(container, step);   // ⚡ the shared chart frame: runs only when this chart changed
  }, [entry, ratio, usd, at, seriesRef, chartRef, lastBarRef, shownRef, container]);
  if (!(Number(entry) > 0)) return null;
  return <div className="clv2" data-testid="chart-live" aria-hidden="true">
    <i className="clv2-line" ref={line} />
    <i className="clv2-lead" ref={lead} />
    <div className="clv2-buy" ref={buy} data-testid="chart-live-buy">
      <svg className="clv2-ring" viewBox="0 0 16 16"><circle className="clv2-ring-bg" cx="8" cy="8" r="6" /><circle className="clv2-ring-arc" ref={arc} cx="8" cy="8" r="6" strokeDasharray={RING.toFixed(1)} strokeDashoffset={RING.toFixed(1)} /><circle className="clv2-ring-core" cx="8" cy="8" r="2.2" /></svg>
      <b ref={vit}>{entryWord || 'IN'}</b>
    </div>
    <div className="clv2-tag" ref={tag} data-testid="chart-live-tag"><small>{label}</small><b ref={pctEl}>—</b><span ref={usdEl} /><i className="clv2-dot" /></div>
  </div>;
}
