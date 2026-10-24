import React, { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, ColorType, LineStyle, CrosshairMode } from 'lightweight-charts';
import { fetchBars, foldTrade, onTrade, GRAN } from '../../lib/cbFeed';

// 📈 the perps desk's chart: TRUE candles (Coinbase Exchange — a US-regulated venue; the live candle folds every trade as it prints) + volume,
// and YOUR levels on it: entry / mark, ☠ liquidation, TP + SL. TP and SL DRAG straight on the chart before the trade (and on a live
// position): grab a line within 8 px, move, release → `onDrag(id, price)`. Lines: [{ id, price, color, title, drag, dash }].
const near = 8;
export function PerpsChart({ asset, iv = '1m', lines = [], onDrag, onPrice }) {
  const host = useRef(null); const chartRef = useRef(null); const seriesRef = useRef(null); const volRef = useRef(null); const lastRef = useRef(null);
  const drawn = useRef({}); const linesRef = useRef(lines); const drag = useRef(null);
  const [state, setState] = useState('loading'); const [hot, setHot] = useState(null);
  linesRef.current = lines;

  useEffect(() => {   // the chart itself — rebuilt per market / candle size
    if (!host.current) return undefined;
    const chart = createChart(host.current, {
      autoSize: true, layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#c9a3b9', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, attributionLogo: false },
      grid: { vertLines: { color: 'rgba(255,93,187,.05)' }, horzLines: { color: 'rgba(255,93,187,.06)' } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: 'rgba(255,159,210,.45)', labelBackgroundColor: '#ff5dbb' }, horzLine: { color: 'rgba(255,159,210,.45)', labelBackgroundColor: '#ff5dbb' } },
      rightPriceScale: { borderColor: 'rgba(255,93,187,.18)', scaleMargins: { top: 0.08, bottom: 0.22 } },
      timeScale: { borderColor: 'rgba(255,93,187,.18)', timeVisible: true, secondsVisible: false, rightOffset: 6 },
    });
    const series = chart.addSeries(CandlestickSeries, { upColor: '#45e486', downColor: '#ff5d8f', borderUpColor: '#45e486', borderDownColor: '#ff5d8f', wickUpColor: '#45e486', wickDownColor: '#ff5d8f',
      priceLineColor: '#ff9fd2', priceLineStyle: LineStyle.Dotted,
      autoscaleInfoProvider: orig => {   // the scale always holds YOUR levels (TP / SL / positions; ☠ liq when it is within 4 % of the price)
        const r = orig(); if (!r?.priceRange) return r;
        const last = lastRef.current?.close || (r.priceRange.minValue + r.priceRange.maxValue) / 2;
        const ps = (linesRef.current || []).filter(l => l.price > 0 && (l.id !== 'liq' && !String(l.id).startsWith('l') ? true : Math.abs(l.price / last - 1) <= 0.04)).map(l => l.price);
        if (!ps.length) return r;
        return { ...r, priceRange: { minValue: Math.min(r.priceRange.minValue, ...ps), maxValue: Math.max(r.priceRange.maxValue, ...ps) } };
      } });
    const vol = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'v', lastValueVisible: false, priceLineVisible: false });
    chart.priceScale('v').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    chartRef.current = chart; seriesRef.current = series; volRef.current = vol; drawn.current = {}; lastRef.current = null;
    let alive = true; setState('loading');
    const volBar = b => ({ time: b.time, value: b.volume, color: b.close >= b.open ? 'rgba(69,228,134,.35)' : 'rgba(255,93,143,.35)' });
    fetchBars(asset, iv).then(bars => {
      if (!alive) return;
      if (!bars.length) { setState('empty'); return; }
      series.setData(bars); vol.setData(bars.map(volBar)); lastRef.current = bars[bars.length - 1];
      chart.timeScale().scrollToRealTime(); setState('live'); onPrice?.(lastRef.current.close);
    }).catch(() => alive && setState('error'));
    const off = onTrade((a, price, size, t) => {   // every print → the live candle (opens at the previous close; never a gap)
      if (a !== asset || !lastRef.current || !alive) return;
      const next = foldTrade(lastRef.current, price, size, t, GRAN[iv] || 60);
      if (next === lastRef.current) return;
      lastRef.current = next; series.update(next); vol.update(volBar(next));
    });
    return () => { alive = false; off(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, [asset, iv]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {   // YOUR levels: redraw only what changed
    const s = seriesRef.current; if (!s) return;
    const want = Object.fromEntries((lines || []).filter(l => l && l.price > 0).map(l => [l.id, l]));
    Object.entries(drawn.current).forEach(([id, d]) => { if (!want[id] || d.key !== key(want[id])) { try { s.removePriceLine(d.line); } catch { /* chart rebuilt */ } delete drawn.current[id]; } });
    Object.values(want).forEach(l => { if (drawn.current[l.id]) return;
      drawn.current[l.id] = { key: key(l), line: s.createPriceLine({ price: l.price, color: l.color, lineWidth: l.drag ? 2 : 1, lineStyle: l.dash ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title: l.title }) }; });
    if (!drag.current) chartRef.current?.priceScale('right').applyOptions({ autoScale: true });   // re-fit so a new level is on screen (not mid-drag)
  }, [lines, state]);

  useEffect(() => {   // ✋ drag TP / SL on the chart
    const el = host.current; if (!el) return undefined;
    const pick = y => { const s = seriesRef.current; if (!s) return null;
      return (linesRef.current || []).filter(l => l.drag && l.price > 0).map(l => ({ l, d: Math.abs((s.priceToCoordinate(l.price) ?? -1e9) - y) })).filter(x => x.d <= near).sort((a, b) => a.d - b.d)[0]?.l || null; };
    const yOf = e => e.clientY - el.getBoundingClientRect().top;
    const down = e => { const l = pick(yOf(e)); if (!l) return; drag.current = l.id; e.preventDefault(); e.stopPropagation(); el.setPointerCapture?.(e.pointerId);
      chartRef.current?.applyOptions({ handleScroll: false, handleScale: false }); setHot(l.id); };
    const move = e => { if (drag.current) { const p = seriesRef.current?.coordinateToPrice(yOf(e)); if (p > 0) onDrag?.(drag.current, +p.toFixed(p >= 1000 ? 1 : 4)); return; }
      const l = pick(yOf(e)); el.style.cursor = l ? 'ns-resize' : ''; setHot(l ? l.id : null); };
    const up = () => { if (!drag.current) return; drag.current = null; chartRef.current?.applyOptions({ handleScroll: true, handleScale: true }); setHot(null); };
    el.addEventListener('pointerdown', down, true); el.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
    return () => { el.removeEventListener('pointerdown', down, true); el.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
  }, [onDrag]);

  return <div className={`pc ${hot ? 'is-grab' : ''}`} data-testid="perps-chart">
    <div className="pc-canvas" ref={host} />
    {state !== 'live' ? <p className="pc-msg">{state === 'loading' ? 'Loading true candles…' : state === 'empty' ? 'No candles yet.' : 'Coinbase did not answer — retrying on the next pick.'}</p> : null}
    {(lines || []).some(l => l.drag) ? <span className="pc-hint" aria-hidden="true">✋ drag TP / SL</span> : null}
  </div>;
}
const key = l => `${l.price}|${l.color}|${l.title}|${l.drag ? 1 : 0}`;
