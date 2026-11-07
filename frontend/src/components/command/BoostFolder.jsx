import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { ProgressCircle, Slider } from '@heroui/react';
import { motion } from 'motion/react';
import { Check, CircleDashed, Layers3, ShieldCheck, Zap } from 'lucide-react';
import { SendWarning, boostX, dayEarn, seatOf, tinyUsd, usePoolRates } from './KeepDeal';
import { ProofSendForm, WeightBars, proofTitle } from './ProofKit';
import { Ic3 } from '../../lib/icon3d';
import { money } from './SplitFlow';
import { Fx, Roll } from './CollectiveSetup';
import '../../styles/boostFolder.css';

const Coin3D = lazy(() => import('./Coin3D'));

// 🪙 THE BOOST FOLDER (owner 2026-11-06): the agent's own dashboard, one screen. Its numbers across the top, its proofs on the left, the picked proof's real loop and its send in the middle, burn and pools on the right. The rules and the calculator live in The Collective. Every number comes from the server's ledger (collective_stake.py).
export function useAgentPool(cat, work, every = 30000) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; let first = true; const go = () => { if (first || !document.hidden) { first = false; Promise.resolve().then(() => work(cat.id, { op: 'pool' })).then(j => { if (on && j) setD({ ...j, readAt: Date.now() }); }).catch(() => {}); } }; go(); const t = setInterval(go, every); return () => { on = false; clearInterval(t); }; }, [cat?.id, work, every]);
  return d;
}
export function LiveCount({ pool, readAt, testid = 'bst-count' }) {
  const el = useRef(null); const base = Number(pool?.owedUsd) || 0; const rate = Number(pool?.ratePerSecUsd) || 0; const at = readAt || 0;
  useEffect(() => { const paint = () => { if (el.current) el.current.textContent = `$${(base + rate * Math.max(0, Date.now() - at) / 1000).toFixed(8)}`; }; paint(); if (!rate) return undefined; const t = setInterval(() => { if (!document.hidden) paint(); }, 200); return () => clearInterval(t); }, [base, rate, at]);
  return <b ref={el} className="bst-num m-num" data-testid={testid}>$0.00000000</b>;
}
const pct = v => `${(Number(v) || 0).toFixed(2)}%`;
const pts = v => (Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
const xOf = v => `${+(Number(v) || 0).toFixed(2)}x`;
const left = until => { const s = Math.max(0, until - Date.now() / 1000); return s >= 86400 ? `${(s / 86400).toFixed(1)} days` : `${Math.max(1, Math.round(s / 3600))} h`; };
const rise = i => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.04, duration: 0.2 } });
const Ring = ({ part, label }) => <ProgressCircle aria-label={label} value={Math.round(Math.max(0, Math.min(1, part)) * 100)} className="bof-ring"><ProgressCircle.Track><ProgressCircle.TrackCircle /><ProgressCircle.FillCircle /></ProgressCircle.Track></ProgressCircle>;

// ⚡ Burn points for time at the top seat.
function FastCompound({ s, r, busy, onBuy, focus }) {
  const most = Math.max(1, r.fastMaxDays ?? 30); const price = r.fastPtsPerDay ?? 5; const afford = Math.floor(((s.pointsLeft || 0) / price) * 4) / 4; const top = Math.min(most, afford); const [days, setDays] = useState(1); const d = Math.min(days, Math.max(0.25, top)); const cost = d * price; const lift = (s.topPct || 0) - (s.cutPct || 0); const can = top >= 0.25 && lift > 0;
  return <section className={`bof-card bof-fast${focus ? ' is-focus' : ''}${s.fastUntil ? ' is-on' : ''}`} data-testid="bof-fast"><header><Zap size={14} aria-hidden="true" /><h4>BURN POINTS</h4>{s.fastUntil ? <em className="m-num" data-testid="bof-fast-left">{left(s.fastUntil)} left</em> : null}</header>
    <div className="bof-cuts" aria-label="Its cut now and the top cut"><span><small>ITS SEAT</small><b className="m-num">{pct(s.nowPct)}</b></span><i aria-hidden="true"><motion.u initial={false} animate={{ scaleX: Math.min(1, (s.nowPct || 0) / Math.max(0.01, s.topPct || 1)) }} /></i><span><small>TOP SEAT</small><b className="m-num">{pct(s.topPct)}</b></span></div>
    {can ? <><Slider aria-label="Days at the top cut" className="bof-slider" minValue={0.25} maxValue={Math.max(0.25, top)} step={0.25} value={d} onChange={v => setDays(Number(v))} data-testid="bof-days"><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider>
      <div className="bof-fast-row"><span><b className="m-num">{d} day{d === 1 ? '' : 's'}</b><small>{pts(cost)} points. Its limit drops by {money(cost)}</small></span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onBuy(d)} data-tip="Burns these points. The extra comes only from room nobody holds, so no other agent's cut shrinks" data-testid="bof-burn">{busy ? 'Burning…' : 'Burn'}</button></div></>
      : <p className="bof-note" data-testid="bof-fast-why">{!s.pointsLeft ? 'It has no points. A graded proof brings points.' : lift <= 0 ? 'It already holds the top seat.' : `It needs ${pts(price / 4)} points for the shortest burn.`}</p>}</section>;
}

const KIND_ICON = { PoW: '⛏', PoP: '🎯', PoB: '🏟', PoC: '💡', PoS: '🧱', PoStatic: '🧱' };
const KIND_LIST = [['PoW', 'powFolders', 'pow'], ['PoP', 'popFolders', 'pop'], ['PoB', 'pobFolders', 'pob'], ['PoC', 'pocFolders', 'poc'], ['PoS', 'psFolders', 'pos']];
const PLAN_KEY = Object.fromEntries(KIND_LIST.map(k => [k[0], k[2]]));
export const sendableProofs = d => KIND_LIST.flatMap(([kind, key]) => (d?.[key] || []).filter(f => f.id && !f.live).map(f => ({ kind, f }))).sort((a, b) => (Number(b.f.at) || 0) - (Number(a.f.at) || 0));
const count = v => (Array.isArray(v) ? v.length : v && typeof v === 'object' ? Object.keys(v).length : 0);
// What its own folder really holds for each step of the loop. Nothing here is a guess: no record, no number.
const FOUND = {
  Research: f => { const shots = count(f.shots); const reads = count(f.reads) + count(f.sources); return shots || reads ? [shots ? `${shots} snapshot${shots === 1 ? '' : 's'}` : '', reads ? `${reads} source${reads === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ') : ''; },
  Decide: f => { const n = count(f.calls) + count(f.picks); return n ? `${n} call${n === 1 ? '' : 's'} on file` : ''; },
  File: f => (f.at ? new Date(f.at * 1000).toLocaleDateString() : ''),
  Grade: f => (f.pnlPct != null ? `${f.pnlPct >= 0 ? '+' : ''}${Number(f.pnlPct).toFixed(1)}%` : f.graded ? String(f.graded) : f.won != null ? (f.won ? 'Won' : 'Lost') : ''),
};
function ProofLoop({ kind, f, plans }) {
  const plan = plans?.plans?.[PLAN_KEY[kind]]; const loop = plans?.loop || []; if (!plan) return null;
  const graded = !!FOUND.Grade(f);
  return <ol className="bof-loop" data-testid={`bof-loop-${kind}`}>{loop.map(step => { const done = step === 'Grade' ? graded : true; const found = FOUND[step]?.(f); return <li key={step} className={done ? 'is-done' : 'is-wait'} data-testid={`bof-step-${step}`}><i aria-hidden="true">{done ? <Check size={11} /> : <CircleDashed size={11} />}</i><b>{step}</b><span>{plan.steps?.[step] || (step === 'Clarify' ? 'What you asked it to do' : '')}</span>{found ? <em className="m-num">{found}</em> : null}</li>; })}</ol>;
}
// 🧾 Every seat that read it, then everyone who scored it, in order.
function Verdicts({ x, review }) {
  const seats = review?.seats || []; const rows = x?.scored || [];
  return <div className="bof-verdicts" data-testid="bof-verdicts">{seats.length ? <ul>{seats.map(s => <li key={s.k} className={s.ok ? 'is-ok' : 'is-no'} data-tip={s.why}><ShieldCheck size={12} aria-hidden="true" /><b>{s.name}</b><small>{s.why}</small></li>)}</ul> : null}
    {rows.length ? <ol className="bof-receipt" data-testid={`bof-receipt-${x.id}`}>{rows.map((r, i) => <li key={i}><b className="m-num">{Math.round(r.score)}</b><span><small>{r.by}{r.was != null ? ` · was ${Math.round(r.was)}` : ''}</small>{r.why ? <em>{r.why}</em> : null}</span></li>)}</ol> : <small className="bof-receipt-wait">Waiting for OSSY and G4 to read it. Its score can change until they have.</small>}</div>;
}
const WORD = x => (x.held ? 'Held by the checks' : x.grade == null ? 'Waiting on a score' : `Score ${Math.round(x.grade)}`);
// What this send could do, on the pot and today's pool rate. Three scores, so the choice is plain.
function SendPreview({ usd, rules, top, pot, testid = 'bof-preview' }) {
  const rates = usePoolRates(); const year = rates?.hotPct ?? null; const scores = [...new Set([100, Math.round(top * 0.6), top])];
  return <table className="bof-preview" data-testid={testid}><thead><tr><th>Score</th><th>Boost</th><th>Most it can earn</th><th>Seat</th><th data-tip={year == null ? 'Reading today\'s pool rate' : `Today's pot of ${money(pot)} at a hot deep pool's live rate of ${year}% a year. An example, not a promise`}>A day today</th></tr></thead><tbody>{scores.map(g => { const x = boostX(g); const seat = seatOf(rules, x, usd); return <tr key={g} data-testid={`${testid}-${g}`}><td className="m-num">{g}</td><td className="m-num">{+x.toFixed(2)}x</td><td className="m-num">{money(usd * x)}</td><td className="m-num">{seat.toFixed(2)}%</td><td className="m-num">{year == null ? '…' : tinyUsd(dayEarn(seat, pot, year))}</td></tr>; })}</tbody></table>;
}
function ProofDesk({ cat, work, pick, plans, send, rules, score, weights, onSent }) {
  const [usd, setUsd] = useState(5); const top = score?.top || 300;
  if (!pick) return <section className="bof-card bof-desk" data-testid="bof-it"><p className="bof-note" data-testid="bof-it-none">No filed proof yet. Run any proof from its folder, and it shows up here ready to send.</p></section>;
  const { kind, f } = pick; const sent = f.sent || send; const plan = plans?.plans?.[PLAN_KEY[kind]];
  return <section className="bof-card bof-desk" data-testid="bof-it"><header className="bof-desk-h"><Ic3 e={KIND_ICON[kind]} size="26px" /><span><b>{proofTitle(f)}</b><small className="m-num">{plan?.code || kind}{plan?.what ? ` · ${plan.what}` : ''}</small></span>{send?.grade != null ? <em className="bof-score m-num" data-testid="bof-total-score" data-tip={`Its total score, out of ${top} today`}>{Math.round(send.grade)}<small>/{top}</small></em> : null}</header>
    <div className="bof-desk-body"><ProofLoop kind={kind} f={f} plans={plans} /><WeightBars v={weights?.[f.id]} testid="bof-weights" />
      {sent ? <div className="bof-after"><h4>SENT{send?.usd != null ? <span className="m-num"> {money(send.usd)} → {send.held ? '0' : money(send.usd * (send.x || 1))} limit</span> : null}{send?.sig ? <a href={`https://solscan.io/tx/${send.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Its transaction on Solscan">Tx ↗</a> : null}</h4><Verdicts x={send || { id: f.id }} review={f.sent?.review || f.review} /></div>
        : <div className="bof-after"><h4>SEND IT</h4><ProofSendForm key={f.id} cat={cat} work={work} f={f} kind={kind} coin={false} rules={rules} onUsd={setUsd} onSent={onSent} /><SendPreview usd={Number(usd) || 0} rules={rules} top={top} pot={score?.potUsd || 0} /></div>}</div></section>;
}
const FILTERS = ['All', 'Ready', 'Sent'];
function ProofRail({ rows, on, setOn, sendOf, sentNow, weights }) {
  const [view, setView] = useState('All'); const isSent = x => !!(x.f.sent || sentNow[x.f.id] || sendOf(x)); const shown = rows.filter(x => view === 'All' || (view === 'Sent') === isSent(x));
  return <section className="bof-card bof-rail" data-testid="bof-rail"><header><h4>PROOFS</h4><small className="m-num">{rows.filter(x => !isSent(x)).length} ready</small></header>
    <span className="m-seg" role="group" aria-label="Which proofs">{FILTERS.map(k => <button key={k} type="button" className={view === k ? 'active' : ''} aria-pressed={view === k} onClick={() => setView(k)} data-testid={`bof-show-${k}`}>{k}</button>)}</span>
    <ul className="bof-it-list" data-testid="bof-it-list">{shown.map(x => { const send = sendOf(x); return <li key={x.f.id}><button type="button" className={on === x.f.id ? 'is-on' : ''} aria-pressed={on === x.f.id} onClick={() => setOn(x.f.id)} data-tip={`Open this ${x.kind}`} data-testid={send?.id === x.f.id ? `bof-send-${send.id}` : `bof-it-${x.f.id}`}><Ic3 e={KIND_ICON[x.kind] || '🧾'} size="20px" /><span><b>{proofTitle(x.f)}</b><small className="m-num">{x.kind}{send ? ` · ${WORD(send)}${send.usd != null ? ` · ${money(send.usd)} → ${send.held ? '0' : money(send.usd * (send.x || 1))}` : ''}` : isSent(x) ? ' · Sent' : ''}</small></span>{weights?.[x.f.id] ? <b className={`pwb-rank is-${weights[x.f.id].rank}`} data-tip={`On its record: ${Math.round(weights[x.f.id].score)}`}>{weights[x.f.id].rank}</b> : null}</button></li>; })}{!shown.length ? <li className="bof-note">{rows.length ? `Nothing ${view.toLowerCase()} yet.` : 'No proofs yet.'}</li> : null}</ul></section>;
}
export function BoostFolder({ cat, work }) {
  const d0 = useAgentPool(cat, work); const [over, setOver] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [focus, setFocus] = useState(false); const [d, setD] = useState(null); const [on, setOn] = useState(null); const [sentNow, setSentNow] = useState({});
  useEffect(() => { let live = true; Promise.resolve().then(() => work(cat.id, { op: 'state' })).then(j => { if (live) setD(j || {}); }).catch(() => { if (live) setD({}); }); return () => { live = false; }; }, [cat?.id, work]);
  const sends = useMemo(() => d0?.sends || [], [d0?.sends]); const folders = useMemo(() => sendableProofs(d), [d]);
  // A send made before the folder kept its receipt still shows, so no money ever goes missing from the list.
  const rows = useMemo(() => { const sigs = new Set(folders.map(x => x.f.sent?.sig).filter(Boolean)); const loose = sends.filter(x => !sigs.has(x.sig)).map(x => ({ kind: x.kind || 'PoW', loose: true, f: { id: x.id, name: x.sym ? `${x.name || 'Proof'} · $${x.sym}` : x.name, sent: { sig: x.sig } } })); return [...folders, ...loose]; }, [folders, sends]);
  const sendOf = x => sends.find(y => (x.loose ? y.id === x.f.id : !!x.f.sent?.sig && y.sig === x.f.sent.sig)) || null;
  if (!d0) return <p className="dsk-note">reading its boost…</p>;
  const r = d0.rules || {}; const score = d0.score; const s = { ...(d0.stake || {}), ...(over || {}) }; const pools = d0.pools || []; const cap = s.capUsd || 0; const live = pools.filter(p => p.on); const top = score?.top || 300; const next = (score?.ladder || []).find(x => x.top > top);
  const pick = rows.find(x => x.f.id === on) || rows.find(x => !sendOf(x) && !x.f.sent) || rows[0] || null;
  const buy = async days => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'pool_fast', cap: days }); setOver(j.stake); } catch (e) { setErr(e.message || 'Not saved'); } setBusy(false); };
  const hitCoin = () => { setFocus(true); setTimeout(() => setFocus(false), 1200); };
  return <Fx><div className="bof" data-testid="bof">
    <motion.section className="bof-bar m-live" {...rise(0)}>
      <button type="button" className={`bof-coin${s.fastUntil ? ' is-fast' : ''}`} onClick={hitCoin} data-tip="Its ring is the points left. Tap to light up the burn" data-testid="bof-coin"><Ring part={cap ? s.pointsLeft / cap : 0} label="Points left" /><span className="bof-coin-3d"><Suspense fallback={null}><Coin3D energy={s.fastUntil ? 1 : s.pointsLeft ? 0.65 : 0.35} size={58} /></Suspense></span></button>
      <span className="is-cash" data-tip="Rewards counting live. A real pool profit releases to it second by second. Taking them out is off until a lawyer has looked" data-testid="bof-cash-tile"><small>BOOST CASH</small><LiveCount pool={d0.pool} readAt={d0.readAt} testid="bst-count" /><em className="bof-off" data-testid="bst-withdraw-off">Withdrawals off</em></span>
      {[['BOOST POINTS', <Roll key="p" v={s.pointsLeft || 0} fmt={pts} testid="bof-points" />, cap ? `of ${pts(cap)}` : 'From graded proofs', 'What its proofs and dollars hold. Each dollar of boost cash or each burn takes one off'], ['ITS BOOST', <Roll key="x" v={s.x || 0} fmt={xOf} testid="bof-x" />, s.grade ? `Average score ${Math.round(s.grade)}` : 'From its first score', 'Its score over 100. The most it can earn, as a multiple of what it sent'], ['ITS SEAT', <Roll key="c" v={s.nowPct || 0} fmt={pct} testid="bof-cut" />, 'Of each pool profit', 'Its share of every real pool profit right now'], ['STAKED', <Roll key="s" v={s.sentUsd || 0} fmt={money} testid="bof-staked" />, 'In the pools', 'What its proofs have sent. It stays in the pools']].map(([k, v, sub, t]) => <span key={k} data-tip={t}><small>{k}</small>{v}<em>{sub}</em></span>)}
      <span className="bof-top" data-tip="How high a score can go today. A bigger pot raises it" data-testid="bof-top"><small>TOP SCORE</small><b className="m-num">{top}</b><em className="m-num">{next ? `${money(score?.potUsd || 0)} of ${money(next.pot)} for ${next.top}` : top >= 1000 ? 'At the top' : 'Reading the pot'}</em>{next ? <i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, (score?.potUsd || 0) / Math.max(1, next.pot)))})` }} /></i> : null}</span>
    </motion.section>
    <div className="bof-main">
      <motion.div className="bof-col" {...rise(1)}><ProofRail rows={rows} on={pick?.f.id} setOn={setOn} sendOf={sendOf} sentNow={sentNow} weights={d0.weights} /></motion.div>
      <motion.div className="bof-col" {...rise(2)}><ProofDesk cat={cat} work={work} pick={pick} plans={d0.proofPlan} send={pick ? sendOf(pick) : null} rules={r} score={score} weights={d0.weights} onSent={x => { if (pick) setSentNow(y => ({ ...y, [pick.f.id]: x })); }} /></motion.div>
      <motion.div className="bof-col bof-side" {...rise(3)}><FastCompound s={s} r={r} busy={busy} onBuy={buy} focus={focus} />
        <section className="bof-card bof-pools" data-testid="bof-pools"><header><Layers3 size={14} aria-hidden="true" /><h4>WHERE THE STAKE WORKS</h4><small className="m-num">{live.length} open</small></header>
          {live.length ? <ul>{live.map(p => <li key={p.id} data-testid={`bof-pool-${p.id}`}><b>{p.pair}</b><small>{p.platform}</small><em className="m-num" data-tip="Profit this pool has really paid">{money(p.profitUsd)}</em>{p.address ? <a href={`https://solscan.io/account/${p.address}`} target="_blank" rel="noopener noreferrer" data-tip="See the pool on Solscan">↗</a> : null}</li>)}</ul> : <p className="bof-note" data-testid="bof-no-pools">No pool is open yet. Until one is, there is no profit, and nothing pays.</p>}</section>
        <SendWarning rules={r} /></motion.div>
    </div>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
  </div></Fx>;
}
