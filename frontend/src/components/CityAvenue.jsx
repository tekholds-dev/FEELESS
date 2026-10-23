import React, { Suspense, lazy, useEffect, useState } from 'react';
import { useMarket } from '../hooks/useMarket';
import { familiaTrade } from './FamiliaTrade';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { PLACES, usd } from '../lib/cityPlan';
import { apiUrl } from '../lib/api';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import '../styles/cityAvenue.css';

// 🛣 FEELESS AVENUE (owner, 2026-10-22: "implement the site's best tabs and features in Fee City with a pop-out of vitals and quick tools to
// buy … like a Pump Radar building that shows all of Pump Radar … people go to Familia for the one-stop shop in web3"). Every building on the
// Avenue pops out the REAL tool, not a link: Pump Radar (a drawn scope + one-tap trade), the $FEE Bank (fee-free buys), and the site's own
// Runners / Watchlist / Rep / FeeCat / Fuel / FEEd panels, loaded only when you walk in. Trades open INSIDE Familia (FamiliaTrade dock) — the wallet signs.
const RunnersPanel = lazy(() => import('./RunnersPanel').then(m => ({ default: m.RunnersPanel })));
const WatchlistDashboard = lazy(() => import('./command/CreatorProfile').then(m => ({ default: m.WatchlistDashboard })));
const RepTools = lazy(() => import('./RepTools').then(m => ({ default: m.RepTools })));
const FeeCatsPlatform = lazy(() => import('./command/FeeCatsPlatform'));
const FeeCatProfile = lazy(() => import('./command/FeeCatProfile').then(m => ({ default: m.FeeCatProfile })));
const FeeCatStage = lazy(() => import('./command/FeeCatStage').then(m => ({ default: m.FeeCatStage })));
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
// pure: the $FEE family of coins from /assets → a row each (price, 24h, cap, liquidity) + its pool for the trade dock
export function bankRows(data) {
  return (data?.assets || data?.items || []).filter(a => a?.pair).map(a => ({ id: a.id || a.symbol, sym: a.pair.baseToken?.symbol || a.symbol || a.id, price: num(a.pair.priceUsd),
    ch: num(a.pair.priceChange?.h24), mc: num(a.pair.marketCap ?? a.pair.fdv), liq: num(a.pair.liquidity?.usd), vol: num(a.pair.volume?.h24), pair: a.pair }));
}

function Meter({ label, value, fill, tone, tip, i }) {
  return <span className={`av-meter ${tone || ''}`} style={{ '--i': i }} data-tip={tip}><em>{label}</em><b className="m-num" key={value}>{value}</b>
    <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, fill || 0))})` }} /></u></span>;
}
const trade = p => familiaTrade(p);   // 🏙 trades open INSIDE Familia (the dock), never another page

// 📡 PUMP RADAR — the Pump board as a drawn scope (blips = coins, #1 nearest the centre, size = heat) + the ranked list with one-tap trade
function PumpRadar({ scope = 'pump' }) {
  const { data, loading } = useMarket(`/feed?kind=trending&chain=solana&page=1&scope=${scope}`, 15000);
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
          onClick={() => trade(p)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); trade(p); } }} aria-label={`Trade ${p.baseToken.symbol}`} data-tip={`$${p.baseToken.symbol} · 5m ${pct(num(p.priceChange?.m5))} — tap to trade it here`}>
          <circle cx={b.x} cy={b.y} r="15" className="av-hit" /><circle cx={b.x} cy={b.y} r={b.r} /><text x={b.x} y={b.y - b.r - 3}>{p.baseToken.symbol.slice(0, 6)}</text></g>; })}
      </svg>
      <ol className="av-list">
        {loading && !coins.length ? <li className="m-dim">Reading the Pump board…</li> : null}
        {coins.map((p, i) => { const m5 = num(p.priceChange?.m5); return <li key={p.pairAddress} style={{ '--i': i }}>
          <em>{i + 1}</em><TokenAvatar pair={p} size={26} />
          <span className="av-sym"><b>${p.baseToken.symbol}</b><small>MC {usd(p.marketCap ?? p.fdv)} · 1h {usd(p.volume?.h1)}</small></span>
          <span className={`av-heat ${m5 != null && m5 < 0 ? 'down' : 'up'}`}><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, heatOf(m5))})` }} /></u><b className="m-num">{pct(m5)}</b></span>
          <button type="button" className="m-btn m-go" onClick={() => trade(p)} data-tip="Trade it right here — chart + Quick trade slide over the room; your wallet signs" data-testid={`av-trade-${p.baseToken.address}`}>⚡ Trade</button></li>; })}
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
        <button type="button" className="m-btn m-go" onClick={() => trade(r.pair)} data-tip={`Buy $${r.sym} right here — fee-free; your wallet signs`} data-testid={`av-buy-${r.id}`}>⚡ Buy fee-free</button>
      </article>)}</div>
  </div>;
}

// 📈 THE TRADE CENTER — the agents' REAL card, live: everyone sees the record (seats, green, average %, by model — no coins, nobody front-runs
// its exits); the creator / staff also see every seat with the model holding it and one tap to its chart + Quick trade in the room. One read every 15 s while open.
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
      <button type="button" className="m-btn" onClick={() => trade({ chainId: 'solana', pairAddress: r.pair, baseToken: { symbol: r.symbol } })} data-tip="Its chart + Quick trade, right here in the room" data-testid={`av-seat-${i}`}>📈 Open</button></li>)}</ol>
      : <p className="av-lede">Coins stay private so nobody front-runs the desk's exits — the creator sees every seat here.</p>}
    {d.closed?.n ? <div className="av-closed" data-testid="av-closed"><em className="av-sub">REAL RECORD · LAST {d.closed.n} CLOSED LOTS (price only, fees apart)</em>
      <div className="av-models">{Object.entries(d.closed.by).map(([k, r], i) => <span key={k} className={`av-model ${r.median >= 0 ? 'up' : 'down'}`} style={{ '--i': i }} data-tip={`${k}: ${r.n} real trades, ${r.wonPct}% won, typical ${r.median}%`}>
        <b>{k}</b><em className="m-num">{r.wonPct}% won · {pct(r.median)}</em></span>)}</div>
      <ol className="av-list av-lots">{d.closed.last.map((r, i) => <li key={`${r.sym}-${r.at}-${i}`} style={{ '--i': i }}><span className="av-who">{r.who}</span>
        <span className="av-sym"><b>${r.sym}</b><small>{r.rule || 'closed'}</small></span><b className={`m-num ${r.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(r.pct)}</b></li>)}</ol></div> : null}
  </div>;
}

// ⚖ THE REP COURTHOUSE — the week's TOP CATCHES (the Rep engine's real record: wallets caught bundling / sniping / funding, launches each hit,
// blocklisted or not) with the vitals on top; tap a wallet → its cited case file. 🔎 Check anyone = the Rep tools.
export const courtVitals = d => { const t = d?.totals || {}; return [['CAUGHT 7D', t.caught], ['BLOCKLISTED', t.blocklisted], ['FUNDERS', t.funders], ['RUGS', t.rugs]]; };
function Courthouse() {
  const [tab, setTab] = useState('catches'); const [d, setD] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/rug-report?days=7')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {}); return () => { on = false; }; }, []);
  const top = (d?.caught || []).slice().sort((a, b) => (b.launches || 0) - (a.launches || 0)).slice(0, 10); const max = Math.max(1, ...top.map(x => x.launches || 0));
  const open = w => window.dispatchEvent(new CustomEvent('feeless:investigate', { detail: w }));   // the one case-file host (CaseFile.investigate)
  return <div className="av-court" data-testid="av-court">
    <div className="m-seg av-seg" role="tablist">{[['catches', '⚖ Top catches'], ['check', '🔎 Check anyone']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-tip={k === 'catches' ? "The week's worst wallets the Rep engine caught" : 'Scan any wallet or coin'}>{l}</button>)}</div>
    {tab === 'check' ? <RepTools /> : <>
      <div className="av-vitals">{courtVitals(d).map(([l, v], i) => <Meter key={l} i={i} label={l} value={v == null ? '—' : Number(v).toLocaleString('en-US')} fill={Math.log10(1 + (v || 0)) / 4} tone={l === 'RUGS' ? 'is-down' : 'is-up'} tip={`${l.toLowerCase()} in the last 7 days — from the Rep engine's own records`} />)}</div>
      <ol className="av-list av-catches">{!d ? <li className="m-dim">Reading the court record…</li> : null}
        {top.map((x, i) => <li key={x.wallet} style={{ '--i': i }}><em>{i + 1}</em>
          <span className="av-sym"><b>{x.wallet.slice(0, 4)}…{x.wallet.slice(-4)}</b><small>{(x.roles || []).join(' · ') || 'flagged'}{x.blocked ? ' · ⛔ blocklisted' : ''}</small></span>
          <span className="av-heat down"><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, (x.launches || 0) / max)})` }} /></u><b className="m-num">{x.launches} launches</b></span>
          <button type="button" className="m-btn" onClick={() => open(x.wallet)} data-tip="Open its case file — every launch it hit, who funded it, the evidence" data-testid={`av-case-${i}`}>🔎 Case</button></li>)}</ol></>}
  </div>;
}

// 🐱 FEECAT TOWER — the leader live (her vitals, lives, open trades) + YOUR cats: their vitals, create / launch a cat right here (trader or agent)
function CatTower() {
  const [tab, setTab] = useState('live');
  return <div className="av-court" data-testid="av-cats">
    <div className="m-seg av-seg" role="tablist">{[['live', '🐱 FeeCat live'], ['mine', '🧪 Your cats + create']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}
      data-tip={k === 'live' ? 'FeeCat right now: her nine lives, discipline, open trades' : 'Your cats with their vitals — create or launch one here (trader or agent)'} data-testid={`av-cats-${k}`}>{l}</button>)}</div>
    {tab === 'live' ? <><FeeCatStage /><FeeCatProfile catId="leader" /></> : <FeeCatsPlatform />}
  </div>;
}

// 📉 THE PERPS DESK — the perps US traders can legally use (Kraken Pro · Coinbase), priced live from a global reference board (mark, 24h,
// funding APR, open interest, max leverage) + one tap to the regulated venue. Leverage math on screen.
// 🇺🇸 US-legal venues only (owner, 2026-10-23): Kraken Pro (CFTC-regulated perps via Bitnomial) · Coinbase (perpetual-style futures, CFTC FCM).
// Drift / Hyperliquid / Jupiter Perps are gone — they block or don't clearly serve US traders. In-app orders on these = the owner's call (API + legal).
export const VENUE = { kraken: ['Kraken Pro', () => 'https://pro.kraken.com/'], coinbase: ['Coinbase', () => 'https://www.coinbase.com/derivatives'] };
function PerpsDesk() {
  const { data } = useMarketJson('/api/reputation/familia/perps', 60000); const rows = data?.markets || []; const [lev, setLev] = useState(10);
  const oi = rows.reduce((s2, r) => s2 + (r.oiUsd || 0), 0); const hot = rows.reduce((b, r) => (Math.abs(r.fundApr || 0) > Math.abs(b?.fundApr || 0) ? r : b), null);
  return <div className="av-court" data-testid="av-perps">
    <div className="av-vitals">
      <Meter i={0} label="MARKETS" value={String(rows.length)} fill={rows.length / 12} tip="The busiest perps markets by 24h volume" />
      <Meter i={1} label="OPEN INTEREST" value={usd(oi)} fill={Math.log10(1 + oi) / 11} tip="Open positions across these markets, in $" />
      <Meter i={2} label="HOTTEST FUNDING" value={hot ? `${hot.coin} ${hot.fundApr > 0 ? '+' : ''}${hot.fundApr}%` : '—'} fill={Math.min(1, Math.abs(hot?.fundApr || 0) / 100)} tone={(hot?.fundApr || 0) > 0 ? 'is-down' : 'is-up'} tip="Funding as a yearly rate — positive: longs pay shorts" />
      <Meter i={3} label={`LIQUIDATED AT ${lev}×`} value={`${(100 / lev).toFixed(1)}% move`} fill={1 / lev * 5} tone="is-down" tip="How far the price can go against you before the position is gone (before fees)" />
    </div>
    <label className="phb-earn-in av-lev"><span>Leverage</span><input type="range" min="1" max="50" value={lev} onChange={e => setLev(Number(e.target.value))} aria-label="Leverage" data-testid="av-lev" /><b>{lev}×</b></label>
    <ol className="av-list av-perps">{!rows.length ? <li className="m-dim">Reading the perps markets…</li> : null}
      {rows.map((r, i) => <li key={r.coin} style={{ '--i': i }}><em>{i + 1}</em>
        <span className="av-sym"><b>{r.coin}</b><small>${r.mark >= 100 ? r.mark.toLocaleString('en-US', { maximumFractionDigits: 0 }) : r.mark.toPrecision(4)} · OI {usd(r.oiUsd)} · up to {r.maxLev}×</small></span>
        <span className={`av-heat ${(r.ch24 ?? 0) < 0 ? 'down' : 'up'}`}><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(r.ch24 || 0) / 15))})` }} /></u><b className="m-num">{pct(r.ch24)} · f {r.fundApr > 0 ? '+' : ''}{r.fundApr}%</b></span>
        <span className="av-venues">{r.venues.map(v => <a key={v} className="m-btn" href={VENUE[v][1](r.coin)} target="_blank" rel="noopener noreferrer" data-tip={`Trade ${r.coin} perps on ${VENUE[v][0]} — your wallet signs there; their own region rules apply`}>{VENUE[v][0].split(' ')[0]} ↗</a>)}</span></li>)}</ol>
    <p className="av-lede">⚠ Leverage cuts both ways: at {lev}× a {(100 / lev).toFixed(1)}% move against you liquidates the position. FEELESS shows the market; each venue runs its own checks.</p>
  </div>;
}
function useMarketJson(url, every) {
  const [data, setData] = useState(null);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl(url)).then(r => (r.ok ? r.json() : null)).then(x => on && x && setData(x)).catch(() => {}); load();
    const t = setInterval(() => { if (!document.hidden) load(); }, every); return () => { on = false; clearInterval(t); }; }, [url, every]);
  return { data };
}

// 🗼 TRENCH TOWERS as a list (the Family Deck): the agents' INTAKE list (READY first) — status, 5m move, the desk's read, the theory line, ⚡ Trade.
// Empty intake (the kernel just restarted) → the live Pump board, so the tab is never blank.
export const ageWord = m => (m < 60 ? `${Math.round(m)}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`);
export function TrenchList() {
  const { data } = useMarketJson('/api/reputation/familia/intake', 30000); const rows = data?.coins || [];
  if (data && !rows.length) return <div className="av-court"><p className="av-lede">The desk's intake list is refilling — here's the live Pump board meanwhile.</p><PumpRadar /></div>;
  return <ol className="av-list av-tt" data-testid="av-tt">{!data ? <li className="m-dim">Reading the intake list…</li> : null}
    {rows.map((r, i) => <li key={r.mint} style={{ '--i': i }}><em>{i + 1}</em>
      <span className="av-sym"><b>${r.sym}</b><small>{[r.status, r.mc ? `MC ${usd(r.mc)}` : null, r.ageMin != null ? `${ageWord(r.ageMin)} old` : null].filter(Boolean).join(' · ')}</small>
        {r.read || r.theory ? <small className="av-read" data-tip={r.theory || ''}>{r.read || r.theory}</small> : null}</span>
      <span className={`av-heat ${(r.ch ?? 0) < 0 ? 'down' : 'up'}`}><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, heatOf(r.ch))})` }} /></u><b className="m-num">5m {pct(r.ch)}</b></span>
      <button type="button" className="m-btn m-go" disabled={!r.pair} onClick={() => trade({ chainId: 'solana', pairAddress: r.pair, baseToken: { address: r.mint, symbol: r.sym } })} data-tip="Trade it right here — chart + Quick trade slide over the room; your wallet signs" data-testid={`av-tt-${i}`}>⚡ Trade</button></li>)}</ol>;
}

const BODY = {
  perps: () => <PerpsDesk />, tt: () => <TrenchList />,
  trades: () => <TradeCenter />,
  pumpradar: () => <PumpRadar />, feebank: () => <FeeBank />, runners: () => <RunnersPanel />, watch: () => <WatchlistDashboard />, rep: () => <Courthouse />,
  feecat: () => <CatTower />, gas: () => <GetGas />, sleep: () => <NightVault />,
  feedx: () => <><div className="av-tools"><button type="button" className="m-btn" onClick={() => window.dispatchEvent(new Event('feeless:feed-pop'))} data-tip="Float FEEd over any page — keep reading while you trade" data-testid="av-feed-pop">⤢ Pop out FEEd</button></div><FeedPanel /></>,
};

// 🏛 an outer city's CITY HALL room: its own launchpad board as a live radar (Pump · LaunchLab · LetsBONK), or the court for Cartel Docks
export function HallRoom({ city }) {
  const scope = { harbor: 'pump', heights: 'raydium', bay: 'bonk' }[city];
  return <div className="av-room" data-testid={`hall-${city}`}>{scope ? <PumpRadar scope={scope} /> : <Courthouse />}</div>;
}

// one Avenue room: the tool itself — everything happens in the room (no jump to another FEELESS page)
export function AvenueRoom({ lens }) {
  const p = PLACES.find(x => x.lens === lens && x.tool); const Body = BODY[lens];
  if (!p || !Body) return null;
  return <div className={`av-room k-${p.key}`} style={{ '--pc': p.color }} data-testid={`avenue-${lens}`}>
    <Suspense fallback={<div className="av-load" aria-busy="true"><i /><i /><i /></div>}><Body /></Suspense>
  </div>;
}
