import React, { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries, ColorType, LineStyle, CrosshairMode } from 'lightweight-charts';
import { ema, vwap, bollinger, rsi } from '../../lib/indicators';
import { fetchBars, foldTrade, onTrade, GRAN } from '../../lib/cbFeed';

// 📈 the perps desk's chart: TRUE candles (Coinbase Exchange — a US-regulated venue; the live candle folds every trade as it prints) + volume,
// and YOUR levels on it: entry / mark, ☠ liquidation, TP + SL. TP and SL DRAG straight on the chart before the trade (and on a live
// position): grab a line within 8 px, move, release → `onDrag(id, price)`. Lines: [{ id, price, color, title, drag, dash }].
// `ind` = the indicators on (lib/indicators: EMA 9/21 · VWAP · BB 20·2 on the price pane, RSI 14 in its own pane) — recomputed from the
// true candles at most once a second while trades print.
const near = 8;
export function PerpsChart({ asset, iv = '1m', lines = [], onDrag, onPrice, ind = [] }) {
  const host = useRef(null); const chartRef = useRef(null); const seriesRef = useRef(null); const volRef = useRef(null); const lastRef = useRef(null);
  const drawn = useRef({}); const linesRef = useRef(lines); const drag = useRef(null); const barsRef = useRef([]); const indRef = useRef({}); const indOn = useRef(ind); const paint = useRef(() => {});
  indOn.current = ind;
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
    chartRef.current = chart; seriesRef.current = series; volRef.current = vol; drawn.current = {}; lastRef.current = null; indRef.current = {};
    const line = (id, color, w = 1, pane = 0, dash = false) => indRef.current[id] || (indRef.current[id] = chart.addSeries(LineSeries, { color, lineWidth: w, lineStyle: dash ? LineStyle.Dashed : LineStyle.Solid,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }, pane));
    let paintAt = 0;
    paint.current = (force = false) => {   // the indicators on, from the bars loaded + the live candle (≤ 1 / s while trades print)
      const now = Date.now(); if (!force && now - paintAt < 1000) return; paintAt = now;
      const bars = barsRef.current; const on = new Set(indOn.current || []);
      const set = (id, data, color, w, pane, dash) => { if (data) line(id, color, w, pane, dash).setData(data); else if (indRef.current[id]) indRef.current[id].setData([]); };
      set('e9', on.has('ema') ? ema(bars, 9) : null, '#ffd36b', 1.5); set('e21', on.has('ema') ? ema(bars, 21) : null, '#9b8cff', 1.5);
      set('vw', on.has('vwap') ? vwap(bars) : null, '#6ad7ff', 2, 0, true);
      const bb = on.has('bb') ? bollinger(bars, 20, 2) : null;
      set('bu', bb && bb.upper, 'rgba(255,159,210,.65)', 1); set('bm', bb && bb.mid, 'rgba(255,159,210,.35)', 1, 0, true); set('bl', bb && bb.lower, 'rgba(255,159,210,.65)', 1);
      if (on.has('rsi')) { const r = line('rsi', '#ff9fd2', 1.5, 1); r.setData(rsi(bars, 14));
        if (!indRef.current.rsiLines) { r.createPriceLine({ price: 70, color: 'rgba(255,93,143,.5)', lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: '70' });
          r.createPriceLine({ price: 30, color: 'rgba(69,228,134,.5)', lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: '30' }); indRef.current.rsiLines = true; }
        try { chart.panes()[1]?.setHeight(110); } catch { /* older pane api */ } }
      else if (indRef.current.rsi) { try { chart.removeSeries(indRef.current.rsi); } catch { /* gone */ } delete indRef.current.rsi; delete indRef.current.rsiLines; }
    };
    let alive = true; setState('loading');
    const volBar = b => ({ time: b.time, value: b.volume, color: b.close >= b.open ? 'rgba(69,228,134,.35)' : 'rgba(255,93,143,.35)' });
    fetchBars(asset, iv).then(bars => {
      if (!alive) return;
      if (!bars.length) { setState('empty'); return; }
      series.setData(bars); vol.setData(bars.map(volBar)); lastRef.current = bars[bars.length - 1]; barsRef.current = bars; paint.current(true);
      chart.timeScale().scrollToRealTime(); setState('live'); onPrice?.(lastRef.current.close);
    }).catch(() => alive && setState('error'));
    const off = onTrade((a, price, size, t) => {   // every print → the live candle (opens at the previous close; never a gap)
      if (a !== asset || !lastRef.current || !alive) return;
      const next = foldTrade(lastRef.current, price, size, t, GRAN[iv] || 60);
      if (next === lastRef.current) return;
      lastRef.current = next; series.update(next); vol.update(volBar(next));
      const bs = barsRef.current; barsRef.current = bs.length && bs[bs.length - 1].time === next.time ? [...bs.slice(0, -1), next] : [...bs, next]; paint.current();
    });
    return () => { alive = false; off(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, [asset, iv]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { paint.current(true); }, [ind.join('|')]); // eslint-disable-line react-hooks/exhaustive-deps

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
