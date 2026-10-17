import { addChartJob } from '../../lib/chartFrame';
import React, { useEffect, useRef } from 'react';
import '../../styles/candleClock.css';

// ⏱ CANDLE CLOCK (owner, 2026-10-16: "TradingView-style countdown to the candle close"): a small tag under the live price on the price axis
// that counts down to the forming candle's close (mm:ss, h:mm:ss for 1h+). Rides the shared chart frame (moves with the price, the text
// updates on the 1s safety refresh) — no own timer, no React render per second. The last 10s glow.

/** Seconds left in the candle of `bucketSec` at unix second `nowSec` → "0:42" / "1:04:12". */
export function clockWord(nowSec, bucketSec) {
  const b = Math.max(1, Math.round(Number(bucketSec) || 60));
  const left = b - (Math.floor(Number(nowSec) || 0) % b);
  const h = Math.floor(left / 3600); const m = Math.floor((left % 3600) / 60); const s = left % 60;
  const ss = String(s).padStart(2, '0');
  return { left, word: h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}` };
}

export function CandleClock({ seriesRef, chartRef, lastBarRef, shownRef, container, bucketSec }) {
  const tag = useRef(null);
  useEffect(() => addChartJob(container, () => {
    const el = tag.current; const s = seriesRef.current?.series; const c = chartRef?.current; const box = container?.current; const bar = lastBarRef.current;
    if (!el || !s || !c || !box || !bar) return;
    const px = shownRef?.current ?? bar.close ?? bar.value;
    let y; let axis = 56;
    try { y = s.priceToCoordinate(px); axis = c.priceScale('right').width() || axis; } catch { return; }
    if (y == null) { el.style.opacity = '0'; return; }
    const { left, word } = clockWord(Date.now() / 1000, bucketSec);
    if (el.textContent !== word) el.textContent = word;
    el.classList.toggle('is-end', left <= 10);
    const x = (box.offsetLeft || 0) + box.clientWidth - axis;
    el.style.width = `${axis}px`;
    el.style.transform = `translate3d(${x.toFixed(1)}px, ${((box.offsetTop || 0) + y + 11).toFixed(1)}px, 0)`;
    el.style.opacity = '1';
  }), [seriesRef, chartRef, lastBarRef, shownRef, container, bucketSec]);
  return <span ref={tag} className="cck" data-testid="candle-clock" aria-label="time to candle close" />;
}
