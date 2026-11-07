import React, { Suspense, lazy, useDeferredValue, useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Ic3 } from '../../lib/icon3d';
import { apiUrl } from '../../lib/api';
import { isCalm } from '../../lib/fxPause';
import '../../styles/keepDeal.css';
import '../../styles/stakeFlow.css';

const StakeFlow = lazy(() => import('./StakeFlow'));
const EarnLine = lazy(() => import('./StakeCharts').then(m => ({ default: m.EarnLine })));

// 🪙 THE DEAL (owner 2026-11-06, ledger: collective_stake.py). A send is a stake in the owner's auto-ranged pools. Its score makes its boost: 300, the base top and only for a flawless proof, is 3x. The top grows to 1000 with the pot. It may earn up to that many times what it sent, only from real pool profit. The boost is also its cut of every profit. Every number here is the live rule from the server.
export const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const GRADE_BASE = 300; export const GRADE_MAX = 1000;
export const boostX = grade => Math.max(1, Math.min(GRADE_MAX, Number(grade) || 0) / 100);   // score over 100: the most it can ever earn, as a multiple of what it sent
export const pointsFor = (sent, grade) => (Number(sent) || 0) * boostX(grade);
// Dollars lift the cut: $10 1x, $100 2x, $1,000 3x. Past the knee each 10x adds only part of a step. Same rule as size_of on the server.
export const sizeOf = (rules, usd) => { const n = Number(usd) || 0; if (n <= 0) return 0; const knee = rules?.kneeUsd ?? 1000; return Math.max(0.25, 1 + Math.log10(Math.min(n, knee) / 10)) + (n > knee ? Math.log10(n / knee) * ((rules?.sizeAbovePct ?? 50) / 100) : 0); };
// Its share of each profit: its boost times its dollars, and never past what one wallet may hold. Same rule as cuts() on the server.
export const seatOf = (rules, x, usdIn) => Math.min(x * sizeOf(rules, usdIn) * (rules?.cutPerX ?? 1), rules?.walletCapPct ?? 10);
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only stake what you can lose.</b> It stays in the pools. It earns only from real pool profit, and pools can lose money. Taking rewards out is off for now. {rules?.collectivePoolPct != null ? `The Collective takes ${Math.round(rules.collectivePoolPct)}% of each profit.` : ''}</p>;
}
// 🎬 What a grade really means, played out. Three stories, each on the same rules as the ledger, and each ending in what it could not do.
const STORIES = [['A flawless $5', 5, 300, 'A $5 PoStatic project with nothing wrong in it. While the pot is small, 300 is the top anyone can score'], ['A good $100', 100, 187, 'Solid work, with a few things left to prove'], ['When the pot is huge', 5, 1000, 'The same flawless $5, once the pot is big enough to pay 10x and pay it at once']];
const STORY_PROFIT = 50;
export function storyOf(rules, usdIn, grade) {
  const x = boostX(grade); const limit = pointsFor(usdIn, grade); const seat = seatOf(rules, x, usdIn); const perDay = seat / 100 * STORY_PROFIT;
  return { x, limit, seat, perDay, days: perDay > 0 ? Math.ceil(limit / perDay) : null };
}
export function StakeStory({ rules = null, onTry = null, testid }) {
  const [at, setAt] = useState(0); const [, u, g, tag] = STORIES[at]; const st = storyOf(rules, u, g); const calm = isCalm();
  const beats = [['🧾', 'It sends', usd(u), 'A proof and its dollars go in the pools'], ['⚖', 'It scores', `${g}`, g >= GRADE_BASE ? 'Five checks, its print, then every reviewer says flawless' : 'Five checks, its print, then the reviewers'], ['🚀', 'That is a boost of', `${+st.x.toFixed(2)}x`, `The most it can ever earn is ${usd(st.limit)}`], ['🪑', 'Its seat', `${st.seat.toFixed(2)}%`, 'Its boost times its dollars, and never past what one wallet may hold'], ['📈', `If the pools make ${usd(STORY_PROFIT)} a day`, `${usd(st.perDay)} a day`, st.days > 3650 ? 'It would take more than ten years' : `Reaches its limit around day ${st.days.toLocaleString()}`]];
  return <section className="kst" data-testid={testid}><header><small>WHAT A SCORE MEANS</small><span className="m-seg" role="group" aria-label="Pick a story">{STORIES.map(([n], i) => <button key={n} type="button" className={at === i ? 'active' : ''} aria-pressed={at === i} onClick={() => { setAt(i); onTry?.(STORIES[i][1], STORIES[i][2]); }} data-testid={`${testid}-${i}`}>{n}</button>)}</span></header>
    <p className="kst-tag">{tag}</p>
    <ol className="kst-beats" key={at}>{beats.map(([ic, k, v, t], i) => <motion.li key={k} initial={calm ? false : { opacity: 0, y: 14, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ delay: i * 0.28, duration: 0.3 }} data-testid={`${testid}-beat-${i}`}><Ic3 e={ic} size="30px" /><small>{k}</small><b className="m-num">{v}</b><span>{t}</span></motion.li>)}</ol>
    <motion.p className="kst-end" key={`end-${at}`} initial={calm ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }}><b>{usd(st.limit)} is a ceiling, not a payout.</b> Only real pool profit pays it. If the pools make nothing, it earns nothing, and pools can lose money. An example, not a promise.</motion.p></section>;
}
// 🪜 How high a score can go today, and what a bigger pot unlocks.
const STEPS_OF = rules => [[0, 300, rules?.dripDays ?? 7], [rules?.tier500Usd ?? 10000, 500, (rules?.dripDays ?? 7) / 2], [rules?.tier750Usd ?? 100000, 750, (rules?.dripDays ?? 7) / 4], [rules?.tier1000Usd ?? 1000000, 1000, 0]];
const speedWord = d => (d <= 0 ? 'Pays at once' : d >= 1 ? `Pays over ${+d.toFixed(1)} day${d === 1 ? '' : 's'}` : `Pays over ${Math.round(d * 24)} hours`);
export function ScoreLadder({ rules, score = null, testid = 'score-ladder' }) {
  const rows = score?.ladder ? score.ladder.map(r => [r.pot, r.top, r.drip]) : STEPS_OF(rules); const top = score?.top ?? rows[0][1]; const pot = score?.potUsd ?? null; const next = rows.find(r => r[1] > top); const part = next && pot != null ? Math.min(1, pot / Math.max(1, next[0])) : 0;
  return <section className="ksl" data-testid={testid}><header><span><small>TODAY'S TOP SCORE</small><b className="m-num" data-testid={`${testid}-top`}>{top}</b></span><p>Only a flawless proof reaches the top. A score over 100 is its boost: {top} is {top / 100}x. {next ? <>When the pot reaches {usd(next[0])}, the top becomes {next[1]}.</> : 'The pot is at the top of the range.'}</p>{pot != null && next ? <span className="ksl-pot" data-tip="What the Collective really holds now, against the next step"><small className="m-num">POT {usd(pot)}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, part)})` }} /></i></span> : null}</header>
    <ol>{rows.map(([p, t, d]) => <li key={t} className={t === top ? 'is-now' : t < top ? 'is-past' : ''} data-testid={`${testid}-${t}`}><b className="m-num">{t}</b><em className="m-num">{t / 100}x</em><small>{speedWord(d)}</small><small className="m-num">{p ? `Pot ${usd(p)}` : 'From day one'}</small></li>)}</ol></section>;
}
// 📡 Today's typical yearly rates, shared by every example on the page. One read per 5 minutes.
const RATES = { at: 0, v: null, wait: null };
const readRates = () => { if (RATES.v && Date.now() - RATES.at < 300000) return Promise.resolve(RATES.v); RATES.wait = RATES.wait || fetch(apiUrl('/api/reputation/pool-rates')).then(r => (r.ok ? r.json() : null)).then(j => { RATES.wait = null; if (j) { RATES.v = j; RATES.at = Date.now(); } return j; }).catch(() => { RATES.wait = null; return null; }); return RATES.wait; };
export function usePoolRates() { const [v, setV] = useState(RATES.v); useEffect(() => { let on = true; readRates().then(j => { if (on && j) setV(j); }); return () => { on = false; }; }, []); return v; }
export const dayProfit = (pot, yearPct) => (Number(pot) || 0) * (Number(yearPct) || 0) / 100 / 365;
export const dayEarn = (seat, pot, yearPct) => (Number(seat) || 0) / 100 * dayProfit(pot, yearPct);
export const tinyUsd = v => { const n = Number(v) || 0; if (!n) return '$0.00'; if (n >= 1) return usd(n); return `$${n >= 0.01 ? n.toFixed(3) : n >= 0.0001 ? n.toFixed(4) : '<0.0001'}`; };
export const limitIn = (limit, perDay) => { if (!(perDay > 0)) return 'Never, no profit'; const d = limit / perDay; return d < 1 ? 'Under a day' : d < 365 ? `${Math.ceil(d)} days` : d > 36500 ? 'Over 100 years' : `${(d / 365).toFixed(1)} years`; };
const SIZES = [1, 5, 25, 100, 1000, 10000];
const Amount = ({ label, tip, unit = '$', value, set, step = 'any', min = 0, chips = null, testid }) => <div className="kpd-in" data-tip={tip}><label><small>{label}</small><span className="kpd-box">{unit === '$' ? <i>$</i> : null}<input className="m-num" type="number" min={min} step={step} value={value} onChange={e => set(e.target.value === '' ? '' : Number(e.target.value))} aria-label={label} data-testid={testid} />{unit !== '$' ? <i>{unit}</i> : null}</span></label>{chips ? <span className="m-seg" role="group" aria-label={`${label}, quick picks`}>{chips.map(([k, v]) => <button key={k} type="button" className={Number(value) === Number(v) ? 'active' : ''} aria-pressed={Number(value) === Number(v)} onClick={() => set(v)} data-testid={`${testid}-${k.replace(/\W+/g, '').toLowerCase()}`}>{k}</button>)}</span> : null}</div>;
// 🧮 WHAT PAYS. Real amounts in, the live rules out: every size from $1 up, on the pot and rate you type. It starts on a hot deep pool's live rate, since the middle of the board pays under 1% some days.
export function KeepDeal({ rules, sendUsd = null, start = null, score = null, testid = 'keep-deal' }) {
  const rates = usePoolRates(); const top = score?.top ?? 300; const livePot = score?.potUsd ?? null;
  const [sent, setSent] = useState(start?.usd || 1); const [grade, setGrade] = useState(start?.grade || top); const [pot, setPot] = useState(10000); const [typed, setTyped] = useState(null);
  const rate = typed ?? rates?.hotPct ?? 20; const s = sendUsd ?? (Number(sent) || 0); const g = Math.max(0, Math.min(GRADE_MAX, Number(grade) || 0)); const x = boostX(g); const seat = seatOf(rules, x, s); const limit = pointsFor(s, g); const perDay = dayEarn(seat, pot, rate); const slow = useDeferredValue({ s, g, x, seat, limit, profit: dayProfit(pot, rate), piece: rules?.collectivePoolPct ?? 20 });
  const rateChips = [['Flat', 0], ...(rates?.lendPct != null ? [[`Lending ${rates.lendPct}%`, rates.lendPct]] : []), ...(rates?.poolPct != null ? [[`Pool ${rates.poolPct}%`, rates.poolPct]] : []), ...(rates?.hotPct != null ? [[`Hot ${rates.hotPct}%`, rates.hotPct]] : [])];
  const potChips = [...(livePot != null ? [['Today', livePot]] : []), ['$10K', 10000], ['$100K', 100000], ['$1M', 1000000]];
  return <section className="kpd" data-testid={testid}>
    <div className="kpd-inputs">{sendUsd == null ? <Amount label="IT SENDS" tip="Any real amount. $1 is the least" value={sent} set={setSent} min={1} testid={`${testid}-usd`} chips={[['$1', 1], ['$5', 5], ['$100', 100]]} /> : null}
      <Amount label="ITS SCORE" unit={`of ${top}`} tip={`Only a flawless proof reaches ${top} today. Type more to see what a bigger pot makes possible`} value={grade} set={setGrade} step={1} testid={`${testid}-grade`} chips={[['100', 100], ['187', 187], [`${top}`, top]]} />
      <Amount label="THE POT" tip="What the pools hold. Today is the live number. The others show what happens as it grows" value={pot} set={setPot} testid={`${testid}-pot`} chips={potChips} />
      <Amount label="POOLS MAKE" unit="% a year" tip={rates?.pools ? `Live from ${rates.pools} deep pools and ${rates.lends} lending markets, read today. Rates move daily, and pools can also lose money` : 'Reading today\'s rates'} value={rate} set={setTyped} testid={`${testid}-rate`} chips={rateChips} /></div>
    <ol className="kpd-out" data-testid={`${testid}-flow`}>{[['ITS BOOST', `${+x.toFixed(2)}x`, `Score ${Math.round(g)}`], ['MOST IT CAN EARN', usd(limit), 'Its limit, not a payout'], ['ITS SEAT', `${seat.toFixed(2)}%`, 'Of each pool profit'], ['A DAY', tinyUsd(perDay), `The pools make ${tinyUsd(dayProfit(pot, rate))}`], ['A MONTH', tinyUsd(perDay * 30), 'At this rate, if it holds'], ['REACHES ITS LIMIT', limitIn(limit, perDay), 'Then its cut stops']].map(([k, v, t]) => <li key={k}><small>{k}</small><b className="m-num">{v}</b><em>{t}</em></li>)}</ol>
    <div className="kpd-grid">
      <figure className="kpd-table"><figcaption><b>WHAT PAYS, FROM $1</b><small>At score {Math.round(g)}. Tap a row</small></figcaption><table data-testid={`${testid}-table`}><thead><tr><th>Sends</th><th>Limit</th><th>Seat</th><th>A day</th><th>A month</th><th>To limit</th></tr></thead><tbody>{SIZES.map(u => { const st = seatOf(rules, x, u); const day = dayEarn(st, pot, rate); return <tr key={u} className={u === s ? 'is-on' : ''} onClick={sendUsd == null ? () => setSent(u) : undefined} data-testid={`${testid}-row-${u}`}><td className="m-num">{usd(u)}</td><td className="m-num">{usd(pointsFor(u, g))}</td><td className="m-num">{st.toFixed(2)}%</td><td className="m-num">{tinyUsd(day)}</td><td className="m-num">{tinyUsd(day * 30)}</td><td className="m-num">{limitIn(pointsFor(u, g), day)}</td></tr>; })}</tbody></table><ScoreLadder rules={rules} score={score} testid={`${testid}-ladder`} /></figure>
      <div className="kpd-right"><Suspense fallback={<div className="skf-wait" />}><StakeFlow usd={slow.s} grade={slow.g} x={slow.x} points={slow.limit} seat={slow.seat} collectivePct={slow.piece} dayUsd={slow.profit} testid={`${testid}-map`} /></Suspense>
        <figure className="skc"><Suspense fallback={<div className="skf-wait" />}><EarnLine points={slow.limit} seat={slow.seat} profitDay={slow.profit} testid={`${testid}-earn`} /></Suspense></figure></div></div>
    <SendWarning rules={rules} /></section>;
}
