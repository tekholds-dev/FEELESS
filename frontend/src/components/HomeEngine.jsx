// 🔬 WATCH FEELESS WORK (Home; owner, 2026-10-14: "the HUD is confusing — the buys and sells are cool, show what FEELESS is best at").
// One real launch coin at a time goes through the checks FEELESS really runs, animated: 🐋 top-10 · 👤 dev · 📦 bundles + snipers ·
// 💧 pool · 🌊 buyers — each a bar that fills to the coin's own number, ✓ or ✗ against the line — then the verdict STAMPS in
// (🛡 BLOCKED + the check it missed · ✅ CLEARED · 🏃 RUNNER). Every 6s the next coin (caught, cleared and runners mixed). Beside it: the
// real cards' confirmed swaps. One slim counter line. Every number from a public endpoint; an unread number shows "—" with an empty bar.
import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
const SPOT_MS = 6000;
const UNREAD = /not scanned|holders unknown|never scanned/i;
export const fateOf = r => (r?.safe === true ? 'safe' : (r?.fails || []).some(f => !UNREAD.test(String(f))) || (r?.safe === false && !(r?.fails || []).length) ? 'fail' : 'wait');
const usd = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
export const ageWord = h => { const m = Number(h) * 60; return !(m >= 0) ? '' : m < 60 ? `${Math.round(m)}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };

// pure: the checks shown for one coin — value, how full its bar is, pass / fail against the line (null = not read)
export function checksOf(r) {
  const t10 = num(r?.top10); const dev = num(r?.dev); const bun = num(r?.bundledN); const sn = num(r?.snipersN); const liq = num(r?.liq); const buy = num(r?.buyShare);
  return [
    { k: 'top10', ico: '🐋', l: 'TOP-10 HOLD', v: t10 == null ? '—' : `${t10.toFixed(0)}%`, fill: t10 == null ? 0 : Math.min(1, t10 / 100), ok: t10 == null ? null : t10 < 30, line: 'under 30%' },
    { k: 'dev', ico: '👤', l: 'DEV BAG', v: dev == null ? '—' : `${dev.toFixed(1)}%`, fill: dev == null ? 0 : Math.min(1, dev / 20), ok: dev == null ? null : dev < 10, line: 'under 10%' },
    { k: 'bundles', ico: '📦', l: 'BUNDLES · SNIPERS', v: bun == null && sn == null ? '—' : `${bun ?? '?'} · ${sn ?? '?'}`, fill: bun == null && sn == null ? 0 : Math.min(1, ((bun || 0) + (sn || 0)) / 12), ok: bun == null && sn == null ? null : (bun || 0) <= 3 && (sn || 0) <= 8, line: '≤ 3 bundled' },
    { k: 'pool', ico: '💧', l: 'POOL', v: usd(liq), fill: liq == null ? 0 : Math.min(1, Math.log10(Math.max(1, liq)) / 6), ok: liq == null ? null : liq >= 8000, line: '≥ $8K' },
    { k: 'buyers', ico: '🌊', l: 'BUYERS', v: buy == null ? '—' : `${buy.toFixed(0)}%`, fill: buy == null ? 0 : buy / 100, ok: buy == null ? null : buy >= 50, line: '≥ 50%' },
  ];
}
// pure: the coins the spotlight walks through — caught, cleared, runners woven, one per ticker; coins not read yet are skipped
export function spotlight(rows, run, n = 12) {
  const runSet = new Set((run?.live || []).map(r => String(r.symbol || '').toUpperCase()));
  const seen = new Set(); const by = { fail: [], safe: [], runner: [] };
  for (const r of rows || []) {
    const sy = String(r?.symbol || '').toUpperCase(); if (!r?.mint || !sy || seen.has(sy)) continue;
    const f = runSet.has(sy) ? 'runner' : fateOf(r); if (f === 'wait') continue;
    seen.add(sy); by[f].push({ ...r, verdict: f });
  }
  const out = [];
  for (let i = 0; out.length < n && i < n; i++) [by.fail[i], by.safe[i], by.runner[i]].forEach(x => { if (x && out.length < n) out.push(x); });
  return out;
}
export const verdictOf = r => (r.verdict === 'runner' ? ['🏃', 'RUNNER', 'passed every gate and it is running'] : r.verdict === 'safe' ? ['✅', 'CLEARED', 'passed the safety scan']
  : ['🛡', 'BLOCKED', `missed: ${String((r.fails || []).find(x => !UNREAD.test(String(x))) || 'a safety check').replace(/\s+/g, ' ').slice(0, 46).replace(/^./, c => c.toLowerCase())}`]);
// pure: the real cards' confirmed swaps
export const realTrades = (proof, n = 7) => (proof?.feed || []).slice(0, n).map(f => ({ id: f.sig || f.at, side: f.side === 'sell' ? 'sell' : 'buy', sym: f.symbol, mint: f.mint, pair: f.pair,
  pct: f.pct == null ? null : Number(f.pct), usd: Number(f.usd) || 0, at: Number(f.at) || 0 }));
export const counters = (open, run, proof) => ({ live: open?.seen ?? (open?.rows?.length || null), blocked: open?.rows ? open.rows.filter(r => fateOf(r) === 'fail').length : null,
  runners: Array.isArray(run?.live) ? run.live.length : null, swaps: Array.isArray(proof?.feed) ? proof.feed.length : null });
const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null); const [i, setI] = useState(0); const [hold, setHold] = useState(false);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      Promise.all(['fuses/trench/open', 'runners', 'fuses/proof'].map(u => sharedJson(`/api/reputation/${u}`, { maxAge: POLL - 2000 }).catch(() => null)))
        .then(([open, run, proof]) => { if (on && (open || run || proof)) setD(p => ({ open: open || p?.open, run: run || p?.run, proof: proof || p?.proof })); }); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  const spots = useMemo(() => spotlight(d?.open?.rows, d?.run), [d?.open, d?.run]);
  useEffect(() => { if (hold || spots.length < 2) return undefined; const t = setInterval(() => setI(x => x + 1), SPOT_MS); return () => clearInterval(t); }, [hold, spots.length]);
  if (!d) return null;
  const c = counters(d.open, d.run, d.proof); const trades = realTrades(d.proof);
  const cur = spots.length ? spots[i % spots.length] : null; const v = cur ? verdictOf(cur) : null;
  const go = (e, url) => { if (onOpen) { e.preventDefault(); onOpen(url); } };
  const open = x => openCoin({ mint: x.mint, symbol: x.symbol || x.sym, pairAddress: x.pairAddress || x.pair });
  return <section className="wfw" data-testid="home-engine">
    <header className="wfw-top"><span className="wfw-title"><b>WATCH FEELESS WORK</b><i className="wfw-live" aria-hidden="true">● LIVE</i></span>
      <span className="wfw-count" data-testid="wfw-count"><span><b>{c.live ?? '—'}</b> coins live</span><span className="is-bad"><b>{c.blocked ?? '—'}</b> blocked</span><span><b>{c.runners ?? '—'}</b> runners</span><span className="is-gold"><b>{c.swaps ?? '—'}</b> real swaps 24h</span></span></header>
    <div className="wfw-body">
      {cur ? <div className={`wfw-spot is-${cur.verdict}`} key={cur.mint + i} onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)} data-testid="wfw-spot">
        <button type="button" className="wfw-coin" onClick={() => open(cur)} data-testid={`wfw-coin-${cur.symbol}`}>
          {cur.logo ? <img src={cur.logo} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} /> : <i aria-hidden="true">{String(cur.symbol).slice(0, 1)}</i>}
          <b>${String(cur.symbol).slice(0, 12)}</b><small>{cur.ageH != null ? `${ageWord(cur.ageH)} old · ` : ''}cap {usd(num(cur.mcap))}</small></button>
        <ul className="wfw-checks">{checksOf(cur).map((k, j) => <li key={k.k} className={k.ok == null ? 'is-unread' : k.ok ? 'is-ok' : 'is-bad'} style={{ '--j': j }} data-tip={`${k.l}: ${k.v} — the line is ${k.line}`}>
          <span className="wfw-ck"><i aria-hidden="true">{k.ico}</i>{k.l}</span><span className="wfw-bar"><u style={{ '--f': k.fill }} /></span><b>{k.v}</b><em aria-hidden="true">{k.ok == null ? '·' : k.ok ? '✓' : '✗'}</em></li>)}</ul>
        <div className="wfw-stamp" data-testid="wfw-verdict"><b>{v[0]} {v[1]}</b><small>{v[2]}</small></div>
        <span className="wfw-dots" aria-hidden="true">{spots.map((_, j) => <i key={j} className={j === i % spots.length ? 'on' : ''} />)}</span>
      </div> : <div className="wfw-spot is-wait"><small>the scan is reading the first coins…</small></div>}
      <div className="wfw-trades" data-testid="wfw-trades"><small className="wfw-h">💵 REAL MONEY · CONFIRMED SWAPS</small>
        <ol>{trades.map((t, j) => <li key={t.id} className={`is-${t.side}`} style={{ '--j': j }}><button type="button" onClick={() => open(t)}>
          <span className="wfw-side">{t.side === 'sell' ? 'SELL' : 'BUY'}</span><b>${t.sym}</b><span className={t.pct == null ? '' : t.pct >= 0 ? 'up' : 'dn'}>{t.side === 'sell' && t.pct != null ? `${t.pct > 0 ? '+' : ''}${t.pct.toFixed(1)}%` : `$${t.usd.toFixed(2)}`}</span><small>{ago(t.at)}</small></button></li>)}
          {!trades.length ? <li className="is-empty"><small>no real swaps in the last 24h</small></li> : null}</ol></div>
    </div>
    <a className="wfw-go" href="/terminal/fuse?tab=runners" onClick={e => go(e, '/terminal/fuse?tab=runners')}>See every coin it's reading →</a>
  </section>;
}
