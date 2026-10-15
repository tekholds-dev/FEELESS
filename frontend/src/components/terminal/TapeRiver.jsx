import React, { useEffect, useMemo, useRef, useState } from 'react';
import { formatUSD } from '../../lib/dexscreener';
import { investigate } from '../CaseFile';
import '../../styles/tapeRiver.css';

// 🌊 THE TAPE RIVER v2 (owner, 2026-10-15: "a cool realtime animation for the trade tape … click to see what's good and bad" → "do a better
// trade tape river"). The SAME live swaps the tape lists (useTradeStream — no new request), over the last RIVER_SEC:
//   · every trade is a bubble AT THE PRICE IT TRADED (up = higher), across = how long ago (right = now), on a live price line — a dump or a
//     pump is a shape, not a list; green = buy, red = sell, size = log $, 🐋 whales ringed with their $, your trades dashed, flagged wallets
//     (DEV · SNIPER · BUNDLE · TOP) outlined; a new trade lands with a ripple.
//   · the tug: $ bought vs sold in the last 60s + buyers / sellers counted + the momentum arrow (last 10s vs the minute).
// Tap a bubble → who, the $, the wallet's flags, 🔎 case file. Re-laid out once a second (transform with a 1s linear glide, nothing else).
export const RIVER_SEC = 45;

export function bubbleOf(t, cut, nowMs, tags = []) {
  const usd = Number(t.usd) || 0; const age = Math.max(0, (nowMs - Date.parse(t.ts)) / 1000);
  const r = Math.max(4, Math.min(20, 3 + Math.log10(Math.max(1, usd)) * 4));
  const bad = tags.some(g => g.tone === 'bad'); const warn = !bad && tags.some(g => g.tone === 'warn');
  return { id: t.tx, side: t.kind === 'buy' ? 'buy' : 'sell', usd, age, r, whale: usd >= cut, flag: bad ? 'bad' : warn ? 'warn' : null, price: Number(t.price) || 0 };
}

export function tug(trades, nowMs, sec = 60) {
  let buy = 0; let sell = 0; let nb = 0; let ns = 0; let b10 = 0; let s10 = 0; const bw = new Set(); const sw = new Set();
  for (const t of trades) {
    const age = (nowMs - Date.parse(t.ts)) / 1000;
    if (age > sec) continue;
    const u = Number(t.usd) || 0;
    if (t.kind === 'buy') { buy += u; nb += 1; if (t.wallet) bw.add(t.wallet); if (age <= 10) b10 += u; } else { sell += u; ns += 1; if (t.wallet) sw.add(t.wallet); if (age <= 10) s10 += u; }
  }
  const all = buy + sell; const share = all ? buy / all : 0.5; const s10all = b10 + s10; const share10 = s10all ? b10 / s10all : null;
  const word = !all ? 'QUIET' : share >= 0.62 ? 'BUYERS IN CHARGE' : share <= 0.38 ? 'SELLERS IN CHARGE' : 'TUG OF WAR';
  const turn = share10 == null ? null : share10 - share >= 0.15 ? 'up' : share - share10 >= 0.15 ? 'down' : 'flat';
  return { buy, sell, nb, ns, share, word, buyers: bw.size, sellers: sw.size, turn };
}

// price → 0…1 inside the window's own range (a flat window sits in the middle)
export function priceScale(prices) {
  const ps = prices.filter(p => p > 0); if (!ps.length) return () => 0.5;
  const lo = Math.min(...ps); const hi = Math.max(...ps); const span = hi - lo;
  return p => (span > 0 && p > 0 ? (p - lo) / span : 0.5);
}

export function TapeRiver({ trades, cut, tags, me }) {
  const [now, setNow] = useState(() => Date.now()); const [sel, setSel] = useState(null);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000); return () => clearInterval(t); }, []);
  const seen = useRef(null);
  const live = useMemo(() => trades.filter(t => (now - Date.parse(t.ts)) / 1000 < RIVER_SEC).slice(0, 60), [trades, now]);
  const fresh = useMemo(() => { const ids = new Set(live.map(t => t.tx)); const prev = seen.current; seen.current = ids; return prev ? new Set([...ids].filter(x => !prev.has(x))) : new Set(); }, [live]);
  const tg = tug(trades, now);
  const ys = priceScale(live.map(t => Number(t.price) || 0));
  const bubbles = live.map(t => ({ t, b: bubbleOf(t, cut, now, tags.get(t.wallet) || []) }));
  const pts = bubbles.slice().sort((a, z) => z.b.age - a.b.age).map(({ b }) => `${(100 - (b.age / RIVER_SEC) * 100).toFixed(2)},${(92 - ys(b.price) * 84).toFixed(2)}`).join(' ');
  const pick = sel ? trades.find(t => t.tx === sel) : null;
  const pickTags = pick ? (tags.get(pick.wallet) || []) : [];
  const big = new Set(bubbles.slice().sort((a, z) => z.b.usd - a.b.usd).slice(0, 3).map(x => x.b.id));
  return <div className="trv" data-testid="tape-river">
    <div className="trv-tug" data-tip={`last 60s: $${Math.round(tg.buy)} bought by ${tg.buyers} wallets (${tg.nb} buys) vs $${Math.round(tg.sell)} sold by ${tg.sellers} (${tg.ns} sells)`}>
      <b className={`trv-word is-${tg.word === 'BUYERS IN CHARGE' ? 'up' : tg.word === 'SELLERS IN CHARGE' ? 'dn' : 'mid'}`} key={tg.word}>{tg.word}</b>
      <span className="trv-bar" aria-hidden><i style={{ transform: `scaleX(${tg.share.toFixed(3)})` }} /></span>
      <small>{tg.buyers}▲ {tg.sellers}▼ {tg.turn === 'up' ? '↗ buyers rising' : tg.turn === 'down' ? '↘ sellers rising' : ''}</small></div>
    <div className="trv-water" role="list" aria-label="Live trades by price and time">
      <svg className="trv-line" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>{pts ? <polyline points={pts} /> : null}</svg>
      <i className="trv-now" aria-hidden />
      {bubbles.map(({ t, b }) => {
        const mine = t.mine || (me && t.wallet === me);
        const x = 100 - (b.age / RIVER_SEC) * 100; const y = 92 - ys(b.price) * 84;
        return <button key={b.id} type="button" role="listitem" className={`trv-b is-${b.side} ${b.whale ? 'is-whale' : ''} ${b.flag ? `is-${b.flag}` : ''} ${mine ? 'is-mine' : ''} ${sel === b.id ? 'is-on' : ''} ${fresh.has(b.id) ? 'is-new' : ''}`}
          style={{ '--r': `${b.r}px`, transform: `translate(calc(${x.toFixed(2)}cqw - var(--r)), calc(${y.toFixed(2)}cqh - var(--r)))` }}
          onClick={() => setSel(s => (s === b.id ? null : b.id))} data-testid="trv-bubble" aria-label={`${b.side} ${formatUSD(b.usd)}`}>
          {b.whale ? <em>🐋</em> : mine ? <em>✓</em> : null}
          {(b.whale || big.has(b.id)) && b.usd >= 50 ? <small className="trv-usd">{formatUSD(b.usd)}</small> : null}</button>;
      })}
      {!bubbles.length ? <span className="trv-quiet">no trades in the last {RIVER_SEC}s</span> : null}
    </div>
    {pick ? <div className="trv-pop" data-testid="trv-pop">
      <b className={pick.kind === 'buy' ? 'm-pos' : 'm-neg'}>{pick.kind === 'buy' ? 'BUY' : 'SELL'} {formatUSD(pick.usd)}</b>
      <span>{pick.wallet ? `${pick.wallet.slice(0, 4)}…${pick.wallet.slice(-4)}` : 'unknown wallet'}{Number(pick.usd) >= cut ? ' · 🐋 whale for this coin' : ''}</span>
      {pickTags.length ? pickTags.map(g => <em key={g.id} className={`trv-flag is-${g.tone}`} data-tip={g.why}>{g.tone === 'bad' ? '⚠ ' : ''}{g.label} — {g.why}</em>) : <em className="trv-flag is-ok">✓ no flags on this wallet for this coin</em>}
      {pick.wallet ? <button type="button" className="m-btn" onClick={() => investigate(pick.wallet)}>🔎 Case file</button> : null}
      <button type="button" className="m-btn" onClick={() => setSel(null)} aria-label="Close">✕</button></div> : null}
  </div>;
}
