// ⚡ THE FEELESS STACK (Home; replaced the Trench Sieve + the $FEE stamp — owner, 2026-10-14: "the sieve was supposed to show what FEELESS
// is capable of, in a cool way"). Six live engines on one circuit — 🛰 SEES · 🛡 CATCHES · 🌦 READS · 🏃 HUNTS · ⚛ FUSES · 🧾 PROVES — each
// a chip with its REAL number from a public endpoint (a missing number reads "—", never a made-up one), data packets running the bus
// between them, a chip flashing when its number changes, and a ticker of the rugs the scan really caught. Tap a chip → that page.
// Four shared reads every 30s (first load always; repeats pause in a hidden tab). transform / opacity only.
import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
const UNREAD = /not scanned|holders unknown|never scanned/i;
// pure: a coin's fate on the safety scan — "not scanned yet" is waiting, never a fail
export const fateOf = r => (r?.safe === true ? 'safe' : (r?.fails || []).some(f => !UNREAD.test(String(f))) || (r?.safe === false && !(r?.fails || []).length) ? 'fail' : 'wait');
// pure: the coins the scan CAUGHT (busiest first, one per ticker) with the reason it gave
export function caughtCoins(rows, n = 12) {
  const out = []; const seen = new Set();
  for (const r of rows || []) {
    const sy = String(r?.symbol || '').toUpperCase();
    if (!r?.mint || !sy || seen.has(sy) || fateOf(r) !== 'fail') continue;
    seen.add(sy);
    out.push({ mint: r.mint, sym: String(r.symbol).slice(0, 10), pair: r.pairAddress, why: (r.fails || []).some(x => !UNREAD.test(String(x))) ? `missed: ${String((r.fails || []).find(x => !UNREAD.test(String(x)))).replace(/\s+/g, ' ').slice(0, 40)}` : 'failed a safety check' });
    if (out.length >= n) break;
  }
  return out;
}
// pure: every number on the stack, only from what the endpoints answered (null → "—")
export function stackVitals(open, fc, run, prime, proof) {
  const rows = open?.rows || []; const safe = rows.filter(r => fateOf(r) === 'safe').length; const fail = rows.filter(r => fateOf(r) === 'fail').length; const read = safe + fail;
  const cards = Array.isArray(prime?.cards) ? prime.cards : null;
  const feed = Array.isArray(proof?.feed) ? proof.feed : null;
  return { seen: open?.seen ?? (rows.length || null), read: rows.length ? read : null, safe: rows.length ? safe : null, caught: rows.length ? fail : null,
    safePct: read ? Math.round((safe / read) * 100) : null, runners: Array.isArray(run?.live) ? run.live.length : null, nextAt: run?.nextRoundAt || null,
    weather: fc?.level || null, green: fc?.breadthPct ?? null, buyers: fc?.buyersPct ?? null,
    cards: cards ? cards.length : null, real: cards ? cards.filter(c => c?.real).length : null, swaps: feed ? feed.length : null };
}
const WX = { clear: '☀ CLEAR', rain: '🌧 RAIN', storm: '⛈ STORM' };
const num = v => (v == null ? '—' : Number(v).toLocaleString('en-US'));
// pure: the six engines, in the order a coin travels through FEELESS
export function stackChips(v) {
  return [
    { k: 'sees', ico: '🛰', verb: 'SEES', n: num(v.seen), sub: 'launch coins live', go: '/terminal/fuse?tab=runners', tip: 'Every launch coin the feed carries right now — Pump, LetsBONK, LaunchLab, Jupiter rankings' },
    { k: 'catches', ico: '🛡', verb: 'CATCHES', n: num(v.caught), sub: v.read ? `of ${num(v.read)} scanned` : 'scans holders', go: '/terminal/fuse?tab=runners', tip: 'Coins our holder scan caught: top-10 bags, bundles, snipers, dev wallets, live authorities — before a cent goes in', tone: 'bad' },
    { k: 'reads', ico: '🌦', verb: 'READS', n: v.weather ? WX[v.weather] || String(v.weather).toUpperCase() : '—', sub: v.green == null ? 'the market' : `${Math.round(v.green)}% green 1h`, go: '/terminal/fuse?tab=cards', tip: 'Runner weather from paper runs on real prices + the share of launch coins up on the hour. A reading, never a promise.' },
    { k: 'hunts', ico: '🏃', verb: 'HUNTS', n: num(v.runners), sub: 'runners passing every gate', go: '/terminal/fuse?tab=runners', tip: 'Coins passing every runner gate on the live board', clock: v.nextAt },
    { k: 'fuses', ico: '⚛', verb: 'FUSES', n: num(v.cards), sub: v.real ? `${v.real} on real money` : 'cards live', go: '/terminal/fuse?tab=arena', tip: 'Fuse cards trading right now — many coins in one card, exits run by the engine' },
    { k: 'proves', ico: '🧾', verb: 'PROVES', n: num(v.swaps), sub: 'real swaps signed 24h', go: '/terminal/fuse', tip: 'Confirmed on-chain swaps of the real cards in the last 24h, each with its tx and the engine’s reason', tone: 'gold' },
  ];
}
function Clock({ at }) {
  const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), 1000); return () => clearInterval(t); }, []);
  if (!at) return null; const s = Math.max(0, Math.round(at - n / 1000)); return <em className="hen-clock">next round {Math.floor(s / 60)}:{String(s % 60).padStart(2, '0')}</em>;
}

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      Promise.all(['fuses/trench/open', 'fuses/forecast', 'runners', 'fuses/prime', 'fuses/proof'].map(u => sharedJson(`/api/reputation/${u}`, { maxAge: POLL - 2000 }).catch(() => null)))
        .then(([open, fc, run, prime, proof]) => { if (on && (open || fc || run || prime || proof)) setD(p => ({ open: open || p?.open, fc: fc || p?.fc, run: run || p?.run, prime: prime || p?.prime, proof: proof || p?.proof })); }); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  if (!d) return null;
  const v = stackVitals(d.open, d.fc, d.run, d.prime, d.proof); const chips = stackChips(v); const caught = caughtCoins(d.open?.rows);
  const go = (e, url) => { if (onOpen) { e.preventDefault(); onOpen(url); } };
  return <section className={`hen m-card m-live is-${v.weather || 'none'}`} data-testid="home-engine">
    <header className="hen-head"><span className="hen-title"><b>⚡ THE FEELESS STACK <i className="hen-live" aria-hidden="true">● LIVE</i></b>
      <small>six engines, one circuit — every number is live right now</small></span>
      {v.safePct != null ? <em className="hen-wx" data-tip="Of the coins we scanned, the share that passed every safety check">{v.safePct}% pass the scan</em> : null}</header>
    <div className="hen-board">
      <span className="hen-bus" aria-hidden="true">{[0, 1, 2, 3, 4].map(i => <i key={i} style={{ '--i': i }} />)}</span>
      {chips.map((c, i) => <a key={c.k} href={c.go} className={`hen-chip is-${c.k}${c.tone ? ` is-${c.tone}` : ''}`} style={{ '--i': i }} onClick={e => go(e, c.go)} data-tip={c.tip} data-testid={`hen-chip-${c.k}`}>
        <span className="hen-ico" aria-hidden="true">{c.ico}</span><small className="hen-verb">{c.verb}</small>
        <b key={c.n} className="hen-n">{c.n}</b><small className="hen-sub">{c.sub}</small>{c.clock ? <Clock at={c.clock} /> : null}</a>)}
    </div>
    {caught.length ? <div className="hen-tick" data-testid="hen-caught" aria-label="Coins the scan caught">
      <small>🛡 JUST CAUGHT</small>
      <div className="hen-tick-view"><div className="hen-tick-run" style={{ '--tick-sec': `${Math.max(20, caught.length * 4)}s` }}>
        {[0, 1].map(k => <span key={k} className="hen-tick-row" aria-hidden={k ? 'true' : undefined}>
          {caught.map(b => <button key={b.mint} type="button" tabIndex={k ? -1 : 0} onClick={() => openCoin({ mint: b.mint, symbol: b.sym, pairAddress: b.pair })}><b>${b.sym}</b> · {b.why}</button>)}</span>)}
      </div></div></div> : null}
  </section>;
}
