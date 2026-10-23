import React, { Suspense, lazy, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { searchTokens } from '../lib/dexscreener';
import { useMarket } from '../hooks/useMarket';
import { openWarRoom } from './WarRoomHost';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { familiaDocked as docked, dockCount, ROOM_PATH } from '../lib/familiaRoom';
import '../styles/familiaTrade.css';

const TrenchChart = lazy(() => import('./terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
const SwapWorkspace = lazy(() => import('./command/SwapWorkspace').then(m => ({ default: m.SwapWorkspace })));
// 🏙 the FEELESS tools that open as a room over Familia (lib/familiaRoom) — the real page, not a link out
const FusePage = lazy(() => import('./FusePage').then(m => ({ default: m.FusePage })));
const MetaLaunchSetup = lazy(() => import('./terminal/MetaLaunchSetup'));
const ReputationCenter = lazy(() => import('./command/ReputationCenter').then(m => ({ default: m.ReputationCenter })));
const ROOMS = { fuse: ['⚔', 'FUSE CARDS', 'build a card · the Arena · your cards — your wallet signs', FusePage],
  launch: ['🚀', 'LAUNCH A COIN', 'the curve, the fees, the shield — your wallet signs', MetaLaunchSetup],
  shield: ['🛡', 'RUG SHIELD', 'paste any coin — holders, dev, snipers, bundles, the verdict', ReputationCenter] };

// 🏙 TRADE INSIDE FAMILIA (owner, 2026-10-22: "Trench Towers etc. on Familia all need to be able to trade IN Familia — no redirects to other
// parts of FEELESS"): every ⚡ Trade in a Familia building slides the coin's desk over the room you are in — the same TrenchChart the war room
// uses (chart, your trades on candles, Quick trade, Dip / Rip, rug shield; your wallet signs), and a coin-for-coin errand opens the swap with both
// coins set. The Familia page mounts ONE dock; anywhere else (no dock) the same call opens the war room as before.
export const familiaDocked = docked;
export function familiaTrade(pair) {
  if (!pair?.pairAddress) return;
  if (docked()) window.dispatchEvent(new CustomEvent('feeless:familia-trade', { detail: { kind: 'coin', pair } }));
  else openWarRoom(pair);
}
export function familiaSwap(swap) {   // {from, to} mints — the dock's swap reads them like the Trade tab does (you still press Get quote)
  try { sessionStorage.setItem('feeless.swap.pair', JSON.stringify({ input: swap?.from, output: swap?.to, amount: swap?.amount, pct: swap?.pct })); } catch { /* storage blocked */ }
  window.dispatchEvent(new CustomEvent('feeless:familia-trade', { detail: { kind: 'swap', swap } }));
}

const ready = p => !!(p && p.priceUsd != null && p.baseToken?.symbol);
const usd = v => { const n = Number(v); return !Number.isFinite(n) || n <= 0 ? '—' : n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
const pct = v => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

export function FamiliaTradeDock() {
  const [desk, setDesk] = useState(null); const [err, setErr] = useState(''); const [wide, setWide] = useState(false);
  const assets = useMarket(desk?.kind === 'swap' ? '/assets' : null, 300000);
  useEffect(() => {
    dockCount(1);
    let seq = 0;
    const open = e => {
      const d = e.detail || {}; const id = ++seq; setErr('');
      if (d.kind === 'swap') { setDesk({ kind: 'swap', swap: d.swap, n: id }); return; }   // n: a new errand remounts the swap (it reads the coins once)
      if (ROOMS[d.kind]) { setDesk({ kind: d.kind }); return; }   // 🏙 a FEELESS tool as a room over Familia
      const p = d.pair || {};
      if (ready(p)) { setDesk({ kind: 'coin', pair: { chainId: 'solana', ...p } }); return; }
      setDesk({ kind: 'coin', pair: { chainId: 'solana', ...p }, loading: true });
      searchTokens(p.pairAddress).then(ps => {
        if (id !== seq) return;
        const hit = (ps || []).find(x => x.pairAddress === p.pairAddress) || (ps || []).find(x => p.baseToken?.address && x.baseToken?.address === p.baseToken.address);
        if (hit) setDesk({ kind: 'coin', pair: hit }); else setErr('That pool did not answer — try again in a moment.');
      }).catch(() => id === seq && setErr('The market data did not answer — try again in a moment.'));
    };
    const esc = e => { if (e.key === 'Escape') setDesk(null); };
    window.addEventListener('feeless:familia-trade', open); window.addEventListener('keydown', esc);
    return () => { dockCount(-1); window.removeEventListener('feeless:familia-trade', open); window.removeEventListener('keydown', esc); };
  }, []);
  if (!desk) return null;
  const room = ROOMS[desk.kind];
  if (room) {
    const [ic, name, sub, Page] = room;
    return createPortal(<div className="ftd" data-testid="familia-trade">
      <button type="button" className="ftd-veil" aria-label="Close" onClick={() => setDesk(null)} />
      <aside className="ftd-desk is-wide is-room" role="dialog" aria-label={`${name} inside Familia`} data-testid={`familia-room-${desk.kind}`}>
        <i className="ftd-sky" aria-hidden="true"><b /><b /><b /></i>
        <header className="ftd-head"><span className="ftd-av ftd-room-ic" aria-hidden="true">{ic}</span>
          <span className="ftd-id"><em>🏙 INSIDE FAMILIA</em><b>{name}</b><small>{sub}</small></span>
          <span className="ftd-tools"><a className="m-btn ftd-ico" href={ROOM_PATH[desk.kind]} data-tip="Open it as a full FEELESS page instead" data-testid="ftd-full">↗</a>
            <button type="button" className="m-btn ftd-ico" onClick={() => setDesk(null)} aria-label="Close" data-tip="Back to the room (Esc)" data-testid="ftd-close">✕</button></span>
        </header>
        <div className="ftd-body ftd-room"><Suspense fallback={<div className="ftd-load" aria-busy="true"><i /><i /><i /><span>opening {name.toLowerCase()}…</span></div>}><Page /></Suspense></div>
      </aside>
    </div>, document.body);   // 🪟 a portal: the dock sits above every Familia bar / stacking context
  }
  const p = desk.pair; const coin = desk.kind === 'coin';
  const m5 = Number(p?.priceChange?.m5);
  return createPortal(<div className="ftd" data-testid="familia-trade">
    <button type="button" className="ftd-veil" aria-label="Close the trade desk" onClick={() => setDesk(null)} />
    <aside className={`ftd-desk${wide ? ' is-wide' : ''}`} role="dialog" aria-label={coin ? `Trade ${p?.baseToken?.symbol || 'coin'} inside Familia` : 'Swap inside Familia'}>
      <i className="ftd-sky" aria-hidden="true"><b /><b /><b /></i>
      <header className="ftd-head">
        {coin ? <>{ready(p) ? <TokenAvatar pair={p} size={36} /> : <span className="ftd-av" aria-hidden="true" />}
          <span className="ftd-id"><em>🏙 FAMILIA TRADE DESK</em><b>${p?.baseToken?.symbol || '…'}</b><small>{p?.baseToken?.name || 'reading the pool…'}</small></span></>
          : <span className="ftd-id"><em>{desk.swap?.title || '🏙 FAMILIA TRADE DESK'}</em><b>⚖ Swap</b><small>{desk.swap?.sub || 'both coins set — press Get quote; your wallet signs'}</small></span>}
        <span className="ftd-tools">
          <button type="button" className="m-btn ftd-ico" onClick={() => setWide(!wide)} aria-pressed={wide} data-tip={wide ? 'Narrow the desk' : 'Widen the desk — bigger chart, still in Familia'} data-testid="ftd-wide">{wide ? '⇥' : '⤢'}</button>
          <button type="button" className="m-btn ftd-ico" onClick={() => setDesk(null)} aria-label="Close" data-tip="Back to the room (Esc)" data-testid="ftd-close">✕</button></span>
      </header>
      {coin && ready(p) ? <div className="ftd-vit" data-testid="ftd-vitals">
        {[['MARKET CAP', usd(p.marketCap ?? p.fdv)], ['LIQUIDITY', usd(p.liquidity?.usd)], ['5M', pct(m5)], ['1H VOL', usd(p.volume?.h1)]].map(([k, v], i) => <span key={k} style={{ '--i': i }}
          className={k === '5M' && Number.isFinite(m5) ? (m5 >= 0 ? 'is-up' : 'is-dn') : ''}><em>{k}</em><b key={v}>{v}</b></span>)}</div> : null}
      <p className="ftd-note"><i aria-hidden="true" />{desk.swap?.where || 'trading inside Familia'} · non-custodial — your wallet signs every order · 0% FEELESS fee on $FEE · rFEE · FEECAT buys</p>
      <div className="ftd-body">
        {err ? <p className="m-note" role="alert">{err}</p> : null}
        {coin && !err && !ready(p) ? <div className="ftd-load" aria-busy="true"><i /><i /><i /><span>opening the desk…</span></div> : null}
        <Suspense fallback={<div className="ftd-load" aria-busy="true"><i /><i /><i /><span>loading the chart…</span></div>}>
          {coin && ready(p) ? <div className="eco-chart ftd-chart"><TrenchChart key={p.pairAddress} pair={p} /></div> : null}
          {!coin ? <div className="ftd-swap"><SwapWorkspace key={desk.n} pair={null} feeAsset={(assets.data?.assets || []).find(a => a.id === 'fee')} feeAssets={assets.data?.assets || []} onWallet={() => {}} /></div> : null}
        </Suspense>
      </div>
    </aside>
  </div>, document.body);
}
