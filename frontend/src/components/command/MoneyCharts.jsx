import React from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Sankey, Tooltip, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';

// 📊 Money charts (owner 2026-11-05: free libraries, never hand-drawn): shadcn/ui charts on Recharts. Loaded only when a money screen opens.
const FMT = v => (Math.abs(v) >= 100 ? `$${Math.round(v).toLocaleString()}` : `$${Number(v).toFixed(2)}`);
export const flowGraph = (rows, colors = {}) => { const live = rows.filter(r => r[2] > 0.0001); const names = [...new Set(live.flatMap(r => [r[0], r[1]]))]; return { nodes: names.map(name => ({ name, color: colors[name] || '#8fa3cc' })), links: live.map(([a, b, value]) => ({ source: names.indexOf(a), target: names.indexOf(b), value })) }; };
function FlowNode({ x, y, width, height, payload }) {
  const left = !payload.sourceNodes?.length; const tx = left ? x + width + 7 : x - 7; const mid = y + height / 2;   // a starting point's name reads to the right
  return <g><rect x={x} y={y} width={width} height={Math.max(height, 3)} rx={2} fill={payload.color} /><text x={tx} y={mid - 2} textAnchor={left ? 'start' : 'end'} className="mch-n">{payload.name}</text><text x={tx} y={mid + 11} textAnchor={left ? 'start' : 'end'} className="mch-v">{FMT(payload.value)}</text></g>;
}
function FlowLink({ sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, payload }) {
  return <path d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`} fill="none" stroke={payload.target?.color || '#8fa3cc'} strokeOpacity={0.3} strokeWidth={Math.max(1, linkWidth)} />;
}
const FlowTip = ({ active, payload }) => { const p = payload?.[0]?.payload?.payload; if (!active || !p) return null; const link = p.source && p.target; return <div className="mch-tip"><b>{link ? `${p.source.name} → ${p.target.name}` : p.name}</b><em className="m-num">{FMT(p.value)}</em></div>; };
export function MoneyFlow({ rows, colors, height = 300, testid = 'money-flow', label = 'Where the money goes' }) {
  const data = flowGraph(rows, colors);
  if (!data.links.length) return <p className="mch-none">Nothing flows at these numbers.</p>;
  return <div className="mch-flow" style={{ height }} data-testid={testid} role="img" aria-label={label}><ResponsiveContainer width="100%" height="100%"><Sankey data={data} node={<FlowNode />} link={<FlowLink />} nodeWidth={8} nodePadding={26} iterations={32} sort={false} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}><Tooltip content={<FlowTip />} /></Sankey></ResponsiveContainer></div>;
}
const axis = { tickLine: false, axisLine: false, tickMargin: 6, fontSize: 10 };
export function BackLines({ c, testid = 'cs-curves' }) {
  const P = [['week', '1 week', '#57c7ff'], ['month', '30 days', '#3ee58a'], ['quarter', '90 days', '#c58bff']]; const max = Math.max(...P.map(p => c[`${p[0]}Days`]), 7); const days = [...new Set([0, ...P.map(p => c[`${p[0]}Days`]), max])].sort((a, b) => a - b);
  const data = days.map(d => Object.fromEntries([['d', d], ...P.map(([n]) => [n, Math.round(c[`${n}Back`] * Math.min(1, d / c[`${n}Days`]) * 10) / 10])]));
  const cfg = Object.fromEntries(P.map(([k, label, color]) => [k, { label, color }]));
  return <div data-testid={testid}><ChartContainer config={cfg} className="aspect-auto h-[190px] w-full"><LineChart data={data} margin={{ left: 0, right: 10, top: 6 }}><CartesianGrid vertical={false} strokeOpacity={0.12} /><XAxis dataKey="d" type="number" domain={[0, max]} ticks={days} tickFormatter={v => `${v}d`} {...axis} /><YAxis width={34} domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={v => `${v}%`} {...axis} /><ChartTooltip content={<ChartTooltipContent labelFormatter={(_, p) => `Day ${p?.[0]?.payload?.d}`} formatter={(v, n) => <><span className="mch-tn">{cfg[n]?.label}</span><b className="m-num">{v}% back</b></>} />} />{P.map(([k]) => <Line key={k} dataKey={k} type="linear" stroke={`var(--color-${k})`} strokeWidth={2} dot={false} />)}<ChartLegend content={<ChartLegendContent />} /></LineChart></ChartContainer></div>;
}
export function PlanBars({ c, testid = 'cs-bars' }) {
  const lock = 100 - c.skimPct; const row = (name, n) => ({ name, back: lock * c[`${n}Back`] / 100, later: lock * (100 - c[`${n}Back`]) / 100, now: c.skimPct, vault: 0 });
  const data = [row('1 week', 'week'), row('30 days', 'month'), row('90 days', 'quarter'), { name: 'Vault', back: 0, later: 0, now: c.skimPct, vault: lock }];
  const cfg = { back: { label: 'Back to the agent', color: '#3ee58a' }, later: { label: 'Collective, later', color: '#2f7fd6' }, now: { label: 'Collective, now', color: '#57c7ff' }, vault: { label: 'Vault', color: '#c58bff' } };
  return <div data-testid={testid}><ChartContainer config={cfg} className="aspect-auto h-[190px] w-full"><BarChart data={data} layout="vertical" margin={{ left: 0, right: 8 }}><CartesianGrid horizontal={false} strokeOpacity={0.12} /><XAxis type="number" domain={[0, 100]} tickFormatter={v => `$${v}`} {...axis} /><YAxis type="category" dataKey="name" width={58} interval={0} {...axis} /><ChartTooltip content={<ChartTooltipContent formatter={(v, n) => <><span className="mch-tn">{cfg[n]?.label}</span><b className="m-num">{FMT(v)}</b></>} />} />{Object.keys(cfg).map(k => <Bar key={k} dataKey={k} stackId="a" fill={`var(--color-${k})`} barSize={14} />)}<ChartLegend content={<ChartLegendContent />} /></BarChart></ChartContainer></div>;
}
// The year example: its lines, a marker on the chosen day.
export function YearLines({ rows, series, at, label }) {
  const cfg = Object.fromEntries(series.map(([k, l, color]) => [k, { label: l, color }])); const data = rows.map((r, i) => ({ ...r, day: i * 10 }));
  return <ChartContainer config={cfg} className="aspect-auto h-[160px] w-full" aria-label={label}><LineChart data={data} margin={{ left: 0, right: 8, top: 6 }}><CartesianGrid vertical={false} strokeOpacity={0.12} /><XAxis dataKey="day" type="number" domain={[0, 360]} ticks={[0, 90, 180, 270, 360]} tickFormatter={v => `${v}d`} {...axis} /><YAxis width={44} tickFormatter={v => (v >= 1000 ? `$${Math.round(v / 1000)}K` : `$${Math.round(v)}`)} {...axis} /><ChartTooltip content={<ChartTooltipContent labelFormatter={(_, p) => `Day ${p?.[0]?.payload?.day}`} formatter={(v, n) => <><span className="mch-tn">{cfg[n]?.label}</span><b className="m-num">{FMT(v)}</b></>} />} /><ReferenceLine x={at} stroke="#ffffff55" />{series.map(([k]) => <Line key={k} dataKey={k} stroke={`var(--color-${k})`} strokeWidth={2} dot={false} isAnimationActive={false} />)}</LineChart></ChartContainer>;
}
