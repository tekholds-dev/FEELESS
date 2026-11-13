import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, MarkLineComponent, MarkPointComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { usd as money } from './KeepDeal';
import { isCalm } from '../../lib/fxPause';
import '../../styles/stakeFlow.css';

echarts.use([LineChart, GridComponent, MarkLineComponent, MarkPointComponent, TooltipComponent, CanvasRenderer]);

// 📈 How an example pool profit fills a stake up to its limit, on the same rules as the ledger.
const day = () => document.body.classList.contains('theme-day');
const inks = () => (day() ? { text: '#3b4a60', grid: '#0f1f3a18', line: '#b57a12', soft: '#0f1f3a40', tip: '#ffffff', tipText: '#101826', chip: '#ffffff' } : { text: '#aab6cc', grid: '#ffffff12', line: '#ffc24d', soft: '#ffffff40', tip: '#0b111c', tipText: '#eef3ff', chip: '#0b111c' });
function Plot({ option, testid, label }) {
  const box = useRef(null); const chart = useRef(null);
  useEffect(() => { let raf = 0; const c = echarts.init(box.current, null, { renderer: 'canvas' }); chart.current = c; const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => c.resize()); }); ro?.observe(box.current); return () => { cancelAnimationFrame(raf); ro?.disconnect(); c.dispose(); }; }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { chart.current?.setOption({ animation: !isCalm(), animationDuration: 260, ...option }, true); }, [option]);
  return <div ref={box} className="skc-plot" role="img" aria-label={label} data-testid={testid} />;
}
const tip = c => ({ trigger: 'axis', backgroundColor: c.tip, borderColor: c.soft, textStyle: { color: c.tipText, fontSize: 12 }, confine: true });

// What it would earn if the pools made this much: its seat of each day's profit, until its points run out. An example on the viewer's own number.
export const earnRows = (points, seat, profitDay, days = 360) => { const out = []; const step = Math.max(1, Math.round(days / 72)); for (let d = 0; d <= days; d += step) out.push([d, Math.min(points, seat / 100 * profitDay * d)]); return out; };
export const capDay = (points, seat, profitDay) => (seat > 0 && profitDay > 0 ? Math.ceil(points / (seat / 100 * profitDay)) : null);
export function EarnLine({ points, seat, profitDay, testid = 'stake-earn' }) {
  const c = inks(); const hit = capDay(points, seat, profitDay); const inside = hit != null && hit <= 360; const span = inside ? Math.max(14, Math.min(360, Math.ceil(hit * 1.5))) : 360; const rows = earnRows(points, seat, profitDay, span);   // the view fits the climb, so a limit reached on day 5 is not a wall
  const option = { grid: { left: 52, right: 16, top: 18, bottom: 26 }, tooltip: { ...tip(c), formatter: ps => `Day ${ps[0].value[0]}<br/><b>${money(ps[0].value[1])}</b> earned` }, xAxis: { type: 'value', min: 0, max: span, minInterval: 1, axisLabel: { color: c.text, fontSize: 10, formatter: 'Day {value}' }, axisLine: { lineStyle: { color: c.soft } }, splitLine: { show: false } }, yAxis: { type: 'value', max: v => Math.max(points * 1.12, v.max), axisLabel: { color: c.text, fontSize: 10, formatter: v => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(v < 10 ? 1 : 0)}`) }, splitLine: { lineStyle: { color: c.grid } } },
    series: [{ name: 'Earned', type: 'line', showSymbol: false, lineStyle: { width: 2, color: '#b48cff' }, itemStyle: { color: '#b48cff' }, areaStyle: { color: '#b48cff1f' }, data: rows, markLine: { silent: true, symbol: 'none', lineStyle: { color: c.line, type: 'dashed', width: 1.5 }, label: { color: c.text, fontSize: 10, fontFamily: 'JetBrains Mono, monospace', position: 'insideStartTop', distance: 6, padding: [3, 7], borderRadius: 6, backgroundColor: c.chip, borderColor: c.line, borderWidth: 1, formatter: `ITS LIMIT ${money(points)}` }, data: [{ yAxis: points }] },   // 🏷 owner 2026-11-12: the label sat on the line where it flattens; it reads at the start now
      markPoint: inside ? { silent: true, symbol: 'circle', symbolSize: 9, itemStyle: { color: '#b48cff', borderColor: '#fff', borderWidth: 1.5 }, label: { show: true, position: 'bottom', distance: 8, color: c.text, fontSize: 10, fontFamily: 'JetBrains Mono, monospace', formatter: `LIMIT HIT · DAY ${hit}` }, data: [{ coord: [hit, points] }] } : undefined }] };
  return <Plot option={option} testid={testid} label={inside ? `At this profit it reaches its ${money(points)} limit around day ${hit}` : `At this profit it earns ${money(rows[rows.length - 1][1])} in a year, under its ${money(points)} limit`} />;
}
