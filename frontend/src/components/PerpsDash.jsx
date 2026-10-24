import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useGlide } from '../lib/useGlide';
import { useLivePrice } from '../lib/livePriceHub';
import { cash } from '../lib/earnStake';
import { RealPerps } from './RealPerps';
import { PaperPerps } from './PaperPerps';
import '../styles/perpsDash.css';

// 📉 FEELESS PERPS — the trading dash in the Perps building's own PINK meta (owner, 2026-10-23: "a perps TRADING DASH, quick trades, litty …
// live realtime vitals, match the pink, don't go stale"). Everything on it is live:
// · the market strip — SOL · ETH · BTC marks tick every 2 s (the shared live price hub), flash with the move, draw their own tick trail, and say
//   how many seconds since the last tick;
// · the vitals of the picked market — WHO'S CROWDED (Jupiter's long vs short pool utilisation, a tug-of-war), BORROW / HR (long vs short),
//   the FUNDING needle, OPEN INTEREST counting, the 1-MINUTE MOVE from the real ticks;
// · the LIVE chart of the market's deepest Solana pool with YOUR lines (the ticket's ☠ liquidation price moves as you change leverage; open
//   positions draw entry + liq) beside the Jupiter ticket (your wallet signs). 🧪 PRACTICE = the paper desk, one tap away.
// · ⏱ KALSHI — the US-legal 15-minute up / down odds on the same coin (read-only until DFlow's production key; CLAUDE.md › P0 #0).
const PriceChart = lazy(() => import('./terminal/PriceChart').then(m => ({ default: m.PriceChart })));
export const PERP_POOLS = {   // the deepest USDC pool on Solana per market (DexScreener, 2026-10-23) — the chart's candles + the live tick; Jupiter's oracle marks the trade
  SOL: { pairAddress: 'Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE', mint: 'So11111111111111111111111111111111111111112', symbol: 'SOL' },
  ETH: { pairAddress: 'AU971DrPyhhrpRnmEBp5pDTWL2ny7nofb5vYBjDJkR2E', mint: '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs', symbol: 'WETH' },
  BTC: { pairAddress: 'HxA6SKW5qA4o12fjVgTpXdq2YnZ5Zv1s7SB4FFomsyLM', mint: 'cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij', symbol: 'cbBTC' },
};
const MKTS = Object.keys(PERP_POOLS);
const IVS = [['1m', '1M'], ['5m', '5M'], ['15m', '15M']];
const TRAIL = 90;   // ticks kept per market (≈ 3 min at 2 s)
const px = v => (v == null ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : `$${Number(v).toFixed(2)}`);
const pc = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}%`);
const big = v => (!(v > 0) ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : `$${(v / 1e6).toFixed(1)}M`);

// pure: the lines the chart draws for this market — the ticket's preview (☠ wiped at) + every open position's entry / liquidation
export function perpLines(asset, ticket, positions) {
  const out = [];
  if (ticket?.liq > 0) out.push({ px: ticket.liq, title: `☠ ${ticket.side.toUpperCase()} ${ticket.lev}× wiped`, color: '#ff5d73' });
  (positions || []).filter(p => p.asset === asset).forEach(p => {
    if (p.entry > 0) out.push({ px: p.entry, title: `${p.side === 'long' ? '▲' : '▼'} ${p.lev}× entry`, color: p.side === 'long' ? '#45e486' : '#ff9fd2' });
    if (p.liq > 0) out.push({ px: p.liq, title: `☠ ${p.lev}× liq`, color: '#ff5d73' });
  });
  return out;
}
// pure: the % move over the last `sec` seconds of real ticks [{t, v}] (null until the window has two ticks)
export function moveOver(ticks, sec, now) {
  const w = (ticks || []).filter(x => now - x.t <= sec * 1000); if (w.length < 2) return null;
  return (w[w.length - 1].v / w[0].v - 1) * 100;
}
// pure: who's crowded — Jupiter's long vs short pool utilisation → the long share of the tug (0..1) + the crowded side
export function crowd(pool) {
  const l = Number(pool?.longUtilizationPercent); const s = Number(pool?.shortUtilizationPercent);
  if (!(l >= 0) || !(s >= 0) || l + s <= 0) return null;
  return { long: l, short: s, share: l / (l + s), side: l > s ? 'LONGS' : s > l ? 'SHORTS' : 'EVEN' };
}

function useNow(ms = 1000) { const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), ms); return () => clearInterval(t); }, [ms]); return n; }

// one market tile: its own live tick (2 s), a flash on each move, the real tick trail, seconds since the last tick
function MktTile({ a, i, on, board, onPick, onTick }) {
  const pl = PERP_POOLS[a];
  const lp = useLivePrice(useMemo(() => ({ chainId: 'solana', baseToken: { address: pl.mint }, priceUsd: board?.mark, priceChange: { h24: board?.ch24 } }), [pl.mint, board?.mark, board?.ch24]));
  const v = lp.usd; const g = useGlide(v ?? null, 600); const trail = useRef([]); const [dir, setDir] = useState(''); const [at, setAt] = useState(0); const now = useNow();
  useEffect(() => { if (!(v > 0)) return undefined; const last = trail.current[trail.current.length - 1];
    if (!last || last.v !== v) { trail.current = [...trail.current, { t: Date.now(), v }].slice(-TRAIL); setAt(Date.now()); onTick?.(a, trail.current); }
    if (last && last.v !== v) { setDir(v > last.v ? 'is-up' : 'is-dn'); const t = setTimeout(() => setDir(''), 700); return () => clearTimeout(t); } return undefined; }, [v, a, onTick]);
  const tr = trail.current; const lo = Math.min(...tr.map(x => x.v)); const hi = Math.max(...tr.map(x => x.v)); const span = hi - lo || 1;
  const path = tr.length > 1 ? tr.map((x, k) => `${(k / (tr.length - 1)) * 100},${28 - ((x.v - lo) / span) * 24}`).join(' ') : '';
  const ch = lp.change24h; const age = at ? Math.max(0, Math.round((now - at) / 1000)) : null;
  return <button type="button" role="radio" aria-checked={on} className={`pd-mkt ${on ? 'is-on' : ''} ${dir}`} style={{ '--i': i }} onClick={() => onPick(a)}
    data-tip={`${a}-PERP on Jupiter · live every 2 s · funding ${board?.fundApr != null ? `${board.fundApr > 0 ? '+' : ''}${board.fundApr}% a year` : '…'}`} data-testid={`pd-m-${a}`}>
    <span className="pd-sym"><b>{a}</b><small>-PERP</small></span>
    <b className={`pd-mark m-num ${dir}`} key={v}>{px(g)}</b>
    <svg className="pd-trail" viewBox="0 0 100 30" preserveAspectRatio="none" aria-hidden="true">{path ? <polyline points={path} className={tr[tr.length - 1].v >= tr[0].v ? 'is-up' : 'is-dn'} /> : null}</svg>
    <span className="pd-foot"><small className={`m-num ${(ch ?? 0) < 0 ? 'is-dn' : 'is-up'}`}>{pc(ch)} 24h</small><small className="pd-age"><i className="pd-beat" key={at} />{age == null ? 'syncing' : `${age}s`}</small></span>
  </button>;
}

function Vital({ label, tip, children, cls = '', i = 0 }) {
  return <div className={`pd-vit ${cls}`} style={{ '--i': i }} data-tip={tip}><em>{label}</em>{children}</div>;
}

// ⏱ KALSHI — US-legal (CFTC-regulated) odds on the picked coin: the 15-minute "up?" window (target vs the live mark, the odds as a split,
// the window's own countdown, what $1 pays either way) + the 5 pm strike nearest the mark. Read-only until DFlow's key lands (no dead button).
export function kalshiRead(k, mark, now) {
  const m = k?.m15; if (!m || (m.yes == null && m.no == null)) return null;
  const end = Date.parse(m.closes || ''); const left = Number.isFinite(end) ? Math.max(0, Math.round((end - now) / 1000)) : null;
  const up = m.yes != null ? m.yes : 1 - m.no;
  return { up, left, frac: left == null ? 0 : Math.min(1, left / 900), above: m.target > 0 && mark > 0 ? mark - m.target : null, target: m.target,
    payUp: m.yes > 0 ? 1 / m.yes : null, payDn: m.no > 0 ? 1 / m.no : null, day: k?.day || null };
}
const dayWord = iso => { const d = new Date(iso); return Number.isFinite(d.getTime()) ? d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric' }).toUpperCase() : 'CLOSE'; };
function KalshiOdds({ asset, k, mark, now }) {
  const r = kalshiRead(k, mark, now); const g = useGlide(r ? Math.round(r.up * 1000) / 10 : 50, 600);
  if (!r) return null;
  const mm = r.left == null ? '—' : `${Math.floor(r.left / 60)}:${String(r.left % 60).padStart(2, '0')}`;
  return <div className={`pd-odds ${r.up >= 0.5 ? 'is-up' : 'is-dn'}`} data-testid="pd-odds" data-tip={`Kalshi (CFTC-regulated, US-legal): "${asset} price up in the next 15 mins?" — YES pays $1 if ${asset} ends the window at or above the target`}>
    <span className="pd-oh"><em>⏱ KALSHI · {asset} UP IN 15 MIN?</em><b className="m-num">{g.toFixed(0)}%</b><small>US · CFTC-REGULATED</small></span>
    <div className="pd-osplit" aria-hidden="true"><s className="is-up" style={{ transform: `scaleX(${g / 100})` }} /><s className="is-dn" style={{ transform: `scaleX(${1 - g / 100})` }} /></div>
    <span className="pd-ostat"><em>TARGET</em><b className="m-num">{px(r.target)}</b><small className={`m-num ${(r.above ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{r.above == null ? '' : `live ${r.above >= 0 ? '▲ +' : '▼ −'}${px(Math.abs(r.above))}`}</small></span>
    <span className="pd-ostat pd-oclock"><em>CLOSES IN</em><b className="m-num">{mm}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${r.frac})` }} /></u></span>
    <span className="pd-ostat"><em>$1 PAYS</em><b className="m-num is-up">{r.payUp ? `$${r.payUp.toFixed(2)}` : '—'} <i>UP</i></b><b className="m-num is-dn">{r.payDn ? `$${r.payDn.toFixed(2)}` : '—'} <i>DOWN</i></b></span>
    {r.day ? <span className="pd-ostat"><em>{dayWord(r.day.closes)} · ABOVE {px(r.day.strike)}</em><b className="m-num">{Math.round(r.day.yes * 100)}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${r.day.yes})` }} /></u></span> : null}
  </div>;
}

export function PerpsDash({ devAddress = '' }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl('/api/reputation/familia/perps')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setRows(x.markets || [])).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 15000); return () => { on = false; clearInterval(t); }; }, []);
  const by = useMemo(() => Object.fromEntries(rows.map(r => [r.coin, r])), [rows]);
  const [ks, setKs] = useState({});
  useEffect(() => { let on = true; const load = () => fetch(apiUrl('/api/reputation/familia/kalshi')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setKs(x.coins || {})).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 10000); return () => { on = false; clearInterval(t); }; }, []);
  const [ticks, setTicks] = useState({}); const onTick = useMemo(() => (a, tr) => setTicks(t => ({ ...t, [a]: tr })), []);
  const marks = useMemo(() => Object.fromEntries(MKTS.map(a => [a, (ticks[a] || []).slice(-1)[0]?.v || by[a]?.mark])), [by, ticks]);
  const [asset, setAsset] = useState('SOL'); const [iv, setIv] = useState('1m'); const [tab, setTab] = useState('live');
  const [ticket, setTicket] = useState(null); const [pos, setPos] = useState([]); const [pools, setPools] = useState(null);
  const now = useNow();
  const total = pos.reduce((s, x) => s + (x.pnl || 0), 0); const tot = useGlide(Math.round(total * 100) / 100);
  const pool = PERP_POOLS[asset]; const r = by[asset]; const jp = pools?.[asset]; const cr = crowd(jp);
  const m1 = moveOver(ticks[asset], 60, now); const m3 = moveOver(ticks[asset], 180, now);
  const oi = useGlide(r?.oiUsd || 0, 900); const tug = useGlide(cr ? cr.share * 100 : 50, 700);
  const fund = Number(r?.fundApr); const needle = Number.isFinite(fund) ? Math.max(-80, Math.min(80, fund * 4)) : 0;
  const bl = Number(jp?.longBorrowRatePercent); const bs = Number(jp?.shortBorrowRatePercent); const bmax = Math.max(bl || 0, bs || 0, 0.0001);
  const pair = useMemo(() => ({ chainId: 'solana', pairAddress: pool.pairAddress, baseToken: { address: pool.mint, symbol: pool.symbol }, quoteToken: { symbol: 'USDC' }, priceUsd: marks[asset] }), [pool, marks, asset]);
  const fuse = useMemo(() => ({ lines: perpLines(asset, ticket, pos) }), [asset, ticket, pos]);
  return <section className="pd" data-testid="perps-dash">
    <header className="pd-head">
      <span className="pd-title"><em>JUPITER · YOUR WALLET SIGNS · UP TO 100×</em><b>FEELESS <i>PERPS</i></b></span>
      <span className="pd-seg m-seg" role="tablist" aria-label="Desk">{[['live', '⚡ LIVE', 'Real perps on Jupiter — your wallet signs every open and close'], ['practice', '🧪 PRACTICE', 'Paper perps at the real mark — no money moves']].map(([k, l, tip]) =>
        <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-tip={tip} data-testid={`pd-tab-${k}`}>{l}</button>)}</span>
      <span className={`pd-pnl ${total > 0 ? 'is-up' : total < 0 ? 'is-dn' : ''}`} data-tip="Open P&L across your Jupiter positions, before fees (fees sit on each position)"><em>OPEN P&L</em>
        <b className="m-num">{pos.length ? `${tot < 0 ? '−' : '+'}${cash(Math.abs(tot))}` : '$0.00'}</b><small>{pos.length ? `${pos.length} live` : 'flat'}</small></span>
    </header>
    <div className="pd-mkts" role="radiogroup" aria-label="Market">{MKTS.map((a, i) => <MktTile key={a} a={a} i={i} on={a === asset} board={by[a]} onPick={setAsset} onTick={onTick} />)}</div>
    <div className="pd-vits" data-testid="pd-vits">
      <Vital i={0} cls="pd-tugv" label="WHO'S CROWDED" tip={cr ? `Jupiter's ${asset} pool: longs use ${cr.long.toFixed(1)}%, shorts ${cr.short.toFixed(1)}% of what they can borrow — the crowded side pays more and gets squeezed first` : 'Reading Jupiter’s pool…'}>
        <div className="pd-tug" aria-hidden="true"><s className="is-l" style={{ transform: `scaleX(${tug / 100})` }} /><s className="is-s" style={{ transform: `scaleX(${1 - tug / 100})` }} /><i style={{ transform: `translateX(${tug - 50}%)` }} /></div>
        <span className="pd-tugn"><b className="is-up m-num">▲ {cr ? `${cr.long.toFixed(1)}%` : '—'}</b><small>{cr ? `${cr.side} CROWDED` : '…'}</small><b className="is-dn m-num">{cr ? `${cr.short.toFixed(1)}%` : '—'} ▼</b></span></Vital>
      <Vital i={1} label="BORROW / HR" tip="What Jupiter charges each side per hour to hold the position (on its size)">
        <span className="pd-bars"><span><u><s className="is-up" style={{ transform: `scaleX(${(bl || 0) / bmax})` }} /></u><small className="m-num">▲ {Number.isFinite(bl) ? `${bl.toFixed(4)}%` : '—'}</small></span>
          <span><u><s className="is-dn" style={{ transform: `scaleX(${(bs || 0) / bmax})` }} /></u><small className="m-num">▼ {Number.isFinite(bs) ? `${bs.toFixed(4)}%` : '—'}</small></span></span></Vital>
      <Vital i={2} label="FUNDING" tip="Funding as a yearly rate on the global board — positive: longs pay shorts">
        <span className="pd-gauge" aria-hidden="true"><svg viewBox="0 0 60 34"><path d="M5 30 A25 25 0 0 1 55 30" className="pd-arc" /></svg><i style={{ transform: `rotate(${needle}deg)` }} /></span>
        <b className={`m-num ${fund > 0 ? 'is-dn' : 'is-up'}`}>{Number.isFinite(fund) ? `${fund > 0 ? '+' : ''}${fund}%` : '—'}</b></Vital>
      <Vital i={3} label="OPEN INTEREST" tip="Open positions across the global board, in $"><b className="m-num pd-hot">{big(oi)}</b><small>{r?.vol24 ? `${big(r.vol24)} traded 24h` : ''}</small></Vital>
      <Vital i={4} cls={m1 == null ? '' : m1 >= 0 ? 'is-up' : 'is-dn'} label="1-MIN MOVE" tip="The move over the last 60 s of live ticks (3 min under it)">
        <b className="m-num pd-hot" key={Math.round((m1 || 0) * 1000)}>{pc(m1, 3)}</b><small className="m-num">3m {pc(m3, 3)}</small></Vital>
    </div>
    <KalshiOdds asset={asset} k={ks[asset]} mark={marks[asset]} now={now} />
    {tab === 'live' ? <div className="pd-grid">
      <div className="pd-chart" data-testid="pd-chart">
        <div className="pd-cbar"><span className="pd-cname"><b>{asset}<i>-PERP</i></b><small className="m-num">{px(marks[asset])}</small></span>
          <span className="m-seg pd-iv" role="radiogroup" aria-label="Candle size">{IVS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={iv === k} className={iv === k ? 'active' : ''} onClick={() => setIv(k)} data-tip={`${l} candles`} data-testid={`pd-iv-${k}`}>{l}</button>)}</span></div>
        <div className="pd-plot"><Suspense fallback={<p className="pd-dim">Loading the live chart…</p>}><PriceChart key={`${pool.pairAddress}-${iv}`} pair={pair} interval={iv} showVolume plain fuse={fuse} wallets={false} fee={false} /></Suspense></div>
      </div>
      <RealPerps asset={asset} onAsset={setAsset} marks={marks} devAddress={devAddress} onTicket={setTicket} onPositions={setPos} onPools={setPools} />
    </div> : <PaperPerps row={r} lev={ticket?.lev || 10} devAddress={devAddress} />}
  </section>;
}
