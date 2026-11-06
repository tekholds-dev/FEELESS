import React, { Suspense, lazy, useState } from 'react';
import { Slider } from '@heroui/react';
import '../../styles/keepDeal.css';
import '../../styles/stakeFlow.css';

const StakeFlow = lazy(() => import('./StakeFlow'));
const SeatCurve = lazy(() => import('./StakeCharts').then(m => ({ default: m.SeatCurve })));
const EarnLine = lazy(() => import('./StakeCharts').then(m => ({ default: m.EarnLine })));

// 🪙 THE DEAL (owner 2026-11-06, ledger: collective_stake.py). A send is a stake in the owner's auto-ranged pools. Its grade makes its boost: grade 87 is 1.87x. It may earn up to that many times what it sent, only from real pool profit. The boost is also its cut of every profit. Every number here is the live rule from the server.
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const boostX = grade => 1 + Math.max(0, Math.min(100, Number(grade) || 0)) / 100;
export const pointsFor = (sent, grade) => (Number(sent) || 0) * boostX(grade);
// Dollars lift the cut: $10 1x, $100 2x, $1,000 3x. Past the knee each 10x adds only part of a step. Same rule as size_of on the server.
export const sizeOf = (rules, usd) => { const n = Number(usd) || 0; if (n <= 0) return 0; const knee = rules?.kneeUsd ?? 1000; return Math.max(0.25, 1 + Math.log10(Math.min(n, knee) / 10)) + (n > knee ? Math.log10(n / knee) * ((rules?.sizeAbovePct ?? 50) / 100) : 0); };
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only stake what you can lose.</b> It stays in the pools. It earns only from real pool profit, and pools can lose money. Taking rewards out is off for now. {rules?.collectivePoolPct != null ? `The Collective takes ${Math.round(rules.collectivePoolPct)}% of each profit.` : ''}</p>;
}
// A dollar slider that feels even from $1 to $100,000.
const toUsd = v => { const n = 10 ** (v / 20); return n >= 1000 ? Math.round(n / 100) * 100 : n >= 100 ? Math.round(n / 10) * 10 : Math.max(1, Math.round(n)); };
const toSlide = u => Math.log10(Math.max(1, u)) * 20;
const PROFITS = [100, 1000, 10000];
export function KeepDeal({ rules, sendUsd = null, start = null, testid = 'keep-deal' }) {
  const [sent, setSent] = useState(start?.usd || 100); const [grade, setGrade] = useState(start?.grade || 87); const [profit, setProfit] = useState(1000); const s = sendUsd ?? sent; const x = boostX(grade); const cut = x * sizeOf(rules, s) * (rules?.cutPerX ?? 1); const points = pointsFor(s, grade); const hit = cut > 0 ? Math.ceil(points / (cut / 100 * profit)) : null;
  return <section className="kpd" data-testid={testid}><SendWarning rules={rules} />
    <div className="kpd-sliders">{sendUsd == null ? <label className="kpd-slide" data-tip="Slide it, or tap the seat chart below"><small>IT SENDS</small><b className="m-num" data-testid={`${testid}-usd`}>{usd(s)}</b><Slider aria-label="Dollars it sends" minValue={0} maxValue={100} step={1} value={toSlide(s)} onChange={v => setSent(toUsd(Number(v)))} data-testid={`${testid}-send`}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider></label> : null}<label className="kpd-slide" data-tip="What the five checks and its fingerprint give the proof"><small>THE GRADE</small><b className="m-num" data-testid={`${testid}-grade-n`}>{Math.round(grade)}</b><Slider aria-label="The grade" minValue={0} maxValue={100} step={1} value={grade} onChange={v => setGrade(Number(v))} data-testid={`${testid}-grade`}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider></label></div>
    <ol className="kpd-flow" data-testid={`${testid}-flow`}>{[['ITS BOOST', `${x.toFixed(2)}x`, `Grade ${Math.round(grade)}: 1 + ${Math.round(grade)}/100`], ['BOOST POINTS', points.toLocaleString(undefined, { maximumFractionDigits: 2 }), `The most this proof can earn is ${usd(points)}`], ['ITS SEAT', `${cut.toFixed(2)}%`, `Of every pool profit: ${x.toFixed(2)}x boost times ${sizeOf(rules, s).toFixed(2)}x for its dollars, and past $${(rules?.kneeUsd ?? 1000).toLocaleString()} that grows slowly`]].map(([k, v, t], i) => <li key={k} style={{ '--i': i }} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></li>)}</ol>
    <Suspense fallback={<div className="skf-wait" />}><StakeFlow usd={s} grade={grade} x={x} points={points} seat={cut} collectivePct={rules?.collectivePoolPct ?? 20} testid={`${testid}-map`} /></Suspense>
    <div className="skc-grid"><figure className="skc"><figcaption><b>HOW BIG THE SEAT GETS</b>{sendUsd == null ? <small>Tap the chart to try a size</small> : null}</figcaption><Suspense fallback={<div className="skf-wait" />}><SeatCurve rules={rules} usd={s} grade={grade} onPick={sendUsd == null ? u => setSent(toUsd(toSlide(u))) : null} testid={`${testid}-seat`} /></Suspense></figure>
      <figure className="skc"><figcaption><b>IF THE POOLS MADE, A DAY</b><span className="m-seg" role="group" aria-label="Pool profit a day, for this example">{PROFITS.map(v => <button key={v} type="button" className={profit === v ? 'active' : ''} aria-pressed={profit === v} onClick={() => setProfit(v)} data-tip={`An example: the pools make $${v.toLocaleString()} a day`} data-testid={`${testid}-profit-${v}`}>${v >= 1000 ? `${v / 1000}K` : v}</button>)}</span></figcaption><Suspense fallback={<div className="skf-wait" />}><EarnLine points={points} seat={cut} profitDay={profit} testid={`${testid}-earn`} /></Suspense><small data-testid={`${testid}-earn-say`}>An example on the number you pick, not a promise. {hit && hit <= 360 ? <>Its limit of {usd(points)} comes around day {hit}, then its cut stops.</> : <>It stays under its {usd(points)} limit for the whole year.</>} Pools can make nothing, or lose money.</small></figure></div></section>;
}
