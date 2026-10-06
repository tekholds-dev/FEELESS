import React, { useEffect, useState } from 'react';
import { PumpProfile } from './PumpProfile';
import { createPortal } from 'react-dom';
import { useCoinEdge } from '../lib/coinEdge';
import { useLivePrices } from '../lib/livePrices';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { openWarRoom } from './WarRoomHost';
import { investigate } from './CaseFile';
import '../styles/fusePage.css';
import '../styles/coinDrawer.css';

// 🪙 ONE coin drawer, sitewide: openCoin({ mint, pairAddress, symbol, logo, runner }) from anywhere → this panel slides in with
// everything FEELESS knows about the coin (the coin edge: signals with sources, verification, runner gates + bond boxes, live
// price) and the three things you do with a coin: 📈 Chart · 🔎 Case file · ＋ Add to card. Mounted once (CoinDrawerHost).
export const openCoin = coin => window.dispatchEvent(new CustomEvent('feeless:coin', { detail: coin }));
export const addToCard = coin => {
  if (window.location.pathname.startsWith('/terminal/fuse')) window.dispatchEvent(new CustomEvent('feeless:add-to-card', { detail: coin }));
  else window.location.assign(`/terminal/fuse?tab=lab&add=${encodeURIComponent(coin.pairAddress || '')}&mint=${encodeURIComponent(coin.mint || '')}&sym=${encodeURIComponent(coin.symbol || '')}${coin.runner ? '&runner=1' : ''}`);
};
// A coin may arrive as { mint, pairAddress, symbol, logo } OR as a market pair ({ baseToken, pairAddress, volume … }). Without this
// a pair opened the drawer with no mint: the title read "$…" and it sat on "Reading the coin…" for good.
export const asCoin = d => { if (!d) return null; const b = d.baseToken || {};
  return { ...d, mint: d.mint || b.address || d.baseAddress, symbol: d.symbol || b.symbol, logo: d.logo || d.info?.imageUrl,
    stats: d.stats || (d.volume || d.liquidity || d.marketCap ? { mcap: Number(d.marketCap || d.fdv) || 0, vol1h: Number(d.volume?.h1) || 0, liq: Number(d.liquidity?.usd) || 0,
      ageH: d.pairCreatedAt ? (Date.now() - Number(d.pairCreatedAt)) / 3.6e6 : null, moves: d.priceChange || null } : null) }; };
const big = v => (!v ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const age = h => (h == null ? '—' : h < 1 ? `${Math.round(h * 60)}m` : h < 48 ? `${Math.round(h)}h` : `${Math.round(h / 24)}d`);
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const px = v => (v >= 1 ? v.toFixed(3) : v >= 0.001 ? v.toFixed(6) : v ? v.toPrecision(3) : '—');

export function CoinDrawerHost() {
  const [coin, setCoin] = useState(null);
  useEffect(() => { const on = e => setCoin(asCoin(e.detail)); window.addEventListener('feeless:coin', on); return () => window.removeEventListener('feeless:coin', on); }, []);
  useEffect(() => { if (!coin) return undefined; const k = e => e.key === 'Escape' && setCoin(null); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [coin]);
  return coin ? <CoinDrawer coin={coin} onClose={() => setCoin(null)} /> : null;
}

export function CoinDrawer({ coin, onClose }) {
  const e = useCoinEdge(coin.mint);
  const live = useLivePrices(coin.pairAddress ? [coin.pairAddress] : []).get(coin.pairAddress);
  const pair = { chainId: 'solana', pairAddress: coin.pairAddress, baseToken: { address: coin.mint, symbol: coin.symbol }, info: { imageUrl: coin.logo } };
  const v = e?.verify?.level; const run = e?.runner; const pulse = e?.pulse;
  const [slow, setSlow] = useState(false);   // no read after 6s → say so instead of "Reading…" for good
  useEffect(() => { setSlow(false); const t = setTimeout(() => setSlow(true), 6000); return () => clearTimeout(t); }, [coin.mint]);
  const st = coin.stats; const mv = st?.moves || {};
  const moves = [['5m', live?.m5 ?? mv.m5], ['1h', live?.h1 ?? mv.h1], ['6h', mv.h6], ['24h', mv.h24]].filter(x => x[1] != null && Number.isFinite(Number(x[1])));
  const top = Math.max(10, ...moves.map(x => Math.abs(Number(x[1]))));
  // 🎚 the timeframe you tap drives the whole card: its move sets the backdrop's colour and heat, and the live price ticks a spark line
  const [tf, setTf] = useState('1h');
  const sel = Number((moves.find(x => x[0] === tf) || moves[0] || [0, 0])[1]) || 0;
  const heat = Math.max(0.25, Math.min(1, Math.abs(sel) / 60));
  const [ticks, setTicks] = useState([]);
  useEffect(() => { setTicks([]); }, [coin.mint]);
  useEffect(() => { const p = Number(live?.price); if (p > 0) setTicks(t => (t[t.length - 1] === p ? t : [...t.slice(-39), p])); }, [live?.price]);
  const spark = ticks.length > 1 ? (() => { const lo = Math.min(...ticks); const hi = Math.max(...ticks); const r = hi - lo || 1;
    return ticks.map((v, i) => `${(i / (ticks.length - 1) * 100).toFixed(1)},${(30 - (v - lo) / r * 28).toFixed(1)}`).join(' '); })() : null;
  const it = e?.intel || {}; const n = v => (v == null ? '—' : `${Number(v).toFixed(1)}%`);
  const vit = e ? [['TOP 10 HOLD', n(it.top10Pct), it.top10Pct != null && it.top10Pct > 30], ['INSIDERS', n(it.insidersHoldingPct), it.insidersHoldingPct > 8], ['DEV HOLDS', n(it.devHoldingPct), it.devHoldingPct > 10],
    ['BUNDLED', it.bundledWallets ? String(it.bundledWallets.length) : '—', (it.bundledWallets || []).length > 1], ['CREATOR', run?.creatorRep || '—', ['suspect', 'high'].includes(run?.creatorRep)],
    ['5M TRADES', pulse ? `${pulse.buys || 0} buy · ${pulse.sells || 0} sell` : '—', false], ['AVG TRADE', pulse?.avgTradeUsd ? `$${Math.round(pulse.avgTradeUsd)}` : '—', false],
    ['STAGE', run?.stage === 'curve' ? `curve ${Math.round(run.curve || 0)}%` : run?.stage || '—', false]] : [];
  return createPortal(<div className="ce-shade" role="presentation" onClick={onClose} data-testid="coin-drawer">
    <aside className={`ce cd ${sel >= 0 ? 'is-up' : 'is-dn'}`} style={{ '--heat': heat }} role="dialog" aria-modal="true" aria-label={`${coin.symbol || 'Coin'} details`} onClick={ev => ev.stopPropagation()}>
      <div className="cd-live" aria-hidden><i /><i /><i /><b /><b /><b /><b /><b /><b /></div>
      <header className="cd-head"><TokenAvatar pair={pair} size={44} /><div><h3>${coin.symbol || `${(coin.mint || '').slice(0, 4)}…`}
        {v === 'verified' && <i className="fl-real" data-tip="FEELESS verified">✓ VERIFIED</i>}{v === 'gold' && <i className="fl-real" data-tip="Official / reviewed">✦ GOLD</i>}</h3>
        <small className="m-dim">{coin.mint ? `${coin.mint.slice(0, 6)}…${coin.mint.slice(-6)}` : ''}</small></div>
        <button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <div className="ce-sum">
        <div><small>PRICE · LIVE</small><b className="m-num">${px(live?.price)}</b><em className={(live?.m5 || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(live?.m5)} 5m · {pc(live?.h1)} 1h</em></div>
        <div data-tip="Last 5 minutes of trades (Pump Pulse)"><small>FLOW · 5M</small><b className="m-num">{pulse ? `${pulse.buyShare}% buys` : '—'}</b><em>{pulse ? `${(pulse.buys || 0) + (pulse.sells || 0)} trades` : 'quiet'}</em></div>
        {run && <div data-tip={run.passing ? 'Passes every Fuse Runners gate right now' : (run.gates || []).join(' · ')}><small>RUNNER</small><b className={`m-num ${run.passing ? 'm-pos' : 'm-neg'}`}>{run.passing ? `${Math.round(run.score || 0)} · ${run.lane || ''}` : '✕ gated'}</b><em>{run.passing ? 'passes all gates' : run.gates?.[0]}</em></div>}
      </div>
      {st && <div className="cd-stats" data-testid="cd-stats">{[['MARKET CAP', big(st.mcap)], ['1H VOLUME', big(st.vol1h)], ['POOL', big(st.liq)], ['AGE', age(st.ageH)]].map(([l, x], i) => <div key={l} style={{ '--i': i }}><small>{l}</small><b className="m-num">{x}</b></div>)}</div>}
      {spark && <svg className="cd-spark" viewBox="0 0 100 32" preserveAspectRatio="none" data-testid="cd-spark" aria-label="Live price since you opened this"><polyline points={spark} /></svg>}
      {moves.length > 0 && <div className="cd-moves" data-testid="cd-moves">{moves.map(([l, x], i) => { const n = Number(x); return <div key={l} role="button" tabIndex={0} aria-pressed={tf === l} onClick={() => setTf(l)} onKeyDown={ev => (ev.key === 'Enter' || ev.key === ' ') && setTf(l)}
        className={`${n >= 0 ? 'up' : 'dn'} ${tf === l ? 'on' : ''}`} style={{ '--i': i }} data-testid={`cd-tf-${l}`}><small>{l}</small>
        <span><i style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(n) / top))})` }} /></span><b className="m-num">{n >= 1000 ? `${(n / 100 + 1).toFixed(1)}x` : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`}</b></div>; })}</div>}
      {coin.mint && <PumpProfile mint={coin.mint} compact />}
      {vit.length > 0 && <div className="cd-vit" data-testid="cd-vitals">{vit.map(([l, x, bad], i) => <div key={l} className={bad ? 'bad' : ''} style={{ '--i': i }}><small>{l}</small><b className="m-num">{x}</b></div>)}</div>}
      {e?.sources?.length > 0 && <div className="cd-src">{e.sources.map(sx => <span key={sx.kind} className="m-chip" data-tip={sx.detail}>{sx.label}</span>)}</div>}
      {e?.signals?.length > 0 && <ul className="cd-sig">{e.signals.map((s, i) => <li key={i} className={s.warn ? 'warn' : ''}><b>{s.text}</b><small className="m-dim">{s.source}</small></li>)}</ul>}
      {run?.bond?.length > 0 && <div className="cd-bond"><small className="m-label">🔔 BOND BOXES</small><div>{run.bond.map(b => <span key={b.label} className={b.ok ? 'ok' : ''}>{b.ok ? '✓' : '·'} {b.label}</span>)}</div></div>}
      {!e && (slow || !coin.mint ? <p className="m-note" data-testid="cd-noread">FEELESS has no holder read on this coin yet{coin.mint ? ' — open the 🔎 Case file to scan it now' : ''}.</p>
        : <p className="m-dim cd-reading"><i /><i /><i /> Reading the coin…</p>)}
      <div className="cd-acts">
        <button type="button" className="m-btn" onClick={() => { onClose(); openWarRoom(pair); }} data-testid="cd-chart">📈 Chart</button>
        <button type="button" className="m-btn" onClick={() => { onClose(); investigate(coin.mint); }} data-testid="cd-case">🔎 Case file</button>
        <button type="button" className="m-btn primary m-go" disabled={run && !run.passing && coin.runner} onClick={() => { onClose(); addToCard(coin); }} data-testid="cd-add"
          data-tip={run && !run.passing && coin.runner ? 'Fails a runner gate right now' : 'Add to your Fuse card (3 pools + 3 runners)'}>＋ Add to card</button>
      </div>
    </aside></div>, document.body);
}
