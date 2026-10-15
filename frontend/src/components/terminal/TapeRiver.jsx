import React, { useEffect, useState } from 'react';
import { formatUSD } from '../../lib/dexscreener';
import { investigate } from '../CaseFile';
import '../../styles/tapeRiver.css';

// 🌊 THE TAPE RIVER (owner, 2026-10-15: "a cool realtime animation for the trade tape — like the intake band, with the buyer / seller amount +
// colour, click to see what's good and bad"). The SAME live swaps the tape lists (useTradeStream — no new request) drawn as bubbles drifting
// right → left over the last RIVER_SEC: green buys above the line, red sells below, size = log of the $, whales ringed, your own trades
// marked, wallets the coin's intel flags (DEV · SNIPER · BUNDLE · TOP) outlined. On top: the buy / sell tug of the last minute + a one-word
// read. Tap a bubble → who it was, the $ and the flags + 🔎 case file. transform / opacity only; a bubble's drift is ONE finite animation.
export const RIVER_SEC = 45;

export function bubbleOf(t, cut, nowMs, tags = []) {
  const usd = Number(t.usd) || 0; const age = Math.max(0, (nowMs - Date.parse(t.ts)) / 1000);
  const r = Math.max(5, Math.min(22, 4 + Math.log10(Math.max(1, usd)) * 4.2));
  const bad = tags.some(g => g.tone === 'bad'); const warn = !bad && tags.some(g => g.tone === 'warn');
  return { id: t.tx, side: t.kind === 'buy' ? 'buy' : 'sell', usd, age, r, whale: usd >= cut, flag: bad ? 'bad' : warn ? 'warn' : null, lane: (parseInt(String(t.tx || '').slice(-3), 36) || 0) % 3 };
}

export function tug(trades, nowMs, sec = 60) {
  let buy = 0; let sell = 0; let nb = 0; let ns = 0;
  for (const t of trades) {
    if ((nowMs - Date.parse(t.ts)) / 1000 > sec) continue;
    const u = Number(t.usd) || 0;
    if (t.kind === 'buy') { buy += u; nb += 1; } else { sell += u; ns += 1; }
  }
  const all = buy + sell; const share = all ? buy / all : 0.5;
  const word = !all ? 'QUIET' : share >= 0.62 ? 'BUYERS IN CHARGE' : share <= 0.38 ? 'SELLERS IN CHARGE' : 'TUG OF WAR';
  return { buy, sell, nb, ns, share, word };
}

export function TapeRiver({ trades, cut, tags, me }) {
  const [now, setNow] = useState(() => Date.now()); const [sel, setSel] = useState(null);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 5000); return () => clearInterval(t); }, []);
  const live = trades.filter(t => (now - Date.parse(t.ts)) / 1000 < RIVER_SEC).slice(0, 60);
  const tg = tug(trades, now);
  const pick = sel ? trades.find(t => t.tx === sel) : null;
  const pickTags = pick ? (tags.get(pick.wallet) || []) : [];
  return <div className="trv" data-testid="tape-river">
    <div className="trv-tug" data-tip={`last 60s: $${Math.round(tg.buy)} bought (${tg.nb}) vs $${Math.round(tg.sell)} sold (${tg.ns})`}>
      <b className={`trv-word is-${tg.word === 'BUYERS IN CHARGE' ? 'up' : tg.word === 'SELLERS IN CHARGE' ? 'dn' : 'mid'}`} key={tg.word}>{tg.word}</b>
      <span className="trv-bar" aria-hidden><i style={{ transform: `scaleX(${tg.share.toFixed(3)})` }} /></span>
      <small>{formatUSD(tg.buy)} ▲ · ▼ {formatUSD(tg.sell)}</small></div>
    <div className="trv-water" role="list" aria-label="Live trades as bubbles">
      <i className="trv-mid" aria-hidden />
      {live.map(t => {
        const b = bubbleOf(t, cut, now, tags.get(t.wallet) || []); const mine = t.mine || (me && t.wallet === me);
        return <button key={b.id} type="button" role="listitem" className={`trv-b is-${b.side} ${b.whale ? 'is-whale' : ''} ${b.flag ? `is-${b.flag}` : ''} ${mine ? 'is-mine' : ''} ${sel === b.id ? 'is-on' : ''}`}
          style={{ '--r': `${b.r}px`, '--dur': `${RIVER_SEC}s`, '--delay': `-${b.age.toFixed(1)}s`, '--lane': b.lane }}
          onClick={() => setSel(s => (s === b.id ? null : b.id))} data-testid="trv-bubble" aria-label={`${b.side} ${formatUSD(b.usd)}`}>
          {b.whale ? <em>🐋</em> : mine ? <em>✓</em> : null}</button>;
      })}
    </div>
    {pick ? <div className="trv-pop" data-testid="trv-pop">
      <b className={pick.kind === 'buy' ? 'm-pos' : 'm-neg'}>{pick.kind === 'buy' ? 'BUY' : 'SELL'} {formatUSD(pick.usd)}</b>
      <span>{pick.wallet ? `${pick.wallet.slice(0, 4)}…${pick.wallet.slice(-4)}` : 'unknown wallet'}{Number(pick.usd) >= cut ? ' · 🐋 whale for this coin' : ''}</span>
      {pickTags.length ? pickTags.map(g => <em key={g.id} className={`trv-flag is-${g.tone}`} data-tip={g.why}>{g.tone === 'bad' ? '⚠ ' : ''}{g.label} — {g.why}</em>) : <em className="trv-flag is-ok">✓ no flags on this wallet for this coin</em>}
      {pick.wallet ? <button type="button" className="m-btn" onClick={() => investigate(pick.wallet)}>🔎 Case file</button> : null}
      <button type="button" className="m-btn" onClick={() => setSel(null)} aria-label="Close">✕</button></div> : null}
  </div>;
}
