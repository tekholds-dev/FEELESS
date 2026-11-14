import React, { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { isCalm } from '../../lib/fxPause';
import '../../styles/agentPot.css';

// 🫙 ITS POT — redo (owner 2026-11-14: "redo … don't do the same thing or same examples or visuals"). The old tab was boost-cash tiles, a split
// chart and four honey tanks. This one is about ITS OWN proofs: every real proof it filed sits on a board by the score it would carry into the
// pot (the boost it would send at), the hottest one is called out, and tapping any proof opens what made its score — the real weighted parts.
// Then its live account (sent, counting, seat) and the send controls. All real: the pool op (weights per proof, stake, pools) + its folders.
const KEYS = [['powFolders', 'PoW'], ['popFolders', 'PoP'], ['pobFolders', 'PoB'], ['pocFolders', 'PoC'], ['psFolders', 'PoStatic'], ['poeFolders', 'PoEco']];
const RANK = { S: 'var(--m-accent)', A: 'var(--m-accent)', B: 'var(--ap-b)', C: 'var(--m-warn)', D: 'var(--m-danger)' };
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${(n / 1000).toFixed(1)}K` : `$${n.toFixed(2)}`; };

/** Pure: its filed proofs joined to their pot score → board points, oldest first. A proof with no score yet is left off. */
export function potBoard(d, weights) {
  const rows = [];
  KEYS.forEach(([key, kind]) => (d?.[key] || []).forEach(f => { const w = f?.id && weights?.[f.id]; if (w && w.score != null) rows.push({ id: f.id, kind, title: String(f.topic || f.name || f.title || `${kind} #${f.n || ''}`).slice(0, 70), at: Number(f.at) || 0, score: Number(w.score) || 0, top: Number(w.top) || 300, rank: w.rank || 'D', parts: w.parts || [], x: Math.max(1, (Number(w.score) || 0) / 100) }); }));
  rows.sort((a, b) => a.at - b.at);
  return rows.map((r, i) => ({ ...r, n: i + 1 }));
}
/** Pure: the one part that would lift this proof's score most if it were perfect — what to fix first. */
export function biggestLift(parts) {
  return (parts || []).filter(p => p.value != null).map(p => ({ ...p, gain: p.weight * (1 - Number(p.value)) })).sort((a, b) => b.gain - a.gain)[0] || null;
}

function Dot({ cx, cy, payload, pick, setPick }) {
  const on = pick === payload.id; const r = 5 + payload.x * 3;
  return <g className={`ap-dot${on ? ' is-on' : ''}`} onClick={() => setPick(payload.id)} role="button" tabIndex={0} aria-label={`${payload.kind} ${payload.title}, score ${payload.score}`} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setPick(payload.id); }}>
    <circle cx={cx} cy={cy} r={r + 7} className="ap-halo" fill={RANK[payload.rank]} />
    <circle cx={cx} cy={cy} r={r} fill={RANK[payload.rank]} stroke={on ? 'var(--m-text)' : 'none'} strokeWidth={2} />
  </g>;
}

function Parts({ p }) {
  const lift = biggestLift(p.parts); const calm = isCalm();
  return <section className="ap-why" data-testid="ap-why" key={p.id}>
    <header><small>{p.kind} · #{p.n} · RANK {p.rank}</small><h4>{p.title}</h4></header>
    <div className="ap-why-score"><b className="m-num">{Math.round(p.score)}</b><span>of {p.top}<em>would send at {+p.x.toFixed(2)}x</em></span></div>
    <ul>{p.parts.map((x, i) => <motion.li key={x.key} initial={calm ? false : { opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} data-tip={`${x.weight} of 100 points`}>
      <span>{x.label}<small>{x.note}</small></span>
      <i className="ap-bar" style={{ '--w': `${x.weight}%` }}><u style={{ transform: `scaleX(${x.value == null ? 0 : Number(x.value)})` }} /></i>
      <b className="m-num">{x.value == null ? '—' : `${Math.round(Number(x.value) * x.weight)}/${x.weight}`}</b></motion.li>)}</ul>
    {lift ? <p className="ap-lift" data-testid="ap-lift">Fix first: <b>{lift.label}</b>. Perfect there adds up to {Math.round(lift.gain / 100 * p.top)} points.</p> : null}
  </section>;
}

export default function AgentPot({ pool, d, actions = null, ledger = null, count = null }) {
  const rows = useMemo(() => potBoard(d, pool?.weights), [d, pool?.weights]); const [pick, setPick] = useState(null);
  const best = rows.reduce((b, r) => (!b || r.score > b.score ? r : b), null); const cur = rows.find(r => r.id === pick) || best;
  const st = pool?.stake || {}; const top = pool?.score?.top || 300; const sent = Number(st.sentUsd) || 0;
  const pools = (pool?.pools || []).slice(0, 6);
  if (!pool) return <p className="ap-none">Reading its pot…</p>;
  return <div className="ap" data-testid="dsk-honey">
    <header className="ap-hero m-live">
      <div><small>ITS POT</small><h3 data-testid="ap-verdict">{sent > 0 ? <>It has <em>{usd(sent)}</em> working at {+(Number(st.x) || 1).toFixed(2)}x.</> : best ? <>Nothing in the pot yet. Its best proof would go in at <em>{+best.x.toFixed(2)}x</em>.</> : <>Nothing in the pot yet, and no scored proof to send.</>}</h3></div>
      <dl className="ap-facts">
        <div data-tip="What it has counting right now, from real pool profit only"><dt>COUNTING</dt><dd>{count || <b className="m-num">$0.00</b>}</dd></div>
        <div data-tip="Its share of each pool profit right now"><dt>ITS SEAT</dt><dd className="m-num">{(Number(st.nowPct) || 0).toFixed(2)}%</dd></div>
        <div data-tip={`Today's top score anyone can carry. It rises as the pot grows`}><dt>TOP TODAY</dt><dd className="m-num">{top}</dd></div>
        <span className="bst-off" data-tip="Its earnings keep counting. Taking them out is switched off for now.">WITHDRAWALS OFF</span>
      </dl>
    </header>
    <div className="ap-main">
      <section className="ap-board" data-testid="ap-board">
        <header><small>ITS PROOFS · WHAT EACH WOULD CARRY IN</small><span>{rows.length} scored · tap one</span></header>
        {rows.length ? <div className="ap-chart"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 10, right: 12, bottom: 4, left: -18 }}>
          <CartesianGrid stroke="var(--ap-grid)" vertical={false} />
          <XAxis dataKey="n" type="number" domain={[0, rows.length + 1]} tick={{ fill: 'var(--m-dim)', fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <YAxis dataKey="score" type="number" domain={[0, top]} tick={{ fill: 'var(--m-dim)', fontSize: 10 }} tickLine={false} axisLine={false} />
          <ZAxis dataKey="x" range={[60, 260]} />
          <ReferenceLine y={100} stroke="var(--m-line-hi)" strokeDasharray="4 4" label={{ value: '1x', fill: 'var(--m-dim)', fontSize: 10, position: 'insideTopLeft' }} />
          <ReferenceLine y={top} stroke="var(--m-accent)" strokeDasharray="4 4" label={{ value: `${top / 100}x top`, fill: 'var(--m-accent)', fontSize: 10, position: 'insideBottomRight' }} />
          <Tooltip cursor={false} content={({ payload }) => (payload?.[0] ? <div className="ap-tip"><b>{payload[0].payload.kind} · {Math.round(payload[0].payload.score)}</b><span>{payload[0].payload.title}</span></div> : null)} />
          <Scatter data={rows} shape={p => <Dot {...p} pick={cur?.id} setPick={setPick} />} isAnimationActive={!isCalm()} />
        </ScatterChart></ResponsiveContainer></div> : <p className="ap-none">No proof has a score yet. File one, and it lands here.</p>}
      </section>
      {cur ? <Parts p={cur} /> : null}
    </div>
    <div className="ap-foot">
      <section className="ap-send"><header><small>SEND IT IN</small></header>{actions}</section>
      <section className="ap-pools" data-testid="ap-pools"><header><small>WHERE A SEND WORKS</small><span>{pools.filter(x => x.on).length} of {(pool?.pools || []).length} pools on</span></header>
        {pools.length ? <ul>{pools.map((x, i) => <li key={x.id} className={x.on ? 'is-on' : ''} style={{ '--i': i }} data-tip={x.on ? 'Live: sends work here' : 'Off: the owner has not switched it on'}><i aria-hidden="true" /><b>{x.pair}</b><small>{x.platform}</small><em className="m-num">{usd(x.profitUsd)}</em></li>)}</ul> : <p className="ap-none">No pools listed yet.</p>}</section>
    </div>
    {ledger}
  </div>;
}
