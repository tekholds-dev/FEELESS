import React, { Suspense, lazy, useState } from 'react';
import { Slider } from '@heroui/react';
import { motion } from 'motion/react';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/keepDeal.css';
import '../../styles/stakeFlow.css';

const StakeFlow = lazy(() => import('./StakeFlow'));
const SeatCurve = lazy(() => import('./StakeCharts').then(m => ({ default: m.SeatCurve })));
const EarnLine = lazy(() => import('./StakeCharts').then(m => ({ default: m.EarnLine })));

// 🪙 THE DEAL (owner 2026-11-06, ledger: collective_stake.py). A send is a stake in the owner's auto-ranged pools. Its grade, up to 300, is its boost: grade 200 is 200x. It may earn up to that many times what it sent, only from real pool profit. The boost is also its cut of every profit. Every number here is the live rule from the server.
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const GRADE_MAX = 300;
export const boostX = grade => Math.max(1, Math.min(GRADE_MAX, Number(grade) || 0));   // the most it can ever earn
export const seatX = grade => 1 + Math.max(0, Math.min(GRADE_MAX, Number(grade) || 0)) / GRADE_MAX;   // how fast: stays small, so one great proof never crowds out the rest
export const pointsFor = (sent, grade) => (Number(sent) || 0) * boostX(grade);
// Dollars lift the cut: $10 1x, $100 2x, $1,000 3x. Past the knee each 10x adds only part of a step. Same rule as size_of on the server.
export const sizeOf = (rules, usd) => { const n = Number(usd) || 0; if (n <= 0) return 0; const knee = rules?.kneeUsd ?? 1000; return Math.max(0.25, 1 + Math.log10(Math.min(n, knee) / 10)) + (n > knee ? Math.log10(n / knee) * ((rules?.sizeAbovePct ?? 50) / 100) : 0); };
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only stake what you can lose.</b> It stays in the pools. It earns only from real pool profit, and pools can lose money. Taking rewards out is off for now. {rules?.collectivePoolPct != null ? `The Collective takes ${Math.round(rules.collectivePoolPct)}% of each profit.` : ''}</p>;
}
// 🎬 What a grade really means, played out. Three stories, each on the same rules as the ledger, and each ending in what it could not do.
const STORIES = [['The $2 moonshot', 2, 200, 'A tiny proof that graded huge'], ['The steady hand', 100, 87, 'A normal proof, a normal grade'], ['The perfect whale', 1000, 300, 'The top grade on a big send']];
const STORY_PROFIT = 1000;
export function storyOf(rules, usdIn, grade) {
  const x = boostX(grade); const limit = pointsFor(usdIn, grade); const seat = seatX(grade) * sizeOf(rules, usdIn) * (rules?.cutPerX ?? 1); const perDay = seat / 100 * STORY_PROFIT;
  return { x, limit, seat, perDay, days: perDay > 0 ? Math.ceil(limit / perDay) : null };
}
export function StakeStory({ rules = null, onTry = null, testid }) {
  const [at, setAt] = useState(0); const [, u, g, tag] = STORIES[at]; const st = storyOf(rules, u, g); const calm = typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
  const beats = [['🧾', 'It sends', usd(u), 'A proof and its dollars go in the pools'], ['⚖', 'It grades', `${g} / ${GRADE_MAX}`, 'Five checks and its fingerprint'], ['🚀', 'That is a boost of', `${Math.round(st.x)}x`, `The most it can ever earn is ${usd(st.limit)}`], ['🪑', 'Its seat', `${st.seat.toFixed(2)}%`, 'Small on purpose, so nobody crowds out the rest'], ['📈', `If the pools make ${usd(STORY_PROFIT)} a day`, `${usd(st.perDay)} a day`, st.days > 3650 ? 'It would take more than ten years' : `Reaches its limit around day ${st.days.toLocaleString()}`]];
  return <section className="kst" data-testid={testid}><header><small>WHAT A GRADE MEANS</small><span className="m-seg" role="group" aria-label="Pick a story">{STORIES.map(([n], i) => <button key={n} type="button" className={at === i ? 'active' : ''} aria-pressed={at === i} onClick={() => { setAt(i); onTry?.(STORIES[i][1], STORIES[i][2]); }} data-testid={`${testid}-${i}`}>{n}</button>)}</span></header>
    <p className="kst-tag">{tag}</p>
    <ol className="kst-beats" key={at}>{beats.map(([ic, k, v, t], i) => <motion.li key={k} initial={calm ? false : { opacity: 0, y: 14, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ delay: i * 0.28, duration: 0.3 }} data-testid={`${testid}-beat-${i}`}><Ic3 e={ic} size="30px" /><small>{k}</small><b className="m-num">{v}</b><span>{t}</span></motion.li>)}</ol>
    <motion.p className="kst-end" key={`end-${at}`} initial={calm ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }}><b>{usd(st.limit)} is a ceiling, not a payout.</b> Only real pool profit pays it. If the pools make nothing, it earns nothing, and pools can lose money. An example, not a promise.</motion.p></section>;
}
// A dollar slider that feels even from $1 to $100,000.
const toUsd = v => { const n = 10 ** (v / 20); return n >= 1000 ? Math.round(n / 100) * 100 : n >= 100 ? Math.round(n / 10) * 10 : Math.max(1, Math.round(n)); };
const toSlide = u => Math.log10(Math.max(1, u)) * 20;
const PROFITS = [100, 1000, 10000];
export function KeepDeal({ rules, sendUsd = null, start = null, testid = 'keep-deal' }) {
  const [sent, setSent] = useState(start?.usd || 100); const [grade, setGrade] = useState(start?.grade || 87); const [profit, setProfit] = useState(1000); const s = sendUsd ?? sent; const x = boostX(grade); const cut = seatX(grade) * sizeOf(rules, s) * (rules?.cutPerX ?? 1); const points = pointsFor(s, grade); const hit = cut > 0 ? Math.ceil(points / (cut / 100 * profit)) : null;
  return <section className="kpd" data-testid={testid}>{sendUsd == null ? <StakeStory rules={rules} onTry={(u, g) => { setSent(u); setGrade(g); }} testid={`${testid}-story`} /> : null}<SendWarning rules={rules} />
    <div className="kpd-sliders">{sendUsd == null ? <label className="kpd-slide" data-tip="Slide it, or tap the seat chart below"><small>IT SENDS</small><b className="m-num" data-testid={`${testid}-usd`}>{usd(s)}</b><Slider aria-label="Dollars it sends" minValue={0} maxValue={100} step={1} value={toSlide(s)} onChange={v => setSent(toUsd(Number(v)))} data-testid={`${testid}-send`}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider></label> : null}<label className="kpd-slide" data-tip="What the five checks and its fingerprint give the proof"><small>THE GRADE</small><b className="m-num" data-testid={`${testid}-grade-n`}>{Math.round(grade)}</b><Slider aria-label="The grade" minValue={0} maxValue={GRADE_MAX} step={1} value={grade} onChange={v => setGrade(Number(v))} data-testid={`${testid}-grade`}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider></label></div>
    <ol className="kpd-flow" data-testid={`${testid}-flow`}>{[['ITS BOOST', `${x.toFixed(2)}x`, `Grade ${Math.round(grade)} means up to ${Math.round(x)} times what it sent`], ['BOOST POINTS', points.toLocaleString(undefined, { maximumFractionDigits: 2 }), `The most this proof can earn is ${usd(points)}`], ['ITS SEAT', `${cut.toFixed(2)}%`, `Of every pool profit: ${seatX(grade).toFixed(2)}x for its grade times ${sizeOf(rules, s).toFixed(2)}x for its dollars, and past $${(rules?.kneeUsd ?? 1000).toLocaleString()} that grows slowly`]].map(([k, v, t], i) => <li key={k} style={{ '--i': i }} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></li>)}</ol>
    <Suspense fallback={<div className="skf-wait" />}><StakeFlow usd={s} grade={grade} x={x} points={points} seat={cut} collectivePct={rules?.collectivePoolPct ?? 20} testid={`${testid}-map`} /></Suspense>
    <div className="skc-grid"><figure className="skc"><figcaption><b>HOW BIG THE SEAT GETS</b>{sendUsd == null ? <small>Tap the chart to try a size</small> : null}</figcaption><Suspense fallback={<div className="skf-wait" />}><SeatCurve rules={rules} usd={s} grade={grade} onPick={sendUsd == null ? u => setSent(toUsd(toSlide(u))) : null} testid={`${testid}-seat`} /></Suspense></figure>
      <figure className="skc"><figcaption><b>IF THE POOLS MADE, A DAY</b><span className="m-seg" role="group" aria-label="Pool profit a day, for this example">{PROFITS.map(v => <button key={v} type="button" className={profit === v ? 'active' : ''} aria-pressed={profit === v} onClick={() => setProfit(v)} data-tip={`An example: the pools make $${v.toLocaleString()} a day`} data-testid={`${testid}-profit-${v}`}>${v >= 1000 ? `${v / 1000}K` : v}</button>)}</span></figcaption><Suspense fallback={<div className="skf-wait" />}><EarnLine points={points} seat={cut} profitDay={profit} testid={`${testid}-earn`} /></Suspense><small data-testid={`${testid}-earn-say`}>An example on the number you pick, not a promise. {hit && hit <= 360 ? <>Its limit of {usd(points)} comes around day {hit}, then its cut stops.</> : <>It stays under its {usd(points)} limit for the whole year.</>} Pools can make nothing, or lose money.</small></figure></div></section>;
}
