import React, { useEffect, useMemo, useState } from 'react';
import { formatUSD } from '../../lib/dexscreener';
import { investigate } from '../CaseFile';
import '../../styles/trenchPulse.css';

// 🥊 TRENCH PULSE (owner, 2026-10-15: "the trade river is ass in trench trading — try a better degen idea"; replaces the Tape River).
// The SAME live swaps the tape lists (useTradeStream — no new request), read the way a trencher reads a chart in 5 seconds:
//   · ONE word: SEND · BUYERS STACKING · CHOP · SELLERS LEAD · DUMPING · 🚨 RUG WATCH (a flagged wallet — dev / sniper / bundle / top
//     holder — is selling) · QUIET, with the reason under it.
//   · PRESSURE BARS: the last 60s in 5-second buckets, buys up / sells down from one line (height = $) — acceleration is a shape.
//   · COUNTERS: buyers vs sellers (unique wallets), fresh wallets buying, biggest buy / sell, flagged $ sold.
//   · WALLET RACE: the 5 wallets pushing hardest over 2 min by NET $ (green = net buyer, red = net seller), flags shown, tap = case file.
// A read of the tape, never a promise. Re-read once a second; bars move by transform only.
export const PULSE_SEC = 60; export const BUCKET = 5; export const RACE_SEC = 120;
const ageOf = (t, now) => (now - Date.parse(t.ts)) / 1000;
const isBad = tags => (tags || []).some(g => g.tone === 'bad');

export function buckets(trades, now, sec = PULSE_SEC, step = BUCKET) {
  const n = Math.ceil(sec / step); const out = Array.from({ length: n }, () => ({ buy: 0, sell: 0 }));
  for (const t of trades || []) { const a = ageOf(t, now); if (a < 0 || a >= sec) continue; const i = n - 1 - Math.floor(a / step); out[i][t.kind === 'buy' ? 'buy' : 'sell'] += Number(t.usd) || 0; }
  return out;
}

export function pulse(trades, now, tags = new Map(), seenBefore = new Set()) {
  let buy = 0; let sell = 0; let badSell = 0; let topB = null; let topS = null; let b20 = 0; let s20 = 0;
  const bw = new Set(); const sw = new Set(); const fresh = new Set(); const badWho = new Set();
  for (const t of trades || []) {
    const a = ageOf(t, now); if (a < 0 || a > PULSE_SEC) continue;
    const u = Number(t.usd) || 0; const w = t.wallet;
    if (t.kind === 'buy') { buy += u; if (w) { bw.add(w); if (!seenBefore.has(w)) fresh.add(w); } if (!topB || u > topB.usd) topB = { usd: u, wallet: w }; if (a <= 20) b20 += u; }
    else { sell += u; if (w) sw.add(w); if (!topS || u > topS.usd) topS = { usd: u, wallet: w }; if (a <= 20) s20 += u; if (w && isBad(tags.get(w))) { badSell += u; badWho.add(w); } }
  }
  const all = buy + sell; const share = all ? buy / all : 0.5; const s20all = b20 + s20; const share20 = s20all ? b20 / s20all : share;
  const rising = share20 - share >= 0.12; const fading = share - share20 >= 0.12;
  let word; let why;
  if (badSell >= 50 && badSell >= sell * 0.25) { word = 'RUG WATCH'; why = `${badWho.size} flagged wallet${badWho.size > 1 ? 's' : ''} sold ${formatUSD(badSell)} in the last minute`; }
  else if (!all) { word = 'QUIET'; why = 'no trades in the last minute'; }
  else if (share >= 0.7 && bw.size >= 5 && !fading) { word = 'SEND'; why = `${bw.size} wallets bought ${formatUSD(buy)} vs ${formatUSD(sell)} sold`; }
  else if (share >= 0.58) { word = 'BUYERS STACKING'; why = `${Math.round(share * 100)}% of the $ is buying${rising ? ', and rising' : fading ? ', but cooling' : ''}`; }
  else if (share <= 0.3 && sw.size >= 3) { word = 'DUMPING'; why = `${sw.size} wallets sold ${formatUSD(sell)} vs ${formatUSD(buy)} bought`; }
  else if (share <= 0.42) { word = 'SELLERS LEAD'; why = `${Math.round((1 - share) * 100)}% of the $ is selling${rising ? ', buyers stepping in' : ''}`; }
  else { word = 'CHOP'; why = `even fight — ${bw.size} buyers vs ${sw.size} sellers`; }
  return { word, why, buy, sell, share, buyers: bw.size, sellers: sw.size, fresh: fresh.size, topB, topS, badSell, turn: rising ? 'up' : fading ? 'down' : 'flat' };
}

export function race(trades, now, tags = new Map(), n = 5) {
  const by = new Map();
  for (const t of trades || []) {
    if (!t.wallet || ageOf(t, now) > RACE_SEC) continue;
    const r = by.get(t.wallet) || { wallet: t.wallet, net: 0, n: 0, mine: false }; const u = Number(t.usd) || 0;
    r.net += t.kind === 'buy' ? u : -u; r.n += 1; r.mine = r.mine || !!t.mine; by.set(t.wallet, r);
  }
  const rows = [...by.values()].sort((a, z) => Math.abs(z.net) - Math.abs(a.net)).slice(0, n);
  const max = Math.max(1, ...rows.map(r => Math.abs(r.net)));
  return rows.map(r => ({ ...r, w: Math.abs(r.net) / max, tags: tags.get(r.wallet) || [] }));
}

const WORD_TONE = { SEND: 'up', 'BUYERS STACKING': 'up', CHOP: 'mid', QUIET: 'mid', 'SELLERS LEAD': 'dn', DUMPING: 'dn', 'RUG WATCH': 'rug' };
const short = w => (w ? `${w.slice(0, 4)}…${w.slice(-4)}` : '?');

export function TrenchPulse({ trades, tags = new Map(), me }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000); return () => clearInterval(t); }, []);
  const older = useMemo(() => new Set((trades || []).filter(t => ageOf(t, now) > PULSE_SEC && t.wallet).map(t => t.wallet)), [trades, now]);
  const p = pulse(trades, now, tags, older);
  const bars = buckets(trades, now); const peak = Math.max(1, ...bars.map(b => Math.max(b.buy, b.sell)));
  const rows = race(trades, now, tags);
  const tone = WORD_TONE[p.word] || 'mid';
  return <div className={`tpl is-${tone}`} data-testid="trench-pulse">
    <div className="tpl-top">
      <b className={`tpl-word is-${tone}`} key={p.word} data-testid="tpl-word">{p.word === 'RUG WATCH' ? '🚨 ' : p.word === 'SEND' ? '🚀 ' : ''}{p.word}</b>
      <small className="tpl-why">{p.why}{p.turn === 'up' ? ' ↗' : p.turn === 'down' ? ' ↘' : ''}</small>
      <span className="tpl-share" data-tip="share of the last 60s $ that was buying"><b className={p.share >= 0.5 ? 'm-pos' : 'm-neg'}>{Math.round(p.share * 100)}%</b><small>BUYS</small></span>
    </div>
    <div className="tpl-tug" aria-hidden><i style={{ transform: `scaleX(${p.share.toFixed(3)})` }} /><u style={{ left: `${(p.share * 100).toFixed(1)}%` }} /></div>
    <div className="tpl-bars" aria-label="Buy and sell pressure, last 60 seconds in 5-second steps" data-tip="Last 60s in 5-second steps — green up = $ bought, red down = $ sold. Right = now.">
      {bars.map((b, i) => <span key={i} className={`tpl-col ${i === bars.length - 1 ? 'is-now' : ''}`}><i className="is-b" style={{ transform: `scaleY(${(b.buy / peak).toFixed(3)})` }} /><i className="is-s" style={{ transform: `scaleY(${(b.sell / peak).toFixed(3)})` }} /></span>)}
    </div>
    <div className="tpl-kpis">
      <span data-tip="unique wallets buying vs selling in the last 60s"><em>WALLETS</em><b><i className="m-pos">{p.buyers}▲</i> <i className="m-neg">{p.sellers}▼</i></b></span>
      <span data-tip="wallets buying that the tape had not seen before this minute"><em>FRESH BUYERS</em><b>{p.fresh}</b></span>
      <span data-tip={p.topB?.wallet ? `biggest buy · ${p.topB.wallet}` : 'no buy'}><em>TOP BUY</em><b className="m-pos">{p.topB ? formatUSD(p.topB.usd) : '—'}</b></span>
      <span data-tip={p.topS?.wallet ? `biggest sell · ${p.topS.wallet}` : 'no sell'}><em>TOP SELL</em><b className="m-neg">{p.topS ? formatUSD(p.topS.usd) : '—'}</b></span>
      <span className={p.badSell > 0 ? 'is-alarm' : ''} data-tip="$ sold in the last 60s by wallets flagged on this coin (dev · sniper · bundle · top holder)"><em>FLAGGED SOLD</em><b>{p.badSell > 0 ? formatUSD(p.badSell) : '0'}</b></span>
    </div>
    {rows.length ? <ol className="tpl-race" aria-label="Wallets pushing hardest, last 2 minutes">
      {rows.map(r => { const mine = r.mine || (me && r.wallet === me); const bad = isBad(r.tags);
        return <li key={r.wallet}><button type="button" className={`tpl-row ${r.net >= 0 ? 'is-b' : 'is-s'} ${bad ? 'is-bad' : ''}`} onClick={() => investigate(r.wallet)} data-tip={`${r.n} trades · net ${formatUSD(r.net)} in 2 min${r.tags.length ? ` · ${r.tags.map(g => g.label).join(', ')}` : ''} — tap for the case file`}>
          <code>{mine ? '✓ YOU' : short(r.wallet)}</code><span className="tpl-tags">{r.tags.slice(0, 2).map(g => <em key={g.id || g.label} className={`tpl-tag is-${g.tone}`}>{g.label}</em>)}</span>
          <span className="tpl-net"><i style={{ transform: `scaleX(${r.w.toFixed(3)})` }} /></span><b>{r.net >= 0 ? '+' : '−'}{formatUSD(Math.abs(r.net))}</b></button></li>; })}
    </ol> : null}
  </div>;
}
