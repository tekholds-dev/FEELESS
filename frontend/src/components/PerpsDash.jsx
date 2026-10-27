import React, { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useGlide } from '../lib/useGlide';
import { useWallet } from '../hooks/useWallet';
import { useTickers } from '../lib/cbFeed';
import { MKTS, perpPlan } from '../lib/perps';
import { PerpTicket } from './perps/PerpTicket';
import { PerpPositions } from './perps/PerpPositions';
import { KalshiDesk } from './perps/KalshiDesk';
import { LiveFlow } from './perps/LiveFlow';
import { BrokerDesk } from './BrokerDesk';
import { INDICATORS } from '../lib/indicators';
import { PaperPerps } from './PaperPerps';
import '../styles/perpsDash.css';

// 📉 FEELESS PERPS — the trading terminal (owner, 2026-10-23: "all mechanics a real perps desk has … only realtime vitals … true chart data
// ALWAYS … live TP / SL before the trade on the chart"). Docs: docs/PERPS.md.
// · TOP — the brand, the three markets (true price ticking on every trade, 24 h, prints / min), LIVE / PRACTICE, your open P&L.
// · THE STRIP — the picked market's live vitals: true MARK (Coinbase prints) · Jupiter's ORACLE + the basis · 24 h change + RANGE · VOLUME ·
//   SPREAD · BORROW / HR long vs short · WHO'S CROWDED · OI + FUNDING.
// · THE CHART — true candles (lib/cbFeed) with every level: the ticket's ☠ liq · TP · SL (drag them), and each position's entry / liq / TP / SL.
// · THE TICKET — side · collateral · leverage · TP / SL → Jupiter's quote → the wallet signs (perps/PerpTicket).
// · BELOW — POSITIONS (live P&L, TP / SL edit, partial close) · ⏱ KALSHI 15-MIN (US-legal up / down from $1) · 🧪 PRACTICE, beside 🌊 LIVE FLOW
//   (taker pressure, momentum, RVOL, whale prints, Jupiter's top traders this week — perps/LiveFlow).
const PerpsChart = lazy(() => import('./perps/PerpsChart').then(m => ({ default: m.PerpsChart })));   // the chart library loads only when the desk opens
const IVS = [['1m', '1M'], ['5m', '5M'], ['15m', '15M'], ['1h', '1H']];
const px = v => (v == null || !Number.isFinite(v) ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 1 })}` : `$${Number(v).toFixed(v >= 10 ? 2 : 4)}`);
const pc = (v, d = 2) => (v == null || !Number.isFinite(v) ? '—' : `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}%`);
const big = v => (!(v > 0) ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : `$${(v / 1e3).toFixed(1)}K`);

// pure: the chart's levels — the ticket (☠ liq, TP, SL draggable) + every open position on this market (entry, liq, its TP / SL)
export function perpLines(asset, t, plan, mark, positions) {
  const out = [];
  if (plan && mark > 0) {
    out.push({ id: 'liq', price: plan.liq, color: '#ff5d73', title: `☠ ${t.lev}× LIQ`, dash: true });
    if (t.tp) out.push({ id: 'tp', price: t.tp, color: '#45e486', title: 'TP', drag: true });
    if (t.sl) out.push({ id: 'sl', price: t.sl, color: '#ff9f43', title: 'SL', drag: true });
  }
  (positions || []).filter(p => p.asset === asset).forEach((p, i) => {
    if (p.entry > 0) out.push({ id: `e${i}`, price: p.entry, color: p.side === 'long' ? '#45e486' : '#ff9fd2', title: `${p.side === 'long' ? '▲' : '▼'} ${p.lev}× ENTRY`, dash: true });
    if (p.liq > 0) out.push({ id: `l${i}`, price: p.liq, color: '#ff5d73', title: `☠ ${p.lev}×` });
    (p.tpsl || []).forEach(o => { if (o.price > 0) out.push({ id: `o${o.id}`, price: o.price, color: o.kind === 'tp' ? '#45e486' : '#ff9f43', title: `${o.kind.toUpperCase()} ${p.lev}×`, dash: true }); });
  });
  return out;
}
// pure: who's crowded — Jupiter's long vs short pool utilisation → the long share (0..1) + the crowded side
export function crowd(pool) {
  const l = Number(pool?.longUtilizationPercent); const s = Number(pool?.shortUtilizationPercent);
  if (!(l >= 0) || !(s >= 0) || l + s <= 0) return null;
  return { long: l, short: s, share: l / (l + s), side: l > s ? 'LONGS' : s > l ? 'SHORTS' : 'EVEN' };
}
// pure: the 24 h range → where the price sits in it (0..1)
export const inRange = (p, lo, hi) => (p > 0 && hi > lo ? Math.max(0, Math.min(1, (p - lo) / (hi - lo))) : null);

function useNow(ms = 1000) { const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), ms); return () => clearInterval(t); }, [ms]); return n; }
function useJson(url, every) {
  const [d, setD] = useState(null);
  const load = useCallback(() => (url ? fetch(apiUrl(url)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {}) : null), [url]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, every); return () => clearInterval(t); }, [load, every]);
  return [d, load];
}
function Flash({ v, fmt, cls = '' }) {   // a live number: glides to each print, flashes green / pink with the move
  const g = useGlide(v ?? null, 350); const [dir, setDir] = useState(''); const [prev, setPrev] = useState(v);
  useEffect(() => { if (v != null && prev != null && v !== prev) { setDir(v > prev ? 'is-up' : 'is-dn'); setPrev(v); const t = setTimeout(() => setDir(''), 600); return () => clearTimeout(t); } setPrev(v); return undefined; }, [v]); // eslint-disable-line react-hooks/exhaustive-deps
  return <b className={`m-num pd-flash ${dir} ${cls}`}>{fmt(g)}</b>;
}

export function PerpsDash({ devAddress = '' }) {
  const { wallet, provider, connect } = useWallet() || {}; const addr = (wallet?.chain === 'solana' ? wallet.address : '') || devAddress;
  const [asset, setAsset] = useState('SOL'); const [iv, setIv] = useState('1m'); const [tab, setTab] = useState('pos');
  const [ind, setInd] = useState(() => { try { return JSON.parse(localStorage.getItem('feeless.perps.ind') || '["ema","vwap"]'); } catch { return ['ema', 'vwap']; } });
  const flip = k => setInd(o => { const n = o.includes(k) ? o.filter(x => x !== k) : [...o, k]; try { localStorage.setItem('feeless.perps.ind', JSON.stringify(n)); } catch { /* private */ } return n; });
  const [brk] = useJson('/api/reputation/familia/broker', 60000);
  const [t, setT] = useState({ side: 'long', usd: 10, lev: 10, tp: null, sl: null }); const set = useCallback(x => setT(o => ({ ...o, ...x })), []);
  const tk = useTickers(); const now = useNow();
  const [board] = useJson('/api/reputation/familia/perps', 30000);
  const [landing, setLanding] = useState(null);   // a just-signed open: shown at once, polled fast until Jupiter lists it (≤ 60s)
  const [jp, reloadJp] = useJson(`/api/reputation/familia/perps-real?address=${encodeURIComponent(addr || '')}`, landing ? 1500 : 5000);
  const [ks] = useJson('/api/reputation/familia/kalshi', 10000);
  const [caps] = useJson('/api/reputation/familia/broker/cdc-caps', 300000);   // Crypto.com's live market count for the rail
  // 🧭 the provider rail swipes, most-used first (owner 2026-10-27: "side swipe … top 3 used show first") — taps counted on this device
  const [use, setUse] = useState(() => { try { return JSON.parse(localStorage.getItem('feeless.perps.use') || '{}') || {}; } catch { return {}; } });
  const goProv = (k, go) => { setTab(go); setUse(u => { const n = { ...u, [k]: (u[k] || 0) + 1 }; try { localStorage.setItem('feeless.perps.use', JSON.stringify(n)); } catch { /* private */ } return n; }); };
  const by = useMemo(() => Object.fromEntries((board?.markets || []).map(r => [r.coin, r])), [board]);
  const stats = jp?.stats || {}; const pools = jp?.pools || {}; const positions = jp?.positions || [];
  useEffect(() => { if (!landing) return undefined;
    if (positions.some(p => p.asset === landing.asset && p.side === landing.side && (p.size || 0) >= landing.size * 0.5)) { setLanding(null); return undefined; }
    const t = setTimeout(() => setLanding(null), Math.max(0, 60000 - (Date.now() - landing.at))); return () => clearTimeout(t); }, [landing, positions]);
  const marks = useMemo(() => Object.fromEntries(MKTS.map(a => [a, tk[a]?.price || stats[a]?.price || by[a]?.mark || null])), [tk, stats, by]);
  const mark = marks[asset]; const live = tk[asset]; const st = stats[asset] || {}; const pool = pools[asset]; const cr = crowd(pool); const brd = by[asset] || {};
  const ch24 = live?.open24 > 0 ? (live.price / live.open24 - 1) * 100 : st.ch24; const hi = live?.high24 || st.hi24; const lo = live?.low24 || st.lo24;
  const where = inRange(mark, lo, hi); const spread = live?.bid > 0 && live?.ask > 0 ? ((live.ask - live.bid) / ((live.ask + live.bid) / 2)) * 1e4 : null;
  const basis = st.price > 0 && mark > 0 ? (mark / st.price - 1) * 100 : null; const age = live?.at ? Math.max(0, (now - live.at) / 1000) : null;
  const plan = perpPlan(mark, t.usd, t.lev, t.side, pool?.openFeePercent ?? 0.06);
  const liqKey = plan ? Math.round(plan.liq * 100) : 0;
  const lines = useMemo(() => perpLines(asset, t, plan, mark, landing ? [...positions, landing] : positions), [asset, t, liqKey, positions, landing]); // eslint-disable-line react-hooks/exhaustive-deps
  const onDrag = useCallback((id, p) => { if (id === 'tp' || id === 'sl') set({ [id]: p }); }, [set]);
  const total = positions.reduce((s, p) => { const m = marks[p.asset]; return s + (m > 0 && p.entry > 0 ? p.size * (m / p.entry - 1) * (p.side === 'long' ? 1 : -1) : (p.pnl || 0)); }, 0);
  const tot = useGlide(Math.round(total * 100) / 100, 400); const tug = useGlide(cr ? cr.share * 100 : 50, 700);
  const vol24 = live?.vol24 && mark ? live.vol24 * mark : st.vol24; const bmax = Math.max(pool?.longBorrowRatePercent || 0, pool?.shortBorrowRatePercent || 0, 1e-9);
  const pick = a => { setAsset(a); set({ tp: null, sl: null }); };
  const prov = ['kalshi', 'broker', 'cdc'].includes(tab) ? tab : 'jup';   // 🧭 the provider picked on the rail owns the trade station + the colors
  const below = tab === 'practice' ? 'practice' : 'pos';
  return <section className={`pd is-${t.side} pv-${prov}`} data-testid="perps-dash">
    <header className="pd-top">
      <span className="pd-brand"><i aria-hidden="true" /><b>FEELESS<em>PERPS</em></b><small>JUPITER · WALLET SIGNS · TRUE DATA</small></span>
      <div className="pd-mkts" role="radiogroup" aria-label="Market">{MKTS.map((a, i) => { const x = tk[a]; const c = x?.open24 > 0 ? (x.price / x.open24 - 1) * 100 : stats[a]?.ch24;
        return <button key={a} type="button" role="radio" aria-checked={a === asset} className={`pd-mkt ${a === asset ? 'is-on' : ''}`} style={{ '--i': i }} onClick={() => pick(a)}
          data-tip={`${a}-PERP on Jupiter · true price from Coinbase prints`} data-testid={`pd-m-${a}`}>
          <span className="pd-sym"><b>{a}</b><small>-PERP</small></span><Flash v={marks[a]} fmt={px} />
          <small className={`m-num pd-c ${(c ?? 0) < 0 ? 'is-dn' : 'is-up'}`}>{pc(c)}</small><u className="pd-tpm" aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, (x?.tpm || 0) / 600)})` }} /></u></button>; })}</div>
      <span className={`pd-pnl ${total > 0 ? 'is-up' : total < 0 ? 'is-dn' : ''}`} data-tip="Open P&L across your positions on the true price, before fees"><em>OPEN P&L</em>
        <b className="m-num">{positions.length ? `${tot < 0 ? '−' : '+'}$${Math.abs(tot).toFixed(2)}` : '$0.00'}</b><small>{positions.length ? `${positions.length} live` : 'flat'}</small></span>
    </header>
    <div className="pd-prov" role="radiogroup" aria-label="Provider — swipe for more, most used first" data-testid="pd-prov">{[
      ['jup', 'JUPITER PERPS', 'long / short · up to 250× · your wallet signs', 'FROM $10', 'LIVE', true, 'pos', 'Real perps on Jupiter (Solana) — Jupiter itself lists only SOL · ETH · BTC; your wallet signs; TP / SL + partial close', 3],
      ['cdc', 'CRYPTO.COM', `perps to ${caps?.perps?.maxLev || 100}× · spot · your own account`, 'FROM $1', 'YOUR KEY', true, 'cdc', 'Your Crypto.com Exchange account: every perp + spot pair it lists, searchable — paste its API key once (trading on, withdrawals off)', (caps?.perps?.n || 0) + (caps?.spot?.n || 0) || null],
      ['kalshi', 'KALSHI UP / DOWN', 'strike windows · BTC · ETH · SOL · S&P · NASDAQ', 'FROM $1', ks?.tradable ? 'LIVE' : 'KEY PENDING', !!ks?.tradable, 'kalshi', 'US-legal (CFTC) up / down strike contracts tokenized on Solana — needs the DFlow key', (ks?.coins || []).length || null],
      ['broker', '🏦 YOUR BROKER', 'US stocks · ETFs · crypto in your own account', 'FROM $1', 'LIVE', true, 'broker', 'Your own broker: paste your FREE Alpaca keys ($0 to start) — or link any broker when SnapTrade is set up', '11K+']]
      .map((r, i) => [...r, i]).sort((x, y) => (use[y[0]] || 0) - (use[x[0]] || 0) || x[9] - y[9])
      .map(([k, n, sub, min, st, on, go, tip, mk], i) => <button key={k} type="button" role="radio" aria-checked={prov === k}
        className={`pd-pv is-${k} ${on ? 'is-live' : 'is-wait'} ${prov === k ? 'is-on' : ''}`} style={{ '--i': i }} onClick={() => goProv(k, go)} data-tip={tip} data-testid={`pd-pv-${k}`}>
        <b>{i < 3 && use[k] ? <u className="pd-rank">#{i + 1}</u> : null}{n}</b><small>{sub}</small>
        <span><i className="m-num">{min}</i>{mk ? <s className="m-num pd-mk">{typeof mk === 'number' ? mk.toLocaleString() : mk} MKTS</s> : null}<em>{st}</em></span></button>)}</div>
    <div className="pd-strip" data-testid="pd-vits">
      <span className="pd-cell pd-mark" data-tip="True price: the last Coinbase print"><em>MARK <i className="pd-beat" key={live?.at} /></em><Flash v={mark} fmt={px} cls="pd-hero" /><small className="m-num">{live ? `${live.tpm} prints/min · ${age != null ? `${age.toFixed(1)}s` : ''}` : 'connecting…'}</small></span>
      <span className="pd-cell" data-tip="Jupiter's oracle price (what the trade fills at) and how far the true price sits from it"><em>JUP ORACLE</em><b className="m-num">{px(st.price)}</b><small className={`m-num ${(basis ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}>{basis == null ? '' : `basis ${pc(basis, 3)}`}</small></span>
      <span className={`pd-cell ${(ch24 ?? 0) >= 0 ? 'is-up' : 'is-dn'}`} data-tip="24 h change on the true price + the 24 h volume"><em>24H</em><Flash v={ch24} fmt={v => pc(v)} /><small className="m-num">{big(vol24)} vol</small></span>
      <span className="pd-cell pd-range" data-tip={`24 h low ${px(lo)} · high ${px(hi)}`}><em>24H RANGE</em><u aria-hidden="true"><i style={{ left: `${(where ?? 0.5) * 100}%` }} /></u><small className="m-num">{px(lo)} — {px(hi)}</small></span>
      <span className="pd-cell" data-tip="Best bid / best ask spread on the true book, in basis points"><em>SPREAD</em><b className="m-num">{spread == null ? '—' : `${spread.toFixed(1)} bp`}</b><small className="m-num">{live?.bid ? `${px(live.bid)} / ${px(live.ask)}` : ''}</small></span>
      <span className="pd-cell" data-tip="What Jupiter charges each side per hour to hold (on its size)"><em>BORROW / HR</em><span className="pd-bars"><u><s className="is-up" style={{ transform: `scaleX(${(pool?.longBorrowRatePercent || 0) / bmax})` }} /></u>
        <u><s className="is-dn" style={{ transform: `scaleX(${(pool?.shortBorrowRatePercent || 0) / bmax})` }} /></u></span>
        <small className="m-num">▲ {pool ? `${(pool.longBorrowRatePercent || 0).toFixed(4)}%` : '—'} ▼ {pool ? `${(pool.shortBorrowRatePercent || 0).toFixed(4)}%` : '—'}</small></span>
      <span className="pd-cell pd-tugc" data-tip={cr ? `Jupiter's ${asset} pool: longs use ${cr.long.toFixed(1)}%, shorts ${cr.short.toFixed(1)}% — the crowded side pays more + gets squeezed first` : 'Reading Jupiter’s pool…'}>
        <em>{cr ? `${cr.side} CROWDED` : "WHO'S CROWDED"}</em><div className="pd-tug" aria-hidden="true"><s className="is-l" style={{ transform: `scaleX(${tug / 100})` }} /><s className="is-s" style={{ transform: `scaleX(${1 - tug / 100})` }} /><i style={{ left: `${tug}%` }} /></div>
        <small className="m-num">▲ {cr ? `${cr.long.toFixed(0)}%` : '—'} · ▼ {cr ? `${cr.short.toFixed(0)}%` : '—'}</small></span>
      <span className="pd-cell" data-tip="Open interest + funding (yearly) on the global board — positive funding: longs pay shorts"><em>OI · FUNDING</em><b className="m-num">{big(brd.oiUsd)}</b><small className={`m-num ${(brd.fundApr ?? 0) > 0 ? 'is-dn' : 'is-up'}`}>{brd.fundApr != null ? `${brd.fundApr > 0 ? '+' : ''}${brd.fundApr}% / yr` : ''}</small></span>
    </div>
    <div className="pd-main">
      <div className="pd-chart" data-testid="pd-chart">
        <div className="pd-cbar"><span className="pd-cname"><b>{asset}<i>-PERP</i></b><small>TRUE CANDLES · COINBASE · LIVE</small></span>
          <span className="pd-ind" role="group" aria-label="Indicators">{INDICATORS.map(([k, l, tip]) => <button key={k} type="button" aria-pressed={ind.includes(k)} className={ind.includes(k) ? 'is-on' : ''} onClick={() => flip(k)} data-tip={tip} data-testid={`pd-ind-${k}`}>{l}</button>)}</span>
          {t.tp || t.sl ? <span className="pd-lv">{t.tp ? <i className="is-tp">TP {px(t.tp)}</i> : null}{t.sl ? <i className="is-sl">SL {px(t.sl)}</i> : null}</span> : null}
          <span className="m-seg pd-iv" role="radiogroup" aria-label="Candle size">{IVS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={iv === k} className={iv === k ? 'active' : ''} onClick={() => setIv(k)} data-tip={`${l} candles`} data-testid={`pd-iv-${k}`}>{l}</button>)}</span></div>
        <div className="pd-plot"><Suspense fallback={<p className="pc-msg">Loading true candles…</p>}><PerpsChart asset={asset} iv={iv} lines={lines} onDrag={onDrag} ind={ind} /></Suspense></div>
      </div>
      {prov === 'kalshi' ? <div className="pd-side" data-testid="pd-side-kalshi"><KalshiDesk asset={asset} rows={ks?.coins} marks={marks} now={now} tradable={!!ks?.tradable} addr={addr} wallet={wallet} provider={provider} connect={connect} /></div>
        : prov !== 'jup' ? <div className="pd-side" data-testid={`pd-side-${prov}`}><BrokerDesk venue={prov === 'cdc' ? 'cdc' : null} /></div>
        : <PerpTicket asset={asset} mark={mark} pool={pool} t={t} set={set} addr={addr} wallet={wallet} provider={provider} connect={connect} solPx={marks.SOL} onOpened={x => { setLanding(x); reloadJp(); setTab('pos');
        setTimeout(() => document.querySelector('[data-testid="pd-below"]')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60); }} />}
    </div>
    <div className="pd-below" data-testid="pd-below">
      <div className="pd-bl">
      <div className="pd-tabs m-seg" role="tablist" aria-label="Panels">{[['pos', `JUPITER POSITIONS${positions.length ? ` · ${positions.length}` : ''}`, 'Your Jupiter positions, marked live'], ['practice', '🧪 PRACTICE', 'Paper perps at the real mark — no money moves']].map(([k, l, tip]) =>
        <button key={k} type="button" role="tab" aria-selected={below === k} className={below === k ? 'active' : ''} onClick={() => setTab(k === 'pos' && prov !== 'jup' ? tab : k)} data-tip={tip} data-testid={`pd-b-${k}`}>{l}</button>)}</div>
      {below === 'pos' && landing ? <div className={`pp-landing is-${landing.side}`} data-testid="pp-landing" role="status">
        <i aria-hidden="true" /><b>{landing.side === 'long' ? '▲' : '▼'} {landing.asset} {landing.lev}× · ${Math.round(landing.size).toLocaleString()}</b>
        <small>LANDED on-chain · waiting for Jupiter to list it</small>
        <a href={`https://solscan.io/tx/${landing.txid}`} target="_blank" rel="noopener noreferrer" data-tip="Open the transaction on Solscan">{String(landing.txid).slice(0, 8)}… ↗</a></div> : null}
      {below === 'pos' ? <PerpPositions trades={jp?.trades || []} positions={positions} marks={marks} addr={addr} provider={provider} wallet={wallet} connect={connect} reload={reloadJp} onPick={pick} />
          : <PaperPerps row={{ ...brd, coin: asset, mark }} lev={Math.round(t.lev)} devAddress={devAddress} />}
      </div>
      <LiveFlow asset={asset} />
    </div>
  </section>;
}
