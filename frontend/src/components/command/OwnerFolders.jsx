import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Chip, Slider, Switch } from '@heroui/react';
import { motion } from 'motion/react';
import { CircleAlert, Gift, LifeBuoy, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { money } from './SplitFlow';
import { ColonyPot } from './HiveBoard';
import { Pools, Dials } from './CollectiveOwner';
import { Fx, Roll } from './CollectiveSetup';
import '../../styles/collectiveHq.css';
import '../../styles/ownerFolders.css';

// 👑 THE OWNER'S FOLDERS (owner 2026-11-06), on the owner-only AGENTS desktop: open pools, pay sooner, reward the best, what to do when pools pay nothing, the spots his money works in, and the safety dials. All read and write the same ledger as Collective HQ. The server re-checks he is the owner on every call.
const rise = i => ({ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.05, duration: 0.24 } });
const nonce = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
const LEDGER_NOTE = 'This pays on the ledger. Withdrawals are off, so no money leaves the wallet yet.';
const Head = ({ icon: I, title, line }) => <header className="ofd-h"><I size={20} aria-hidden="true" /><span><h3>{title}</h3><small>{line}</small></span></header>;
const Seg = ({ value, set, opts, label, id }) => <span className="m-seg" role="group" aria-label={label}>{opts.map(([k, l]) => <button key={k} type="button" className={value === k ? 'active' : ''} aria-pressed={value === k} onClick={() => set(k)} data-testid={`${id}-${k}`}>{l}</button>)}</span>;
const Amount = ({ value, set, top, label, id }) => <div className="ofd-amt"><Slider aria-label={label} className="ofd-slider" minValue={0} maxValue={Math.max(1, top)} step={Math.max(0.01, top / 200)} value={Math.min(value, Math.max(1, top))} onChange={v => set(Number(v))} data-testid={`${id}-slider`}><Slider.Track><Slider.Fill /><Slider.Thumb /></Slider.Track></Slider><label><span>$</span><input className="m-input m-num" type="number" min="0" step="any" value={value} onChange={e => set(Math.max(0, Number(e.target.value) || 0))} aria-label={label} data-testid={`${id}-usd`} /></label></div>;

// 💸 Pay sooner, and reward the best.
export function PayFolder({ d, save, busy }) {
  const s = d.stake || {}; const agents = d.stakeAgents || []; const [source, setSource] = useState('compound'); const [usd, setUsd] = useState(0); const [token, setToken] = useState('USDC'); const [cat, setCat] = useState(''); const [gift, setGift] = useState(0); const [why, setWhy] = useState(''); const room = source === 'compound' ? s.compoundUsd : s.keepUsd; const waiting = agents.reduce((n, a) => n + (a.pointsLeft || 0), 0);
  return <Fx><div className="ofd" data-testid="ofd-pay"><Head icon={Gift} title="Pay and reward" line={LEDGER_NOTE} />
    <div className="hq-kpis">{[['WHAT COMPOUNDED', s.compoundUsd, 'Profit nobody took'], ['THE COLLECTIVE EARNED', s.keepUsd, 'Fees and its piece of each profit'], ['AGENTS CAN STILL EARN', waiting, 'Every agent\'s points left'], ['PAID SO FAR', s.paidUsd, 'Every cut paid']].map(([k, v, t], i) => <motion.article key={k} {...rise(i)} style={{ '--c': ['#ff8bd8', '#c58bff', '#ffc24d', '#3ee58a'][i] }} data-tip={t}><small>{k}</small><Roll v={v || 0} fmt={money} /></motion.article>)}</div>
    {d.payPaused ? <p className="ofd-warn" role="status" data-testid="ofd-paused"><CircleAlert size={15} aria-hidden="true" /> Payouts are stopped in Safety. A profit compounds until you turn them back on.</p> : null}
    <section className="hq-card" data-testid="ofd-early"><h4>PAY AGENTS SOONER<small>Shared by each one's cut, up to its points. Never from a stake</small></h4>
      <div className="ofd-row"><Seg value={source} set={setSource} opts={[['compound', 'From what compounded'], ['keep', 'From what we earned']]} label="Pay from" id="ofd-source" /><Seg value={token} set={setToken} opts={[['USDC', 'USDC'], ['SOL', 'SOL']]} label="Token" id="ofd-token" /></div>
      <Amount value={usd} set={setUsd} top={room || 0} label="How much to pay" id="ofd-early" />
      <button type="button" className="m-btn m-go" disabled={busy || !usd || usd > (room || 0) || !waiting} onClick={() => { save(null, { payEarly: { source, token, usd, nonce: nonce() } }); setUsd(0); }} data-tip={waiting ? 'Takes this from what you picked and adds it to agents\' earnings' : 'No agent has points to pay'} data-testid="ofd-early-go">Pay {money(usd)}</button></section>
    <section className="hq-card" data-testid="ofd-bonus"><h4>A BONUS FOR ONE AGENT<small>From what the Collective earned. It takes none of its points</small></h4>
      {agents.length ? <><select className="m-input" value={cat} onChange={e => setCat(e.target.value)} aria-label="Agent" data-testid="ofd-bonus-agent"><option value="">Pick an agent</option>{agents.map(a => <option key={a.id} value={a.id}>{a.name} · {a.x.toFixed(2)}x</option>)}</select>
        <Amount value={gift} set={setGift} top={s.keepUsd || 0} label="Bonus" id="ofd-bonus" /><input className="m-input" value={why} onChange={e => setWhy(e.target.value)} maxLength={120} placeholder="What for" aria-label="What the bonus is for" data-testid="ofd-bonus-why" />
        <button type="button" className="m-btn m-go" disabled={busy || !cat || !gift || gift > (s.keepUsd || 0)} onClick={() => { save(null, { bonus: { cat, token, usd: gift, why, nonce: nonce() } }); setGift(0); setWhy(''); }} data-testid="ofd-bonus-go">Give {money(gift)}</button></> : <p className="fch-nil">No agent has staked yet.</p>}</section>
    {d.payLog?.length ? <ol className="ofd-log" data-testid="ofd-log">{d.payLog.map((x, i) => <li key={`${x.at}${i}`}><b className="m-num">{money(x.usd)}</b><span>{x.kind === 'bonus' ? `Bonus to ${x.name}${x.why ? `: ${x.why}` : ''}` : `Paid early from ${x.source === 'keep' ? 'what we earned' : 'what compounded'}`}</span><small>{new Date(x.at * 1000).toLocaleDateString()}</small></li>)}</ol> : null}
  </div></Fx>;
}

// 🛟 What pays when pools do not, each with what it can really afford today.
export function FallbackFolder({ d, onPay }) {
  const s = d.stake || {}; const c = d.cfg || {}; const owed = (d.stakeAgents || []).reduce((n, a) => n + (a.pointsLeft || 0), 0);
  const PLANS = [['live', 'Profit only', 'ON NOW', 'Agents earn only when a pool pays. Safest for the Collective, and quiet when pools are flat.', s.profitUsd, 'Paid in by pools so far'], ['compound', 'Top up from what compounded', 'YOUR CALL', `Pays from profit you already kept. It slows compounding, and it can never touch a stake.`, s.compoundUsd, 'Can pay today'], ['keep', 'Top up from fees', 'YOUR CALL', `Agent wallet fees and top-ups help pay rewards. Your income shrinks by what you pay, and pools stay untouched.`, s.keepUsd, 'Can pay today'], ['bonus', 'Reward the best proofs', 'YOUR CALL', 'Hand-pick the top graded agents. Keeps the best agents sending while pools are flat.', s.keepUsd, 'Can pay today']];
  return <Fx><div className="ofd" data-testid="ofd-fallback"><Head icon={LifeBuoy} title="Fallbacks" line="When pools pay nothing, these are the ways left to reward agents. Each uses only profit or the Collective's own money." />
    <p className="ofd-big" data-tip="Every agent's points left"><small>AGENTS CAN STILL EARN</small><Roll v={owed} fmt={money} /><em>Not a debt. It is the most they could still be paid if there is profit.</em></p>
    <ol className="ofd-plans">{PLANS.map(([k, t, tag, line, v, sub], i) => <motion.li key={k} {...rise(i)} data-testid={`ofd-plan-${k}`}><Chip className={`hq-chip${k === 'live' ? ' is-ok' : ''}`}>{tag}</Chip><b>{t}</b><p>{line}</p><span className="m-num">{money(v)}<small>{sub}</small></span>{k === 'live' ? null : <button type="button" className="m-btn" onClick={onPay} data-tip="Opens Pay and reward" data-testid={`ofd-plan-go-${k}`}>Set it up</button>}</motion.li>)}</ol>
    <section className="hq-card"><h4>EACH $100 OF PROFIT TODAY</h4><p className="hq-note is-plain">Agents {(d.stakeAgents || []).reduce((n, a) => n + (a.nowPct || 0), 0).toFixed(2)}% · the Collective {c.collectivePoolPct}% · the rest compounds.</p></section>
  </div></Fx>;
}

const PLATFORM_OF = { raydium: 'raydium', meteora: 'meteora' };
const yearly = rate => (Number(rate) || 0) * 365 * 100;
// 📈 Live pools with their real numbers, and the plan for where the Collective's money works. It shows data and his limits. It does not pick for him, and past fees are no promise.
export function SpotsFolder({ d, save, busy }) {
  const [rows, setRows] = useState(null); const [err, setErr] = useState(''); const [sort, setSort] = useState('deep'); const pools = d.pools || []; const c = d.cfg || {}; const used = pools.reduce((n, p) => n + (Number(p.targetPct) || 0), 0);
  const read = useCallback(() => { setErr(''); fetch(apiUrl('/api/reputation/familia-pools/ranges?top=1')).then(r => (r.ok ? r.json() : Promise.reject(new Error('Pools could not be read')))).then(j => setRows(j.pools || [])).catch(e => setErr(e.message)); }, []);
  useEffect(() => { read(); }, [read]);
  const shown = useMemo(() => [...(rows || [])].sort((a, b) => (sort === 'deep' ? b.tvl - a.tvl : b.rate - a.rate)).slice(0, 14), [rows, sort]); const has = a => pools.some(p => p.address === a);
  return <Fx><div className="ofd" data-testid="ofd-spots"><Head icon={Sparkles} title="Spots" line="Real pools, read live, and your plan for 2 or 3 of them. The picks are yours: this is data, not advice, and past fees promise nothing." />
    <section className="hq-card" data-testid="ofd-plan"><h4>YOUR PLAN<small>{used.toFixed(0)}% placed · {c.reservePct}% reserve · {Math.max(0, 100 - used - c.reservePct).toFixed(0)}% free</small></h4>
      <div className="ofd-stack" aria-hidden="true">{pools.filter(p => p.targetPct).map((p, i) => <u key={p.id} style={{ width: `${p.targetPct}%`, '--i': i }} data-tip={`${p.pair}: ${p.targetPct}%`} />)}<u className="is-res" style={{ width: `${c.reservePct}%` }} data-tip={`Reserve: ${c.reservePct}%`} /></div>
      {pools.length ? <ul className="ofd-targets">{pools.map(p => <li key={p.id} data-testid={`ofd-target-${p.id}`}><b>{p.pair}</b><small>{p.platform}</small><input className="m-input m-num" type="number" min="0" max={c.spotMaxPct} defaultValue={p.targetPct || 0} onBlur={e => { const v = Number(e.target.value) || 0; if (v !== (p.targetPct || 0)) save(null, { poolSet: { id: p.id, targetPct: v } }); }} aria-label={`Part of the plan for ${p.pair}`} data-testid={`ofd-target-input-${p.id}`} /><span>%</span></li>)}</ul> : <p className="fch-nil">Add a pool from the list below, or open one in Pools.</p>}</section>
    <section className="hq-card" data-testid="ofd-live"><h4>LIVE POOLS<small>Raydium and Meteora, last 24 hours</small><button type="button" className="m-btn ofd-re" onClick={read} aria-label="Read again" data-tip="Read them again"><RefreshCw size={13} aria-hidden="true" /></button></h4>
      <Seg value={sort} set={setSort} opts={[['deep', 'Deepest'], ['rate', 'Most fees per $']]} label="Sort" id="ofd-sort" />
      {err ? <p className="lct-err" role="alert">⚠ {err}</p> : !rows ? <p className="fch-nil">reading pools…</p> : <ul className="ofd-spots">{shown.map(r => <li key={r.pool} data-testid={`ofd-spot-${r.pool}`}><b>{r.name}</b><small>{r.venue} · {r.feePct}% fee</small><span data-tip="Money in the pool"><small>DEPTH</small><em className="m-num">{money(r.tvl)}</em></span><span data-tip="Traded in the last 24 hours"><small>24H</small><em className="m-num">{money(r.vol24)}</em></span><span data-tip="Its last 24 hours of fees, as if every day were like it. Whole pool average, and it ignores price moves. A ranged position can earn more or lose money"><small>FEE RATE, YEARLY</small><em className="m-num">{yearly(r.rate).toFixed(0)}%</em></span><button type="button" className="m-btn" disabled={busy || has(r.pool)} onClick={() => save(null, { poolAdd: { platform: PLATFORM_OF[r.venue] || 'other', pair: r.name, address: r.pool } })} data-tip="Adds it to your plan and makes its folder. It moves no money" data-testid={`ofd-spot-add-${r.pool}`}>{has(r.pool) ? 'Added' : 'Add'}</button></li>)}</ul>}
      <p className="hq-note"><CircleAlert size={13} aria-hidden="true" /> High fee rates usually sit on coins that swing hard. Price moves can cost more than fees earn.</p></section>
  </div></Fx>;
}

const SAFETY = [['reservePct', 'Reserve kept out of every spot', '%', 5, 'Your plan can never place this part. It covers losses and pays agents if a pool fails.'], ['spotMaxPct', 'Most in one spot', '%', 5, 'So one pool failing cannot take everything.'], ['capPct', 'Most one wallet can hold', '%', 1, 'Across all its agents, so a whale or one person with many agents cannot crowd out others.'], ['minStakeUsd', 'Smallest stake that earns points', '$', 1, 'Stops farming with many tiny sends. A smaller send still stakes and earns no points. Sends already made keep what they earned.']];
const MISSING = [['AutoRange on the Collective wallet', 'Pools do not re-center by themselves yet. You range them by hand.'], ['Profit read from pools', 'A profit counts when you paste its transaction. Nothing reads pool earnings by itself yet.'], ['Withdrawals', 'Off until a lawyer has checked the deal. Agents\' earnings stay on the ledger.'], ['A lawyer\'s answer', 'Money sent in, with rewards from pool profit, may count as an investment product.']];
// 🛡 The stop button, the limits and what stands between here and real payouts.
export function SafetyFolder({ d, save, busy, c, setC }) {
  const chain = d.chain; const short = chain?.short?.length; const stops = (d.pools || []).filter(p => (d.stops || []).includes(p.id));
  return <Fx><div className="ofd" data-testid="ofd-safety"><Head icon={ShieldCheck} title="Safety" line="What keeps every agent safe, from the first user to the 100,000th." />
    <div className="hq-chips"><Chip className={`hq-chip${short ? ' is-bad' : chain ? ' is-ok' : ''}`} data-tip="The real wallet against what it must hold, every 5 minutes">{!chain ? 'WALLET NOT READ YET' : short ? `SHORT IN ${chain.short.join(' + ')}` : 'FULLY COVERED'}</Chip><Chip className={`hq-chip${d.audit?.ok ? ' is-ok' : d.audit ? ' is-bad' : ''}`} data-tip="The whole ledger chain is walked every 5 minutes">{!d.audit ? 'CHAIN NOT WALKED YET' : d.audit.ok ? 'CHAIN UNBROKEN' : 'CHAIN BROKEN'}</Chip><Chip className="hq-chip">{d.held?.length || 0} PROOFS HELD</Chip></div>
    <section className="hq-card ofd-stop" data-testid="ofd-stop"><span><b>Stop all payouts</b><small>Profit keeps compounding and the Collective keeps its piece. No cut is paid until you turn this off.</small></span><Switch isSelected={!!d.payPaused} isDisabled={busy} onChange={v => save(null, { payPaused: v })} aria-label="Stop all payouts" data-testid="ofd-stop-switch"><Switch.Control><Switch.Thumb /></Switch.Control></Switch></section>
    {stops.length ? <p className="ofd-warn" role="alert" data-testid="ofd-stops"><CircleAlert size={15} aria-hidden="true" /> Past your stop: {stops.map(p => p.pair).join(', ')}. Nothing moves by itself. Open its folder.</p> : null}
    <section className="hq-card" data-testid="ofd-limits"><h4>THE LIMITS</h4><Dials d={d} save={save} busy={busy} c={c} setC={setC} rows={SAFETY} /></section>
    <section className="hq-card" data-testid="ofd-missing"><h4>NOT BUILT OR NOT DONE YET</h4><ul className="ofd-missing">{MISSING.map(([h, t]) => <li key={h}><b>{h}</b><small>{t}</small></li>)}</ul></section>
  </div></Fx>;
}

// 🏊 One pool's own folder. It appears on the desktop when the pool is listed or opened.
export function PoolDesk({ p, d, save, busy }) {
  const [sig, setSig] = useState(''); const left = (Number(p.inUsd) || 0) - (Number(p.lossUsd) || 0); const num = (k, l, tip, u) => <label className="ofd-field" data-tip={tip}><span>{l}</span><input className="m-input m-num" type="number" min="0" step="any" defaultValue={p[k] || 0} onBlur={e => { const v = Number(e.target.value) || 0; if (v !== (p[k] || 0)) save(null, { poolSet: { id: p.id, [k]: v } }); }} aria-label={l} data-testid={`ofd-pool-${k}`} /><i>{u}</i></label>;
  return <Fx><div className="ofd" data-testid={`ofd-pool-${p.id}`}><Head icon={Sparkles} title={p.pair} line={`${p.platform}${p.address ? ` · ${p.address}` : ''}`} />
    <div className="hq-kpis">{[['PROFIT PAID', p.profitUsd || 0, '#3ee58a', 'Profit this pool really paid'], ['MONEY IN', Number(p.inUsd) || 0, '#57c7ff', 'What you say you put in'], ['LOSS', Number(p.lossUsd) || 0, '#ff8fa3', 'What you say it has lost'], ['STILL WORKING', left, '#ffc24d', 'Money in, less loss']].map(([k, v, col, t], i) => <motion.article key={k} {...rise(i)} style={{ '--c': col }} data-tip={t}><small>{k}</small><Roll v={v} fmt={money} /></motion.article>)}</div>
    <section className="hq-card"><h4>ITS NUMBERS<small>Yours to keep current. Nothing reads them from the pool yet</small></h4><div className="ofd-fields">{num('inUsd', 'Money in', 'What the Collective put in this pool', '$')}{num('lossUsd', 'Loss so far', 'Include what price moves have cost', '$')}{num('targetPct', 'Part of the plan', 'Inside your Safety limits', '%')}{num('stopPct', 'Warn me at a loss of', 'A warning in Safety. Nothing sells by itself', '%')}</div>
      <div className="ofd-row"><button type="button" className={`m-btn${p.on ? ' is-on' : ''}`} disabled={busy} aria-pressed={!!p.on} onClick={() => save(null, { poolSet: { id: p.id, on: !p.on } })} data-tip={p.on ? 'Members see it. Tap to hide it' : 'Hidden from members. Tap to show it'} data-testid="ofd-pool-on">{p.on ? 'Open to members' : 'Closed'}</button>{p.address ? <a className="m-btn" href={`https://solscan.io/account/${p.address}`} target="_blank" rel="noopener noreferrer" data-tip="See it on Solscan">Solscan ↗</a> : null}</div></section>
    <section className="hq-card"><h4>A PROFIT FROM THIS POOL</h4><form className="hq-profit" onSubmit={e => { e.preventDefault(); if (sig.trim()) { save(null, { profitSig: sig.trim(), pool: p.id }); setSig(''); } }}><input className="m-input" value={sig} onChange={e => setSig(e.target.value)} placeholder="Paste the transaction that brought it to the Collective wallet" aria-label="Profit transaction" data-testid="ofd-pool-sig" /><button type="submit" className="m-btn m-go" disabled={busy || !sig.trim()} data-tip="It counts once, and only if the chain shows it landing. Then cuts are paid" data-testid="ofd-pool-sig-go">Pay cuts</button></form></section>
  </div></Fx>;
}

// One ledger read for every owner folder. Adding a pool makes its folder on the next read.
export function useOwnerFolders(call, on = true) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [c, setC] = useState(null);
  useEffect(() => { if (!on) return undefined; let live = true; const go = () => { if (!document.hidden) call('/admin/collective').then(x => live && setD(x)).catch(e => live && setErr(e.message)); }; go(); const t = setInterval(go, 30000); return () => { live = false; clearInterval(t); }; }, [call, on]);
  useEffect(() => { if (d?.cfg) setC(d.cfg); }, [d?.cfg]);
  const save = useCallback(async (cfg, extra) => { setBusy(true); setErr(''); try { setD(await call('/admin/collective', { method: 'POST', body: JSON.stringify(cfg ? { cfg } : extra) })); } catch (e) { setErr(e.message); } finally { setBusy(false); } }, [call]);
  const wrap = body => <>{err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}{d && c ? body : <p className="fch-nil">reading the ledger…</p>}</>;
  const openPay = useCallback(() => window.dispatchEvent(new CustomEvent('feeless:open-win', { detail: 'own-pay' })), []);
  if (!on) return [];
  return [
    { k: 'own-pools', ic: '🏊', label: 'Pools', tip: 'Owner only: open a real pool with the Collective wallet, list pools, and pay cuts from their profit', body: wrap(<div className="ofd"><ColonyPot call={call} />{d ? <Pools d={d} save={save} busy={busy} /> : null}</div>) },
    { k: 'own-spots', ic: '📈', label: 'Spots', tip: 'Owner only: live pool numbers and your plan for where the money works', body: wrap(d ? <SpotsFolder d={d} save={save} busy={busy} /> : null) },
    { k: 'own-pay', ic: '💸', label: 'Pay + reward', tip: 'Owner only: pay agents sooner, or give a bonus', body: wrap(d ? <PayFolder d={d} save={save} busy={busy} /> : null) },
    { k: 'own-fallback', ic: '🛟', label: 'Fallbacks', tip: 'Owner only: what can pay agents when pools do not', body: wrap(d ? <FallbackFolder d={d} onPay={openPay} /> : null) },
    { k: 'own-safety', ic: '🛡', label: 'Safety', tip: 'Owner only: stop payouts, the limits, and what is not built yet', body: wrap(d && c ? <SafetyFolder d={d} save={save} busy={busy} c={c} setC={setC} /> : null) },
    ...(d?.pools || []).map(p => ({ k: `own-pool-${p.id}`, ic: '🌊', label: p.pair, tip: `${p.pair} on ${p.platform}: its numbers, its stop and its profit`, body: <PoolDesk p={p} d={d} save={save} busy={busy} /> })),
  ];
}
