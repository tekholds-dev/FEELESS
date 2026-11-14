import React, { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Layer, PolarAngleAxis, RadialBar, RadialBarChart, Rectangle, ResponsiveContainer, Sankey, Tooltip } from 'recharts';
import { isCalm } from '../../lib/fxPause';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/paysFlow.css';

// 💸 HOW IT PAYS — redo (owner 2026-11-14: "redo, don't do the same thing or same examples or visuals"). The old page was a calculator ($1 / $5 /
// $100, score 300, a table and an earnings curve). This one shows the MECHANISM on the live rules (collective_stake.pay_profit / pool_loss):
// a real pool profit runs out three ways as a river you steer; a loss drains what compounded first; the pot's size unlocks higher tops and faster
// landings on a dial; three guardrails as meters. Nothing here moves money.
const COL = { in: 'var(--m-text)', seats: 'var(--m-accent)', keep: 'var(--m-warn)', compound: 'var(--pf-cool)', loss: 'var(--m-danger)', stake: 'var(--m-mute)' };
const money = v => { const n = Number(v) || 0; return n >= 1e6 ? `$${+(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${+(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
const pct = v => `${+(Number(v) || 0).toFixed(1)}%`;

/** Pure: where 100 parts of a pool PROFIT go, on the live rule. Agents' seats are paid first, the Collective takes its piece of what is left
 * (never more than is left), the rest stays compounding. Same order as collective_stake.pay_profit. */
export function profitSplit(seatsPct, collectivePct) {
  const seats = Math.max(0, Math.min(100, Number(seatsPct) || 0)); const keep = Math.min(Math.max(0, Number(collectivePct) || 0), 100 - seats);
  return { seats, keep, compound: Math.max(0, 100 - seats - keep) };
}
/** Pure: where 100 parts of a pool LOSS come from: what compounded first, then the stakes. Same order as collective_stake.pool_loss. */
export function lossSplit(compoundedPct) {
  const fromCompound = Math.max(0, Math.min(100, Number(compoundedPct) || 0));
  return { fromCompound, fromStake: 100 - fromCompound };
}
/** Pure: the pot ladder from the live rules → each rung with how full the pot is toward it, today's rung marked. */
export function rungs(score) {
  const pot = Number(score?.potUsd) || 0; const ladder = score?.ladder || [];
  return ladder.map((r, i) => ({ ...r, i, fill: r.pot <= 0 ? 1 : Math.min(1, pot / r.pot), open: pot >= r.pot, now: pot >= r.pot && !(ladder[i + 1] && pot >= ladder[i + 1].pot) }));
}
const lands = d => (!d ? 'at once' : d >= 1 ? `over ${+d.toFixed(2)} days` : `over ${Math.round(d * 24)} hours`);

function sankeyOf(mode, a) {
  const parts = mode === 'loss'
    ? [['A pool loses', 'loss'], ['Off what compounded', 'compound', a.fromCompound], ['Off the stakes', 'stake', a.fromStake]]
    : [['A pool profit', 'in'], ['Agents’ seats', 'seats', a.seats], ['The Collective', 'keep', a.keep], ['Stays compounding', 'compound', a.compound]];
  const outs = parts.slice(1).filter(p => p[2] > 0.0001);
  return { nodes: [{ name: parts[0][0], c: parts[0][1] }, ...outs.map(p => ({ name: p[0], c: p[1] }))], links: outs.map((p, i) => ({ source: 0, target: i + 1, value: p[2] })) };
}
function Node({ x, y, width, height, payload }) {
  const right = payload.depth > 0;   // the outflows sit on the right edge: their words go on the inside
  return <Layer><Rectangle x={x} y={y} width={width} height={height} fill={COL[payload.c]} fillOpacity={0.95} radius={3} />
    <text x={right ? x - 8 : x + width + 8} y={y + height / 2} textAnchor={right ? 'end' : 'start'} dominantBaseline="middle" className="pf-node-t">
      {payload.name}{payload.depth ? <tspan className="pf-node-v"> {pct(payload.value)}</tspan> : null}</text></Layer>;
}
function Link({ sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, payload }) {
  return <path className="pf-link" d={`M${sourceX},${sourceY} C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}`} stroke={COL[payload.target.c]} strokeWidth={Math.max(1, linkWidth)} fill="none" />;
}

function River({ rules }) {
  const [mode, setMode] = useState('profit'); const [seats, setSeats] = useState(Math.min(60, (rules.walletCapPct ?? 10) * 3)); const [comp, setComp] = useState(70);
  const cp = rules.collectivePoolPct ?? 20;
  const a = mode === 'loss' ? lossSplit(comp) : profitSplit(seats, cp);
  const data = useMemo(() => sankeyOf(mode, a), [mode, a.seats, a.keep, a.compound, a.fromCompound]);   // eslint-disable-line react-hooks/exhaustive-deps
  const said = mode === 'loss'
    ? <><b>{pct(a.fromCompound)}</b> comes off what the pools already compounded{a.fromStake > 0 ? <>, and <b>{pct(a.fromStake)}</b> off the stakes</> : ', so no stake is touched'}. Nobody&rsquo;s points change and nothing is promised back.</>
    : <>Seated agents take <b>{pct(a.seats)}</b> first. The Collective takes <b>{pct(a.keep)}</b>{a.keep < cp ? ` (its ${cp}% only fits what is left)` : ''}. <b>{pct(a.compound)}</b> stays in the pools and keeps compounding.</>;
  return <section className="pf-river m-live" data-testid="pf-river">
    <header><div><small>ONE POOL RESULT, FOLLOWED</small><h3>{mode === 'loss' ? 'A loss drains in this order.' : 'A profit splits three ways.'}</h3></div>
      <span className="m-seg" role="group" aria-label="Pool result">{[['profit', 'Pool makes money'], ['loss', 'Pool loses money']].map(([k, l]) => <button key={k} type="button" className={mode === k ? 'active' : ''} aria-pressed={mode === k} onClick={() => setMode(k)} data-tip={k === 'loss' ? 'Where a loss is taken from' : 'Where a profit goes'} data-testid={`pf-mode-${k}`}>{l}</button>)}</span></header>
    <div className="pf-sankey" data-testid="pf-sankey" aria-label={`${data.nodes.map(n => n.name).join(', ')}`}>
      <ResponsiveContainer width="100%" height="100%"><Sankey data={data} node={<Node />} link={<Link />} nodePadding={26} nodeWidth={12} margin={{ top: 12, bottom: 12, left: 8, right: 8 }} iterations={0}><Tooltip formatter={v => pct(v)} /></Sankey></ResponsiveContainer>
    </div>
    <label className="pf-steer">
      <span>{mode === 'loss' ? 'Compounded so far, against this loss' : 'Seats agents hold right now'}</span>
      <input type="range" min="0" max="100" step="1" value={mode === 'loss' ? comp : seats} onChange={e => (mode === 'loss' ? setComp : setSeats)(Number(e.target.value))} aria-label={mode === 'loss' ? 'Compounded so far' : 'Seats held by agents'} data-tip={mode === 'loss' ? 'Slide it: the more the pools compounded, the less a loss reaches any stake' : 'Slide it: every seat is a boost × its dollars, one wallet capped. More seats leave less to compound'} data-testid="pf-steer" />
      <b className="m-num">{mode === 'loss' ? pct(comp) : pct(seats)}</b>
    </label>
    <p className="pf-said" role="status" data-testid="pf-said">{said}</p>
  </section>;
}

function Dial({ score }) {
  const rs = rungs(score); const now = rs.find(r => r.now) || rs[0]; const pot = useCountUp(Number(score?.potUsd) || 0); const calm = isCalm();
  const data = rs.map(r => ({ name: `Top ${r.top}`, v: Math.round(r.fill * 100), fill: r.open ? 'var(--m-accent)' : 'var(--pf-dim)' })).reverse();
  return <section className="pf-dial" data-testid="pf-dial">
    <header><small>THE POT UNLOCKS</small><h3>A bigger pot pays more, sooner.</h3></header>
    <div className="pf-dial-body">
      <div className="pf-ring" aria-hidden="true"><RadialBarChart width={150} height={150} data={data} innerRadius={30} outerRadius={74} startAngle={90} endAngle={-270} barSize={9}>
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} /><RadialBar dataKey="v" background={{ fill: 'var(--pf-track)' }} cornerRadius={6} isAnimationActive={!calm} /></RadialBarChart>
        <span className="pf-ring-c"><small>THE POT</small><b className="m-num" data-testid="pf-pot">{money(pot)}</b></span></div>
      <ol className="pf-rungs">{rs.map(r => <motion.li key={r.top} className={`${r.open ? 'is-open' : ''}${r.now ? ' is-now' : ''}`} style={{ '--i': r.i }} initial={calm ? false : { opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: r.i * 0.06 }} data-tip={r.open ? 'Unlocked' : `${money(r.pot - (Number(score?.potUsd) || 0))} more in the pot unlocks it`} data-testid={`pf-rung-${r.top}`}>
        <b className="m-num">{r.top}</b><span><em>{r.pot ? `from a ${money(r.pot)} pot` : 'from day one'}</em><small>top score · profit lands {lands(r.drip)}</small></span><i>{r.now ? 'NOW' : r.open ? 'OPEN' : 'LOCKED'}</i></motion.li>)}</ol>
    </div>
    <p className="pf-said">Today the best proof can score <b>{now?.top ?? 300}</b>, and a profit reaches agents {lands(now?.drip)}.</p>
  </section>;
}

function Rails({ rules }) {
  const rows = [['ONE WALLET’S MOST', rules.walletCapPct ?? 10, `${rules.walletCapPct ?? 10}% of any profit, however much it sends`, 'pf-cap'],
    ['THE COLLECTIVE’S PIECE', rules.collectivePoolPct ?? 20, `${rules.collectivePoolPct ?? 20}% of what agents leave, never their seats`, 'pf-keep'],
    ['A STAKE’S CEILING', ((rules.score?.top || 300) / 1000) * 100, `${(rules.score?.top || 300) / 100}x what it sent, then its seat stops`, 'pf-ceil']];
  return <section className="pf-rails" aria-label="Guardrails">{rows.map(([k, v, say, id], i) => <div key={k} style={{ '--i': i }} data-testid={id}><small>{k}</small><i className="pf-meter"><u style={{ transform: `scaleX(${Math.min(1, v / 100)})` }} /></i><span>{say}</span></div>)}
    <p className="pf-warn"><b>No promised rate.</b> Only real pool profit pays, never someone else&rsquo;s stake, and pools can lose money. Nothing moves from this page.</p></section>;
}

export default function PaysFlow({ rules }) {
  if (!rules) return <p className="cvx-none">Reading the live rules…</p>;
  return <div className="pf" data-testid="pf"><River rules={rules} /><div className="pf-side"><Dial score={rules.score} /><Rails rules={rules} /></div></div>;
}
