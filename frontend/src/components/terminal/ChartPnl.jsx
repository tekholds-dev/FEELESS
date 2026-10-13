// 💹 YOUR LIVE P&L ON EVERY CHART (owner, 2026-10-12: "not showing live pnl for all charts"). The badge used to live only in the trench
// chart's wrapper; it is drawn by `PriceChart` itself now (`ChartPnl`), so the coin drawer, quick look, mini chart, mini card and the
// Agents cockpit all carry it. One position read per coin (`sharedJson`), the host chart's own streamed price (no second poll).
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { sharedJson } from '../../lib/sharedJson';
import { applyFill, pnlSummary } from '../../lib/position';
import { fetchLivePrice } from '../../lib/livePrice';
import { ShareGifButton } from '../ShareGif';
import { useEasedNumber } from '../../lib/easedNumber';
import { tickHeat } from '../../lib/pnlTicker';
import { mcapOf } from '../../lib/mcap';
import { tiny } from '../../lib/num';
import '../../styles/pnlTicker.css';
import { ChartLive } from './ChartLive';

// The viewer's live position in this coin: average entry from their real swaps, P&L against the
// live price (updates with every tick), and a flash the moment one of their trades confirms.
export function useMyPosition(pair) {
  const { wallet } = useWallet() || {};
  const [pos, setPos] = useState(null); const [flash, setFlash] = useState(0);
  const token = pair?.baseToken?.address; const address = wallet?.address;
  // Trades confirmed in this tab that the server hasn't read back yet: kept on top of its answer for 90s.
  const pending = useRef([]);
  const withPending = useCallback(server => {
    const now = Date.now();
    pending.current = pending.current.filter(f => now - f.at < 90000 && !(server?.trades || []).some(t => t.tx === f.signature));
    return pending.current.reduce(applyFill, server || null);
  }, []);
  const load = useCallback(() => {
    if (!address || !token || typeof fetch !== 'function') { setPos(null); return; }
    sharedJson(`/api/reputation/position/${address}/${token}`, { maxAge: 4000 }).then(d => { if (d) setPos(withPending(d.position)); }).catch(() => {});   // ONE request per coin however many charts show it
  }, [address, token, withPending]);
  useEffect(() => { pending.current = []; load(); const timer = setInterval(load, 10000); return () => clearInterval(timer); }, [load]);
  useEffect(() => {
    const onTrade = e => {
      const d = e.detail || {};
      if (d.mint && d.mint !== token) return;
      if (d.mint && d.tokens > 0) { pending.current.push({ ...d, at: Date.now() }); setPos(p => applyFill(p, d)); }
      setFlash(Date.now()); setTimeout(load, 2500); setTimeout(load, 8000); setTimeout(load, 20000);
    };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => window.removeEventListener('feeless:trade-confirmed', onTrade);
  }, [token, load]);
  return [pos, flash];
}

export function PnlBadge({ pos, pair, price, flash, symbol, imageUrl, mcPerPrice, label = 'YOU', live = false, cls = '' }) {
  const [open, setOpen] = useState(false);
  const [livePrice, setLivePrice] = useState(price);
  useEffect(() => { setLivePrice(price); }, [price]);
  useEffect(() => {
    if (!pair?.pairAddress || live) return undefined;   // `live` = the host chart hands in its own streamed price: no second poll
    let alive = true;
    const refresh = () => fetchLivePrice(pair).then(q => { if (alive && Number(q?.usd) > 0) setLivePrice(Number(q.usd)); }).catch(() => {});
    refresh(); const timer = setInterval(refresh, 2500);
    return () => { alive = false; clearInterval(timer); };
  }, [pair?.chainId, pair?.pairAddress, live]);   // keyed by the POOL: a parent that rebuilds `pair` each render must not restart the poll
  // 💹 live ticker: each REAL price tick sets the effect level (how far it moved); the numbers glide to the real value at ≤ 30fps
  const prevPx = useRef(null); const [tick, setTick] = useState({ n: 0, heat: 0, dir: 0 });
  useEffect(() => { const t = tickHeat(prevPx.current, livePrice); prevPx.current = livePrice; if (t.dir) setTick(x => ({ n: x.n + 1, heat: t.heat, dir: t.dir })); }, [livePrice]);
  const ok = pos && pos.tokensHeld > 0 && livePrice > 0; const sum0 = ok ? pnlSummary(pos, livePrice) : null;
  const ePct = useEasedNumber(sum0 ? sum0.pct : null); const eUsd = useEasedNumber(sum0 ? sum0.pnl : null); const eVal = useEasedNumber(sum0 ? sum0.value : null);
  if (!ok) return null;
  const fmtMc = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(0)}`);
  const entryPx = Number(pos.fillPrice) || pos.avgEntry; const entryMc = mcPerPrice ? fmtMc(entryPx * mcPerPrice) : null; const nowMc = mcPerPrice ? fmtMc(livePrice * mcPerPrice) : null;
  const sum = pnlSummary(pos, livePrice); const { pct, value } = sum; const usd = sum.pnl;
  const sign = v => (v >= 0 ? '+' : '−');
  const money = v => `$${Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: Math.abs(v) >= 100 ? 0 : 2 })}`;
  const sp = ePct ?? pct; const su = eUsd ?? usd; const sv = eVal ?? value;
  return <div key={flash} className={`my-pnl pnt ${cls} pnt-h-${tick.heat} ${pct >= 0 ? 'up' : 'down'} ${flash ? 'just-traded' : ''} ${open ? 'is-open' : ''}`} data-testid="my-pnl" data-heat={tick.heat}>
    {tick.n ? <i key={tick.n} className={`pnt-tick ${tick.dir > 0 ? 'is-up' : 'is-dn'}`} aria-hidden="true" /> : null}
    <button type="button" className="my-pnl-head" onClick={() => setOpen(o => !o)} aria-expanded={open} title="Your live position · tap for details">
      <small>{label}</small>{label !== 'YOU' ? null : pos.locked ? <small className="my-pnl-lock" title="Entry locked: read from your wallet's transaction and priced at the moment you signed">🔒</small> : !pos.pending && <small className="my-pnl-est" title="Not locked yet: some of this is still an estimate">≈</small>}<b className="pnt-pct">{sign(sp)}{Math.abs(sp).toFixed(Math.abs(sp) >= 100 ? 0 : 2)}%</b><span>{sign(su)}{money(su)}</span><em>{money(sv)}</em><i aria-hidden="true">{open ? '▾' : '▸'}</i>
    </button>
    {open && <div className="my-pnl-more">
      <dl className="m-kv"><dt>Bought</dt><dd>{money(sum.bought)}</dd>{sum.sold > 0 && <><dt>Sold</dt><dd>{money(sum.sold)}</dd></>}<dt>Holding</dt><dd>{money(value)}</dd><dt>Entry</dt><dd>{mcPerPrice ? `MC ${fmtMc(sum.entry * mcPerPrice)}` : `$${tiny(sum.entry, 4)}`} <small>after fees</small></dd><dt>Now</dt><dd>{nowMc ? `MC ${nowMc}` : `$${tiny(livePrice, 4)}`}</dd>
        {pos.realizedUsd ? <><dt>Realized</dt><dd>{sign(pos.realizedUsd)}{money(pos.realizedUsd)}</dd></> : null}{pos.feesUsd ? <><dt>Fees paid</dt><dd>${pos.feesUsd.toFixed(pos.feesUsd < 1 ? 3 : 2)}</dd></> : null}</dl>
      <small className="my-pnl-src" data-testid="my-pnl-src">{label !== 'YOU' ? "the card's own book entry · the chart's live price · fees apart" : pos.pending ? '⏳ just confirmed · reading the exact fill' : pos.locked ? '🔒 locked · exact on-chain amounts, priced at the moment you signed' : pos.exact ? '✓ exact amounts · price still confirming' : '≈ estimate from the quote (fees in) · exact fill not read yet'}{pos.coverage != null && pos.coverage < 0.95 ? ` · ${Math.round(pos.coverage * 100)}% of your coins have a known cost` : ''} · live ~2.5s</small>
      <div className="my-pnl-actions"><ShareGifButton className="my-pnl-share" label="🎞 Share" card={{ kicker: 'LIVE POSITION · FEELESS TRENCHES', title: `$${symbol}`, imageUrl, tone: pct >= 0 ? 'up' : 'down', bigValue: Math.abs(pct), bigPrefix: pct >= 0 ? '+' : '−', bigSuffix: '%', bigDigits: 1, lines: [`${usd >= 0 ? '+' : '−'}$${Math.abs(usd).toLocaleString(undefined, { maximumFractionDigits: 2 })} P&L · bought ${money(sum.bought)} · holding ${money(value)}`, entryMc ? `entry MC ${entryMc} · now MC ${nowMc}` : `entry $${tiny(entryPx, 4)} · live $${tiny(livePrice, 4)}`] }} /><button type="button" className="my-pnl-exit" onClick={() => window.dispatchEvent(new CustomEvent('feeless:quick-exit', { detail: { pct: 100, mint: pair?.baseToken?.address } }))}>Exit</button></div>
    </div>}
  </div>;
}

// the badge a chart draws for itself: `pos` given (a Fuse seat, a position the parent already read) → that; else the viewer's own.
// `live` = the host chart's own scale + live candle → the BUY chip and the P&L tag that rides the candle (ChartLive); `tagOnly` = no pill
// (the parent already shows the numbers — the trench chart's own badge, the cockpit's trade strip).
const firstBuy = pos => { const b = (pos?.trades || []).filter(t => t.side !== 'sell' && Number(t.ts) > 0).map(t => Number(t.ts)); return b.length ? Math.min(...b) : null; };
function OnChart({ pos, live, label }) {
  const entry = Number(pos?.fillPrice) || Number(pos?.avgEntry) || 0; const held = Number(pos?.tokensHeld) || 0;
  if (!live || !(entry > 0) || !(held > 0)) return null;
  return <ChartLive {...live} entry={entry} usd={Number(pos.investedPoolUsd) || Number(pos.investedUsd) || entry * held} at={pos.at || firstBuy(pos)} label={label || 'YOU'} entryWord={live.fmt ? live.fmt(entry) : null} />;
}
function SelfPnl({ pair, price, live }) {
  const [pos, flash] = useMyPosition(pair);
  return <><Badge pos={pos} flash={flash} pair={pair} price={price} /><OnChart pos={pos} live={live} /></>;
}
function Badge({ pos, flash, pair, price, label }) {
  const px = Number(price) > 0 ? Number(price) : Number(pair?.priceUsd) || 0;
  const mc = mcapOf(px, pair?.marketCap, pair?.baseToken?.address) || 0;
  return <PnlBadge pos={pos} flash={flash} pair={pair} price={px} live={Number(price) > 0} label={label} cls="pnt-auto" mcPerPrice={mc > 0 && px > 0 ? mc / px : null}
    symbol={pair?.baseToken?.symbol} imageUrl={pair?.info?.imageUrl} />;
}
export function ChartPnl({ pair, price, pnl, live }) {
  if (pnl === false || !pair?.pairAddress) return null;
  if (!(pnl && typeof pnl === 'object')) return <SelfPnl pair={pair} price={price} live={live} />;
  const pos = pnl.pos || pnl;
  return <>{pnl.tagOnly ? null : <Badge pos={pos} pair={pair} price={price} label={pnl.label} />}<OnChart pos={pos} live={live} label={pnl.label} /></>;
}
