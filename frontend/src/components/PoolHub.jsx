import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { sharedJson } from '../lib/sharedJson';
import { resolveCoin } from '../lib/resolveCoin';
import { familiaTrade } from './FamiliaTrade';
import { POOL_KIND, usd, apyTxt } from '../lib/cityPlan';
import '../styles/poolHub.css';
import { useWallet } from '../hooks/useWallet';
import { LEND_SIDES, okAmount, lendLine, lendQuote, lendSign } from '../lib/lendEarn';
import { StakeSeg } from './EarnStake';
import { useStake, cash } from '../lib/earnStake';
import { FamEmpty } from './FamEmpty';
import { MoneyDesk, RangePicture, JOB_OF } from './MoneyDesk';

// 🏦 THE POOL HUB (the Pool Hall in Fee City + every pool building in the outer cities): every top and rising Solana pool in ONE pop-out —
// v2 AMMs, v3 / CLMM, DLMM bins, auto-compounding vaults, lending, liquid staking, perps, RWA — with live TVL, APY and its 7-day move.
// Each row does the real-money thing without "running to each site": ⚡ trade / stake through OUR engine (the chart + Quick trade slide over the room, your
// wallet signs), ＋ deposit on the pool's OWN page (opened exactly, your wallet signs there — FEELESS never holds funds), 🏠 set your
// family's building to it (display only). Data: /api/reputation/familia-pools (DefiLlama yields + our pair feed, ≤ 10 min old).
export const KIND_COLOR = { v2: '#ff9f45', v3: '#6ad7ff', dlmm: '#ffd36b', vault: '#3ddc84', lend: '#f5c451', stake: '#45e4c8', perps: '#ff5dbb', rwa: '#e8e3d6' };
const LENS = [['all', 'ALL'], ['v2', 'V2'], ['v3', 'V3'], ['dlmm', 'DLMM'], ['vault', 'VAULTS'], ['lend', 'LEND'], ['stake', 'STAKE'], ['perps', 'PERPS'], ['rwa', 'RWA']];
const SORT = [['tvl', 'TOP'], ['apy', 'YIELD'], ['rise', 'RISING']];

export function usePools() {
  const [v, setV] = useState(null);
  useEffect(() => { let on = true; const go = () => sharedJson('/api/reputation/familia-pools', { maxAge: 240000 }).then(d => on && d && setV(d)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 300000); return () => { on = false; clearInterval(t); }; }, []);
  return v;
}

// pure: a DEX pool paying ~nothing (APY ≤ 0.05 %) is dead money — it never leads a list (a search still finds it). 2026-10-24: IOST-USDC led V3 TOP
// on a stale $90.7M TVL at 0.0 % APY.
export const deadPool = r => ['v2', 'v3', 'dlmm'].includes(r?.kind) && !(Number(r?.apy) > 0.05);
// pure: the rows a lens + sort + search show
export function poolRows(pools, lens = 'all', sort = 'tvl', q = '') {
  const s = String(q || '').trim().toLowerCase();
  const rows = (pools || []).filter(r => (lens === 'all' || r.kind === lens) && (!s || `${r.sym} ${r.proto}`.toLowerCase().includes(s)) && (s || !deadPool(r)));
  const key = { tvl: r => r.tvl || 0, apy: r => (r.apy == null ? -1 : r.apy), rise: r => r.rise || 0 }[sort] || (r => r.tvl || 0);
  return rows.slice().sort((a, b) => key(b) - key(a));
}
// pure: what the ⚡ button does for a row — trade the pool's token, stake into the LST, or nothing (lend / vault / RWA = deposit only)
export function tradeOf(r) {
  if (!r) return null;
  if (r.kind === 'stake') return r.hold ? { word: `Stake · buy ${r.sym}`, mint: r.hold } : null;
  if (r.kind === 'perps' && /JLP/i.test(r.sym || '') && r.hold) return { word: `Buy ${r.sym}`, mint: r.hold };   // 🎰 JLP is a token: buy it through our engine
  if (['v2', 'v3', 'dlmm'].includes(r.kind)) return r.pair ? { word: `Trade ${r.sym.split('-')[0]}`, pair: r.pair } : r.hold ? { word: `Trade ${r.sym.split('-')[0]}`, mint: r.hold } : null;
  return null;
}

export async function goTrade(r) {
  const t = tradeOf(r); if (!t) return;
  if (t.pair) { familiaTrade({ chainId: 'solana', pairAddress: t.pair }); return; }
  const p = await resolveCoin('solana', t.mint);
  if (p?.pairAddress && !p.preMarket) familiaTrade({ chainId: 'solana', pairAddress: p.pairAddress }); else toast.error(`No pool to trade ${r.sym} through FEELESS yet — use ＋ Deposit on ${r.proto}.`);
}

function Gauge({ v }) {   // APY ring: fills to 50 % APY, gold past it
  const k = v == null ? 0 : Math.max(0.03, Math.min(1, v / 50));
  return <span className={`phb-gauge ${v != null && v >= 50 ? 'is-hot' : ''}`} style={{ '--k': k }} aria-hidden="true"><i /></span>;
}

// one pool, the same row in the hub list and the side panel
// 📈 REAL 24h (fee_pools.earn_24h mirrored): what $X earned in the last 24h at the live APY — fees / interest vs reward tokens; null when a DEX
// pool publishes no APY (never a guessed fee tier)
export function earn24(r, usd = 1000) {
  if (r?.apy == null) return null;
  const d = p => (usd * (Number(p) || 0)) / 100 / 365;
  return { total: d(r.apy), base: d(r.base ?? r.apy), reward: d(r.reward || 0), poolDay: ((Number(r.tvl) || 0) * Number(r.apy)) / 100 / 365 };
}
const money = v => (v >= 1 ? `$${v.toFixed(2)}` : v >= 0.01 ? `$${v.toFixed(3)}` : `$${v.toFixed(4)}`);
// pure: chart path in a 600 × 160 box (TVL as an area, APY as a line on its own scale)
export function chartPaths(points, days = 30) {
  const last = points?.length ? points[points.length - 1].t : 0; const ps = (points || []).filter(p => p.t >= last - days * 86400);
  if (ps.length < 2) return null;
  const t0 = ps[0].t, t1 = ps[ps.length - 1].t; const x = t => ((t - t0) / Math.max(1, t1 - t0)) * 600;
  const tMax = Math.max(...ps.map(p => p.tvl)) || 1, tMin = Math.min(...ps.map(p => p.tvl)); const aMax = Math.max(...ps.map(p => p.apy)) || 1, aMin = Math.min(...ps.map(p => p.apy));
  const y = (v, lo, hi) => 150 - ((v - lo) / Math.max(1e-9, hi - lo || hi || 1)) * 130;
  const tvl = ps.map(p => `${x(p.t).toFixed(1)},${y(p.tvl, tMin * 0.98, tMax).toFixed(1)}`); const apy = ps.map(p => `${x(p.t).toFixed(1)},${y(p.apy, aMin * 0.95, aMax).toFixed(1)}`);
  return { area: `M0,160 L${tvl.join(' L')} L600,160 Z`, tvl: `M${tvl.join(' L')}`, apy: `M${apy.join(' L')}`, first: ps[0], last: ps[ps.length - 1], n: ps.length };
}
// 🎯 RANGE TUNER (owner, 2026-10-22: "if a user wants to tweak the v3 pool for better gains it should show TRUE data and impermanent loss").
// Exact concentrated-liquidity math, start price 1, range [1/k, k]: value of the LP vs simply HOLDING the two coins after the price moves ×m.
// ilV2 = the classic full-range pool. rangeFactor = how much more liquidity each $ provides in that range (= more fees per $, ONLY while in range).
export const ilV2 = m => 2 * Math.sqrt(m) / (1 + m) - 1;
export function ilRange(m, k) {
  const pa = 1 / k, pb = k, sp = Math.sqrt;
  const x0 = 1 - 1 / sp(pb), y0 = 1 - sp(pa);   // L = 1 at price 1
  const v = m <= pa ? (1 / sp(pa) - 1 / sp(pb)) * m : m >= pb ? sp(pb) - sp(pa) : (1 / sp(m) - 1 / sp(pb)) * m + (sp(m) - sp(pa));
  return v / (x0 * m + y0) - 1;
}
export const rangeFactor = k => 1 / (1 - 1 / Math.sqrt(k));

function PoolDetail({ r }) {
  const [d, setD] = useState(null); const [days, setDays] = useState(30); const [amt, setAmt] = useState(1000);
  useEffect(() => { let on = true; sharedJson(`/api/reputation/familia-pools/chart/${r.id}`, { maxAge: 600000 }).then(x => on && setD(x || { points: [] })).catch(() => on && setD({ points: [] })); return () => { on = false; }; }, [r.id]);
  const c = chartPaths(d?.points, days); const e = earn24(r, amt);
  const tvlMove = c ? ((c.last.tvl / Math.max(1, c.first.tvl)) - 1) * 100 : null;
  return <div className="phb-detail" data-testid={`pool-detail-${r.id}`}>
    <div className="phb-chart">
      <header><b>TVL</b><i className="k-tvl" /> <b>APY</b><i className="k-apy" />{tvlMove != null ? <em className={tvlMove >= 0 ? 'up' : 'dn'}>{tvlMove >= 900 ? `${(c.last.tvl / Math.max(1, c.first.tvl)).toLocaleString('en-US', { maximumFractionDigits: 0 })}×` : `${tvlMove >= 0 ? '+' : ''}${tvlMove.toFixed(1)}%`} TVL in {days}d</em> : null}
        <span className="m-seg">{[7, 30, 90].map(n => <button key={n} type="button" className={days === n ? 'active' : ''} onClick={() => setDays(n)} data-tip={`The last ${n} days`}>{n}D</button>)}</span></header>
      {c ? <svg viewBox="0 0 600 160" preserveAspectRatio="none" role="img" aria-label={`TVL and APY, last ${days} days`}><path d={c.area} className="area" /><path d={c.tvl} className="tvl" /><path d={c.apy} className="apy" /></svg>
        : <p className="phb-nochart">{d ? (r.src === 'pair' ? 'A live DEX pool — no history published; ⚡ trade it here for its candles.' : 'No history for this pool yet.') : 'Reading its history…'}</p>}
      {c ? <footer><span>{usd(c.first.tvl)} → <b>{usd(c.last.tvl)}</b></span><span>APY {apyTxt(c.first.apy)} → <b>{apyTxt(c.last.apy)}</b></span><span>{c.n} days of data · DefiLlama</span></footer> : null}
    </div>
    <div className="phb-earn">
      <header><b>💵 REAL 24h</b><small>at today's APY · before gas</small></header>
      {e ? <>
        <label className="phb-earn-in"><span>If you had</span><input type="range" min="5" max="100000" step="5" value={amt} onChange={e2 => setAmt(Number(e2.target.value))} aria-label="Amount deposited" /><b>{usd(amt)}</b></label>
        <p className="phb-earn-big"><b key={amt}>+{money(e.total)}</b><small>in 24h · {money(e.total * 30)} a month</small></p>
        <span className="phb-earn-split"><i style={{ flexGrow: Math.max(0.01, e.base) }} className="b" data-tip="Fees / interest — paid in the pool's own assets" /><i style={{ flexGrow: Math.max(0.0001, e.reward) }} className="r" data-tip="Reward tokens — their price can fall" /></span>
        <small className="phb-earn-legend"><em className="b">fees / interest {money(e.base)}</em><em className="r">rewards {money(e.reward)}</em></small>
        <p className="phb-earn-pool" data-tip="What the whole pool paid its depositors in the last 24h (TVL × APY ÷ 365)">The pool paid <b>{usd(e.poolDay)}</b> to depositors in 24h</p>
        {r.il ? <small className="phb-warn">⚠ impermanent-loss risk: a two-token pool can lose value vs holding when prices move apart.</small> : null}</>
        : <p className="phb-nochart">This DEX pool publishes no APY — its 24h volume is {usd(r.vol || 0)} ({Math.round(((r.vol || 0) / Math.max(1, r.tvl || 1)) * 100)}% of its size). Fees go to LPs in the pool's own coins.</p>}
    </div>
    {['v3', 'dlmm'].includes(r.kind) ? <RangePicture pool={r} amt={amt} /> : null}
  </div>;
}

// 🏦 DEPOSIT HERE (Jupiter Lend rows): amount → the server builds + checks the transaction → you read exactly what runs → your wallet signs.
export function LendBox({ r, onClose, amount0 = '' }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [side, setSide] = useState('deposit'); const [amt, setAmt] = useState(amount0); const [q, setQ] = useState(null); const [st, setSt] = useState(''); const [busy, setBusy] = useState(false); const [sig, setSig] = useState('');
  const sol = wallet?.chain === 'solana' && wallet?.address;
  const review = async () => {
    if (!sol) { await connect?.('solana'); return; }
    setBusy(true); setQ(null); setSt('Building it with Jupiter…');
    try { setQ(await lendQuote({ address: wallet.address, asset: r.mints[0], side, amount: amt })); setSt(''); } catch (e) { setSt(''); toast.error(e.message); }
    setBusy(false);
  };
  const sign = async () => {
    setBusy(true);
    try { const s = await lendSign({ provider, address: wallet.address, quote: q, onStatus: setSt }); setSig(s); setQ(null); setSt(''); toast.success(`🏦 ${side === 'withdraw' ? 'Withdrawn' : 'Deposited'} — it landed`); } catch (e) { setSt(''); toast.error(e.message); }
    setBusy(false);
  };
  return <div className="phb-lend" data-testid={`lend-${r.id}`}>
    <header><b>🏦 {r.sym} · Jupiter Lend</b><small>your wallet signs · FEELESS never holds funds</small><button type="button" className="phb-x" onClick={onClose} aria-label="Close" data-tip="Close">✕</button></header>
    <div className="phb-lend-row">
      <div className="m-seg" role="tablist" aria-label="Deposit or withdraw">{LEND_SIDES.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={side === k} className={side === k ? 'active' : ''} onClick={() => { setSide(k); setQ(null); }} data-tip={k === 'deposit' ? 'Lend it out and earn the APY' : 'Take it back out to your wallet'}>{w}</button>)}</div>
      <label className="phb-amt"><input className="m-input" inputMode="decimal" value={amt} onChange={e => { setAmt(e.target.value.replace(',', '.')); setQ(null); }} placeholder="0.00" aria-label={`Amount of ${r.sym}`} data-testid="lend-amt" /><em>{r.sym}</em></label>
      <button type="button" className="m-btn" disabled={busy || (sol && !okAmount(amt))} onClick={review} data-tip="Jupiter builds it, FEELESS checks every program in it before your wallet sees it" data-testid="lend-review">{sol ? 'Review' : 'Connect wallet'}</button>
    </div>
    {q ? <div className="phb-lend-q" data-testid="lend-quote"><p>{lendLine(q, amt)}</p><small>Checked: you pay + sign alone · runs only {q.programs.join(' · ')}</small>
      <button type="button" className="m-btn m-go" disabled={busy} onClick={sign} data-tip="Simulated first — nothing is signed if Solana would reject it" data-testid="lend-sign">Sign in wallet</button></div> : null}
    {st ? <p className="phb-lend-st" aria-live="polite"><i aria-hidden="true" />{st}</p> : null}
    {sig ? <p className="phb-lend-ok">✅ Landed · <a href={`https://solscan.io/tx/${sig}`} target="_blank" rel="noopener noreferrer">view on Solscan ↗</a> · <a href="https://jup.ag/lend/earn" target="_blank" rel="noopener noreferrer">your position on Jupiter ↗</a></p> : null}
  </div>;
}

export function PoolRow({ r, i = 0, big = false, blocks = [], onLink, onDesk = null }) {
  const [pick, setPick] = useState(false); const [lend, setLend] = useState(false); const [more, setMore] = useState(false); const [desk, setDesk] = useState(false); const t = tradeOf(r); const stake = useStake(); const e = earn24(r, stake);
  const canLend = r.project === 'jupiter-lend' && (r.mints || []).length > 0;
  const tvlK = Math.max(0.04, Math.min(1, (Math.log10(1 + (r.tvl || 0)) - 4) / 5.5));
  return <li className={`phb-row k-${r.kind} ${big ? 'is-big' : ''}`} style={{ '--i': Math.min(i, 14), '--kc': KIND_COLOR[r.kind] || '#45e486' }} data-testid={`pool-${r.id}`}>
    <span className="phb-id"><b>{r.sym}</b><small>{r.proto} · {POOL_KIND[r.kind] || r.kind}{r.meta ? ` · ${r.meta}` : ''}</small></span>
    <span className="phb-tvl" data-tip={`Total value locked ${usd(r.tvl)}${r.vol ? ` · 24h volume ${usd(r.vol)}` : ''}`}><em>TVL</em><b className="m-num">{usd(r.tvl)}</b><u><s style={{ transform: `scaleX(${tvlK})` }} /></u></span>
    <span className="phb-apy" data-tip={r.apy == null ? 'No APY published for this DEX pool — its 24h volume vs liquidity shows how busy it is' : `APY ${apyTxt(r.apy)}${r.base != null ? ` · base ${apyTxt(r.base)}` : ''}${r.reward ? ` · rewards ${apyTxt(r.reward)}` : ''}${r.il ? ' · impermanent-loss risk' : ''}`}>
      <Gauge v={r.apy} /><span><em>{r.apy == null ? 'TURNOVER' : 'APY'}</em><b className="m-num">{r.apy == null ? `${Math.round(((r.vol || 0) / Math.max(1, r.tvl || 1)) * 100)}%` : apyTxt(r.apy)}</b></span></span>
    <span className={`phb-rise ${r.rise > 0 ? 'up' : r.rise < 0 ? 'dn' : ''}`} data-tip={r.d7 != null ? `APY move over 7 days: ${r.d7 >= 0 ? '+' : ''}${r.d7}` : 'How busy vs its size (24h volume ÷ liquidity)'}>{r.rise > 0 ? '▲' : r.rise < 0 ? '▼' : '•'} {Math.abs(r.rise || 0).toFixed(1)}</span>
    {e ? <span className="phb-24" data-tip={`$${stake.toLocaleString('en-US')} here earned ${money(e.total)} in the last 24h at today's APY (${money(e.base)} fees / interest + ${money(e.reward)} rewards) — ${cash(e.total * 30)} a month, ${cash(e.total * 365)} a year`} data-testid={`pool-earn-${r.id}`}>
      <em>${stake >= 1000 ? `${stake / 1000}K` : stake} · DAY</em><b key={stake}>+{cash(e.total)}</b><small className="es-yr">{cash(e.total * 365)} / yr</small></span> : null}
    <span className="phb-acts">
      <button type="button" className={`m-btn ${more ? 'active' : ''}`} aria-expanded={more} onClick={() => setMore(v => !v)} data-tip="The pool's TVL + APY history and what your money would have earned" data-testid={`pool-more-${r.id}`}>📈 Chart + 24h</button>
      {t ? <button type="button" className="m-btn m-go" onClick={() => goTrade(r)} data-tip="Through FEELESS, right here: the chart + Quick trade open on this pool, you pick the amount, your wallet signs" data-testid={`pool-trade-${r.id}`}>⚡ {t.word}</button> : null}
      {canLend ? <button type="button" className={`m-btn m-go ${lend ? 'active' : ''}`} aria-expanded={lend} onClick={() => setLend(v => !v)} data-tip="Deposit or withdraw right here — Jupiter builds it, FEELESS checks it, your wallet signs" data-testid={`pool-lend-${r.id}`}>🏦 Deposit here</button> : null}
      <button type="button" className={`m-btn m-go ${desk ? 'active' : ''}`} aria-expanded={desk} onClick={() => { if (!(onDesk && onDesk(r))) setDesk(v => !v); }} data-tip="Put money to work from here: pick the provider, your amount, see it compound — the action runs in FEELESS and your wallet signs" data-testid={`pool-desk-${r.id}`}>💸 Put it to work</button>
      {onLink && blocks.length ? (pick ? <select className="m-input phb-pick" autoFocus defaultValue="" onChange={e => { if (e.target.value) { onLink(e.target.value, r); setPick(false); } }} onBlur={() => setPick(false)} aria-label="Which of your buildings">
        <option value="" disabled>Set which building…</option>{blocks.map(b => <option key={b} value={b}>{b}</option>)}</select>
        : <button type="button" className="m-btn" onClick={() => (blocks.length === 1 ? onLink(blocks[0], r) : setPick(true))} data-tip="Your family's building wears this pool: its name, kind and live APY on the billboard (display only)" data-testid={`pool-link-${r.id}`}>🏠 Set building</button>) : null}
    </span>{lend ? <LendBox r={r} onClose={() => setLend(false)} /> : null}{desk ? <MoneyDesk job={JOB_OF[r.kind] || 'lend'} focus={r} compact /> : null}{more ? <PoolDetail r={r} /> : null}</li>;
}

// 🐱 FEECAT'S COMBO (owner, 2026-10-22: "the cat suggests pool combos … real mass compound"): a 50 / 30 / 20 split picked from the LIVE hub —
// the safest big stable lending market (cash leg), the deepest liquid-staking pool (SOL leg), the best FEE-earning pool (fees, not emissions,
// so the yield is not just reward tokens). Blended APY + what it earns a day / a month at your amount — true math, every leg's risk named.
export function catCombo(rows, amt = 100) {
  const rs = (rows || []).filter(r => Number.isFinite(r?.apy) && r.apy > 0);
  const top = (xs, k) => xs.reduce((b, r) => ((r[k] || 0) > (b?.[k] || 0) ? r : b), null);
  const legs = [
    ['CASH', 0.5, top(rs.filter(r => r.kind === 'lend' && r.stable && r.tvl >= 5e6 && r.apy <= 40), 'apy'), 'stablecoin lending · smart-contract risk only'],
    ['SOL', 0.3, top(rs.filter(r => r.kind === 'stake' && r.tvl >= 1e7 && r.apy <= 20), 'apy'), 'liquid staking · moves with SOL\'s price'],
    ['FEES', 0.2, top(rs.filter(r => ['v2', 'v3', 'dlmm', 'vault'].includes(r.kind) && r.tvl >= 1e6 && r.apy <= 200 && (r.base || 0) >= r.apy * 0.4), 'base'), 'trading fees · impermanent-loss risk'],
  ].filter(l => l[2]);
  const wsum = legs.reduce((a, l) => a + l[1], 0) || 1;
  const apy = legs.reduce((a, l) => a + (l[1] / wsum) * l[2].apy, 0);
  const day = (amt * apy) / 100 / 365;
  return { legs: legs.map(([role, w, r, risk]) => ({ role, w: w / wsum, r, risk })), apy: Math.round(apy * 100) / 100, day, month: day * 30, year: amt * apy / 100 };
}
function CatCombo({ pools }) {
  const [amt, setAmt] = useState(25); const [leg, setLeg] = useState(null); const c = useMemo(() => catCombo(pools?.pools, amt), [pools, amt]);   // owner: from $5, honest small numbers
  if (!c.legs.length) return null;
  const m = v => (v >= 1 ? `$${v.toFixed(2)}` : v >= 0.01 ? `$${v.toFixed(3)}` : `$${v.toFixed(5)}`);
  return <div className="phb-combo" data-testid="cat-combo"><header data-tip="Real APYs move every day; this is today's math, not a promise. Lending + staking pay slowly — big daily % only comes with big risk."><b>🐱 FEECAT'S COMBO</b><small>picked from the live hub · {c.legs.length} legs</small></header>
    <ComboLive c={c} amt={amt} />
    <label className="phb-earn-in"><span>Put in</span><input type="range" min="5" max="50000" step="5" value={amt} onChange={e => setAmt(Number(e.target.value))} aria-label="Amount for the combo" data-testid="combo-amt" /><b>${amt.toLocaleString('en-US')}</b></label>
    <p className="phb-combo-big"><b key={amt}>{c.apy.toFixed(1)}% APY</b><span>≈ {m(c.day)} a day · {m(c.month)} a month · {m(c.year)} a year</span></p>
    <ol>{c.legs.map((l, i) => <li key={l.role} style={{ '--i': i }}><em>{l.role} · {Math.round(l.w * 100)}%</em><span><b>{l.r.sym}</b><small>{l.r.proto} · TVL {usd(l.r.tvl)} · {l.risk}</small></span>
      <strong className="m-num">{apyTxt(l.r.apy)}</strong><button type="button" className={`m-btn m-go ${leg === l.role ? 'active' : ''}`} aria-expanded={leg === l.role} onClick={() => setLeg(x => (x === l.role ? null : l.role))} data-tip={`Put this leg to work right here — your wallet signs`} data-testid={`combo-go-${l.role}`}>💸</button></li>)}</ol>
    {leg ? <MoneyDesk key={leg} job={JOB_OF[c.legs.find(l => l.role === leg)?.r.kind] || 'lend'} focus={c.legs.find(l => l.role === leg)?.r} title={`${leg} LEG`} compact /> : null}
  </div>;
}
// 💸 the combo, alive: the split as a stacked bar (each leg's weight, its own colour) + the money it would have earned since you opened the
// hall, ticking every second at your amount and today's blended APY (true math, before gas)
const LEG_C = { CASH: '#6ad7ff', SOL: '#b388ff', FEES: '#45e486' };
function ComboLive({ c, amt }) {
  const [t0] = useState(() => Date.now()); const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000); return () => clearInterval(t); }, []);
  const earned = (amt * c.apy / 100) * ((now - t0) / 1000) / (365 * 24 * 3600);
  return <div className="phb-clive" data-testid="combo-live">
    <div className="phb-cbar" aria-hidden="true">{c.legs.map((l, i) => <s key={l.role} style={{ '--w': l.w, '--c': LEG_C[l.role] || '#ffd36b', '--i': i }} />)}</div>
    <span className="phb-ctick" data-tip="What your amount would have earned since you opened the hall, at today's blended APY"><em>EARNED WHILE YOU LOOK</em><b className="m-num">+${earned.toFixed(earned < 0.01 ? 6 : 4)}</b></span>
  </div>;
}

export function PoolHub({ pools, blocks = [], onLink, start = 'all' }) {
  const [lens, setLens] = useState(start); const [sort, setSort] = useState('tvl'); const [q, setQ] = useState(''); const [qq, setQQ] = useState('');
  useEffect(() => { const t = setTimeout(() => setQQ(q), 250); return () => clearTimeout(t); }, [q]);
  const rows = useMemo(() => poolRows(pools?.pools, lens, sort, qq).slice(0, 60), [pools, lens, sort, qq]);
  const tvl = useMemo(() => (pools?.pools || []).reduce((a, r) => a + (r.tvl || 0), 0), [pools]);
  if (!pools) return <div className="phb phb-load" aria-live="polite"><i /><i /><i /><small>reading every pool…</small></div>;
  return <div className="phb" data-testid="pool-hub"><CatCombo pools={pools} />
    <header className="phb-head"><span className="phb-big"><em>TRACKED TVL</em><b className="m-num" key={Math.round(tvl / 1e6)}>{usd(tvl)}</b></span>
      <StakeSeg />
      <span className="phb-kinds">{Object.entries(pools.kinds || {}).filter(([, n]) => n).map(([k, n]) => <i key={k} style={{ '--kc': KIND_COLOR[k] }} data-tip={`${n} ${POOL_KIND[k] || k} pools on Solana`}><b>{n}</b>{k.toUpperCase()}</i>)}</span></header>
    <div className="phb-ctl">
      <div className="m-seg phb-lens" role="tablist" aria-label="Pool kind">{LENS.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`phb-lens-${k}`}>{w}</button>)}</div>
      <div className="m-seg" role="tablist" aria-label="Sort">{SORT.map(([k, w]) => <button key={k} type="button" role="tab" aria-selected={sort === k} className={sort === k ? 'active' : ''} onClick={() => setSort(k)} data-testid={`phb-sort-${k}`}>{w}</button>)}</div>
      <input className="m-input phb-q" value={q} onChange={e => setQ(e.target.value)} placeholder="SOL, JitoSOL, USDC…" aria-label="Search pools" data-testid="phb-q" /></div>
    {rows.length ? <ol className="phb-list">{rows.map((r, i) => <PoolRow key={r.id} r={r} i={i} blocks={blocks} onLink={onLink} />)}</ol> : <FamEmpty art="search" title="NO POOL MATCHES" note="Try another coin, or clear the kind / search filter." />}
  </div>;
}
