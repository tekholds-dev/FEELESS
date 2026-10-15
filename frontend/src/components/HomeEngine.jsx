// 🎮 TRENCH HUD (Home; owner, 2026-10-14: "the stack isn't a better design — try meta degen senior design"). A game HUD for the live
// trench, every pixel from real data:
//  · COUNTERS — four big rolling numbers (coins live · rugs blocked · runners · real swaps 24h), digits roll on change
//  · HEAT FIELD — every launch coin the feed carries as a dot: across = market cap (log $5K → $5M), up = its 5-min move, size = 1h
//    volume, colour = its safety scan (green safe · pink caught · grey not read). Dots GLIDE to their new place each poll (transform
//    transition); a caught coin wears an ✕. Tap a dot → its drawer.
//  · KILL FEED — real events, newest on top: 🛡 BLOCKED (a coin the scan caught + why), 🏃 RUNNER (passed every gate, up on the hour),
//    🧾 REAL BUY / SELL (the real cards' confirmed swaps with their %). Slides in, fades as it ages.
// Five shared reads every 30s (first load always; repeats pause in a hidden tab). transform / opacity only; a missing number reads "—".
import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
const UNREAD = /not scanned|holders unknown|never scanned/i;
export const fateOf = r => (r?.safe === true ? 'safe' : (r?.fails || []).some(f => !UNREAD.test(String(f))) || (r?.safe === false && !(r?.fails || []).length) ? 'fail' : 'wait');
const failWhy = r => String((r?.fails || []).find(x => !UNREAD.test(String(x))) || 'failed a safety check').replace(/\s+/g, ' ').slice(0, 40);

// pure: the four counters, only from what the endpoints answered (null → "—")
export function hudCounters(open, run, proof) {
  const rows = open?.rows || [];
  return [
    { k: 'live', l: 'COINS LIVE', v: open?.seen ?? (rows.length || null), tip: 'Launch coins the feed carries right now' },
    { k: 'blocked', l: 'RUGS BLOCKED', v: rows.length ? rows.filter(r => fateOf(r) === 'fail').length : null, tip: 'Coins our holder scan caught on this list: whale bags, bundles, snipers, dev wallets, live authorities', tone: 'bad' },
    { k: 'runners', l: 'RUNNERS', v: Array.isArray(run?.live) ? run.live.length : null, tip: 'Coins passing every runner gate on the live board' },
    { k: 'swaps', l: 'REAL SWAPS 24H', v: Array.isArray(proof?.feed) ? proof.feed.length : null, tip: 'Confirmed on-chain swaps of the real cards in the last 24h', tone: 'gold' },
  ];
}
// pure: the heat field — each coin's place (x, y in %), size and fate; one dot per ticker, busiest first
const LO = Math.log10(5e3); const HI = Math.log10(5e6);
export function heatDots(rows, n = 70) {
  const out = []; const seen = new Set();
  for (const r of rows || []) {
    const sy = String(r?.symbol || '').toUpperCase(); const mc = Number(r?.mcap);
    if (!r?.mint || !sy || seen.has(sy) || !(mc > 0)) continue;
    seen.add(sy);
    const m5 = Math.max(-30, Math.min(30, Number(r.chg5m) || 0));
    out.push({ mint: r.mint, sym: String(r.symbol).slice(0, 10), pair: r.pairAddress, fate: fateOf(r), m5: Number(r.chg5m) || 0, mc,
      x: Math.round(Math.max(2, Math.min(98, ((Math.log10(mc) - LO) / (HI - LO)) * 100)) * 10) / 10,
      y: Math.round((50 - (m5 / 30) * 44) * 10) / 10,
      s: Math.round(Math.max(6, Math.min(26, 4 + Math.sqrt(Math.max(0, Number(r.vol1h) || 0)) / 22))) });
    if (out.length >= n) break;
  }
  return out;
}
// pure: the kill feed — real events only, WOVEN (a real swap · a block · a runner …) in each list's own order: no invented times.
// A coin on the runner board is never also shown as blocked (the two checklists differ; the runner board is the stricter live read).
export function killFeed(rows, run, proof, n = 9) {
  const runs = (run?.live || []).slice(0, 4);
  const onBoard = new Set(runs.map(r => String(r.symbol || '').toUpperCase()));
  const swaps = (proof?.feed || []).slice(0, 4).map(f => ({ id: `p${f.sig || f.at}`, kind: f.side === 'sell' ? 'sell' : 'buy', sym: f.symbol, mint: f.mint, pair: f.pair,
    txt: f.side === 'sell' ? `${f.pct == null ? '' : `${f.pct > 0 ? '+' : ''}${Number(f.pct).toFixed(1)}% · `}real sell` : `real buy · $${Number(f.usd || 0).toFixed(2)}` }));
  const seen = new Set();
  const blocks = (rows || []).filter(r => { const k = String(r.symbol || '').toUpperCase(); if (fateOf(r) !== 'fail' || onBoard.has(k) || seen.has(k)) return false; seen.add(k); return true; })
    .slice(0, 4).map(r => ({ id: `b${r.mint}`, kind: 'block', sym: r.symbol, mint: r.mint, pair: r.pairAddress, txt: `missed: ${failWhy(r).replace(/^./, c => c.toLowerCase())}` }));
  const runners = runs.map((r, i) => ({ id: `r${r.mint || r.pairAddress || i}`, kind: 'runner', sym: r.symbol, mint: r.mint || r.baseAddress, pair: r.pairAddress,
    txt: `passed every gate${r.chg1h != null ? ` · ${Number(r.chg1h) > 0 ? '+' : ''}${Number(r.chg1h).toFixed(0)}% 1h` : ''}` }));
  const out = [];
  for (let i = 0; out.length < n && i < 4; i++) [swaps[i], blocks[i], runners[i]].forEach(e => { if (e?.sym && out.length < n) out.push(e); });
  return out;
}
const KIND = { block: ['🛡', 'BLOCKED'], runner: ['🏃', 'RUNNER'], buy: ['🧾', 'REAL BUY'], sell: ['🧾', 'REAL SELL'] };

// a number whose digits roll when it changes (each digit is a column of 0-9 moved with transform)
function Roll({ v }) {
  if (v == null) return <b className="hud-roll">—</b>;
  const s = Number(v).toLocaleString('en-US');
  return <b className="hud-roll" aria-label={s}>{[...s].map((c, i) => /\d/.test(c)
    ? <span key={`${s.length - i}`} className="hud-dg" aria-hidden="true"><span style={{ transform: `translate3d(0, ${-Number(c) * 10}%, 0)` }}>{'0123456789'.split('').map(d => <i key={d}>{d}</i>)}</span></span>
    : <span key={`${s.length - i}c`} className="hud-sep" aria-hidden="true">{c}</span>)}</b>;
}

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      Promise.all(['fuses/trench/open', 'runners', 'fuses/proof', 'fuses/forecast'].map(u => sharedJson(`/api/reputation/${u}`, { maxAge: POLL - 2000 }).catch(() => null)))
        .then(([open, run, proof, fc]) => { if (on && (open || run || proof || fc)) setD(p => ({ open: open || p?.open, run: run || p?.run, proof: proof || p?.proof, fc: fc || p?.fc })); }); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  const dots = useMemo(() => heatDots(d?.open?.rows), [d?.open]);
  const feed = useMemo(() => killFeed(d?.open?.rows, d?.run, d?.proof), [d?.open, d?.run, d?.proof]);
  if (!d) return null;
  const counters = hudCounters(d.open, d.run, d.proof); const wx = d.fc?.level;
  const go = (e, url) => { if (onOpen) { e.preventDefault(); onOpen(url); } };
  const open = x => openCoin({ mint: x.mint, symbol: x.sym, pairAddress: x.pair });
  return <section className={`hud is-${wx || 'none'}`} data-testid="home-engine">
    <header className="hud-top">
      <span className="hud-brand"><b>TRENCH HUD</b><i className="hud-live" aria-hidden="true">● LIVE</i>{wx ? <em data-tip="Runner weather from paper runs on real prices — a reading, never a promise">{wx === 'clear' ? '☀ CLEAR' : wx === 'rain' ? '🌧 RAIN' : wx === 'storm' ? '⛈ STORM' : String(wx).toUpperCase()}</em> : null}</span>
      <div className="hud-counters">{counters.map(c => <span key={c.k} className={`hud-ct${c.tone ? ` is-${c.tone}` : ''}`} data-tip={c.tip} data-testid={`hud-${c.k}`}><Roll v={c.v} /><small>{c.l}</small></span>)}</div>
    </header>
    <div className="hud-body">
      <div className="hud-field" data-testid="hud-field" aria-label="Every live launch coin by market cap and 5-minute move">
        <i className="hud-axis is-zero" aria-hidden="true" /><small className="hud-lab is-up">▲ 5m pumping</small><small className="hud-lab is-dn">▼ dumping</small>
        <small className="hud-lab is-lo">$5K cap</small><small className="hud-lab is-hi">$5M</small><i className="hud-sweep" aria-hidden="true" />
        {dots.map(p => <button key={p.mint} type="button" className={`hud-dot is-${p.fate}`} onClick={() => open(p)} data-testid={`hud-dot-${p.sym}`}
          style={{ transform: `translate3d(${p.x}cqw, ${p.y}cqh, 0)`, '--s': `${p.s}px` }}
          data-tip={`$${p.sym} · ${p.fate === 'safe' ? 'passed the scan' : p.fate === 'fail' ? 'caught by the scan' : 'not read yet'} · ${p.m5 >= 0 ? '+' : ''}${p.m5.toFixed(1)}% 5m`}>
          <i />{p.s >= 14 ? <b>${p.sym}</b> : null}</button>)}
      </div>
      <ol className="hud-feed" data-testid="hud-feed" aria-label="Live events">
        {feed.map((e, i) => <li key={e.id} className={`is-${e.kind}`} style={{ '--i': i }}><button type="button" onClick={() => open(e)}>
          <span className="hud-k">{KIND[e.kind][0]} {KIND[e.kind][1]}</span><b>${e.sym}</b><small>{e.txt}</small></button></li>)}
        {!feed.length ? <li className="is-empty"><small>waiting for the first events…</small></li> : null}
      </ol>
    </div>
    <a className="hud-go" href="/terminal/fuse?tab=runners" onClick={e => go(e, '/terminal/fuse?tab=runners')}>Open the trench lists →</a>
  </section>;
}
