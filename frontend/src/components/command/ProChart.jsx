import React, { useEffect, useRef, useState } from 'react';
import '../../styles/proChart.css';

// 📈 ONE CHART FOR EVERY RESULT LINE (owner 2026-11-05): TradingView's free Lightweight Charts (Apache 2.0), already what our candles run on. Real axes, crosshair, gradient split at the base line. Zoom and pan stay off: these are read-only.
const ok = v => Number.isFinite(Number(v));
// Times must only go up. A row without a time gets its place in line, and the axis then shows its number.
export function toSeries(rows) {
  let last = 0; const dated = rows.every(r => Number(r.at) > 0);
  return rows.filter(r => ok(r.v)).map((r, i) => { const t = dated ? Math.max(Math.floor(Number(r.at)), last + 1) : i + 1; last = t; return { time: t, value: Number(r.v), row: r }; });
}
export function ProChart({ rows = [], lines = null, base = 0, fmt = v => String(v), height = 220, testid = 'pro-chart', label = 'Chart', tip = null, stamps = true }) {
  const box = useRef(null); const tipEl = useRef(null); const [fail, setFail] = useState(false); const key = JSON.stringify(lines ? lines.map(l => [l.name, l.rows.map(r => [r.at, r.v])]) : rows.map(r => [r.at, r.v]));
  useEffect(() => {
    let chart = null; let gone = false; let ro = null; const list = lines || [{ rows }];
    import('lightweight-charts').then(({ createChart, BaselineSeries, LineSeries, createSeriesMarkers, ColorType, CrosshairMode }) => {
      if (gone || !box.current) return;
      const day = document.body.classList.contains('theme-day'); const ink = day ? '#3f5247' : '#93a4b8'; const grid = day ? '#00000012' : '#ffffff0c'; const edge = day ? '#00000024' : '#ffffff1f';
      const dated = list.every(l => l.rows.every(r => Number(r.at) > 0));
      chart = createChart(box.current, { autoSize: true, layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: ink, fontFamily: 'JetBrains Mono', fontSize: 10, attributionLogo: true }, grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        rightPriceScale: { borderColor: edge, scaleMargins: { top: 0.14, bottom: 0.1 } }, timeScale: { borderColor: edge, timeVisible: stamps && dated, secondsVisible: false, fixLeftEdge: true, fixRightEdge: true, ...(dated ? {} : { tickMarkFormatter: t => `#${t}` }) },
        crosshair: { mode: CrosshairMode.Magnet, vertLine: { color: edge, labelVisible: false }, horzLine: { color: edge, labelVisible: false } }, handleScroll: false, handleScale: false, localization: { priceFormatter: fmt, ...(dated ? {} : { timeFormatter: t => `#${t}` }) } });
      const made = list.map(l => { const data = toSeries(l.rows);
        const s = lines ? chart.addSeries(LineSeries, { color: l.color, lineWidth: 2, priceLineVisible: false, lastValueVisible: true, title: '' })
          : chart.addSeries(BaselineSeries, { baseValue: { type: 'price', price: base }, topLineColor: '#3ee58a', topFillColor1: '#3ee58a44', topFillColor2: '#3ee58a05', bottomLineColor: '#ff8fa3', bottomFillColor1: '#ff8fa305', bottomFillColor2: '#ff8fa344', lineWidth: 2, priceLineVisible: false, lastValueVisible: true });
        s.setData(data.map(({ time, value }) => ({ time, value })));
        if (!lines && data.length > 1 && data.length <= 60) createSeriesMarkers(s, data.map((d, i) => (i && d.row.mark !== false ? { time: d.time, position: 'inBar', color: d.value >= data[i - 1].value ? '#3ee58a' : '#ff8fa3', shape: 'circle', size: 0.6 } : null)).filter(Boolean));
        return { s, l, data }; });
      chart.timeScale().fitContent();
      chart.subscribeCrosshairMove(p => { if (!tipEl.current) return; if (!p?.time || !p.point) { tipEl.current.classList.remove('is-on'); return; }
        const parts = made.map(({ s, l, data }) => { const v = p.seriesData.get(s)?.value; if (v == null) return ''; const row = data.find(d => d.time === p.time)?.row; return `${l.name ? `${l.name} ` : ''}${fmt(v)}${!lines && row && tip ? `<small>${String(tip(row)).replace(/[<>&]/g, '')}</small>` : ''}`; }).filter(Boolean);
        tipEl.current.innerHTML = parts.join('<br/>'); tipEl.current.classList.add('is-on'); });
    }).catch(() => { if (!gone) setFail(true); });
    return () => { gone = true; ro?.disconnect(); if (chart) { chart.remove(); chart = null; } };
  }, [key, base, stamps]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <figure className="pch" data-testid={testid} aria-label={label} role="img" style={{ '--pch-h': `${height}px` }}><div className="pch-box" ref={box} /><div className="pch-tip m-num" ref={tipEl} aria-hidden="true" />{fail ? <figcaption className="pch-fail">The chart could not load.</figcaption> : null}</figure>;
}
