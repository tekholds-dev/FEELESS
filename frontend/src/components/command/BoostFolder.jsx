import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { ProgressCircle, Slider } from '@heroui/react';
import { motion } from 'motion/react';
import { BadgeCheck, CircleAlert, Layers3, Zap } from 'lucide-react';
import { KeepDeal } from './KeepDeal';
import { money } from './SplitFlow';
import { Fx, Roll } from './CollectiveSetup';
import '../../styles/boostFolder.css';

const Coin3D = lazy(() => import('./Coin3D'));

// 🪙 THE BOOST FOLDER (owner 2026-11-06): what it staked, its grade, its boost, its cut of every pool profit, and the coin that burns points for fast compound time. Every number comes from the server's ledger (collective_stake.py).
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
const xOf = v => `${(Number(v) || 0).toFixed(2)}x`;
const left = until => { const s = Math.max(0, until - Date.now() / 1000); return s >= 86400 ? `${(s / 86400).toFixed(1)} days` : `${Math.max(1, Math.round(s / 3600))} h`; };
const rise = i => ({ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.05, duration: 0.24 } });
const Ring = ({ part, label, children }) => <ProgressCircle aria-label={label} value={Math.round(Math.max(0, Math.min(1, part)) * 100)} className="bof-ring"><ProgressCircle.Track><ProgressCircle.TrackCircle /><ProgressCircle.FillCircle /></ProgressCircle.Track>{children}</ProgressCircle>;
// ⚡ The coin is the throttle. Its ring is the points left, it spins hard while fast time runs, and tapping it brings up the burn.
function FastCompound({ s, r, busy, onBuy, focus }) {
  const most = Math.max(1, r.fastMaxDays ?? 30); const price = r.fastPtsPerDay ?? 5; const afford = Math.floor(((s.pointsLeft || 0) / price) * 4) / 4; const top = Math.min(most, afford); const [days, setDays] = useState(1); const d = Math.min(days, Math.max(0.25, top)); const cost = d * price; const lift = (s.topPct || 0) - (s.cutPct || 0); const can = top >= 0.25 && lift > 0;
  return <section className={`bof-fast${focus ? ' is-focus' : ''}${s.fastUntil ? ' is-on' : ''}`} data-testid="bof-fast"><header><Zap size={16} aria-hidden="true" /><h4>FAST COMPOUND</h4>{s.fastUntil ? <em className="m-num" data-testid="bof-fast-left">{left(s.fastUntil)} left</em> : null}</header>
    <div className="bof-cuts" aria-label="Its cut now and the top cut"><span><small>ITS SEAT</small><b className="m-num">{pct(s.nowPct)}</b></span><i aria-hidden="true"><motion.u initial={false} animate={{ scaleX: Math.min(1, (s.nowPct || 0) / Math.max(0.01, s.topPct || 1)) }} /></i><span><small>TOP SEAT</small><b className="m-num">{pct(s.topPct)}</b></span></div>
    {can ? <><Slider aria-label="Days at the top cut" className="bof-slider" minValue={0.25} maxValue={Math.max(0.25, top)} step={0.25} value={d} onChange={v => setDays(Number(v))} data-testid="bof-days"><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider>
      <div className="bof-fast-row"><span><b className="m-num">{d} day{d === 1 ? '' : 's'}</b><small>for {cost.toLocaleString(undefined, { maximumFractionDigits: 2 })} boost points. It can then earn {money(cost)} less in all, and reach the rest sooner</small></span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onBuy(d)} data-tip="Burns these points. The extra comes only from room nobody holds, so no other agent's cut shrinks" data-testid="bof-burn">{busy ? 'Burning…' : 'Burn points'}</button></div></>
      : <p className="bof-note" data-testid="bof-fast-why">{!s.pointsLeft ? 'It has no points. A graded proof brings points.' : lift <= 0 ? 'It already holds the top cut.' : `It needs ${(price / 4).toLocaleString(undefined, { maximumFractionDigits: 2 })} points for the shortest burn.`}</p>}</section>;
}
const SEND_WORD = (x, rate) => (x.held ? 'Held by the five checks. No points until cleared' : x.grade == null ? 'Sent before grading, counts as 1x' : `Grade ${Math.round(x.grade)} · ${rate}`);
export function BoostFolder({ cat, work }) {
  const d0 = useAgentPool(cat, work); const [over, setOver] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [focus, setFocus] = useState(false); const fastAt = useRef(null);
  if (!d0) return <p className="dsk-note">reading its boost…</p>;
  const r = d0.rules || {}; const s = { ...(d0.stake || {}), ...(over || {}) }; const pools = d0.pools || []; const sends = d0.sends || []; const cap = s.capUsd || 0; const live = pools.filter(p => p.on);
  const buy = async days => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'pool_fast', cap: days }); setOver(j.stake); } catch (e) { setErr(e.message || 'Not saved'); } setBusy(false); };
  const hitCoin = () => { setFocus(true); fastAt.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }); setTimeout(() => setFocus(false), 1200); };
  return <Fx><div className="bof" data-testid="bof">
    <motion.section className="bof-hero m-live" {...rise(0)}>
      <button type="button" className={`bof-coin${s.fastUntil ? ' is-fast' : ''}`} onClick={hitCoin} data-tip="Its ring is the points left. Tap to burn points for fast compound time" data-testid="bof-coin"><Ring part={cap ? s.pointsLeft / cap : 0} label="Points left" /><span className="bof-coin-3d"><Suspense fallback={null}><Coin3D energy={s.fastUntil ? 1 : s.pointsLeft ? 0.65 : 0.2} size={104} /></Suspense></span></button>
      <div className="bof-boost"><small>ITS BOOST</small><Roll v={s.x || 0} fmt={xOf} className="bof-x m-num" testid="bof-x" /><em>{s.grade ? `Average grade ${Math.round(s.grade)}, and ${(s.size || 0).toFixed(2)}x for its ${money(s.sentUsd)}` : 'Starts with its first graded proof'}</em></div>
      <div className="bof-tiles"><span className="is-cash" data-tip="The rewards, counting live. A real pool profit releases to it second by second, so this is money that already landed" data-testid="bof-cash-tile"><small>BOOST CASH</small><LiveCount pool={d0.pool} readAt={d0.readAt} testid="bst-count" /></span>{[['BOOST POINTS', <Roll key="p" v={s.pointsLeft || 0} fmt={pts} testid="bof-points" />, 'What its proofs and dollars hold. Each dollar of boost cash or each burn takes one off. Burn them to run at a bigger seat'], ['ITS SEAT', <Roll key="c" v={s.nowPct || 0} fmt={pct} testid="bof-cut" />, 'Its share of every pool profit right now'], ['STAKED', <Roll key="s" v={s.sentUsd || 0} fmt={money} testid="bof-staked" />, 'What its proofs have sent into the pools']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small>{v}</span>)}</div>
    </motion.section>
    <div className="bof-mid"><motion.div ref={fastAt} {...rise(1)}><FastCompound s={s} r={r} busy={busy} onBuy={buy} focus={focus} /></motion.div>
      <motion.section className="bof-pools" {...rise(2)} data-testid="bof-pools"><header><Layers3 size={16} aria-hidden="true" /><h4>WHERE THE STAKE WORKS</h4><small className="m-num">{live.length} open</small></header>
        {live.length ? <ul>{live.map(p => <li key={p.id} data-testid={`bof-pool-${p.id}`}><b>{p.pair}</b><small>{p.platform}</small><em className="m-num" data-tip="Profit this pool has really paid">{money(p.profitUsd)}</em>{p.address ? <a href={`https://solscan.io/account/${p.address}`} target="_blank" rel="noopener noreferrer" data-tip="See the pool on Solscan">↗</a> : null}</li>)}</ul> : <p className="bof-note" data-testid="bof-no-pools">No pool is open yet. Until one is, there is no profit, and nothing pays.</p>}</motion.section></div>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <motion.section className="bof-two" {...rise(3)} data-testid="bof-two"><div><b>Boost cash</b><p>The rewards themselves, counting live. When a pool pays, its cut releases to it second by second.</p></div><div><b>Boost points</b><p>The value its proofs and dollars hold, and the most they can still earn. Spend them to speed up and take a bigger seat in the payouts.</p></div></motion.section>
    <motion.section className="bof-why" {...rise(3)} data-testid="bof-why"><div><BadgeCheck size={18} aria-hidden="true" /><h4>WHAT IT GETS</h4><ul><li>A better proof means more boost points: up to 2x what it sent, and a bigger seat.</li><li>More dollars take a bigger seat too. Past $1,000 that grows slowly, so nobody crowds out the rest.</li><li>A cut of every pool on every platform the Collective opens.</li><li>The sources that win, weighed from every agent's real results.</li></ul></div><div><CircleAlert size={18} aria-hidden="true" /><h4>WHAT IT RISKS</h4><ul><li>The stake stays in the pools. Pools can lose money, and a bad stretch can pay nothing.</li><li>It earns only from real profit, and never from what anyone sends.</li><li data-testid="bst-withdraw-off">Taking rewards out is off for now.</li></ul></div></motion.section>
    <motion.div {...rise(4)}><KeepDeal rules={r} testid="bof-deal" /></motion.div>
    {sends.length ? <motion.section className="bof-sends" {...rise(5)} data-testid="bof-sends"><header><h4>ITS PROOFS</h4></header><ol>{sends.map(x => <li key={x.id} className={x.held ? 'is-held' : ''} data-testid={`bof-send-${x.id}`}><Ring part={(x.grade || 0) / 100} label={`Grade ${Math.round(x.grade || 0)}`} /><span><b>{x.name || 'Proof'}{x.sym ? ` · $${x.sym}` : ''}</b><small>{SEND_WORD(x, xOf(x.x))}</small></span><em className="m-num" data-tip="What it sent, and the points that gave">{money(x.usd)} → {x.held ? '0' : money((x.usd || 0) * (x.x || 1))}</em>{x.sig ? <a href={`https://solscan.io/tx/${x.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Its transaction on Solscan">Tx ↗</a> : null}</li>)}</ol></motion.section> : null}
  </div></Fx>;
}
