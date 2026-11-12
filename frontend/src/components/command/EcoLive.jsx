import React, { useEffect, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Layer, Line, Rectangle, ResponsiveContainer, Sankey, Tooltip, XAxis, YAxis } from 'recharts';
import { useAdmin } from '../../lib/adminCall';
import { useCountUp } from '../../lib/useCountUp';

// 🏦 LIVE BOOKS (owner 2026-11-12: "give this dude what he really asked for and really needs instead of this dead ass folder"). The PoEco desk
// asked him to paste a bank file before it showed anything. This needs nothing: his real business, summed live from what FEELESS already
// writes (fees in, rented-model spend out, the real Fuse card), a daily chart, where the money goes and one plain verdict. Owner only.
const usd = v => { const n = Number(v) || 0; const a = Math.abs(n); return `${n < 0 ? '−' : ''}$${a >= 1000 ? `${(a / 1000).toFixed(1)}K` : a >= 1 ? a.toFixed(2) : a.toFixed(3)}`; };
const tipStyle = { background: '#0e0e12', border: '1px solid #ffffff1f', borderRadius: 8, fontSize: 11, color: '#ececf1' };
const axis = { fontSize: 10, fill: '#8b8b95' };

function Kpi({ label, v, tone, sub, tip, i }) {
  const n = useCountUp(Number(v) || 0);
  return <div className={`ecl-kpi is-${tone}`} style={{ '--i': i }} data-tip={tip}><small>{label}</small><b className="m-num">{usd(n)}</b>{sub ? <em>{sub}</em> : null}</div>;
}

/** 💸 MONEY FLOW (owner ask: Sankey, real data only) → { nodes, links } from the live books, or null when no money moved. Sources: fees users paid,
 * plus "your pocket" = whatever the fees did not cover. Uses: FeeBack paid back, each rented model (top 6 + the rest), and what was kept. Balanced by construction. */
export function flowOf(d) {
  const k = d?.kpi || {}; const fees = Math.max(0, k.feesUsd || 0); const back = Math.max(0, k.feeBackPaidUsd || 0); const spend = Math.max(0, k.spendUsd || 0);
  if (fees + spend + back <= 0) return null;
  const pocket = Math.max(0, back + spend - fees); const kept = Math.max(0, fees - back - spend);
  const models = (d.byModel || []).filter(m => m.usd > 0); const other = Math.max(0, spend - models.reduce((a, m) => a + m.usd, 0));
  const nodes = [{ name: 'Fees in', tone: 'in' }, { name: 'Your pocket', tone: 'out' }, { name: 'FEELESS', tone: 'hub' }]; const links = [];
  if (fees > 0) links.push({ source: 0, target: 2, value: fees }); if (pocket > 0) links.push({ source: 1, target: 2, value: pocket });
  const out = (name, value, tone) => { if (value > 0.0001) { nodes.push({ name, tone }); links.push({ source: 2, target: nodes.length - 1, value }); } };
  out('FeeBack paid', back, 'back'); models.forEach(m => out(m.k, m.usd, 'model')); out('Other models', other, 'model'); out('Kept', kept, 'in');
  return { nodes, links };
}
const TONE = { in: '#3cf0c5', out: '#ff5c7a', hub: '#ececf1', back: '#f5c542', model: '#8b8b95' };
function FlowNode({ x, y, width, height, payload, containerWidth }) {
  const right = x > containerWidth / 2;
  return <Layer><Rectangle x={x} y={y} width={width} height={Math.max(2, height)} fill={TONE[payload.tone] || '#8b8b95'} radius={2} />
    <text x={right ? x - 6 : x + width + 6} y={y + height / 2} textAnchor={right ? 'end' : 'start'} dominantBaseline="middle" fontSize={11} fill="#ececf1">{payload.name} <tspan fill="#8b8b95">{usd(payload.value)}</tspan></text></Layer>;
}

export function EcoLive() {
  const { isAdmin, call } = useAdmin(); const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => {
    if (!isAdmin || !call) return undefined;
    const load = () => call('/admin/eco/live').then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message));
    load(); const t = setInterval(load, 60000); return () => clearInterval(t);
  }, [isAdmin, call]);
  if (!isAdmin) return null;
  if (!d) return <section className="ecl" data-testid="eco-live">{err ? <p className="kd-err">{err}</p> : <p className="ecl-wait">Summing your real books…</p>}</section>;
  const k = d.kpi; const flow = flowOf(d); const maxM = Math.max(...d.byModel.map(m => m.usd), 1e-9);
  const first = d.daily.findIndex(x => x.in || x.out); const days = d.daily.slice(Math.max(0, Math.min(first < 0 ? 0 : first - 1, d.daily.length - 7)));   // from the first day with money, at least a week
  return <section className="ecl" data-testid="eco-live">
    <header className="ecl-head"><span><small className="m-label">LIVE BOOKS · YOUR BUSINESS · FILLS ITSELF</small><b>{d.say}</b></span>
      <span className={`ecl-pulse${k.netUsd >= 0 ? ' is-up' : ''}`} data-tip="Updates every minute from the fee ledger, the model-call log and the real card audit" aria-hidden="true" /></header>
    <div className="ecl-kpis">
      <Kpi i={0} label="FEES IN" v={k.feesUsd} tone="in" sub={`${k.trades} trades · ${k.payers} payer${k.payers === 1 ? '' : 's'}`} tip="Every FEELESS fee users paid (fee ledger), all time" />
      <Kpi i={1} label="MODEL SPEND" v={-k.spendUsd} tone="out" sub={`${k.calls} calls · ${usd(k.perCallUsd)} each`} tip="Every rented model call the agents made (mind-call log)" />
      <Kpi i={2} label="NET" v={k.netUsd} tone={k.netUsd >= 0 ? 'in' : 'out'} sub={`7d ${usd(k.net7dUsd)}`} tip="Fees in − FeeBack paid − model spend. 7d adds the real card's last 7 days" />
      <Kpi i={3} label="BURN / DAY" v={-k.burnPerDayUsd} tone="warn" sub="last 7 days" tip="What the models cost per day, averaged over the last week" />
    </div>
    {flow ? <div className="ecl-flow" data-testid="eco-flow" data-tip="Where every dollar came from and went, all time: fees users paid (and your pocket for what fees did not cover) → FeeBack, each rented model, kept"><small className="m-label">MONEY FLOW · ALL TIME</small>
      <ResponsiveContainer width="100%" height={Math.max(150, 26 * flow.nodes.length)}><Sankey data={flow} node={<FlowNode />} nodePadding={14} nodeWidth={8} margin={{ top: 8, right: 150, bottom: 8, left: 110 }} link={{ stroke: '#ffffff', strokeOpacity: 0.08 }} iterations={32}>
        <Tooltip contentStyle={tipStyle} formatter={v => usd(v)} /></Sankey></ResponsiveContainer></div> : null}
    <div className="ecl-grid">
      <div className="ecl-chart" data-tip="Bars: fees in (up) and model spend (down) per day. Line: the running total over 30 days"><small className="m-label">{days.length} DAYS · IN vs OUT · RUNNING NET</small>
        <ResponsiveContainer width="100%" height={150}><ComposedChart data={days.map(b => ({ ...b, out: -b.out }))} margin={{ top: 6, right: 8, bottom: 0, left: -16 }} stackOffset="sign">
          <CartesianGrid vertical={false} stroke="#ffffff10" /><XAxis dataKey="d" tick={axis} axisLine={false} tickLine={false} interval="preserveStartEnd" minTickGap={18} /><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} /><Tooltip contentStyle={tipStyle} formatter={v => usd(v)} />
          <Bar dataKey="in" stackId="a" fill="#3cf0c5" radius={[2, 2, 0, 0]} isAnimationActive={false} name="fees in" /><Bar dataKey="out" stackId="a" fill="#ff5c7a" radius={[2, 2, 0, 0]} isAnimationActive={false} name="model spend" />
          <Line type="monotone" dataKey="cum" stroke="#b48cff" strokeWidth={1.5} dot={false} isAnimationActive={false} name="running net" /></ComposedChart></ResponsiveContainer></div>
      <div className="ecl-where" data-tip="Which rented minds the spend went to"><small className="m-label">WHERE IT GOES</small>
        <ul>{d.byModel.map((m, i) => <li key={m.k} style={{ '--i': i }}><span>{m.k}</span><i className="mlb-bar is-bad"><u style={{ transform: `scaleX(${Math.max(0.03, m.usd / maxM)})` }} /></i><b className="m-num">{usd(m.usd)}</b></li>)}</ul>
        {d.byJob.length ? <p className="ecl-jobs">{d.byJob.map(j => <em key={j.k} className="m-chip">{j.k} {usd(j.usd)}</em>)}</p> : null}</div>
    </div>
    {d.card ? <div className="ecl-card" data-tip="The real Fuse card, from the last scripts/real-audit.py run (read-only)">
      <span><small>REAL CARD</small><b className="m-num">{usd(d.card.putInUsd)}</b><em>put in</em></span>
      <span><small>OPEN</small><b className="m-num">{d.card.open}</b><em>{usd(d.card.openCostUsd)} cost</em></span>
      <span><small>LAST 7 DAYS</small><b className={`m-num${d.card.net7dUsd < 0 ? ' is-out' : ' is-in'}`}>{usd(d.card.net7dUsd)}</b><em>{d.card.trips7d} trip{d.card.trips7d === 1 ? '' : 's'}</em></span>
      {d.card.verdict ? <span className="ecl-verdict"><small>EDGE</small><b>{d.card.verdict}</b><em>{d.card.asOf ? new Date(d.card.asOf * 1000).toLocaleString() : ''}</em></span> : null}
    </div> : null}
  </section>;
}
