import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { LendBox, usePools } from './PoolHub';
import '../styles/fiveRun.css';

// 💵 THE $5 RUN (owner, 2026-10-23: "a minimum of $5 to see REAL compound, real errands, no bs click and drop"): $5 into Jupiter Lend Earn —
// it compounds ON-CHAIN every block. With a deposit, the big number is YOUR money: what Jupiter says the position is worth now (re-read every
// 30 s) ticking between reads at the live rate, plus Jupiter's own earnings count. Without one, the same ticker runs $5 from the moment you
// look. The deposit / withdraw is the verified in-place Jupiter Lend box (backend/lend_earn.py) — your wallet signs, FEELESS never holds it.
const YEAR_S = 31557600;
export const RUN_KEY = 'feeless.run';
export const hasRun = () => { try { return localStorage.getItem(RUN_KEY) === '1'; } catch { return false; } };
// pure: `v` dollars at `apy` % compounding for `sec` seconds (Jupiter accrues every block — continuous is the honest model)
export const grow = (v, apy, sec) => (Number(v) || 0) * Math.exp(Math.log1p((Number(apy) || 0) / 100) * (sec / YEAR_S));
// pure: the ticker's digits — whole cents bright, the compounding tail (cents → 1/10,000,000 of a dollar) dim and rolling
export const split = v => { const s = (Number(v) || 0).toFixed(8); const k = s.indexOf('.') + 3; return [s.slice(0, k), s.slice(k)]; };
const MILES = [['TONIGHT', 8 * 3600], ['A WEEK', 7 * 86400], ['A MONTH', 30 * 86400], ['A YEAR', YEAR_S]];
const tiny = v => { const a = Math.abs(v); return `+$${a >= 1 ? a.toFixed(2) : a >= 0.01 ? a.toFixed(3) : a.toFixed(5)}`; };

function Ticker({ base, apy, from }) {   // the compounding number, every 250 ms (2 s in lite) while the tab is visible
  const lite = typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, lite ? 2000 : 250); return () => clearInterval(t); }, [lite]);
  const [hi, lo] = split(grow(base, apy, Math.max(0, now - from) / 1000));
  return <b className="fr-tick m-num" data-testid="fr-tick">${hi}<small>{lo}</small></b>;
}

function Curve({ amt, apy }) {   // one year of compounding, drawn: the area grows from the dot (now) to the year's end, milestones on it
  const W = 300, H = 90; const end = grow(amt, apy, YEAR_S); const y = v => H - 8 - ((v - amt) / Math.max(1e-9, end - amt)) * (H - 22);
  const pts = Array.from({ length: 25 }, (_, i) => [(i / 24) * W, y(grow(amt, apy, (i / 24) * YEAR_S))]);
  const d = pts.map(([x, yy], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${yy.toFixed(1)}`).join(' ');
  return <svg className="fr-curve" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="frg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#45e486" stopOpacity=".45" /><stop offset="1" stopColor="#45e486" stopOpacity="0" /></linearGradient></defs>
    <path d={`${d} L${W} ${H} L0 ${H} Z`} fill="url(#frg)" /><path className="fr-line" d={d} pathLength="1" />
    {MILES.map(([, s], i) => { const x = Math.max(4, (s / YEAR_S) * W); return <circle key={i} cx={x} cy={y(grow(amt, apy, s))} r="2.6" className="fr-mile" />; })}
    <circle cx="4" cy={y(amt)} r="4.5" className="fr-now" /></svg>;
}

export function FiveRun({ devAddress = '' }) {
  const { wallet } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const hub = usePools(); const [d, setD] = useState(null); const [pick, setPick] = useState('USDC'); const [box, setBox] = useState(null); const [t0] = useState(() => Date.now());
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/familia-pools/run?address=${encodeURIComponent(addr || '')}`)).then(r => (r.ok ? r.json() : null))
    .then(x => { if (!x) return; setD({ ...x, readAt: Date.now() }); if ((x.positions || []).length) { try { localStorage.setItem(RUN_KEY, '1'); } catch { /* private window */ } } }).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => clearInterval(t); }, [load]);
  const assets = d?.assets || []; const a = assets.find(x => x.sym === pick) || assets[0]; const mine = (d?.positions || []).find(p => p.sym === a?.sym);
  const row = useMemo(() => (hub?.pools || []).find(r => r.project === 'jupiter-lend' && a && (r.mints || []).includes(a.mint)), [hub, a]);
  const five = a ? (a.sym === 'USDC' ? '5' : (5 / a.price).toFixed(4)) : '5';
  if (!a) return <section className="fr" data-testid="five-run"><p className="fr-dim">{d ? 'Jupiter Lend did not answer — the run waits for live rates.' : 'Reading Jupiter Lend…'}</p></section>;
  const base = mine ? mine.usd : 5;
  return <section className={`fr ${mine ? 'is-live' : ''}`} data-testid="five-run">
    <header className="fr-head"><span><em>💵 THE $5 RUN · REAL COMPOUNDING</em><b>{mine ? 'Your money, compounding right now' : 'Start with $5 — watch it compound for real'}</b></span>
      <span className="m-seg fr-seg" role="radiogroup" aria-label="Asset">{assets.map(x => <button key={x.sym} type="button" role="radio" aria-checked={x.sym === a.sym} className={x.sym === a.sym ? 'active' : ''}
        onClick={() => { setPick(x.sym); setBox(null); }} data-tip={`${x.sym} on Jupiter Lend Earn · ${x.apy}% a year now, paid every block`} data-testid={`fr-a-${x.sym}`}>{x.sym} <small>{x.apy}%</small></button>)}</span></header>
    <div className="fr-body">
      <div className="fr-num"><em>{mine ? `YOUR ${a.sym} ON JUPITER LEND · ON-CHAIN` : 'WHAT $5 DOES WHILE YOU WATCH'}</em>
        <Ticker base={base} apy={a.apy} from={mine ? d.readAt : t0} />
        <small>{mine ? `${tiny(mine.earned)} earned so far (Jupiter's own count) · re-read every 30 s` : `${a.apy}% a year, compounding every block — the tail digits are real cents-of-cents`}</small></div>
      <Curve amt={base} apy={a.apy} />
    </div>
    <ol className="fr-miles">{MILES.map(([w, s], i) => <li key={w} style={{ '--i': i }}><em>{w}</em><b className="m-num">{tiny(grow(base, a.apy, s) - base)}</b></li>)}</ol>
    <div className="fr-go">{mine ? <><button type="button" className="m-btn m-go" onClick={() => setBox('add')} disabled={!row} data-testid="fr-add" data-tip="Add $5 more — Jupiter builds it, FEELESS checks it, your wallet signs">＋ $5 more</button>
      <button type="button" className="m-btn" onClick={() => setBox('out')} disabled={!row} data-testid="fr-out" data-tip="Take it out any time — pick Withdraw in the box">Withdraw</button></>
      : <button type="button" className="m-btn m-go fr-start" onClick={() => setBox('add')} disabled={!row} data-testid="fr-start"
        data-tip={`$5 of ${a.sym} into Jupiter Lend Earn — Jupiter builds the deposit, FEELESS checks every program in it, your wallet signs`}>{addr ? `💵 START MY $5 RUN · ${a.sym}` : '🔌 Connect wallet · start a $5 run'}</button>}
      <small className="fr-risk">⚠ Lending risk: Jupiter Lend's contracts + {a.sym === 'SOL' ? "SOL's price" : 'the stablecoin peg'}. Min $5. Withdraw any time.</small></div>
    {box && row ? <LendBox key={box} r={row} amount0={box === 'add' ? five : ''} onClose={() => { setBox(null); load(); }} /> : null}
  </section>;
}
