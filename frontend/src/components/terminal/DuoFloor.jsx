import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { TrenchChart } from './TrenchChart';
import { QuickTrade } from './QuickTrade';
import { DipRipTool } from './DipRipTool';
import { TradeTape } from './TradeTape';
import { ShieldBadge } from '../Shield';
import { LiveTank } from '../LiveTank';
import { TokenAvatar } from './MarketPrimitives';
import { LivePrice, LiveChange24, LiveMarketCap } from './LiveCells';
import { useMarket } from '../../hooks/useMarket';
import { useWorkspace } from '../../hooks/useWorkspace';
import { duoState, readDuoPrefs, saveDuoPrefs, readRecent, saveRecent, pushRecent, floorFeed, stepFeed } from '../../lib/duo';
import '../../styles/duoFloor.css';

// 📱📱 THE DUO FLOOR (owner 2026-10-27, iPhone Duo screenshot: "not a full app like split · the switches don't lock to the side · portrait can't
// see full screen · landscape isn't using the new screen size · learn from the pump app"). On an unfolded iPhone Duo (890 × 626 wide, 626 × 890
// upright), a tablet or a phone turned sideways, the Trenches coin floor is its own full-screen trading app — no site chrome:
//   WIDE      rail · CHART half | DOCK half, the split exactly at the crease (50 %). The rail = ← back, your recent coins, ⇄ swap the halves, home.
//   UPRIGHT   coin bar · chart · the dock · a pump-style BUY / SELL bar pinned to the bottom.
// The dock is locked to its half: TRADE (Quick trade · Dip / Rip · shield) · CHAT · CALLS · COINS (the live intake + the feed — tap = this
// chart, in place) · TAPE (live swaps). ‹ › or a swipe on the coin bar steps through the feed. Picks + recents are saved per device.
export const DOCK = [['trade', 'TRADE'], ['chat', 'CHAT'], ['calls', 'CALLS'], ['coins', 'COINS'], ['tape', 'TAPE']];

export function useDuoFloor() {
  const read = () => { const s = duoState(); return { on: s.duo || s.land, wide: s.wide || s.land }; };
  const [st, setSt] = useState(read);
  useEffect(() => { const f = () => setSt(read()); window.addEventListener('feeless:duo', f); window.addEventListener('resize', f); return () => { window.removeEventListener('feeless:duo', f); window.removeEventListener('resize', f); }; }, []);
  return st;
}

const pct = v => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const usd = v => (!(Number(v) > 0) ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);

export function DuoFloor({ pair, pairs = [], newPairs = [], wide, onPick, onBack, chat, calls }) {
  const { has, toggle } = useWorkspace();
  const live = useMarket(pair ? `/pair/${pair.chainId}/${pair.pairAddress}` : null, 3000);
  const lp = live.data?.pairs?.[0]; const cur = lp ? { ...pair, ...lp } : pair;
  const [prefs, setPrefs] = useState(readDuoPrefs); const tab = DOCK.some(([k]) => k === prefs.second) ? prefs.second : 'trade';
  const set = x => setPrefs(saveDuoPrefs({ ...prefs, ...x }));
  const [recent, setRecent] = useState(readRecent);
  useEffect(() => { if (pair?.pairAddress) setRecent(r => saveRecent(pushRecent(r, pair))); }, [pair?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const b = document.body.classList; b.add('duo-floor-on'); return () => b.remove('duo-floor-on'); }, []);
  const feed = useMemo(() => floorFeed(pairs, newPairs), [pairs, newPairs]);
  const step = dir => { const n = stepFeed(feed, cur, dir); if (n) onPick(n); };
  const touch = useRef(null); const plot = useRef(null);
  // the chart takes exactly the height its half has left (bar + toolbar measured, never a guess) — re-measured on fold / turn / resize
  useEffect(() => { const el = plot.current; if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const fit = () => { const tb = el.querySelector('.chart-toolbar'); el.style.setProperty('--dfl-h', `${Math.max(160, el.clientHeight - (tb?.offsetHeight || 0) - 12)}px`); };
    const ro = new ResizeObserver(fit); ro.observe(el); fit(); const t = setTimeout(fit, 600); return () => { ro.disconnect(); clearTimeout(t); }; }, [cur?.pairAddress, wide]);
  const swipe = { onTouchStart: e => { touch.current = e.touches[0]?.clientX ?? null; },
    onTouchEnd: e => { const x0 = touch.current; touch.current = null; const dx = (e.changedTouches[0]?.clientX ?? x0) - x0; if (x0 != null && Math.abs(dx) > 60) step(dx < 0 ? 1 : -1); } };
  const side = s => { set({ second: 'trade' }); setTimeout(() => window.dispatchEvent(new CustomEvent('feeless:qt-side', { detail: { mint: cur?.baseToken?.address, side: s } })), 30); };
  const mint = cur?.baseToken?.address; const watched = cur ? has?.(cur) : false;
  if (!cur) return null;
  const sym = cur.baseToken?.symbol || '?'; const m5 = cur.priceChange?.m5;
  return createPortal(<div className={`dfl ${wide ? 'is-wide' : 'is-up'} ${prefs.swap ? 'is-swap' : ''}`} data-testid="duo-floor" role="application" aria-label={`$${sym} — Duo trading floor`}>
    <div className="dfl-fx" aria-hidden="true"><i /><i /></div>
    {wide ? <nav className="dfl-rail" aria-label="Duo floor">
      <button type="button" className="dfl-rb is-back" onClick={onBack} aria-label="Back to the Trenches" data-tip="Back to the Trenches" data-testid="dfl-back">←</button>
      <span className="dfl-recent" aria-label="Recent coins">{recent.slice(0, 5).map((r, i) => <button key={r.pairAddress} type="button" style={{ '--i': i }} className={`dfl-rc ${r.pairAddress === cur.pairAddress ? 'is-on' : ''}`}
        onClick={() => onPick({ chainId: r.chainId, pairAddress: r.pairAddress, baseToken: { symbol: r.symbol, address: r.mint }, info: { imageUrl: r.img } })} aria-label={`$${r.symbol}`} data-tip={`$${r.symbol} — open it here`} data-testid={`dfl-recent-${i}`}>
        {r.img ? <img src={r.img} alt="" loading="lazy" /> : <b>{String(r.symbol).slice(0, 2)}</b>}</button>)}</span>
      <button type="button" className="dfl-rb" aria-pressed={prefs.swap} onClick={() => set({ swap: !prefs.swap })} aria-label="Swap the two halves" data-tip="Swap the halves — chart ⇄ dock" data-testid="dfl-swap"><i className="dfl-dev" aria-hidden="true"><s /><s /></i></button>
      <Link className="dfl-rb" to="/terminal" aria-label="Home" data-tip="FEELESS home" data-testid="dfl-home">⌂</Link>
    </nav> : null}
    <section className="dfl-chart" data-testid="dfl-chart">
      <header className="dfl-bar" {...swipe} data-testid="dfl-bar"><div className="dfl-row">
        {!wide ? <button type="button" className="dfl-ib" onClick={onBack} aria-label="Back to the Trenches" data-tip="Back to the Trenches" data-testid="dfl-back">←</button> : null}
        <TokenAvatar pair={cur} size={30} />
        <span className="dfl-id"><b>${sym}</b><small>{cur.dexId || cur.chainId} · swipe for the next coin</small></span>
        <span className="dfl-steps"><button type="button" className="dfl-ib" onClick={() => step(-1)} disabled={feed.length < 2} aria-label="Previous coin" data-tip="Previous coin in the feed (or swipe the bar)" data-testid="dfl-prev">‹</button>
          <button type="button" className="dfl-ib" onClick={() => step(1)} disabled={feed.length < 2} aria-label="Next coin" data-tip="Next coin in the feed (or swipe the bar)" data-testid="dfl-next">›</button>
          <button type="button" className={`dfl-ib ${watched ? 'is-on' : ''}`} onClick={() => toggle?.(cur)} aria-pressed={!!watched} aria-label="Watch this coin" data-tip={watched ? 'On your Radar — tap to drop it' : 'Add it to your Radar'} data-testid="dfl-star">{watched ? '★' : '☆'}</button>
          {!wide ? <button type="button" className="dfl-ib" aria-pressed={prefs.swap} onClick={() => set({ swap: !prefs.swap })} aria-label="Swap chart and dock" data-tip="Dock on top ⇄ chart on top" data-testid="dfl-swap">⇅</button> : null}</span></div>
        <div className="dfl-vit">
          <span className="dfl-px" data-tip="Live price · 24h change"><b className="m-num"><LivePrice pair={cur} id="dfl-price" /></b><LiveChange24 pair={cur} id="dfl-change" /></span>
          <span className="dfl-kv" data-tip="Live market cap"><small>MC</small><b className="m-num"><LiveMarketCap pair={cur} id="dfl-mc" /></b></span>
          <span className="dfl-kv" data-tip="Pool liquidity"><small>LIQ</small><b className="m-num">{usd(cur.liquidity?.usd)}</b></span>
          <span className="dfl-kv is-m5" data-tip="Move over the last 5 minutes"><small>5M</small><b className={`m-num ${Number(m5) >= 0 ? 'up' : 'dn'}`}>{pct(m5)}</b><u aria-hidden="true"><s className={Number(m5) >= 0 ? 'up' : 'dn'} style={{ transform: `scaleX(${Math.max(0.05, Math.min(1, Math.abs(Number(m5) || 0) / 30))})` }} /></u></span>
        </div>
      </header>
      <div className="dfl-plot" ref={plot}><TrenchChart pair={cur} defaultInterval="1m" tools={false} tape={false} /></div>
    </section>
    <section className="dfl-side" data-testid="dfl-side">
      <div className="m-seg dfl-tabs" role="tablist" aria-label="Dock">{DOCK.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => set({ second: k })} data-testid={`dfl-tab-${k}`}>{l}</button>)}</div>
      <div className="dfl-pane custom-scroll" key={tab} data-testid={`dfl-pane-${tab}`}>
        {tab === 'trade' ? <><QuickTrade pair={cur} /><DipRipTool pair={cur} />{cur.chainId === 'solana' ? <ShieldBadge mint={mint} /> : null}</> : null}
        {tab === 'chat' ? chat : null}
        {tab === 'calls' ? calls : null}
        {tab === 'coins' ? <><LiveTank onTrade={p => onPick(p)} /><ol className="dfl-feed" aria-label="Coins">{feed.slice(0, 40).map((p, i) => { const ch = Number(p.priceChange?.m5 ?? p.priceChange?.h1); const on = p.pairAddress === cur.pairAddress;
          return <li key={p.pairAddress} style={{ '--i': Math.min(i, 12) }}><button type="button" className={`dfl-coin ${on ? 'is-on' : ''}`} onClick={() => onPick(p)} data-tip={`$${p.baseToken?.symbol} — open it on the chart`} data-testid={`dfl-coin-${i}`}>
            <TokenAvatar pair={p} size={30} /><span className="dfl-cn"><b>${p.baseToken?.symbol}</b><small>{usd(p.marketCap ?? p.fdv)} MC · {usd(p.liquidity?.usd)} liq</small></span>
            <em className={`m-num ${ch >= 0 ? 'up' : 'dn'}`}>{pct(ch)}</em><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(ch || 0) / 50))})` }} className={ch >= 0 ? 'up' : 'dn'} /></u></button></li>; })}</ol></> : null}
        {tab === 'tape' ? <TradeTape pair={cur} /> : null}
      </div>
    </section>
    {!wide ? <div className="dfl-act" data-testid="dfl-act"><button type="button" className="m-btn m-go dfl-buy" onClick={() => side('buy')} data-tip="Quick trade, BUY side — your wallet signs" data-testid="dfl-buy">BUY ${sym}</button>
      <button type="button" className="m-btn dfl-sell" onClick={() => side('sell')} data-tip="Quick trade, SELL side — your wallet signs" data-testid="dfl-sell">SELL</button></div> : null}
  </div>, document.body);
}
