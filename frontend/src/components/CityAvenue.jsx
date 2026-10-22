import React, { Suspense, lazy, useEffect, useState } from 'react';
import { useMarket } from '../hooks/useMarket';
import { openWarRoom } from './WarRoomHost';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { PLACES, usd } from '../lib/cityPlan';
import { apiUrl } from '../lib/api';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import '../styles/cityAvenue.css';

// 🛣 FEELESS AVENUE (owner, 2026-10-22: "implement the site's best tabs and features in Fee City with a pop-out of vitals and quick tools to
// buy … like a Pump Radar building that shows all of Pump Radar … people go to Familia for the one-stop shop in web3"). Every building on the
// Avenue pops out the REAL tool, not a link: Pump Radar (a drawn scope + one-tap trade), the $FEE Bank (fee-free buys), and the site's own
// Runners / Watchlist / Rep / FeeCat / Fuel / FEEd panels, loaded only when you walk in. Trades open the coin's war room — the wallet signs.
const RunnersPanel = lazy(() => import('./RunnersPanel').then(m => ({ default: m.RunnersPanel })));
const WatchlistDashboard = lazy(() => import('./command/CreatorProfile').then(m => ({ default: m.WatchlistDashboard })));
const RepTools = lazy(() => import('./RepTools').then(m => ({ default: m.RepTools })));
const FeeCatProfile = lazy(() => import('./command/FeeCatProfile').then(m => ({ default: m.FeeCatProfile })));
const GetGas = lazy(() => import('./command/TradeDesk').then(m => ({ default: m.GetGas })));
const FeedPanel = lazy(() => import('./command/FeedX').then(m => ({ default: m.FeedPanel })));
const NightVault = lazy(() => import('./NightVault').then(m => ({ default: m.NightVault })));

export const AVENUE_LENSES = PLACES.filter(p => p.tool).map(p => p.lens);
const num = v => { const n = Number(v); return Number.isFinite(n) ? n : null; };
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(1)}%`);

// pure: how hot a 5-minute move is, 0 … 1 (−20 % cold → +40 % on fire)
export const heatOf = m5 => Math.max(0, Math.min(1, ((num(m5) ?? 0) + 20) / 60));
// pure: the Pump board's vitals — how many are moving up now, the average 5m move, the hour's volume, the top mover
export function pumpVitals(pairs) {
  const ps = (pairs || []).filter(p => p?.baseToken?.address); const m5 = ps.map(p => num(p.priceChange?.m5)).filter(v => v != null);
  const top = ps.reduce((b, p) => ((num(p.priceChange?.m5) ?? -Infinity) > (num(b?.priceChange?.m5) ?? -Infinity) ? p : b), null);
  return { n: ps.length, up: m5.filter(v => v > 0).length, avg5m: m5.length ? m5.reduce((s, v) => s + v, 0) / m5.length : null,
    vol1h: ps.reduce((s, p) => s + (num(p.volume?.h1) || 0), 0), top: top ? { sym: top.baseToken.symbol, m5: num(top.priceChange?.m5) } : null };
}
// pure: a coin's blip on the scope — the #1 coin sits nearest the centre, hotter = bigger; angles spread evenly with a fixed twist per coin
export function blipOf(p, i, n) {
  const a = (i / Math.max(1, n)) * Math.PI * 2 + ((String(p?.baseToken?.address || '').charCodeAt(3) || 0) % 7) * 0.09;
  const rr = 24 + (i / Math.max(1, n - 1 || 1)) * 70; const h = heatOf(p?.priceChange?.m5);
  return { x: 110 + Math.cos(a) * rr, y: 110 + Math.sin(a) * rr, r: 3.5 + h * 5, up: (num(p?.priceChange?.m5) ?? 0) >= 0 };
}
// pure: the $FEE family of coins from /assets → a row each (price, 24h, cap, liquidity) + its pool for the war room
export function bankRows(data) {
  return (data?.assets || data?.items || []).filter(a => a?.pair).map(a => ({ id: a.id || a.symbol, sym: a.pair.baseToken?.symbol || a.symbol || a.id, price: num(a.pair.priceUsd),
    ch: num(a.pair.priceChange?.h24), mc: num(a.pair.marketCap ?? a.pair.fdv), liq: num(a.pair.liquidity?.usd), vol: num(a.pair.volume?.h24), pair: a.pair }));
}

function Meter({ label, value, fill, tone, tip, i }) {
  return <span className={`av-meter ${tone || ''}`} style={{ '--i': i }} data-tip={tip}><em>{label}</em><b className="m-num" key={value}>{value}</b>
    <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, fill || 0))})` }} /></u></span>;
}
const trade = p => openWarRoom(p);

// 📡 PUMP RADAR — the Pump board as a drawn scope (blips = coins, #1 nearest the centre, size = heat) + the ranked list with one-tap trade
function PumpRadar() {
  const { data, loading } = useMarket('/feed?kind=trending&chain=solana&page=1&scope=pump', 15000);
  const coins = (data?.pairs || []).filter(p => p.chainId === 'solana' && p.baseToken?.address).slice(0, 12);
  const v = pumpVitals(coins);
  return <div className="av-radar" data-testid="av-pumpradar">
    <div className="av-vitals">
      <Meter i={0} label="MOVING UP NOW" value={`${v.up}/${v.n}`} fill={v.n ? v.up / v.n : 0} tone={v.up >= v.n / 2 ? 'is-up' : 'is-down'} tip="Coins on the Pump board green over the last 5 minutes" />
      <Meter i={1} label="AVG 5M" value={pct(v.avg5m)} fill={heatOf(v.avg5m)} tone={(v.avg5m ?? 0) >= 0 ? 'is-up' : 'is-down'} tip="The board's average 5-minute move" />
      <Meter i={2} label="1H VOLUME" value={usd(v.vol1h)} fill={Math.log10(1 + v.vol1h) / 8} tip="What traded across these coins in the last hour" />
      <Meter i={3} label="TOP MOVER" value={v.top ? `$${v.top.sym} ${pct(v.top.m5)}` : '—'} fill={heatOf(v.top?.m5)} tone="is-up" tip="The hottest 5-minute move on the board" />
    </div>
    <div className="av-radar-grid">
      <svg className="av-scope" viewBox="0 0 220 220" role="img" aria-label="Pump radar scope">
        {[32, 62, 94].map(r => <circle key={r} cx="110" cy="110" r={r} className="av-ring" />)}
        <path d="M110 14 V206 M14 110 H206" className="av-cross" />
        <g className="av-sweep"><path d="M110 110 L110 14 A96 96 0 0 1 193 62 Z" /></g>
        {coins.map((p, i) => { const b = blipOf(p, i, coins.length); return <g key={p.pairAddress} className={`av-blip ${b.up ? 'up' : 'down'}`} style={{ '--i': i }} role="button" tabIndex={0}
          onClick={() => trade(p)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); trade(p); } }} aria-label={`Trade ${p.baseToken.symbol}`} data-tip={`$${p.baseToken.symbol} · 5m ${pct(num(p.priceChange?.m5))} — tap to open its war room`}>
          <circle cx={b.x} cy={b.y} r="15" className="av-hit" /><circle cx={b.x} cy={b.y} r={b.r} /><text x={b.x} y={b.y - b.r - 3}>{p.baseToken.symbol.slice(0, 6)}</text></g>; })}
      </svg>
      <ol className="av-list">
        {loading && !coins.length ? <li className="m-dim">Reading the Pump board…</li> : null}
        {coins.map((p, i) => { const m5 = num(p.priceChange?.m5); return <li key={p.pairAddress} style={{ '--i': i }}>
          <em>{i + 1}</em><TokenAvatar pair={p} size={26} />
          <span className="av-sym"><b>${p.baseToken.symbol}</b><small>MC {usd(p.marketCap ?? p.fdv)} · 1h {usd(p.volume?.h1)}</small></span>
          <span className={`av-heat ${m5 != null && m5 < 0 ? 'down' : 'up'}`}><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, heatOf(m5))})` }} /></u><b className="m-num">{pct(m5)}</b></span>
          <button type="button" className="m-btn m-go" onClick={() => trade(p)} data-tip="Open its war room — chart, tape, Quick trade; your wallet signs" data-testid={`av-trade-${p.baseToken.address}`}>⚡ Trade</button></li>; })}
        {!loading && !coins.length ? <li className="m-dim">No Pump coins pass the quality gates right now.</li> : null}
      </ol>
    </div>
  </div>;
}

// 🏦 THE $FEE BANK — $FEE · rFEE · FEECAT: each a drawn coin, live price / 24h / cap / liquidity; buying them is the one fee-free trade
function FeeBank() {
  const { data, loading } = useMarket('/assets', 300000);
  const rows = bankRows(data);
  return <div className="av-bank" data-testid="av-feebank">
    <p className="av-lede"><b>0% FEELESS fee</b> on buys of $FEE, rFEE and FEECAT — the only fee-free trades on FEELESS. The vault pays out to holders; your wallet signs.</p>
    <div className="av-coins">{loading && !rows.length ? <p className="m-dim">Reading the vault…</p> : null}
      {rows.map((r, i) => <article key={r.id} className="av-coin m-card" style={{ '--i': i }} data-testid={`av-coin-${r.id}`}>
        <svg viewBox="0 0 64 64" aria-hidden="true" className="av-coinart"><circle cx="32" cy="32" r="29" /><circle cx="32" cy="32" r="23" className="in" /><text x="32" y="37">{String(r.sym).slice(0, 6)}</text></svg>
        <header><b>${r.sym}</b><span className={`m-num ${(r.ch ?? 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(r.ch)}</span></header>
        <strong className="m-num" key={r.price}>{r.price == null ? '—' : r.price < 0.01 ? `$${r.price.toPrecision(3)}` : `$${r.price.toFixed(4)}`}</strong>
        <Meter i={i} label="MARKET CAP" value={usd(r.mc)} fill={Math.log10(1 + (r.mc || 0)) / 9} tip="Market cap (DexScreener, or Jupiter while on the curve)" />
        <Meter i={i + 1} label="LIQUIDITY" value={usd(r.liq)} fill={Math.log10(1 + (r.liq || 0)) / 7} tip="Pool liquidity — how much you can buy without moving it far" />
        <button type="button" className="m-btn m-go" onClick={() => trade(r.pair)} data-tip={`Open $${r.sym}'s war room — buys are fee-free; your wallet signs`} data-testid={`av-buy-${r.id}`}>⚡ Buy fee-free</button>
      </article>)}</div>
  </div>;
}

// 📈 THE TRADE CENTER — the agents' REAL card, live: everyone sees the record (seats, green, average %, by model — no coins, nobody front-runs
// its exits); the creator / staff also see every seat with the model holding it and one tap to its war room. One read every 15 s while open.
export function useTradeCenter() {
  const { wallet } = useWallet() || {}; const a = wallet?.address || ''; const [d, setD] = useState(null);
  useEffect(() => { let on = true; const s = a ? readChatSession(a) : '';
    const load = () => fetch(apiUrl(`/api/reputation/familia/trade-center${a && s ? `?address=${a}&session=${encodeURIComponent(s)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 15000); return () => { on = false; clearInterval(t); }; }, [a]);
  return d;
}
function TradeCenter() {
  const d = useTradeCenter();
  if (!d) return <p className="m-dim">Reading the desk…</p>;
  return <div className="av-tc" data-testid="av-trades">
    <div className="av-vitals">
      <Meter i={0} label="SEATS LIVE" value={String(d.open)} fill={d.open / 6} tip="Real-money seats the desk holds right now" />
      <Meter i={1} label="GREEN NOW" value={`${d.green}/${d.open}`} fill={d.open ? d.green / d.open : 0} tone={d.green >= d.open / 2 ? 'is-up' : 'is-down'} tip="Seats up from their entry, live" />
      <Meter i={2} label="AVG LIVE" value={pct(d.avgPct)} fill={heatOf(d.avgPct)} tone={(d.avgPct ?? 0) >= 0 ? 'is-up' : 'is-down'} tip="Average live % across the seats (fees never in P&L)" />
      <Meter i={3} label="BY MODEL" value={Object.entries(d.by || {}).map(([k, v]) => `${k} ${v.n}`).join(' · ') || '—'} fill={Object.keys(d.by || {}).length / 4} tip="Who holds the seats: G4 · OSSY · the agents" />
    </div>
    <div className="av-models">{Object.entries(d.by || {}).map(([k, v], i) => <span key={k} className={`av-model ${(v.avgPct ?? 0) >= 0 ? 'up' : 'down'}`} style={{ '--i': i }} data-tip={`${k}: ${v.n} seat(s), average ${pct(v.avgPct)} live`}><b>{k}</b><em className="m-num">{pct(v.avgPct)}</em></span>)}</div>
    {d.rows ? <ol className="av-list">{d.rows.map((r, i) => <li key={`${r.pair}-${i}`} style={{ '--i': i }}>
      <em>{i + 1}</em><span className="av-who">{r.who}</span>
      <span className="av-sym"><b>${r.symbol}</b><small>{[r.state, r.action, r.why].filter(Boolean).join(' · ') || 'holding'}</small></span>
      <span className={`av-heat ${(r.pct ?? 0) < 0 ? 'down' : 'up'}`}><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, heatOf(r.pct))})` }} /></u><b className="m-num">{pct(r.pct)}</b></span>
      <button type="button" className="m-btn" onClick={() => trade({ chainId: 'solana', pairAddress: r.pair, baseToken: { symbol: r.symbol } })} data-tip="Open its war room — chart, tape, the desk's fills" data-testid={`av-seat-${i}`}>📈 Open</button></li>)}</ol>
      : <p className="av-lede">Coins stay private so nobody front-runs the desk's exits — the creator sees every seat here.</p>}
  </div>;
}

const BODY = {
  trades: () => <TradeCenter />,
  pumpradar: () => <PumpRadar />, feebank: () => <FeeBank />, runners: () => <RunnersPanel />, watch: () => <WatchlistDashboard />, rep: () => <RepTools />,
  feecat: () => <FeeCatProfile catId="leader" />, gas: () => <GetGas />, sleep: () => <NightVault />,
  feedx: () => <><div className="av-tools"><button type="button" className="m-btn" onClick={() => window.dispatchEvent(new Event('feeless:feed-pop'))} data-tip="Float FEEd over any page — keep reading while you trade" data-testid="av-feed-pop">⤢ Pop out FEEd</button></div><FeedPanel /></>,
};

// one Avenue room: the tool itself + its full page
export function AvenueRoom({ lens }) {
  const p = PLACES.find(x => x.lens === lens && x.tool); const Body = BODY[lens];
  if (!p || !Body) return null;
  return <div className={`av-room k-${p.key}`} style={{ '--pc': p.color }} data-testid={`avenue-${lens}`}>
    <Suspense fallback={<div className="av-load" aria-busy="true"><i /><i /><i /></div>}><Body /></Suspense>
    {p.page ? <a className="m-btn av-page" href={p.page} data-tip={`${p.name}'s full page on FEELESS`} data-testid="av-page">Open the full page ↗</a> : null}
  </div>;
}
