import React, { useEffect, useRef, useState } from 'react';
import { grabLevels, snapLevel } from '../../lib/chartGrab';
import '../../styles/chartGrab.css';

// ✋ Grab handles on a Fuse coin's chart: one tab per level the card lets you move (stop · lock / take-profit · trail). Drag it up
// or down — it moves 1% at a time and shows the new % while you hold it; letting go ASKS (event
// `feeless:fuse-level` → the real card confirms and saves). Nothing changes on a cancelled drop.
export function ChartGrab({ seriesRef, container, fuse, ratio = 1 }) {
  const levels = grabLevels(fuse); const key = levels.map(l => `${l.kind}:${l.pct}`).join('|');
  const [ys, setYs] = useState({}); const [drag, setDrag] = useState(null); const dragRef = useRef(null);
  const yOf = p => { try { const y = seriesRef.current?.series.priceToCoordinate(p * ratio); return y == null ? null : y + (container.current?.offsetTop || 0); } catch { return null; } };
  useEffect(() => { if (!key) return undefined;
    const place = () => { const next = {}; levels.forEach(l => { const y = yOf(l.price); if (y != null) next[l.kind] = Math.round(y); }); setYs(o => (JSON.stringify(o) === JSON.stringify(next) ? o : next)); };
    place(); const t = setInterval(place, 300); return () => clearInterval(t); }, [key, ratio]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!levels.length) return null;
  const down = l => e => { e.preventDefault(); e.currentTarget.setPointerCapture?.(e.pointerId); dragRef.current = { l, top: container.current?.getBoundingClientRect().top || 0 }; setDrag({ kind: l.kind, pct: l.pct, price: l.price }); };
  const move = e => { const d = dragRef.current; if (!d) return; let px = null; try { px = seriesRef.current?.series.coordinateToPrice(e.clientY - d.top); } catch { px = null; }
    const s = px > 0 ? snapLevel(d.l.kind, px / ratio, d.l.from) : null; if (s) setDrag({ kind: d.l.kind, ...s }); };
  const up = () => { const d = dragRef.current; dragRef.current = null; const cur = drag; setDrag(null);
    if (d && cur && cur.pct !== d.l.pct) window.dispatchEvent(new CustomEvent('feeless:fuse-level', { detail: { tpl: fuse.tpl, pairAddress: fuse.pairAddress, symbol: fuse.symbol, kind: cur.kind, pct: cur.pct } })); };
  return <div className="cgr" data-testid="chart-grab">{levels.map(l => { const on = drag?.kind === l.kind; const y = on ? yOf(drag.price) : ys[l.kind]; if (y == null) return null; const pct = on ? drag.pct : l.pct;
    return <div key={l.kind} className={`cgr-row is-${l.kind} ${on ? 'is-drag' : ''}`} style={{ transform: `translateY(${y}px)` }}>
      <button type="button" className="cgr-tab" onPointerDown={down(l)} onPointerMove={move} onPointerUp={up} onPointerCancel={up} data-testid={`grab-${l.kind}`} aria-label={`Drag to move the ${l.name}`}
        data-tip={`Grab and drag: ${l.name} ${l.sign > 0 ? '+' : '−'}${l.pct}% ${l.base === 'peak' ? 'off its peak' : 'from entry'} — ${l.scope === 'coin' ? 'this coin only' : 'the card\'s setting (every coin)'}. Moves 1% at a time (${l.min}–${l.max}%). Asks before saving.`}>
        <i aria-hidden>⠿</i>{l.ic} {l.sign > 0 ? '+' : '−'}{pct}%</button><i className="cgr-line" aria-hidden /></div>; })}</div>;
}
