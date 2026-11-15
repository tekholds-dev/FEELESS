import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import '../../styles/moneyCockpit.css';

// 💰 THE MONEY COCKPIT (owner 2026-11-15: "money folder in agents need a complete redo"). One verdict, one meter, three facts, one best move.
// The look: a verdict line from the real ledger; a ring that shows where every dollar sits (placed · reserve · free); the three numbers that
// matter; then the four risk lanes as meters (risk against pay) and the lane you pick, big, with its one action. Same calls as before:
// Chart it and Add to plan move no money. Every number is read live (the ledger, the venues); nothing here is advice.
const RISK = { steady: 1, stake: 2, deep: 3, hot: 4 };
const short$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${(v || 0).toFixed(v && v < 10 ? 2 : 0)}`);

export function verdictOf({ staked = 0, placedPct = 0, reservePct = 0, best = null }) {
  if (!staked && !placedPct) return best ? `Nothing placed yet. The safest lane leads with ${best.name} at ${short$(best.per1k24)} a day on $1K.` : 'Nothing placed yet. Reading every venue.';
  if (placedPct + reservePct > 100) return `Over-planned: ${placedPct}% placed plus a ${reservePct}% reserve. Trim a spot.`;
  return `${short$(staked)} in. ${placedPct}% of the plan is placed, ${reservePct}% is held back, ${Math.max(0, 100 - placedPct - reservePct)}% is free to place.`;
}

function Ring({ placed, reserve }) {
  const R = 52; const C = 2 * Math.PI * R; const p = Math.min(100, placed) / 100; const r = Math.min(100 - Math.min(100, placed), reserve) / 100;
  return <svg className="mck-ring" viewBox="0 0 128 128" role="img" aria-label={`${placed}% placed, ${reserve}% reserve`}>
    <circle cx="64" cy="64" r={R} className="mck-ring-bg" />
    <motion.circle cx="64" cy="64" r={R} className="mck-ring-res" strokeDasharray={C} initial={{ strokeDashoffset: C }} animate={{ strokeDashoffset: C * (1 - r) }} transition={{ duration: 0.9, ease: 'easeOut' }} style={{ rotate: p * 360 - 90, transformOrigin: '64px 64px' }} />
    <motion.circle cx="64" cy="64" r={R} className="mck-ring-on" strokeDasharray={C} initial={{ strokeDashoffset: C }} animate={{ strokeDashoffset: C * (1 - p) }} transition={{ duration: 0.9, ease: 'easeOut' }} style={{ rotate: -90, transformOrigin: '64px 64px' }} />
    <text x="64" y="60" className="mck-ring-n">{Math.round(placed)}%</text><text x="64" y="78" className="mck-ring-l">PLACED</text>
  </svg>;
}

export function MoneyCockpit({ st = {}, lanes = [], rows, placedPct = 0, reservePct = 0, pot = 0, next = null, picks = [], onChart, onPlan, inPlan, busy, payOf, cutsPct = 0, piece = 0, money }) {
  const [at, setAt] = useState('steady');
  const lane = lanes.find(l => l.k === at) || lanes[0]; const r = lane?.best; const top = Math.max(0.01, ...lanes.map(l => l.best?.per1k24 || 0));
  const pay = r && payOf ? payOf(r.per1k24 * 30, 720, cutsPct, piece) : null;
  const facts = [['STAKED', st.stakedUsd, 'What agents really sent, by the ledger'], ['THE COLLECTIVE KEEPS', st.keepUsd, "Fees that are the Collective's own"], ['PAID TO AGENTS', st.paidUsd, 'What agents have really been paid']];
  return <section className="mck" data-testid="money-dash">
    <div className="mck-top" data-testid="grow-real">
      <Ring placed={placedPct} reserve={reservePct} />
      <div className="mck-verdict"><small>WHERE YOUR MONEY STANDS</small><p data-testid="mck-verdict">{verdictOf({ staked: Number(st.stakedUsd) || 0, placedPct, reservePct, best: lanes[0]?.best })}</p>
        <ul className="mck-facts">{facts.map(([k, v, t], i) => <motion.li key={k} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.06 }} data-tip={t}><small>{k}</small><b className="m-num">{money ? money(Number(v) || 0) : short$(v)}</b></motion.li>)}</ul>
        {next ? <span className="mck-rung" data-tip="The pot decides today's top score. A bigger pot opens a higher top"><small>NEXT TOP SCORE {next.top}</small><i aria-hidden="true"><motion.u initial={{ scaleX: 0 }} animate={{ scaleX: Math.min(1, pot / next.pot) }} transition={{ duration: 0.8 }} /></i><em className="m-num">{short$(pot)} of {short$(next.pot)} pot</em></span> : null}
      </div>
    </div>
    <header className="mck-h"><b>THE BEST MOVE BY RISK</b><small>Today's real numbers before price moves. It ranks; the pick and the money stay yours.</small></header>
    {!rows ? <p className="mck-wait" role="status">Reading every venue…</p> : <div className="mck-lanes">
      <div className="mck-meters" role="tablist" aria-label="Risk lane">{lanes.map(l => <button key={l.k} type="button" role="tab" aria-selected={at === l.k} className={at === l.k ? 'is-on' : ''} style={{ '--c': l.col }} onClick={() => setAt(l.k)} data-testid={`money-lane-${l.k}`}>
        <span><b>{l.t}</b><small>{l.n} on the board</small></span>
        <span className="mck-bars" aria-hidden="true"><i className="mck-risk">{[1, 2, 3, 4].map(n => <u key={n} className={n <= RISK[l.k] ? 'is-lit' : ''} />)}</i><i className="mck-pay"><motion.u initial={{ scaleX: 0 }} animate={{ scaleX: (l.best?.per1k24 || 0) / top }} transition={{ duration: 0.7 }} /></i></span>
        <em className="m-num">{l.best ? `$${l.best.per1k24.toFixed(2)}/day` : '—'}</em></button>)}</div>
      <AnimatePresence mode="wait"><motion.article key={lane?.k} className="mck-pick" style={{ '--c': lane?.col }} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.22 }} data-testid="mck-pick">
        <small>{lane?.risk}</small>
        {r ? <><h3 title={r.name}>{r.name}</h3><em className="mck-venue">{String(r.venue || '').replace(/-/g, ' ')}</em>
          <div className="mck-nums"><span><small>A DAY ON $1K</small><b className="m-num">${r.per1k24.toFixed(2)}</b></span><span><small>A YEAR</small><b className="m-num">{r.yearPct.toFixed(1)}%</b></span><span><small>DEPTH</small><b className="m-num">{short$(r.tvl)}</b></span></div>
          {pay ? <p className="mck-pay-line">$1K for a month at today's pace: <b className="m-num">{money ? money(pay.month) : short$(pay.month)}</b> · agents {money ? money(pay.agents) : short$(pay.agents)} · Collective {money ? money(pay.piece) : short$(pay.piece)}</p> : null}
          {lane.next?.length ? <p className="mck-next">Next in this lane: {lane.next.map(x => `${x.name} $${x.per1k24.toFixed(2)}`).join(' · ')}</p> : null}
          <div className="mck-acts"><button type="button" className="m-btn" aria-pressed={!!picks?.includes(r.id)} onClick={() => onChart?.(r.id)} data-tip="Puts it on the chart below with its real history" data-testid={`money-chart-${lane.k}`}>{picks?.includes(r.id) ? 'On the chart' : 'Chart it'}</button>
            {r.kind !== 'pool' ? <button type="button" className="m-btn m-go" disabled={busy || inPlan?.(r)} onClick={() => onPlan?.(r)} data-tip="Adds it to your plan. It moves no money" data-testid={`money-plan-${lane.k}`}>{inPlan?.(r) ? 'In your plan' : 'Add to plan'}</button> : <small className="mck-hand">A pool opens on its venue, by hand, from Open a real pool below.</small>}</div></>
          : <p className="mck-wait">Nothing on the board fits this lane right now.</p>}
      </motion.article></AnimatePresence>
    </div>}
  </section>;
}
