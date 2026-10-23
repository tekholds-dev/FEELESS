import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { usd, apyTxt } from '../lib/cityPlan';
import { familiaDocked, familiaSwap } from './FamiliaTrade';
import { LendBox, goTrade, tradeOf, usePools, ilRange, rangeFactor } from './PoolHub';
import { cash } from '../lib/earnStake';
import { useHotPools } from '../lib/hotPools';
import { dammQuote, dammJoin, dammZap } from '../lib/lpBuilder';
import { lpChanged } from '../lib/lpPositions';
import { LpPositions } from './LpPositions';
import { useWallet } from '../hooks/useWallet';
import { useSolPrice } from '../lib/solPrice';
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
export const AMOUNTS = [5, 10, 100, 1000];   // owner, 2026-10-23: "show what $5–10 does overnight" — small money first, honestly
// 🧼 a narrow side panel never holds the desk (owner: "the right side bar can't hold ish like that"): it asks the page's desk host (Fee City's
// big pop-out over the map) to open it. Returns false when no host is mounted, so the caller can show it inline instead.
let deskHosts = 0;
export const deskHost = d => { deskHosts = Math.max(0, deskHosts + d); };
export function openDesk(detail) { if (!deskHosts) return false; window.dispatchEvent(new CustomEvent('feeless:desk', { detail })); return true; }
const ADDS = [0, 100, 500];   // + a month (DCA): the compounding that actually moves a number
export const JOB_OF = { best: 'best', stake: 'stake', lend: 'lend', vault: 'lend', rwa: 'rwa', perps: 'perps', dex: 'lp', v2: 'lp', v3: 'lp', dlmm: 'lp' };
const RISKS = [['safe', '🛡 SAFE', 'Staking + lending: slow, steady, the coin you put in'], ['degen', '🔥 DEGEN', 'The pools paying the most real fees today — full range, price risk'],
  ['moon', '🚀 MOON', 'Tight v3 / DLMM bands on the busiest pools — the most fees, the most risk']];
const JOB_WORD = { best: 'the best live yields you can start right here', stake: 'liquid staking · SOL that earns', lend: 'lending · interest every block', rwa: 'treasuries on-chain · dollar yield', perps: 'the house side of perps', lp: 'liquidity · swap fees' };
export const RWA_NOTE = 'Tokenized treasuries (USDY, ONyc, BUIDL…) are closed to US persons by their issuers — FEELESS does not route them. Dollar yield here runs through Jupiter Lend\'s stablecoin markets.';
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
  // 🇺🇸 tokenized treasuries (USDY, ONyc, BUIDL …) are closed to US persons by their issuers and FEELESS has no geo check — so they are NEVER a
  // provider here (standing rule: no geo loopholes). Their towers say so; dollar yield routes to Jupiter Lend's stablecoin markets instead.
  const rwa = [];
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

// 💵 SMALL MONEY, HONEST (owner, 2026-10-23: "I want $5–10 to make $0.50–1"): what a goal needs vs what a pool pays. $0.50 a day on $10 is
// 5 %/day ≈ 1,825 % APY — staking (~7 %) and lending (~8 %) never get there; only LP FEES on very busy pools do, with price risk.
export const GOAL = 0.5;
export const needApy = (amt, perDay = GOAL) => ((Number(perDay) || 0) / Math.max(0.01, Number(amt) || 0)) * 365 * 100;
// LP share of the swap fee on pools whose 24h volume we read straight from the DEX (no published APY): PumpSwap 0.20 %, Raydium AMM 0.22 %
const LP_FEE = { PumpSwap: 0.002, Raydium: 0.0022 };
// pure: a pool's real FEE APY — the published base APY, else 24h volume × the LP fee × 365 ÷ liquidity (fees only, before price moves)
export function feeApy(r) {
  if (Number(r?.base) > 0) return Number(r.base);
  const f = LP_FEE[r?.proto]; const v = Number(r?.vol) || 0; const t = Number(r?.tvl) || 0;
  return f && v > 0 && t > 0 ? Math.round(((v * f * 365) / t) * 1000) / 10 : null;
}
// pure: the FEE HUNTERS — the LP pools paying the most real fees right now (≥ $100K deep, so a fill is real), best first
export function feeHunters(rows, n = 5) {
  return (rows || []).filter(r => r && ['v2', 'v3', 'dlmm'].includes(r.kind) && (Number(r.tvl) || 0) >= 1e5).map(r => ({ r, apy: feeApy(r) })).filter(x => x.apy > 0)
    .sort((a, b) => b.apy - a.apy).slice(0, n);
}
// 🚀 MOON: a tight band on a v3 / DLMM pool earns the pool's fees × the band's concentration while the price stays inside (vs a wide ±100 % LP)
export const BANDS = [5, 10, 25];
export const bandBoost = w => rangeFactor(1 + w / 100) / rangeFactor(2);
export function moonHunters(rows, w, n = 5) {
  return (rows || []).filter(r => r && ['v3', 'dlmm'].includes(r.kind) && (Number(r.tvl) || 0) >= 1e5).map(r => ({ r, base: feeApy(r) })).filter(x => x.base > 0)
    .map(x => ({ ...x, apy: x.base * bandBoost(w) })).sort((a, b) => b.apy - a.apy).slice(0, n);
}
function FeeHunters({ rows, amt, moon = false }) {
  const [w, setW] = useState(10);
  const list = useMemo(() => (moon ? moonHunters(rows, w) : feeHunters(rows)), [rows, moon, w]); if (!list.length) return null;
  return <div className={`md-hunt ${moon ? 'is-moon' : ''}`} data-testid={moon ? 'md-moon' : 'md-hunters'}><div className="md-hunt-head"><span><b>{moon ? '🚀 MOON · TIGHT RANGES' : '🔥 FEE HUNTERS'}</b>
      <small>{moon ? `v3 / DLMM fees × a ±${w}% band (×${bandBoost(w).toFixed(1)} vs a wide LP) — only while the price stays inside` : `the pools paying the most real fees today · what ${cash(amt)} would make`}</small></span>
    {moon ? <span className="m-seg md-band" role="radiogroup" aria-label="Band">{BANDS.map(b => <button key={b} type="button" role="radio" aria-checked={w === b} className={w === b ? 'active' : ''} onClick={() => setW(b)} data-tip={`A ±${b}% band: ×${bandBoost(b).toFixed(1)} the fees of a wide LP while the price stays within ${b}%`} data-testid={`md-band-${b}`}>±{b}%</button>)}</span> : null}</div>
    <ol>{list.map(({ r, apy }, i) => { const day = (amt * apy) / 100 / 365; const turn = (Number(r.vol) || 0) / Math.max(1, Number(r.tvl) || 1);
      return <li key={r.id} style={{ '--i': i, '--g': Math.min(1, apy / 2000) }}>
        <span className="md-hunt-id"><b>{r.sym}</b><small>{r.proto} · {turn >= 0.1 ? `${turn.toFixed(turn >= 10 ? 0 : 1)}× its size traded today` : 'quiet'}</small></span>
        <span className="md-hunt-apy"><i aria-hidden="true"><s /></i><strong className="m-num">{apy >= 100 ? Math.round(apy).toLocaleString('en-US') : apy.toFixed(1)}%</strong></span>
        <span className="md-hunt-n" data-tip={`At today's fee pace: ${cash(day / 3)} overnight (8h) · ${cash(day)} a day on ${cash(amt)} — fees only; the coins themselves can fall`}><em>OVERNIGHT</em><b className="m-num">+{cash(day / 3)}</b><small>{cash(day)} / day</small></span>
        {tradeOf(r) ? <button type="button" className="m-btn" onClick={() => goTrade(r)} data-tip="Its coin on the chart + Quick trade, right here" data-testid={`md-hunt-trade-${r.id}`}>⚡</button> : <i />}</li>; })}</ol>
    <small className="md-risk">⚠ {moon ? 'A tight band out-earns everything while the price sits inside it and earns 0 the moment it leaves; you end up holding the coin that fell (impermanent loss). Re-center it when it drifts.' : 'Fee pools pay in their own two coins: if one falls, you hold more of it (impermanent loss) — a memecoin pool can drop 50 % in an hour.'} No risk, no reward — size it like you can lose it.</small>
  </div>;
}

// 🔌 JOIN IN PLACE (owner: "I tightened a v3 pool with $100 and made $120 — no redirects"): half your amount in SOL, half in the coin, into a hot
// Meteora pool — quote → (get the coin with an in-place swap if the wallet lacks it) → the deposit is built in the browser, SIMULATED, then your
// wallet signs. The position is an NFT in your wallet; its fees grow with every trade in the pool.
function JoinBox({ row, amt, onClose }) {
  const { wallet, provider, connect } = useWallet() || {}; const solUsd = useSolPrice(); const sol = wallet?.chain === 'solana' && wallet?.address;
  const [q, setQ] = useState(null); const [st, setSt] = useState(''); const [busy, setBusy] = useState(false); const [done, setDone] = useState(null); const [err, setErr] = useState(''); const [swap, setSwap] = useState(null);
  const solIn = solUsd ? amt / 2 / solUsd : null;
  const quote = async () => { if (!sol) { await connect?.('solana'); return; } if (!solIn) return; setBusy(true); setErr(''); setSt('Reading the pool…');
    try { setQ(await dammQuote({ pool: row.pool, solAmount: solIn, owner: wallet.address })); } catch (e) { setErr(e.message); } setSt(''); setBusy(false); };
  const getCoin = () => { const s2 = { from: SOL, to: row.coin, amount: solIn ? solIn.toFixed(4) : undefined };
    if (familiaDocked()) { familiaSwap(s2); return; }
    try { sessionStorage.setItem('feeless.swap.pair', JSON.stringify({ input: s2.from, output: s2.to, amount: s2.amount })); } catch { /* storage blocked */ } setSwap(`s${Date.now()}`); };
  const join = async () => { setBusy(true); setErr(''); try { setDone(await dammJoin({ provider, owner: wallet.address, quote: q, onStatus: setSt })); setQ(null); lpChanged(); } catch (e) { setErr(e.message); } setSt(''); setBusy(false); };
  // ⚡ ONE TAP: half the SOL buys the coin through the FEELESS swap engine, the other half + what it bought joins (two wallet approvals)
  const zap = async () => { if (!sol) { await connect?.('solana'); return; } if (!solIn) return; setBusy(true); setErr(''); setQ(null);
    try { setDone(await dammZap({ provider, owner: wallet.address, pool: row.pool, coin: row.coin, solAmount: solIn * 2, onStatus: setSt })); lpChanged(); } catch (e) { setErr(e.code === 4001 ? 'Declined in the wallet — nothing more was sent.' : e.message); } setSt(''); setBusy(false); };
  return <div className="md-join" data-testid={`md-join-${row.id}`}>
    <div className="md-join-head"><b>＋ JOIN {row.sym}</b><small>{cash(amt / 2)} in SOL + {cash(amt / 2)} in ${row.coinSym} · your wallet signs</small><button type="button" className="md-x" onClick={onClose} aria-label="Close" data-tip="Close">✕</button></div>
    {done ? <p className="md-join-ok" data-testid="md-join-ok">✅ You're in the pool{done.swap ? ' (zapped)' : ''} — position <b>{done.position.slice(0, 6)}…</b> earns {(row.feeDay * 100).toFixed(1)}%/day at today's pace · tx {done.signature.slice(0, 8)}…</p>
      : !q ? <div className="md-join-go"><button type="button" className="m-btn m-go md-zap" disabled={busy || (sol && !solIn)} onClick={zap} data-testid="md-join-zap"
          data-tip={`One tap: swap ${solIn ? solIn.toFixed(4) : '½'} SOL → $${row.coinSym} (FEELESS swap engine), then join with the other half + what it bought — two wallet approvals, each simulated first`}>
          {sol ? (solIn ? `⚡ ZAP ${cash(amt)} — ${solIn.toFixed(4)} SOL → $${row.coinSym}, then join` : 'Reading the SOL price…') : 'Connect wallet'}</button>
        {sol ? <button type="button" className="m-btn" disabled={busy || !solIn} onClick={quote} data-testid="md-join-quote" data-tip="Already hold the coin? Quote the join with what's in your wallet">Join with what I hold</button> : null}</div>
      : <div className="md-join-q">
        <span><em>YOU PUT IN</em><b className="m-num">{(Number(q.lamports) / 1e9).toFixed(4)} SOL</b><b className="m-num">{q.coinUi.toLocaleString('en-US', { maximumFractionDigits: 2 })} ${row.coinSym}</b></span>
        {q.short ? <button type="button" className="m-btn" onClick={getCoin} data-testid="md-join-getcoin" data-tip={`You hold less ${row.coinSym} than the pool needs — swap ${solIn ? solIn.toFixed(4) : ''} SOL into it here, then join`}>⚡ Get ${row.coinSym} first</button> : null}
        <button type="button" className="m-btn m-go" disabled={busy || q.short} onClick={join} data-testid="md-join-sign" data-tip="Built with Meteora's SDK, simulated first — nothing is signed if the chain would reject it">✍ Join the pool</button></div>}
    {swap ? <div className="md-swap"><Suspense fallback={<p className="md-empty">Opening the swap…</p>}><SwapWorkspace key={swap} pair={null} onWallet={() => {}} /></Suspense></div> : null}
    {st ? <p className="md-empty" aria-live="polite">{st}</p> : null}{err ? <p className="md-join-err" role="alert">{err}</p> : null}
    <small className="md-risk">A position also locks a little SOL as rent (back when you close it). If ${row.coinSym} dumps, you end up holding more of it — that's the risk the fees pay you for.</small>
  </div>;
}
function HotPools({ amt }) {
  const rows = useHotPools(); const [open, setOpen] = useState(null);
  if (!rows) return <p className="md-empty">Reading Meteora's hottest pools…</p>; if (!rows.length) return null;
  return <div className="md-hunt md-hot" data-testid="md-hot"><div className="md-hunt-head"><span><b>🔥 HOT POOLS · JOIN HERE</b><small>Meteora SOL pools paying LPs the most right now · ≥ $20K deep · ≥ 6 h old · ≥ 300 holders</small></span></div>
    <ol>{rows.slice(0, 5).map((r, i) => { const day = amt * r.feeDay;
      return <li key={r.id} style={{ '--i': i, '--g': Math.min(1, r.feeDay / 0.1) }}>
        <span className="md-hunt-id"><b>{r.sym}</b><small>{Math.round(r.ageH)}h old · {r.holders.toLocaleString('en-US')} holders · {usd(r.tvl)} deep</small></span>
        <span className="md-hunt-apy" data-tip={`LPs kept ${(r.feeDay * 100).toFixed(2)}% of the pool in fees over 24h (≈ ${Math.round(r.apy).toLocaleString('en-US')}% a year at that pace)`}><i aria-hidden="true"><s /></i><strong className="m-num">{(r.feeDay * 100).toFixed(1)}%/day</strong></span>
        <span className="md-hunt-n"><em>OVERNIGHT</em><b className="m-num">+{cash(day / 3)}</b><small>{cash(day)} / day</small></span>
        <button type="button" className={`m-btn m-go ${open === r.id ? 'active' : ''}`} aria-expanded={open === r.id} onClick={() => setOpen(x => (x === r.id ? null : r.id))} data-tip={`Join ${r.sym} with ${cash(amt)} right here`} data-testid={`md-hot-join-${r.id}`}>＋</button>
        {open === r.id ? <JoinBox row={r} amt={amt} onClose={() => setOpen(null)} /> : null}</li>; })}</ol>
    <small className="md-risk">⚠ 24h fee pace, not a promise — hot pools cool fast and memecoins can halve in an hour. No risk, no reward: size it like you can lose it.</small>
  </div>;
}

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
  const [pid, setPid] = useState(null); const [amt, setAmt] = useState(10); const [risk, setRisk] = useState(job === 'best' || job === 'lp' ? 'moon' : 'safe'); const [add, setAdd] = useState(0); const [go, setGo] = useState(null);   // 🎚 owner: "no risk no reward — don't be making safe shit"
  const p = provs.find(x => x.id === pid) || (prefer && provs.find(x => String(x.sym).toUpperCase() === String(prefer).toUpperCase())) || provs[0] || null; const g = useMemo(() => growth(amt, p?.apy, add), [amt, p, add]);
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
      <span className="m-seg md-risk-dial" role="radiogroup" aria-label="Risk">{RISKS.map(([k, w, tip]) => <button key={k} type="button" role="radio" aria-checked={risk === k} className={`${risk === k ? 'active' : ''} r-${k}`} onClick={() => setRisk(k)} data-tip={tip} data-testid={`md-risk-${k}`}>{w}</button>)}</span></div>
    <LpPositions compact />
    <div className="md-amt"><span className="m-seg" role="radiogroup" aria-label="Amount">{AMOUNTS.map(a => <button key={a} type="button" role="radio" aria-checked={amt === a} className={amt === a ? 'active' : ''} onClick={() => setAmt(a)} data-tip={`Run the numbers at $${a.toLocaleString('en-US')}`} data-testid={`md-amt-${a}`}>${a >= 1000 ? `${a / 1000}K` : a}</button>)}</span>
      <label className="md-own"><em>$</em><input className="m-input" inputMode="decimal" value={amt} onChange={e => setAmt(Math.max(0, Number(e.target.value.replace(/[^\d.]/g, '')) || 0))} aria-label="Your amount in dollars" data-testid="md-amt" /></label>
      {risk === 'safe' ? <span className="m-seg md-add" role="radiogroup" aria-label="Add every month">{ADDS.map(a => <button key={a} type="button" role="radio" aria-checked={add === a} className={add === a ? 'active' : ''} onClick={() => setAdd(a)} data-tip={a ? `Add $${a} every month — compounding on top` : 'No top-ups'} data-testid={`md-add-${a}`}>{a ? `+$${a}/mo` : 'once'}</button>)}</span> : null}</div>
    {risk !== 'safe' ? <HotPools amt={amt} /> : null}
    {risk !== 'safe' ? <FeeHunters rows={all} amt={amt} moon={risk === 'moon'} /> : null}
    {risk === 'safe' ? <>
    {provs.length ? <div className="md-prov" role="radiogroup" aria-label="Provider">{provs.map((x, i) => <button key={x.id} type="button" role="radio" aria-checked={x === p} className={x === p ? 'is-on' : ''} style={{ '--i': i }}
      onClick={() => { setPid(x.id); setGo(null); }} data-tip={`${x.name} · ${x.sym}${x.tvl ? ` · TVL ${usd(x.tvl)}` : ''} — ${x.how === 'lend' ? 'deposit right here, withdraw any time' : x.how === 'trade' ? 'the pool\'s coin on the chart + Quick trade' : `swap ${x.fromSym} into it right here; holding it earns`}`} data-testid={`md-prov-${x.id}`}>
      <span><b>{x.sym}</b><small>{x.name}</small></span><i className="md-gauge" style={{ '--g': Math.min(1, (Number(x.apy) || 0) / 15) }}><s /></i><strong className="m-num">{x.apy != null ? apyTxt(x.apy) : 'fees'}</strong></button>)}</div>
      : <p className="md-empty">Reading the live providers…</p>}
    {p && p.how === 'trade' && !(Number(p.apy) >= 0.5) ? <p className="md-note">A trade, not a yield: this pool publishes no APY worth compounding. ⚡ opens its chart + Quick trade right here — or pick a provider above that pays.</p> : null}
    {p && (p.how !== 'trade' || Number(p.apy) >= 0.5) ? <div className="md-grow">
      <div className="md-tiles">
        <span style={{ '--i': 0 }} className="is-hot"><em>OVERNIGHT</em><b className="m-num" key={`n${amt}${p.id}`}>+{cash(g.day / 3)}</b><small>8 hours</small></span>
        <span style={{ '--i': 1 }}><em>A DAY</em><b className="m-num" key={`d${amt}${p.id}`}>+{cash(g.day)}</b><small>{cash(g.month)} / mo</small></span>
        <span style={{ '--i': 2 }}><em>IN 1 YEAR</em><b className="m-num" key={`y${amt}${p.id}${add}`}>{dollars(g.end)}</b><small>+{dollars(g.earned)} earned</small></span>
        <span style={{ '--i': 3 }}><em>DOUBLES IN</em><b className="m-num">{g.double && g.double < 100 ? `${g.double.toFixed(g.double < 10 ? 1 : 0)} yr` : '—'}</b></span>
      </div>
      <p className="md-goal" data-testid="md-goal"><em>YOUR GOAL</em> {cash(GOAL)} a day on {cash(amt)} needs <b className="m-num">{Math.round(needApy(amt)).toLocaleString('en-US')}% APY</b> · {p.sym} pays <b className="m-num">{apyTxt(p.apy)}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.01, Math.min(1, (Number(p.apy) || 0) / needApy(amt)))})` }} /></u></p>
      <Curve g={g} add={add} /><Ticker perSec={g.perSec} key={`${amt}${p.id}`} />
    </div> : null}
    {p ? <button type="button" className="m-btn m-go md-go" onClick={run} data-testid="md-go" data-tip={p.how === 'lend' ? 'Jupiter builds it, FEELESS checks every program in it, your wallet signs' : 'The swap opens with both coins set — you press Get quote, your wallet signs'}>{verb}</button> : null}
    {go === 'lend' && p?.how === 'lend' ? <LendBox r={p.row} amount0={/USD/.test(p.sym) ? String(amt) : ''} onClose={() => setGo(null)} /> : null}
    {go && go.startsWith('swap') ? <div className="md-swap" data-testid="md-swap"><Suspense fallback={<p className="md-empty">Opening the swap…</p>}><SwapWorkspace key={go} pair={null} onWallet={() => {}} /></Suspense></div> : null}
    </> : null}
    {job === 'lp' && ['v3', 'dlmm'].includes(focus?.kind) ? <RangePicture /> : null}
    {note || job === 'rwa' ? <p className="md-note">{note || RWA_NOTE}</p> : null}
    <small className="md-risk">⚠ {RISK[job]} APYs move daily — today's math, not a promise.</small>
  </section>;
}
