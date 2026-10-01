import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useCoinEdge } from '../lib/coinEdge';
import { useLivePrices } from '../lib/livePrices';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { openWarRoom } from './WarRoomHost';
import { investigate } from './CaseFile';
import '../styles/fusePage.css';

// 🪙 ONE coin drawer, sitewide: openCoin({ mint, pairAddress, symbol, logo, runner }) from anywhere → this panel slides in with
// everything FEELESS knows about the coin (the coin edge: signals with sources, verification, runner gates + bond boxes, live
// price) and the three things you do with a coin: 📈 Chart · 🔎 Case file · ＋ Add to card. Mounted once (CoinDrawerHost).
export const openCoin = coin => window.dispatchEvent(new CustomEvent('feeless:coin', { detail: coin }));
export const addToCard = coin => {
  if (window.location.pathname.startsWith('/terminal/fuse')) window.dispatchEvent(new CustomEvent('feeless:add-to-card', { detail: coin }));
  else window.location.assign(`/terminal/fuse?tab=lab&add=${encodeURIComponent(coin.pairAddress || '')}&mint=${encodeURIComponent(coin.mint || '')}&sym=${encodeURIComponent(coin.symbol || '')}${coin.runner ? '&runner=1' : ''}`);
};
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const px = v => (v >= 1 ? v.toFixed(3) : v >= 0.001 ? v.toFixed(6) : v ? v.toPrecision(3) : '—');

export function CoinDrawerHost() {
  const [coin, setCoin] = useState(null);
  useEffect(() => { const on = e => setCoin(e.detail); window.addEventListener('feeless:coin', on); return () => window.removeEventListener('feeless:coin', on); }, []);
  useEffect(() => { if (!coin) return undefined; const k = e => e.key === 'Escape' && setCoin(null); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [coin]);
  return coin ? <CoinDrawer coin={coin} onClose={() => setCoin(null)} /> : null;
}

export function CoinDrawer({ coin, onClose }) {
  const e = useCoinEdge(coin.mint);
  const live = useLivePrices(coin.pairAddress ? [coin.pairAddress] : []).get(coin.pairAddress);
  const pair = { chainId: 'solana', pairAddress: coin.pairAddress, baseToken: { address: coin.mint, symbol: coin.symbol }, info: { imageUrl: coin.logo } };
  const v = e?.verify?.level; const run = e?.runner; const pulse = e?.pulse;
  return createPortal(<div className="ce-shade" role="presentation" onClick={onClose} data-testid="coin-drawer">
    <aside className="ce cd" role="dialog" aria-modal="true" aria-label={`${coin.symbol || 'Coin'} details`} onClick={ev => ev.stopPropagation()}>
      <header className="cd-head"><TokenAvatar pair={pair} size={44} /><div><h3>${coin.symbol || `${(coin.mint || '').slice(0, 4)}…`}
        {v === 'verified' && <i className="fl-real" data-tip="FEELESS verified">✓ VERIFIED</i>}{v === 'gold' && <i className="fl-real" data-tip="Official / reviewed">✦ GOLD</i>}</h3>
        <small className="m-dim">{coin.mint ? `${coin.mint.slice(0, 6)}…${coin.mint.slice(-6)}` : ''}</small></div>
        <button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <div className="ce-sum">
        <div><small>PRICE · LIVE</small><b className="m-num">${px(live?.price)}</b><em className={(live?.m5 || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(live?.m5)} 5m · {pc(live?.h1)} 1h</em></div>
        <div data-tip="Last 5 minutes of trades (Pump Pulse)"><small>FLOW · 5M</small><b className="m-num">{pulse ? `${pulse.buyShare}% buys` : '—'}</b><em>{pulse ? `${(pulse.buys || 0) + (pulse.sells || 0)} trades` : 'quiet'}</em></div>
        {run && <div data-tip={run.passing ? 'Passes every Fuse Runners gate right now' : (run.gates || []).join(' · ')}><small>RUNNER</small><b className={`m-num ${run.passing ? 'm-pos' : 'm-neg'}`}>{run.passing ? `${Math.round(run.score || 0)} · ${run.lane || ''}` : '✕ gated'}</b><em>{run.passing ? 'passes all gates' : run.gates?.[0]}</em></div>}
      </div>
      {e?.signals?.length > 0 && <ul className="cd-sig">{e.signals.map((s, i) => <li key={i} className={s.warn ? 'warn' : ''}><b>{s.text}</b><small className="m-dim">{s.source}</small></li>)}</ul>}
      {run?.bond?.length > 0 && <div className="cd-bond"><small className="m-label">🔔 BOND BOXES</small><div>{run.bond.map(b => <span key={b.label} className={b.ok ? 'ok' : ''}>{b.ok ? '✓' : '·'} {b.label}</span>)}</div></div>}
      {!e && <p className="m-dim">Reading the coin…</p>}
      <div className="cd-acts">
        <button type="button" className="m-btn" onClick={() => { onClose(); openWarRoom(pair); }} data-testid="cd-chart">📈 Chart</button>
        <button type="button" className="m-btn" onClick={() => { onClose(); investigate(coin.mint); }} data-testid="cd-case">🔎 Case file</button>
        <button type="button" className="m-btn primary m-go" disabled={run && !run.passing && coin.runner} onClick={() => { onClose(); addToCard(coin); }} data-testid="cd-add"
          data-tip={run && !run.passing && coin.runner ? 'Fails a runner gate right now' : 'Add to your Fuse card (3 pools + 3 runners)'}>＋ Add to card</button>
      </div>
    </aside></div>, document.body);
}
