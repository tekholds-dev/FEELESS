import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { useGlide } from '../lib/useGlide';
import { EarnTicker } from './EarnTicker';
import { JOB_OF, openDesk } from './MoneyDesk';
import { FiveRun } from './FiveRun';
import { AutoRangePicker } from './AutoRangeDesk';
import { usePools } from './PoolHub';
import '../styles/nightVault.css';

// 💤 THE NIGHT VAULT — money while you sleep (FEELESS AVENUE building; backend sleep_money.py, GET /familia-pools/sleep). Five strategies from
// LIVE rows only — 🥩 LST stack · 💵 stable lend · 🎰 JLP · 🌀 auto-compound vaults · 🔁 loops (Kamino's real SOL borrow rate + max LTV → net
// APY, LTV and the cushion before liquidation). A calculator up top (amount × how long you sleep) turns every APY into dollars; each strategy
// shows its risk as four drawn meters and rides on the Pool Hall's own rows (⚡ stake / buy through our engine, 🏦 verified Jupiter Lend
// deposit here, or the protocol's page — your wallet signs, FEELESS never holds funds).
const AMTS = [5, 25, 100, 1000];   // owner, 2026-10-23: start at $5 — small money shown honestly, to the 1/100,000 of a dollar
const NAPS = [['night', '8H NIGHT', 8 / 24], ['week', '1 WEEK', 7], ['month', '1 MONTH', 30], ['year', '1 YEAR', 365]];
const RISKS = [['contract', 'CONTRACT'], ['depeg', 'DEPEG'], ['il', 'IMPERM. LOSS'], ['liq', 'LIQUIDATION']];
export const usd0 = v => { const a = Math.abs(v); return `${v < 0 ? '-' : ''}$${a >= 1e6 ? `${(a / 1e6).toFixed(2)}M` : a >= 1e4 ? `${(a / 1e3).toFixed(1)}K` : a >= 100 ? a.toFixed(0) : a >= 1 ? a.toFixed(2) : a >= 0.01 ? a.toFixed(3) : a.toFixed(5)}`; };
// pure: what `amt` dollars earn at `apy` % over `days` (simple interest — what the protocols quote)
export const sleepEarn = (amt, apy, days) => (Number(amt) || 0) * ((Number(apy) || 0) / 100) * ((Number(days) || 0) / 365);

function Earned({ v }) { const g = useGlide(Math.round(v * 1e6) / 1e6); return <b className="nv-earned">+{usd0(g)}</b>; }   // to the millionth: $5 overnight is real money, not +$0.000

function RiskMeters({ r }) {
  return <div className="nv-risk" data-tip={r.note}>{RISKS.map(([k, l]) => <p key={k} className={`r-${r[k] || 0}`}><em>{l}</em><span>{[0, 1, 2].map(i => <i key={i} className={i < (r[k] || 0) ? 'is-on' : ''} />)}</span></p>)}</div>;
}

function LoopCard({ s, amt, days }) {
  const [pick, setPick] = useState(0); const lp = s.loops[pick] || s.loops[0]; const [x, setX] = useState(null);
  const play = lp.plays.find(p => p.x === x) || lp.plays[lp.plays.length - 1];
  return <div className="nv-loop" data-testid="nv-loopcard">
    {s.loops.length > 1 ? <div className="m-seg nv-seg" role="radiogroup" aria-label="Which LST">{s.loops.map((l, i) => <button key={l.id} type="button" role="radio" aria-checked={i === pick} className={i === pick ? 'active' : ''} onClick={() => { setPick(i); setX(null); }}>{l.sym}</button>)}</div> : null}
    <div className="m-seg nv-seg" role="radiogroup" aria-label="Leverage">{lp.plays.map(p => <button key={p.x} type="button" role="radio" aria-checked={p.x === play.x} className={p.x === play.x ? 'active' : ''} onClick={() => setX(p.x)} data-testid={`nv-x-${p.x}`}>×{p.x}</button>)}</div>
    <div className="nv-loopnums">
      <span><em>NET APY</em><b className={play.apy >= lp.lstApy ? 'is-up' : 'is-dn'}>{play.apy.toFixed(2)}%</b><small>{lp.lstApy.toFixed(2)}% staked × {play.x} − {lp.borrow.toFixed(2)}% SOL borrow × {(play.x - 1).toFixed(1)}</small></span>
      <span><em>YOUR {NAPS.find(n => n[2] === days)?.[1] || ''}</em><Earned v={sleepEarn(amt, play.apy, days)} /></span>
    </div>
    <div className="nv-ltv" data-tip={`LTV ${(play.ltv * 100).toFixed(0)}% against Kamino's max ${(lp.maxLtv * 100).toFixed(0)}% for ${lp.sym}`}>
      <em>LTV</em><u><s style={{ transform: `scaleX(${Math.min(1, play.ltv / lp.maxLtv)})` }} /><i style={{ left: '100%' }} /></u><b>{(play.ltv * 100).toFixed(0)}% / {(lp.maxLtv * 100).toFixed(0)}%</b></div>
    <p className="nv-cushion" data-testid="nv-cushion">🛟 {lp.sym} can slip <b>{(play.cushion * 100).toFixed(0)}%</b> against SOL before this loop hits the max LTV.</p>
    <a className="m-btn m-go" href={lp.app} target="_blank" rel="noopener noreferrer" data-tip="Kamino Multiply builds the loop in one transaction — your wallet signs there (an in-FEELESS loop needs Kamino's SDK: the owner's call)">🔁 Loop it on Kamino ↗</a>
  </div>;
}

// 💤 an open strategy = its top 3 picks as live APY bars, what your amount earns while you look, and ONE button: the money desk pops out
// big with the best pick in focus (owner, 2026-10-24: "clean summary + one pop-out, live ticking vitals" — no wall of pool rows)
function Picks({ s, rows, amt }) {
  const top = rows.slice(0, 3); const hi = Math.max(1, ...top.map(r => Number(r.apy) || 0)); const best = top[0];
  if (!best) return <p className="nv-note">No live pick for this one right now.</p>;
  return <div className="nv-picks" data-testid={`nv-picks-${s.key}`}>
    <ol>{top.map((r, i) => <li key={r.id} style={{ '--i': i }} data-tip={`${r.sym} · ${r.proto} · TVL $${Math.round((r.tvl || 0) / 1e6)}M`}><b>{r.sym}</b><small>{r.proto}</small>
      <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, (Number(r.apy) || 0) / hi)})` }} /></u><i className="m-num">{(Number(r.apy) || 0).toFixed(2)}%</i></li>)}</ol>
    <EarnTicker usd={amt} apy={best.apy} label={`$${amt} IN ${best.sym}`} testid={`nv-earn-${s.key}`} />
    <button type="button" className="m-btn m-go nv-go" onClick={() => openDesk({ job: JOB_OF[best.kind] || 'lend', focus: best, title: `${s.name} · PUT IT TO WORK` })}
      data-tip="The money desk pops out big — the best pick in focus, your amount, watch it compound; your wallet signs" data-testid={`nv-go-${s.key}`}>⚡ PUT IT TO WORK</button>
  </div>;
}

export function NightVault() {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [amt, setAmt] = useState(5); const [nap, setNap] = useState('month'); const [open, setOpen] = useState('lst');
  useEffect(() => { let on = true; const go = () => sharedJson('/api/reputation/familia-pools/sleep', { maxAge: 240000 }).then(x => { if (on && x) { setD(x); setErr(false); } }).catch(() => on && setErr(true));
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 300000); return () => { on = false; clearInterval(t); }; }, []);
  const days = (NAPS.find(n => n[0] === nap) || NAPS[2])[2];
  const byId = useMemo(() => Object.fromEntries((d?.rows || []).map(r => [r.id, r])), [d]);
  const st = d?.strategies || [];
  const best = st.reduce((m, s) => (s.apy > (m?.apy || -1) ? s : m), null);
  const hub = usePools();   // 🤖 the busiest concentrated pools for AutoRange (one shared 4-min read)
  return <section className="nv" data-testid="night-vault">
    <header className="nv-sky"><span className="nv-moon" aria-hidden /><span className="nv-stars" aria-hidden>{Array.from({ length: 14 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</span>
      <span className="nv-z" aria-hidden><i>z</i><i>z</i><i>Z</i></span><span className="nv-stack" aria-hidden>{[0, 1, 2, 3].map(i => <i key={i} style={{ '--i': i }} />)}</span>
      <span className="nv-title" data-tip="APYs are live and move. Simple interest shown (before compounding). Nothing here is advice — every deposit is signed by your wallet, on the protocol's own contracts."><em>FEELESS AVENUE</em><b>THE NIGHT VAULT</b><small>money while you sleep · live APY · your wallet signs</small></span></header>
    <FiveRun />
    <div className="nv-calc">
      <div className="nv-amt"><em>PUT IN</em><div className="m-seg" role="radiogroup" aria-label="Amount">{AMTS.map(a => <button key={a} type="button" role="radio" aria-checked={amt === a} className={amt === a ? 'active' : ''} onClick={() => setAmt(a)} data-testid={`nv-amt-${a}`}>${a >= 1000 ? `${a / 1000}K` : a}</button>)}</div>
        <input className="m-input" type="number" min="0" step="any" value={amt} onChange={e => setAmt(Math.max(0, Number(e.target.value) || 0))} aria-label="Dollars to put in" data-testid="nv-amt-input" /></div>
      <div className="nv-amt"><em>SLEEP FOR</em><div className="m-seg" role="radiogroup" aria-label="How long">{NAPS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={nap === k} className={nap === k ? 'active' : ''} onClick={() => setNap(k)} data-testid={`nv-nap-${k}`}>{l}</button>)}</div></div>
      {best ? <p className="nv-best" data-tip="The highest live APY on this page — check its risk meters before you chase it">💤 best tonight: <b>{best.name}</b> · {best.top} · <b>{best.apy.toFixed(2)}%</b> → <Earned v={sleepEarn(amt, best.apy, days)} /></p> : null}
    </div>
    {!d ? <p className="nv-wait">{err ? 'The vault is locked — the pool feed did not answer. Try again in a minute.' : 'Opening the vault…'}</p> : null}
    <div className="nv-grid">{st.map((s, i) => <article key={s.key} className={`nv-card k-${s.key} ${open === s.key ? 'is-open' : ''}`} style={{ '--i': i }} data-testid={`nv-${s.key}`}>
      <button type="button" className="nv-head" aria-expanded={open === s.key} onClick={() => setOpen(o => (o === s.key ? null : s.key))} data-tip={s.risk?.note}>
        <span><b>{s.name}</b><small>{s.sub}</small></span>
        <span className="nv-apy"><em>UP TO</em><b>{s.apy.toFixed(2)}%</b><small>{s.top}</small></span>
        <span className="nv-out"><em>{usd0(amt)} · {(NAPS.find(n => n[0] === nap) || [])[1]}</em><Earned v={sleepEarn(amt, s.apy, days)} /></span></button>
      <RiskMeters r={s.risk || {}} />
      {open === s.key ? (s.key === 'loop' ? <LoopCard s={s} amt={amt} days={days} />
        : <Picks s={s} rows={(s.rows || []).map(id => byId[id]).filter(Boolean)} amt={amt} />) : null}
    </article>)}</div>
    <AutoRangePicker pools={hub?.pools} amt={amt} title="🤖 AUTORANGE WHILE YOU SLEEP · THE BUSIEST BANDS" />
    {d && !d.kamino ? <p className="nv-note">Kamino's rates did not answer — loops are hidden until they do (no guessed borrow rates).</p> : null}
  </section>;
}
