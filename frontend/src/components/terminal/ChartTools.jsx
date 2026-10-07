import React, { useEffect, useRef, useState } from 'react';
import { CHART_TOOLS, toggleChartTool, useChartTools } from '../../lib/chartTools';
import '../../styles/chartTools.css';

const VERDICT = { edge: ['🟢', 'EDGE', 'is-edge'], wait: ['🟡', 'WAIT', 'is-wait'], none: ['🔴', 'NO EDGE', 'is-none'] };

// 🧰 The tools button on EVERY chart (top-left, inside PriceChart): tap a tool and its levels are drawn from the candles on screen
// and stay there. ⚡ Meta edge = all four + one read (score · where it stands · the plan). A reading, never a forecast.
export function ChartToolsMenu({ read }) {
  const on = useChartTools(); const [open, setOpen] = useState(false); const [more, setMore] = useState(false); const box = useRef(null);
  useEffect(() => { if (!open) return undefined; const out = e => { if (!box.current?.contains(e.target)) setOpen(false); }; const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', out); document.addEventListener('keydown', esc); return () => { document.removeEventListener('pointerdown', out); document.removeEventListener('keydown', esc); }; }, [open]);
  const e = read?.edge; const v = e ? VERDICT[e.verdict] : null;
  return <div className="ctl" ref={box} data-testid="chart-tools">
    <button type="button" className={`ctl-btn ${on.length ? 'is-on' : ''}`} onClick={() => setOpen(o => !o)} aria-expanded={open} aria-label="Chart tools" data-testid="chart-tools-btn"
      data-tip="Chart tools: FVG · magnets · gun line · germ · meta edge — drawn from the candles on screen, on every chart">🧰{on.length > 0 && <b>{on.includes('edge') ? '⚡' : on.length}</b>}</button>
    {v && <button type="button" className={`ctl-edge ${v[2]}`} onClick={() => setMore(m => !m)} aria-expanded={more} data-testid="chart-edge" data-tip="Meta edge: a read of the candles on screen — tap for the reasons. Never a forecast.">
      {v[0]} <b>{e.score}</b> {v[1]}<span>{e.plan}</span></button>}
    {v && more && <ul className="ctl-why" data-testid="chart-edge-why">{e.why.map(w => <li key={w}>{w}</li>)}<li className="ctl-note">Rules-based read of these candles · not advice</li></ul>}
    {open && <div className="ctl-pop" role="menu" data-testid="chart-tools-pop">{CHART_TOOLS.map(([id, ic, name, tip]) => <button key={id} type="button" role="menuitemcheckbox" aria-checked={on.includes(id)} className={on.includes(id) ? 'active' : ''}
      onClick={() => toggleChartTool(id)} data-testid={`chart-tool-${id}`}><i>{ic}</i><b>{name}</b><small>{tip}</small></button>)}</div>}
  </div>;
}

// Draw the read on the chart: price lines (they ride the price axis) + soft bands for gaps and the germ, from where each began
// to the right edge. Bands are plain divs placed from the chart's own coordinates, refreshed while the chart scrolls / zooms.
export function useToolDraw(seriesRef, chartRef, container, read, deps) {
  const lines = useRef([]);
  useEffect(() => {
    const ref = seriesRef.current; const chart = chartRef.current; const host = container.current;
    const drop = () => { lines.current.forEach(l => { try { ref?.series.removePriceLine(l); } catch { /* chart gone */ } }); lines.current = []; };
    drop();
    if (!ref || !read) return drop;
    const add = (price, color, title, lineStyle = 2, lineWidth = 1) => { if (!(price > 0)) return; try { lines.current.push(ref.series.createPriceLine({ price, color, lineWidth, lineStyle, axisLabelVisible: true, title })); } catch { /* chart torn down */ } };
    const bands = [];
    read.fvg.forEach(g => { add(g.mid, g.dir === 'up' ? '#15d16a' : '#ff8fa3', g.dir === 'up' ? '🪜 gap' : '🪜 gap ↓', 3); bands.push({ top: g.top, bot: g.bot, time: g.time, cls: g.dir === 'up' ? 'ctl-band is-up' : 'ctl-band is-down' }); });
    read.magnets.forEach(m => add(m.price, '#f5c451', `🧲 ${m.hits > 1 ? `×${m.hits} ` : ''}${m.side === 'above' ? 'highs' : 'lows'}`, 1));
    if (read.gun) add(read.gun.price, read.gun.fired ? '#45e486' : '#ff9a3c', read.gun.fired ? '🔫 fired' : '🔫 gun line', 0, 2);
    if (read.germ) { add(read.germ.bot, '#b388ff', read.germ.lost ? '🦠 germ lost' : '🦠 germ', 0); bands.push({ top: read.germ.top, bot: read.germ.bot, time: read.germ.time, cls: 'ctl-band is-germ' }); }
    let layer = null; let timer = null;
    if (host && chart && bands.length) {
      layer = document.createElement('div'); layer.className = 'ctl-bands'; host.appendChild(layer);
      const els = bands.map(b => { const d = document.createElement('i'); d.className = b.cls; layer.appendChild(d); return d; });
      const place = () => { try { const w = host.clientWidth - (chart.priceScale('right').width() || 0);
        bands.forEach((b, i) => { const y1 = ref.series.priceToCoordinate(b.top); const y2 = ref.series.priceToCoordinate(b.bot); const x = chart.timeScale().timeToCoordinate(b.time); const d = els[i];
          if (y1 == null || y2 == null) { d.style.opacity = '0'; return; } const x0 = Math.max(0, x == null ? 0 : x);
          d.style.opacity = '1'; d.style.transform = `translate(${x0}px, ${Math.min(y1, y2)}px)`; d.style.width = `${Math.max(0, w - x0)}px`; d.style.height = `${Math.max(2, Math.abs(y2 - y1))}px`; }); } catch { /* chart torn down */ } };
      place(); timer = setInterval(place, 300);
    }
    return () => { if (timer) clearInterval(timer); if (layer) layer.remove(); drop(); };
  }, [read, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
}
