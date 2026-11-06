import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, MarkLineComponent, MarkPointComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { boostX, seatOf, usd as money } from './KeepDeal';
import { isCalm } from '../../lib/fxPause';
import '../../styles/stakeFlow.css';

echarts.use([LineChart, GridComponent, MarkLineComponent, MarkPointComponent, TooltipComponent, CanvasRenderer]);

// 📈 The stake's two pictures, on the same rules as the ledger: how big the seat gets, and how an example pool profit fills it up to its limit.
const day = () => document.body.classList.contains('theme-day');
const inks = () => (day() ? { text: '#3b4a60', grid: '#0f1f3a18', line: '#b57a12', soft: '#0f1f3a40', tip: '#ffffff', tipText: '#101826' } : { text: '#aab6cc', grid: '#ffffff12', line: '#ffc24d', soft: '#ffffff40', tip: '#0b111c', tipText: '#eef3ff' });
function Plot({ option, testid, label, onReady }) {
  const box = useRef(null); const chart = useRef(null);
  useEffect(() => { let raf = 0; const c = echarts.init(box.current, null, { renderer: 'canvas' }); chart.current = c; onReady?.(c); const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => c.resize()); }); ro?.observe(box.current); return () => { cancelAnimationFrame(raf); ro?.disconnect(); c.dispose(); }; }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { chart.current?.setOption({ animation: !isCalm(), animationDuration: 260, ...option }, true); }, [option]);
  return <div ref={box} className="skc-plot" role="img" aria-label={label} data-testid={testid} />;
}
const usdShort = v => (v >= 1000 ? `$${v / 1000}K` : `$${v}`);
const X_STOPS = [];
for (let e = 0; e <= 5; e += 0.1) X_STOPS.push(10 ** e);
const tip = c => ({ trigger: 'axis', backgroundColor: c.tip, borderColor: c.soft, textStyle: { color: c.tipText, fontSize: 12 }, confine: true });

// How big the seat gets for any send. Tap the chart to try a size. The bend is where dollars stop lifting it as fast.
export function SeatCurve({ rules, usd, grade, onPick, testid = 'stake-seat' }) {
  const c = inks(); const seat = (g, u) => seatOf(rules, boostX(g), u); const knee = rules?.kneeUsd ?? 1000; const pick = useRef(onPick); pick.current = onPick; const line = (g, on) => ({ name: on ? `Score ${Math.round(g)}` : `Score ${g}`, type: 'line', showSymbol: false, smooth: false, z: on ? 3 : 1, lineStyle: { width: 2, color: on ? c.line : c.soft }, itemStyle: { color: on ? c.line : c.soft }, data: X_STOPS.map(u => [u, +seat(g, u).toFixed(3)]), endLabel: { show: !on, formatter: `${g}`, color: c.text, fontSize: 10 } });
  const option = { grid: { left: 40, right: 34, top: 14, bottom: 26 }, tooltip: { ...tip(c), formatter: ps => `<b>${money(ps[0].value[0])}</b><br/>${ps.map(p => `${p.seriesName}: ${p.value[1].toFixed(2)}%`).join('<br/>')}` }, xAxis: { type: 'log', logBase: 10, min: 1, max: 100000, axisLabel: { color: c.text, fontSize: 10, formatter: usdShort }, axisLine: { lineStyle: { color: c.soft } }, splitLine: { show: false } }, yAxis: { type: 'value', axisLabel: { color: c.text, fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: c.grid } } },
    series: [line(100), line(300), { ...line(grade, true), markPoint: { symbol: 'circle', symbolSize: 12, itemStyle: { color: c.line, borderColor: c.tip, borderWidth: 2 }, label: { show: true, position: 'top', color: c.tipText, fontSize: 11, fontWeight: 700, formatter: `${seat(grade, usd).toFixed(2)}%` }, data: [{ coord: [Math.max(1, usd), seat(grade, usd)] }] }, markLine: { silent: true, symbol: 'none', lineStyle: { color: c.soft, type: 'dashed', width: 1 }, label: { color: c.text, fontSize: 10, formatter: `${usdShort(knee)}: slows here`, position: 'insideEndTop' }, data: [{ xAxis: knee }] } }] };
  const ready = chart => chart.getZr().on('click', e => { if (!chart.containPixel('grid', [e.offsetX, e.offsetY])) return; const u = chart.convertFromPixel({ xAxisIndex: 0 }, e.offsetX); if (u >= 1) pick.current?.(u); });
  return <Plot option={option} testid={testid} label={`Seat for each size of send at score ${Math.round(grade)}. Now ${seat(grade, usd).toFixed(2)}% at ${money(usd)}`} onReady={ready} />;
}

// What it would earn if the pools made this much: its seat of each day's profit, until its points run out. An example on the viewer's own number.
export const earnRows = (points, seat, profitDay, days = 360) => { const out = []; const step = Math.max(1, Math.round(days / 72)); for (let d = 0; d <= days; d += step) out.push([d, Math.min(points, seat / 100 * profitDay * d)]); return out; };
export const capDay = (points, seat, profitDay) => (seat > 0 && profitDay > 0 ? Math.ceil(points / (seat / 100 * profitDay)) : null);
export function EarnLine({ points, seat, profitDay, testid = 'stake-earn' }) {
  const c = inks(); const hit = capDay(points, seat, profitDay); const inside = hit != null && hit <= 360; const span = inside ? Math.max(14, Math.min(360, Math.ceil(hit * 1.5))) : 360; const rows = earnRows(points, seat, profitDay, span);   // the view fits the climb, so a limit reached on day 5 is not a wall
  const option = { grid: { left: 52, right: 16, top: 18, bottom: 26 }, tooltip: { ...tip(c), formatter: ps => `Day ${ps[0].value[0]}<br/><b>${money(ps[0].value[1])}</b> earned` }, xAxis: { type: 'value', min: 0, max: span, minInterval: 1, axisLabel: { color: c.text, fontSize: 10, formatter: 'Day {value}' }, axisLine: { lineStyle: { color: c.soft } }, splitLine: { show: false } }, yAxis: { type: 'value', max: v => Math.max(points * 1.12, v.max), axisLabel: { color: c.text, fontSize: 10, formatter: v => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(v < 10 ? 1 : 0)}`) }, splitLine: { lineStyle: { color: c.grid } } },
    series: [{ name: 'Earned', type: 'line', showSymbol: false, lineStyle: { width: 2, color: '#45e486' }, itemStyle: { color: '#45e486' }, areaStyle: { color: '#45e4861f' }, data: rows, markLine: { silent: true, symbol: 'none', lineStyle: { color: c.line, type: 'dashed', width: 1.5 }, label: { color: c.text, fontSize: 10, position: 'insideEndTop', formatter: `Its limit ${money(points)}` }, data: [{ yAxis: points }] } }] };
  return <Plot option={option} testid={testid} label={inside ? `At this profit it reaches its ${money(points)} limit around day ${hit}` : `At this profit it earns ${money(rows[rows.length - 1][1])} in a year, under its ${money(points)} limit`} />;
}
