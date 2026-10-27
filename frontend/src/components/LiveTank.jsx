import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import '../styles/liveTank.css';

// 🫧 THE LIVE INTAKE TANK (owner 2026-10-26: "a true intake tank, litty, live realtime"): every pump.fun launch the moment it happens (PumpPortal
// stream via /api/pump/pulse) drops in at the right as a bubble and drifts left as it ages; it floats UP as its market cap grows, size = dev buy,
// colour = how far up its bonding curve it is (green → gold near graduation); a fresh one pops in. Graduations flash along the top. Tap a bubble = its pump.fun page.
// One shared read every 4 s for the whole page; paused while hidden; still under fx-lite / reduced motion.
const sub = new Set(); let cache = null; let timer = null;
async function poll() { if (typeof document !== 'undefined' && document.hidden) return; try { const r = await fetch(apiUrl('/api/pump/pulse?limit=40')); if (r.ok) { cache = await r.json(); sub.forEach(f => f(cache)); } } catch { /* keep the last read */ } }
function usePulse() {
  const [d, setD] = useState(cache);
  useEffect(() => { sub.add(setD); if (!timer) { poll(); timer = setInterval(poll, 4000); } return () => { sub.delete(setD); if (!sub.size) { clearInterval(timer); timer = null; } }; }, []);
  return d;
}
// pure: a launch → where it floats: across = age (newest at the right, drifting left over 10 min), up = market cap on a log scale ($2K at the floor,
// $100K at the top — a coin that pumps floats up), size = dev buy, p = how far up its bonding curve it is
export function place(l, now = Date.now()) {
  const mc = Math.max(2000, Math.min(100000, Number(l.marketCapUsd) || 2000));
  const age = Math.max(0, Math.min(1, (now - Number(l.at || now)) / (10 * 60000)));
  return { x: 1 - age, y: Math.log(mc / 2000) / Math.log(50), r: 6 + Math.min(14, Math.sqrt(Math.max(0, Number(l.devBuySol) || 0)) * 9), p: Math.max(0, Math.min(1, (Number(l.curveProgress) || 0) / 100)) };   // the stream reports curve progress in % (0–100)
}

export function LiveTank({ title = 'LIVE INTAKE · pump.fun launches', compact = false }) {
  const d = usePulse(); const seen = useRef(new Set()); const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(t); }, []);
  const rows = (d?.launches || []).slice(0, compact ? 24 : 40); const now = Date.now();
  const fresh = new Set(rows.filter(l => !seen.current.has(l.mint)).map(l => l.mint)); rows.forEach(l => seen.current.add(l.mint));
  const per = d?.launchesPerMinute || []; const grads = (d?.migrations || []).slice(0, 6);
  return <section className={`ltk ${compact ? 'is-compact' : ''}`} data-testid="live-tank">
    <header><i className={`ltk-dot ${rows.length ? 'is-on' : ''}`} /><b>{title}</b><span className="ltk-k m-num">{d ? `${d.lastMinute} / min` : '…'}</span>
      <span className="ltk-k m-num">{per.reduce((a, x) => a + x, 0)} in 15 min</span></header>
    <div className="ltk-tank" aria-label="New launches: across = time (newest right), up = market cap, colour = bonding-curve progress">
      <i className="ltk-water" aria-hidden="true" /><i className="ltk-glass" aria-hidden="true" />
      {[['$2K', 8], ['$15K', 49], ['$100K', 88]].map(([l, b]) => <em key={l} className="ltk-tick" style={{ bottom: `${b}%` }}>{l}</em>)}<em className="ltk-now">NOW →</em>
      {rows.map(l => { const p = place(l, now); return <a key={l.mint} href={`https://pump.fun/coin/${l.mint}`} target="_blank" rel="noopener noreferrer"
        className={`ltk-b ${fresh.has(l.mint) ? 'is-new' : ''} ${p.p >= 0.6 ? 'is-hot' : ''}`} style={{ left: `${4 + p.x * 92}%`, bottom: `${8 + p.y * 80}%`, '--r': `${p.r}px`, '--p': p.p }}
        data-tip={`$${l.symbol} · ${l.marketCapUsd ? `$${Math.round(l.marketCapUsd).toLocaleString()}` : '—'} MC · ${Math.round(p.p * 100)}% up the curve${l.devBuySol ? ` · dev ${l.devBuySol.toFixed(2)} SOL` : ''}`}>
        <span>{String(l.symbol || '').slice(0, 6)}</span></a>; })}
      {!rows.length ? <p className="ltk-wait">{d ? 'waiting for the next launch…' : 'connecting to the stream…'}</p> : null}
    </div>
    {grads.length && !compact ? <div className="ltk-grads"><em>🎓 GRADUATED</em>{grads.map(g => <span key={g.mint || g.signature}>${g.symbol || String(g.mint || '').slice(0, 4)}</span>)}</div> : null}
  </section>;
}
