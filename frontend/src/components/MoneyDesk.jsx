import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { usd, apyTxt } from '../lib/cityPlan';
import { familiaDocked, familiaSwap } from './FamiliaTrade';
import { LendBox, goTrade, tradeOf, usePools, ilRange, rangeFactor } from './PoolHub';
import { cash } from '../lib/earnStake';
import '../styles/moneyDesk.css';

// 💸 THE MONEY DESK — every money building's pop-out DOES the money in place (owner, 2026-10-23: "no redirects — click to choose the platform /
// provider and do whatever from the pop-out · $5 wouldn't do shit · straight into rapid compound and growth"). Pick a PROVIDER (live APY from
// the Pool Hub) → an AMOUNT that matters → the GROWTH it compounds to (drawn, ticking) → ONE action that runs inside FEELESS: a Jupiter Lend
// deposit (built + checked server-side, your wallet signs) · a SOL → LST / USDC → yield-token swap (the swap opens with both coins set) · the
// pool's coin on the chart + Quick trade. Nothing here opens another site; FEELESS never holds the money.
const SwapWorkspace = lazy(() => import('./command/SwapWorkspace').then(m => ({ default: m.SwapWorkspace })));
export const SOL = 'So11111111111111111111111111111111111111112';
export const USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const JLP = '27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4';
export const AMOUNTS = [100, 500, 1000, 5000];
// 🧼 a narrow side panel never holds the desk (owner: "the right side bar can't hold ish like that"): it asks the page's desk host (Fee City's
// big pop-out over the map) to open it. Returns false when no host is mounted, so the caller can show it inline instead.
let deskHosts = 0;
export const deskHost = d => { deskHosts = Math.max(0, deskHosts + d); };
export function openDesk(detail) { if (!deskHosts) return false; window.dispatchEvent(new CustomEvent('feeless:desk', { detail })); return true; }
const ADDS = [0, 100, 500];   // + a month (DCA): the compounding that actually moves a number
export const JOB_OF = { best: 'best', stake: 'stake', lend: 'lend', vault: 'lend', rwa: 'rwa', perps: 'perps', dex: 'lp', v2: 'lp', v3: 'lp', dlmm: 'lp' };
const JOB_WORD = { best: 'the best live yields you can start right here', stake: 'liquid staking · SOL that earns', lend: 'lending · interest every block', rwa: 'treasuries on-chain · dollar yield', perps: 'the house side of perps', lp: 'liquidity · swap fees' };
const RISK = { best: 'Each yield carries its own risk (staking moves with SOL, lending is smart-contract risk) — pick, read the line, then sign.', stake: 'Moves with SOL\'s price · a staking token can trade slightly under SOL in a panic.', lend: 'Smart-contract risk; a stablecoin can de-peg. You can withdraw any time the market has cash.',
  rwa: 'Issuer + custody risk (a real fund behind the token); some can only be redeemed by verified holders.', perps: 'JLP is the house: it earns fees and loses when traders win.',
  lp: 'Two coins: if the prices split you end up with more of the loser (impermanent loss). Out of range earns nothing.' };

// pure: the in-place ways to put money to work for a job, from the live hub — `how` = lend (Jupiter Lend, wallet signs) · swap (into a yield
// token) · trade (the pool's coin). Best paying first; the tapped pool (`focus`) leads when it can run here.
export function providersOf(job, rows, focus = null) {
  const rs = (rows || []).filter(r => r && r.id);
  const stake = rs.filter(r => r.kind === 'stake' && r.hold && Number(r.apy) > 0 && (r.tvl || 0) >= 5e6).sort((a, b) => b.apy - a.apy).slice(0, 6)
    .map(r => ({ id: r.id, name: r.proto, sym: r.sym, apy: r.apy, tvl: r.tvl, how: 'swap', from: SOL, to: r.hold, fromSym: 'SOL', row: r }));
  const lend = rs.filter(r => r.kind === 'lend' && r.project === 'jupiter-lend' && (r.mints || []).length && Number(r.apy) > 0).sort((a, b) => b.apy - a.apy).slice(0, 6)
    .map(r => ({ id: r.id, name: 'Jupiter Lend', sym: r.sym, apy: r.apy, tvl: r.tvl, how: 'lend', row: r }));
  const rwa = rs.filter(r => r.kind === 'rwa' && r.hold && Number(r.apy) > 0).sort((a, b) => b.apy - a.apy).slice(0, 4)
    .map(r => ({ id: r.id, name: r.proto, sym: r.sym, apy: r.apy, tvl: r.tvl, how: 'swap', from: USDC, to: r.hold, fromSym: 'USDC', row: r }));
  const jlpRow = rs.find(r => /JLP/i.test(r.sym || '') && r.hold);
  const jlp = { id: 'jlp', name: 'Jupiter Perps', sym: 'JLP', apy: jlpRow?.apy ?? null, tvl: jlpRow?.tvl ?? null, how: 'swap', from: USDC, to: jlpRow?.hold || JLP, fromSym: 'USDC', row: jlpRow || null };
  const f = focus && tradeOf(focus) && ['v2', 'v3', 'dlmm'].includes(focus.kind) ? [{ id: focus.id, name: focus.proto, sym: focus.sym, apy: focus.apy ?? null, tvl: focus.tvl, how: 'trade', row: focus }] : [];
  const lead = focus ? [...stake, ...lend, ...rwa].filter(p => p.id === focus.id) : [];
  const best = [...stake.slice(0, 2), ...lend.slice(0, 3), ...rwa.slice(0, 1)].sort((a, b) => b.apy - a.apy);   // ⚡ START COMPOUNDING: the best in-place yields of every kind
  const rest = { best, stake, lend: [...lend, ...rwa.slice(0, 1)], rwa: [...rwa, ...lend.filter(p => /USD/.test(p.sym)).slice(0, 2)], perps: [jlp, ...lend.slice(0, 1)],
    lp: [...f, ...stake.slice(0, 1), ...lend.filter(p => /USD/.test(p.sym)).slice(0, 1)] }[job] || [];
  const seen = new Set(); return [...lead, ...rest].filter(p => (seen.has(p.id) ? false : seen.add(p.id)));
}

// pure: a protocol's deepest pool you can trade through FEELESS (a DEX building's own lead)
export const topPoolOf = (rows, proto) => (rows || []).filter(r => r && String(r.proto || '').toLowerCase().startsWith(String(proto).toLowerCase()) && ['v2', 'v3', 'dlmm'].includes(r.kind) && tradeOf(r))
  .sort((a, b) => ((Number(b.apy) || 0) >= 1) - ((Number(a.apy) || 0) >= 1) || /SOL/.test(b.sym) - /SOL/.test(a.sym) || (b.tvl || 0) - (a.tvl || 0))[0] || null;   // paying, then SOL pairs, then depth
const dollars = v => (Math.abs(v) >= 1000 ? `$${Math.round(v).toLocaleString('en-US')}` : cash(v));

// pure: the money math — daily compounding + an optional monthly top-up; `pts` = 13 monthly points for the curve
export function growth(amt, apy, add = 0, months = 12) {
  const r = Math.max(0, Number(apy) || 0) / 100; const d = r / 365; let v = Number(amt) || 0; let paid = v; const pts = [v];
  for (let m = 1; m <= months; m += 1) { v = v * (1 + d) ** 30.4167 + add; paid += add; pts.push(v); }
  const day = ((Number(amt) || 0) * r) / 365;
  return { day, month: day * 30.4167, end: v, paid, earned: v - paid, pts, perSec: day / 86400, double: r > 0 ? Math.log(2) / Math.log(1 + d) / 365 : null };
}

function Ticker({ perSec }) {   // 💵 the money it earns WHILE you look at it — the number that keeps you here
  const [t0] = useState(() => Date.now()); const [n, setN] = useState(0);
  useEffect(() => { if (!perSec) return undefined; const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches; if (still) return undefined;
    const t = setInterval(() => { if (!document.hidden) setN(((Date.now() - t0) / 1000) * perSec); }, 250); return () => clearInterval(t); }, [perSec, t0]);
  return <span className="md-tick" data-tip="What this amount would have earned since you opened the desk — at today's APY" data-testid="md-tick"><em>EARNED WHILE YOU LOOK</em><b className="m-num">+{cash(n)}</b></span>;
}

function Curve({ g, add }) {
  const W = 300; const H = 92; const top = Math.max(...g.pts, 1); const lo = g.pts[0] * 0.98;
  const xy = (v, i) => [8 + (i / (g.pts.length - 1)) * (W - 16), H - 8 - ((v - lo) / Math.max(1e-9, top - lo)) * (H - 22)];
  const line = g.pts.map((v, i) => `${i ? 'L' : 'M'}${xy(v, i).map(n => n.toFixed(1)).join(',')}`).join(' ');
  const paid = g.pts.map((_, i) => g.pts[0] + add * i); const pl = paid.map((v, i) => `${i ? 'L' : 'M'}${xy(v, i).map(n => n.toFixed(1)).join(',')}`).join(' ');
  return <svg className="md-curve" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Grows to ${cash(g.end)} in a year`}>
    <path d={`${line} L${W - 8},${H - 6} L8,${H - 6} Z`} className="md-area" /><path d={pl} className="md-paid" /><path d={line} className="md-line" />
    <circle cx={xy(g.end, 12)[0]} cy={xy(g.end, 12)[1]} r="3.4" className="md-dot" /></svg>;
}

// 🎯 THE RANGE, DRAWN (owner: "no way to understand the lame range ish"): a price line, your band glowing where it EARNS, dark where it stops,
// today's price as a dot; slide the width → three plain numbers (fee boost · the move that stops it · what a run costs vs holding)
export function RangePicture({ start = 25 }) {
  const [w, setW] = useState(start); const k = 1 + w / 100; const boost = rangeFactor(k); const lag = ilRange(1.2, k) * 100;
  const X = v => 20 + ((Math.log(v) + Math.log(2.2)) / (2 * Math.log(2.2))) * 260;   // a log price axis: ÷2.2 … ×2.2
  return <div className="md-range" data-testid="range-picture">
    <header><b>🎯 YOUR RANGE, DRAWN</b><small>v3 / DLMM pools pay only while the price sits inside your band</small></header>
    <svg viewBox="0 0 300 70" role="img" aria-label={`A band ±${w}% around today's price`}>
      <line x1="20" x2="280" y1="40" y2="40" className="md-axis" />
      <rect x={X(1 / k)} y="22" width={X(k) - X(1 / k)} height="36" rx="6" className="md-band" />
      <text x={(X(1 / k) + X(k)) / 2} y="16" textAnchor="middle" className="md-bandw">EARNS ×{boost.toFixed(1)}</text>
      <text x={(20 + X(1 / k)) / 2} y="64" textAnchor="middle" className="md-off">earns 0</text><text x={(X(k) + 280) / 2} y="64" textAnchor="middle" className="md-off">earns 0</text>
      <g className="md-price"><circle cx="150" cy="40" r="5" /><text x="150" y="16" textAnchor="middle" className="md-now">{w > 60 ? '' : 'today'}</text></g>
    </svg>
    <label className="md-slide"><span>Band ±</span><input type="range" min="2" max="100" value={w} onChange={e => setW(Number(e.target.value))} aria-label="Range width" data-testid="range-w" /><b>{w}%</b></label>
    <div className="md-facts">
      <span style={{ '--i': 0 }}><em>FEES PER $</em><b className="m-num" key={`b${w}`}>×{boost.toFixed(1)}</b><small>vs a plain v2 pool</small></span>
      <span style={{ '--i': 1 }}><em>STOPS EARNING</em><b className="m-num">−{(100 - 100 / k).toFixed(0)}% / +{w}%</b><small>price move either way</small></span>
      <span style={{ '--i': 2 }} className={lag < -2 ? 'is-bad' : ''}><em>IF IT RUNS +20%</em><b className="m-num">{lag.toFixed(1)}%</b><small>vs just holding the coins</small></span>
    </div>
  </div>;
}

export function MoneyDesk({ job: job0 = 'lend', rows = null, focus: focus0 = null, title = null, compact = false, prefer = null, note = null, proto = null }) {
  const hub = usePools(); const all = rows || hub?.pools;   // one shared 4-min read of the Pool Hub
  const job = JOB_OF[job0] || job0;
  const focus = useMemo(() => focus0 || (proto ? topPoolOf(all, proto) : null), [focus0, proto, all]);   // a DEX building leads with its own busiest tradable pool
  const provs = useMemo(() => providersOf(job, all, focus), [job, all, focus]);
  const [pid, setPid] = useState(null); const [amt, setAmt] = useState(1000); const [add, setAdd] = useState(0); const [go, setGo] = useState(null);
  const p = provs.find(x => x.id === pid) || (prefer && provs.find(x => String(x.sym).toUpperCase() === String(prefer).toUpperCase())) || provs[0] || null; const g = useMemo(() => growth(amt, p?.apy, add), [amt, p, add]);
  const best = provs.reduce((m, x) => (Number(x.apy) > Number(m?.apy || -1) ? x : m), null);
  const run = () => {
    if (!p) return;
    if (p.how === 'lend') { setGo('lend'); return; }
    if (p.how === 'trade') { goTrade(p.row); return; }
    const swap = { from: p.from, to: p.to, amount: p.from === USDC ? String(amt) : undefined };
    if (familiaDocked()) { familiaSwap(swap); return; }
    try { sessionStorage.setItem('feeless.swap.pair', JSON.stringify({ input: swap.from, output: swap.to, amount: swap.amount })); } catch { /* storage blocked */ }
    setGo(`swap-${Date.now()}`);
  };
  const verb = !p ? '' : p.how === 'lend' ? `🏦 Deposit into ${p.sym} · Jupiter Lend` : p.how === 'trade' ? `⚡ Trade ${String(p.sym).split('-')[0]} here` : `⚡ ${p.fromSym} → ${p.sym}`;
  return <section className={`md j-${job} ${compact ? 'is-compact' : ''}`} data-testid={`money-desk-${job}`}>
    <div className="md-head"><span><b>💸 {title || 'PUT IT TO WORK'}</b><small>{JOB_WORD[job]} · runs right here · your wallet signs</small></span>
      {best?.apy ? <em className="md-best" data-tip="The best live APY you can start from this desk">BEST {apyTxt(best.apy)}</em> : null}</div>
    {provs.length ? <div className="md-prov" role="radiogroup" aria-label="Provider">{provs.map((x, i) => <button key={x.id} type="button" role="radio" aria-checked={x === p} className={x === p ? 'is-on' : ''} style={{ '--i': i }}
      onClick={() => { setPid(x.id); setGo(null); }} data-tip={`${x.name} · ${x.sym}${x.tvl ? ` · TVL ${usd(x.tvl)}` : ''} — ${x.how === 'lend' ? 'deposit right here, withdraw any time' : x.how === 'trade' ? 'the pool\'s coin on the chart + Quick trade' : `swap ${x.fromSym} into it right here; holding it earns`}`} data-testid={`md-prov-${x.id}`}>
      <span><b>{x.sym}</b><small>{x.name}</small></span><i className="md-gauge" style={{ '--g': Math.min(1, (Number(x.apy) || 0) / 15) }}><s /></i><strong className="m-num">{x.apy != null ? apyTxt(x.apy) : 'fees'}</strong></button>)}</div>
      : <p className="md-empty">Reading the live providers…</p>}
    <div className="md-amt"><span className="m-seg" role="radiogroup" aria-label="Amount">{AMOUNTS.map(a => <button key={a} type="button" role="radio" aria-checked={amt === a} className={amt === a ? 'active' : ''} onClick={() => setAmt(a)} data-tip={`Run the numbers at $${a.toLocaleString('en-US')}`} data-testid={`md-amt-${a}`}>${a >= 1000 ? `${a / 1000}K` : a}</button>)}</span>
      <label className="md-own"><em>$</em><input className="m-input" inputMode="decimal" value={amt} onChange={e => setAmt(Math.max(0, Number(e.target.value.replace(/[^\d.]/g, '')) || 0))} aria-label="Your amount in dollars" data-testid="md-amt" /></label>
      <span className="m-seg md-add" role="radiogroup" aria-label="Add every month">{ADDS.map(a => <button key={a} type="button" role="radio" aria-checked={add === a} className={add === a ? 'active' : ''} onClick={() => setAdd(a)} data-tip={a ? `Add $${a} every month — compounding on top` : 'No top-ups'} data-testid={`md-add-${a}`}>{a ? `+$${a}/mo` : 'once'}</button>)}</span></div>
    {p && p.how === 'trade' && !(Number(p.apy) >= 0.5) ? <p className="md-note">A trade, not a yield: this pool publishes no APY worth compounding. ⚡ opens its chart + Quick trade right here — or pick a provider above that pays.</p> : null}
    {p && (p.how !== 'trade' || Number(p.apy) >= 0.5) ? <div className="md-grow">
      <div className="md-tiles">
        <span style={{ '--i': 0 }}><em>A DAY</em><b className="m-num" key={`d${amt}${p.id}`}>+{cash(g.day)}</b></span>
        <span style={{ '--i': 1 }}><em>A MONTH</em><b className="m-num" key={`m${amt}${p.id}`}>+{cash(g.month)}</b></span>
        <span style={{ '--i': 2 }} className="is-hot"><em>IN 1 YEAR</em><b className="m-num" key={`y${amt}${p.id}${add}`}>{dollars(g.end)}</b><small>+{dollars(g.earned)} earned</small></span>
        <span style={{ '--i': 3 }}><em>DOUBLES IN</em><b className="m-num">{g.double && g.double < 100 ? `${g.double.toFixed(g.double < 10 ? 1 : 0)} yr` : '—'}</b></span>
      </div>
      <Curve g={g} add={add} /><Ticker perSec={g.perSec} key={`${amt}${p.id}`} />
    </div> : null}
    {p ? <button type="button" className="m-btn m-go md-go" onClick={run} data-testid="md-go" data-tip={p.how === 'lend' ? 'Jupiter builds it, FEELESS checks every program in it, your wallet signs' : 'The swap opens with both coins set — you press Get quote, your wallet signs'}>{verb}</button> : null}
    {go === 'lend' && p?.how === 'lend' ? <LendBox r={p.row} amount0={/USD/.test(p.sym) ? String(amt) : ''} onClose={() => setGo(null)} /> : null}
    {go && go.startsWith('swap') ? <div className="md-swap" data-testid="md-swap"><Suspense fallback={<p className="md-empty">Opening the swap…</p>}><SwapWorkspace key={go} pair={null} onWallet={() => {}} /></Suspense></div> : null}
    {job === 'lp' && ['v3', 'dlmm'].includes(focus?.kind) ? <RangePicture /> : null}
    {note ? <p className="md-note">{note}</p> : null}
    <small className="md-risk">⚠ {RISK[job]} APYs move daily — today's math, not a promise.</small>
  </section>;
}
