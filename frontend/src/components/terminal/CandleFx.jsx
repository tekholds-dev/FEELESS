import { addChartJob } from '../../lib/chartFrame';
import React, { useEffect, useRef } from 'react';
import '../../styles/candleFx.css';

// ⚡ CANDLE FX (owner, 2026-10-13: "chart themes more meta, effects per candle — no lag"): the forming candle has an aura that rides its
// drawn close, every REAL tick (the bar's own close changing — never the eased value in between) throws a ring, a ≥ 1% tick bursts sparks,
// and a new candle opening flashes its column. The chart area gets `cfk-up` / `cfk-dn` so a scene (⚡ Neon trench) can follow the candle.
// ONE rAF loop ≤ 30fps writing transforms + classes straight to the DOM (no React render per frame); transform / opacity only; nothing in
// a hidden tab, fx-lite or reduced motion. Never interactive.
const SPARKS = 6;
const kick = (el, cls) => { if (!el) return; el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); };

export function CandleFx({ seriesRef, chartRef, lastBarRef, shownRef, container }) {
  const host = useRef(null);
  useEffect(() => {
    const root = host.current;
    if (!root) return undefined;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches) return undefined;
    const aura = root.querySelector('.cfk-aura'); const ring = root.querySelector('.cfk-ring'); const open = root.querySelector('.cfk-open'); const spark = root.querySelector('.cfk-spark');
    const area = root.parentElement;
    let tick = null; let barT = null; let ringAt = 0; let sparkAt = 0; let dir = 0; let hh = -1;
    const step = t => {
      if (document.hidden || document.body.classList.contains('fx-lite')) return;
      const s = seriesRef.current?.series; const c = chartRef?.current; const box = container?.current; const bar = lastBarRef.current;
      if (!s || !c || !box || !bar) return;
      const px = shownRef?.current ?? bar.close ?? bar.value; const real = bar.close ?? bar.value;
      if (!(px > 0)) return;
      let x; let y;
      try { x = c.timeScale().timeToCoordinate(bar.time); y = s.priceToCoordinate(px); } catch { return; }
      if (x == null || y == null) return;
      const top = box.offsetTop || 0; const left = box.offsetLeft || 0; const h = box.clientHeight || 0;
      const at = `translate3d(${(x + left).toFixed(1)}px, ${(y + top).toFixed(1)}px, 0)`;
      aura.style.transform = at; aura.style.opacity = '1';
      const up = px >= (bar.open ?? px);
      if (dir !== (up ? 1 : -1)) {   // the candle changed colour: the aura and any reactive scene follow it
        dir = up ? 1 : -1;
        aura.classList.toggle('is-dn', !up); area?.classList.toggle('cfk-up', up); area?.classList.toggle('cfk-dn', !up);
      }
      if (tick != null && real !== tick && t - ringAt > 220) {   // a REAL tick (the bar's own close moved)
        ringAt = t;
        ring.style.transform = at; ring.classList.toggle('is-dn', real < tick); kick(ring, 'is-on');
        if (Math.abs(real / tick - 1) >= 0.01 && t - sparkAt > 700) {   // a ≥ 1% tick: sparks
          sparkAt = t; spark.style.transform = at; spark.classList.toggle('is-dn', real < tick); kick(spark, 'is-on');
        }
      }
      tick = real;
      if (h !== hh) { hh = h; open.style.height = `${h}px`; }
      if (barT != null && bar.time !== barT) { open.style.transform = `translate3d(${(x + left).toFixed(1)}px, ${top}px, 0)`; kick(open, 'is-on'); }   // a new candle opened
      barT = bar.time;
    };
    const stop = addChartJob(container, step);   // ⚡ the shared chart frame: runs only when this chart changed
    return () => { stop(); area?.classList.remove('cfk-up', 'cfk-dn'); };
  }, [seriesRef, chartRef, lastBarRef, shownRef, container]);
  return <div className="cfk" ref={host} aria-hidden="true" data-testid="candle-fx">
    <span className="cfk-aura"><i /></span>
    <span className="cfk-ring"><i /></span>
    <span className="cfk-open" />
    <span className="cfk-spark">{Array.from({ length: SPARKS }, (_, i) => <b key={i} style={{ '--i': i }} />)}</span>
  </div>;
}
