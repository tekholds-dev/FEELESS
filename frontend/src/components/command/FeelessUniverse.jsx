import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FeelessMark } from '../FeelessLogo';
import '../../styles/feelessUniverse.css';

// 🌌 THE FEELESS UNIVERSE (owner, 2026-10-20: "roadmap / whitepaper 80% 3D and live animation — how big and different FEELESS is, every feature,
// how users use them like a tutorial, and FEELESS / FeeCat / rFEE as flagship coins for the bigger secure coins later"). One live scene on top
// of the roadmap and the whitepaper: every feature is a planet orbiting the FEELESS core (CSS 3D, transform / opacity only); tap one → its
// tutorial (3–4 steps + where to go). The flagship stack explains the three coins today and the plan after — a plan, never a promise.
export const PLANETS = [
  ['trench', '🗑', 'Trenches', '/terminal/chat', 'Live launch coins with the FEELESS edge on every chart.', ['Open Trenches and pick a coin from the live list.', 'Read the vital ring + the read (SEND IT, WATCH, RUG BAIT) on the chart.', 'Check the wallet bubbles — dev, snipers, bundles, whales — right on the candles.', 'Quick trade from the chart; your wallet signs every swap.']],
  ['fuse', '⚛', 'Fuse cards', '/terminal/fuse', 'Many coins, one card — pools + runners with their own exits.', ['Open Fuse › Build and pick pools / runners (or one-tap Best 3).', 'Pick a risk dial: Safe, Balanced or Degen sets every TP / SL.', 'Fuse in with ONE wallet approval — BEFORE / AFTER receipt shows exact fills.', 'Manage it in My cards: take profit, switch, limits, withdraw.']],
  ['agents', '🤖', 'Agents', '/terminal/fuse?tab=arena', 'Ten desks that read every launch and explain each call.', ['Tally reads the numbers, Sherlock the story, Trigger the moment.', 'Devil argues, Warden sizes, Reaper manages the exit.', 'The Judge grades every real trade; bad generations are replaced.', 'Every decision carries its evidence — no black box.']],
  ['feecat', '🐱', 'FeeCat', '/terminal/feecat', 'The cat that trades in public with nine lives of discipline.', ['Watch her live desk: what she read, why she took or skipped it.', 'Her calls pin onto every chart as 🐱 bubbles.', 'Losses cost lives; at zero she naps — she may only ever trade LESS.', 'Fee-Back is delivered in FEECAT.']],
  ['rep', '🔎', 'Reputation', '/terminal/reputation', 'Case files with cited evidence for any wallet or coin.', ['Paste a wallet or CA — FEELESS builds its case file.', 'Every score point is a claim + its source.', '"Why did it pump?" digs X, the web and Pump callers.', 'Bot Shield flags farmers, wash traders and self-dealers.']],
  ['familia', '🌹', 'La Familia', '/terminal/leaderboard?lens=crews', 'Families with badges you EARN, bounties and a live pulse.', ['Found or join a family with its passcode.', 'Post on the board, set bounties paid in points.', 'Forge your family badge — every part unlocks from tracked numbers.', 'Climb the weekly podium.']],
  ['season', '🏆', 'Seasons', '/terminal/seasons', 'Weekly races: trades, calls, quests and Fuse cards.', ['Every verified trade, call and quest earns season points.', 'Watch the live hub: rank moves, family events, Fuse cards.', 'Badges are numbered for their first 100 earners.', 'Top 3 are crowned every week.']],
  ['feeback', '💸', 'Fee-Back', '/terminal/feeback', 'The fee-return plan: eligible tracked fees back in FEECAT.', ['Trade through FEELESS — every fee is tracked to the cent.', 'Eligibility, valuation and settlement rules are published first.', 'Distribution is audited with replay protection.', 'Status: planned — not live yet.']],
];
export const FLAGSHIPS = [
  ['$FEE', 'fee', 'The core asset. Holding it unlocks perks, chat backgrounds and fee discounts across FEELESS.'],
  ['FEECAT', 'cat', 'The culture coin and the intended Fee-Back delivery layer.'],
  ['rFEE', 'rfee', 'The reserve token behind the Fee Reserve rooms and badges.'],
];

function Planet({ p, i, n, on, onPick }) {
  const [k, ic, name] = p;
  return <button type="button" className={`fu-planet${on ? ' is-on' : ''}`} style={{ '--a': `${(360 / n) * i}deg`, '--i': i }} onClick={() => onPick(k)}
    data-testid={`fu-planet-${k}`} aria-pressed={on}><span className="fu-body"><i>{ic}</i><b>{name}</b></span></button>;
}

export function FeelessUniverse({ mode = 'road' }) {
  const [pick, setPick] = useState(null); const [step, setStep] = useState(0);
  const p = PLANETS.find(x => x[0] === pick);
  useEffect(() => { setStep(0); }, [pick]);
  useEffect(() => { if (!p) return undefined; const t = setInterval(() => setStep(s => (s + 1) % p[5].length), 3200); return () => clearInterval(t); }, [p]);
  return <section className={`fu fu-${mode}`} data-testid="feeless-universe">
    <div className="fu-stars" aria-hidden="true">{Array.from({ length: 18 }, (_, j) => <i key={j} style={{ '--j': j, '--x': `${(j * 5.7 + 2) % 100}%`, '--y': `${(j * 37) % 100}%` }} />)}</div>
    <header className="fu-head"><span className="eyebrow">{mode === 'paper' ? 'THE WHITEPAPER, LIVE' : 'THE MAP OF FEELESS'}</span>
      <h2>One terminal. <em>Every edge in orbit.</em></h2>
      <p>{PLANETS.length} systems run around one core — tap any planet for a walk-through.</p></header>
    <div className="fu-stage">
      <div className="fu-sky">
        <div className="fu-ring r1" aria-hidden="true" /><div className="fu-ring r2" aria-hidden="true" />
        <div className="fu-core"><FeelessMark size={56} /><small>FEELESS</small></div>
        <div className="fu-orbit">{PLANETS.map((x, i) => <Planet key={x[0]} p={x} i={i} n={PLANETS.length} on={pick === x[0]} onPick={k => setPick(pick === k ? null : k)} />)}</div>
      </div>
      <aside className={`fu-guide${p ? ' is-open' : ''}`} data-testid="fu-guide">
        {p ? <><b className="fu-gt">{p[1]} {p[2]}</b><p className="fu-gs">{p[4]}</p>
          <ol>{p[5].map((t, j) => <li key={j} className={j === step ? 'is-now' : j < step ? 'is-done' : ''} onClick={() => setStep(j)}><i>{j + 1}</i><span>{t}</span></li>)}</ol>
          <Link className="m-btn m-go fu-go" to={p[3]}>See it live →</Link></>
          : <p className="fu-hint">👆 Pick a planet. Each one is a live part of FEELESS with its own how-to.</p>}
      </aside>
    </div>
    <div className="fu-flag" data-testid="fu-flagships">
      <div className="fu-coins" aria-hidden="true">{FLAGSHIPS.map(([s, c], i) => <span key={s} className={`fu-coin c-${c}`} style={{ '--i': i }}><b>{s}</b></span>)}</div>
      <div className="fu-flagtx"><span className="eyebrow">FLAGSHIP COINS</span><h3>Three flagships today. Bigger, safer coins tomorrow.</h3>
        <ul>{FLAGSHIPS.map(([s, , t]) => <li key={s}><b>{s}</b> {t}</li>)}</ul>
        <p className="fu-note">$FEE, FEECAT and rFEE are the first coins of the FEELESS family — the proving ground. The plan is larger, audited coins built on the same
          rails once the platform, the audits and the security work are ready. That is a plan, not a promise or financial advice; nothing here is a return.</p></div>
    </div>
  </section>;
}
