import React, { useEffect, useRef } from 'react';
import '../../styles/chartLive.css';

// 🟢 THE TRADE, ON THE CANDLES (owner, 2026-10-12: "meta styled buy and live moving pnl that moves with the current candle"). Two things
// drawn over the plot from the chart's OWN scale: a BUY chip pinned at the entry (its price level, at the buy's candle when it is on
// screen) and a P&L tag that RIDES THE LIVE CANDLE — it sits at the price the forming candle shows right now (the same eased value the
// candle body is drawn with) and moves with every real tick. One rAF loop at ≤ 30fps that writes transforms + text straight to the DOM:
// no React render per frame, nothing invented between ticks.
export const liveRead = (entry, px, usd) => {
  const e = Number(entry); const p = Number(px);
  if (!(e > 0) || !(p > 0)) return null;
  const pct = (p / e - 1) * 100; const cost = Number(usd);
  return { pct, usd: cost > 0 ? cost * (p / e - 1) : null, up: pct >= 0 };
};
export const pctWord = v => (Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2)}%`);
export const usdWord = v => (v == null ? '' : `${v >= 0 ? '+' : '−'}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(Math.abs(v) < 1 ? 3 : 2)}`);

export function ChartLive({ seriesRef, chartRef, lastBarRef, shownRef, container, ratio = 1, entry, usd = null, at = null, label = 'YOU', entryWord = null }) {
  const tag = useRef(null); const buy = useRef(null); const pctEl = useRef(null); const usdEl = useRef(null); const line = useRef(null);
  useEffect(() => {
    if (!(Number(entry) > 0) || typeof requestAnimationFrame === 'undefined') return undefined;
    let alive = true; let raf = 0; let last = 0; let lastTxt = ''; let lastUp = null; let axis = 62; let axisAt = 0; let tagW = 90;
    const step = t => {
      if (!alive) return;
      raf = requestAnimationFrame(step);
      if (t - last < 33) return;
      last = t;
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
      const xt = Math.max(0, Math.min(maxX, xc != null ? xc + 9 : maxX));
      if (y != null) { el.style.transform = `translate3d(${xt.toFixed(0)}px, ${(clamp(y) + top).toFixed(1)}px, 0)`; el.style.opacity = '1'; }
      if (ye != null) {
        const off = ye < 10 || ye > h - 34;   // the entry is off the visible scale: the chip waits at the edge and says which way
        be.style.transform = `translate3d(${x != null && x > 40 ? Math.round(x) : 0}px, ${(clamp(ye) + top).toFixed(1)}px, 0)`; be.style.opacity = '1';
        be.classList.toggle('is-off', off); be.classList.toggle('is-pinned', !(x != null && x > 40));
        if (line.current && y != null) { const a = clamp(ye) + top; const b = clamp(y) + top; line.current.style.transform = `translate3d(${Math.max(0, xt - 4).toFixed(0)}px, ${Math.min(a, b).toFixed(1)}px, 0) scaleY(${Math.max(1, Math.abs(b - a)).toFixed(1)})`; }
      }
      const r = liveRead(e, px, usd); if (!r) return;
      const txt = `${pctWord(r.pct)}|${usdWord(r.usd)}`;
      if (txt !== lastTxt) { lastTxt = txt; if (pctEl.current) pctEl.current.textContent = pctWord(r.pct); if (usdEl.current) usdEl.current.textContent = usdWord(r.usd); tagW = el.offsetWidth || tagW; }
      if (r.up !== lastUp) { lastUp = r.up; el.classList.toggle('is-up', r.up); el.classList.toggle('is-dn', !r.up); if (line.current) { line.current.classList.toggle('is-up', r.up); line.current.classList.toggle('is-dn', !r.up); } }
    };
    raf = requestAnimationFrame(step);
    return () => { alive = false; cancelAnimationFrame(raf); };
  }, [entry, ratio, usd, at, seriesRef, chartRef, lastBarRef, shownRef, container]);
  if (!(Number(entry) > 0)) return null;
  return <div className="clv2" data-testid="chart-live" aria-hidden="true">
    <i className="clv2-line" ref={line} />
    <div className="clv2-buy" ref={buy} data-testid="chart-live-buy"><b>▲ BUY</b>{entryWord ? <span>{entryWord}</span> : null}</div>
    <div className="clv2-tag" ref={tag} data-testid="chart-live-tag"><small>{label}</small><b ref={pctEl}>—</b><span ref={usdEl} /><i className="clv2-dot" /></div>
  </div>;
}
