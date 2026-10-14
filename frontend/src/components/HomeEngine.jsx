// 🧪 THE TRENCH SIEVE (Home; replaced the orbiting reactor — owner, 2026-10-14: "outdo the fuse reactor, it reminds people of ideas already
// made"): what the safety scan really does, coin by coin. Real launch coins FALL down a column through four laser gates — 🔬 SCAN · 🐋 HOLDERS ·
// 📦 BUNDLES · 👤 DEV. A coin that failed stops at the gate that caught it (its own fail reason), is zapped and drops into the ☠ rug pit; a
// coin not read yet hovers at the scanner; a coin that passed every gate falls into the 🏦 vault, where the runners live right now glow.
// Tap any coin → its drawer. Three shared reads every 30s (first load always; repeats pause in a hidden tab). transform / opacity only.
import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
const UNREAD = /not scanned|holders unknown|never scanned/i;
export const fateOf = r => (r?.safe === true ? 'safe' : (r?.fails || []).some(f => !UNREAD.test(String(f))) || (r?.safe === false && !(r?.fails || []).length) ? 'fail' : 'wait');   // "not scanned yet" is not a fail
// pure: the gate that caught a failed coin (0 scan · 1 holders · 2 bundles · 3 dev / creator), from its own first real fail reason
export const SIEVE_GATES = [['🔬', 'SCAN'], ['🐋', 'HOLDERS'], ['📦', 'BUNDLES'], ['👤', 'DEV']];
export function gateOf(r) {
  const f = String(((r?.fails || []).find(x => !UNREAD.test(String(x)))) || '');
  return /top[ -]?10|holder|whale|concentrat/i.test(f) ? 1 : /sniper|bundl|insider/i.test(f) ? 2 : /dev|creator|mint|freeze|authorit|rug/i.test(f) ? 3 : 0;
}
// pure: the coins falling through the sieve — a mix of fates (busiest first), each with its gate, its lane and its place in the loop
export function sieveDrops(rows, n = 12) {
  const pods = enginePods(rows, 80); const by = { safe: [], fail: [], wait: [] };
  pods.forEach(p => by[p.fate].push(p));
  const pick = [...by.fail.slice(0, 5), ...by.safe.slice(0, 4), ...by.wait.slice(0, 3)].slice(0, n);
  return pick.map((p, i) => { const r = (rows || []).find(x => x.mint === p.mint) || {};
    return { ...p, gate: p.fate === 'fail' ? gateOf(r) : p.fate === 'wait' ? 0 : 4, lane: (i * 37) % 76 + 6, delay: -((i * 1.9) % 11.4).toFixed(2), why: p.fate === 'fail' ? String((r.fails || []).find(x => !UNREAD.test(String(x))) || 'failed a safety check').slice(0, 48) : null }; });
}
// pure: the pods on the belt — busiest coins first, a mix of fates so the belt shows what the scan really does
export function enginePods(rows, n = 14) {
  const out = []; const seen = new Set();
  for (const r of rows || []) { const sy = String(r?.symbol || '').toUpperCase(); if (!r?.mint || !sy || seen.has(r.mint) || seen.has(sy)) continue; seen.add(r.mint); seen.add(sy); out.push({ mint: r.mint, sym: String(r.symbol).slice(0, 10), fate: fateOf(r), m5: Number(r.chg5m) || 0, pair: r.pairAddress }); if (out.length >= n) break; }
  return out;
}
// pure: the gate counts + vitals, only from what the endpoints answered (a missing number stays null → "—")
export function engineVitals(open, fc, run) {
  const rows = open?.rows || []; const safe = rows.filter(r => fateOf(r) === 'safe').length; const fail = rows.filter(r => fateOf(r) === 'fail').length;
  const read = safe + fail;
  return { seen: open?.seen ?? (rows.length || null), listed: rows.length || null, read: rows.length ? read : null, safe: rows.length ? safe : null, safePct: read ? Math.round((safe / read) * 100) : null,
    runners: Array.isArray(run?.live) ? run.live.length : null, nextAt: run?.nextRoundAt || null, weather: fc?.level || null, trend: fc?.trend || null, green: fc?.breadthPct ?? null, buyers: fc?.buyersPct ?? null };
}
// pure: the core's beat — 0.7s when the whole board is green, 2.4s when nothing is (no reading = a slow 2s)
export const beatSec = green => (green == null ? 2 : Math.round((2.4 - 1.7 * Math.max(0, Math.min(100, green)) / 100) * 100) / 100);
// pure: the live scan heartbeat — one beat per real coin the scan judged (up = passed, down = caught, a blip = not read yet) + what it caught
export function scanBeats(rows, n = 22) {
  return enginePods(rows, n).map(p => { const r = (rows || []).find(x => x.mint === p.mint) || {};
    return { ...p, why: p.fate === 'fail' ? ((r.fails || [])[0] ? `failed “${String(r.fails[0]).replace(/\s+/g, ' ').slice(0, 40)}”` : 'failed a safety check') : null }; });
}
const BEAT_W = 64;
export function beatPath(beats, h = 26, mid = 30) {
  let d = `M0 ${mid}`;
  beats.forEach((b, i) => { const x = i * BEAT_W + BEAT_W / 2; const k = b.fate === 'safe' ? -h : b.fate === 'fail' ? h : -h * 0.25;
    d += ` L${x - 12} ${mid} L${x - 6} ${mid - k * 0.25} L${x - 2} ${mid + k} L${x + 3} ${mid - k * 0.45} L${x + 8} ${mid} `; });
  return `${d} L${beats.length * BEAT_W} ${mid}`;
}
function ScanPulse({ rows }) {
  const beats = scanBeats(rows); if (beats.length < 4) return null;
  const caught = beats.filter(b => b.fate === 'fail').slice(0, 3); const w = beats.length * BEAT_W; const path = beatPath(beats);
  const strip = k => <div className="hen-ekg-strip" key={k} style={{ width: w }} aria-hidden={k ? 'true' : undefined}>
    <svg width={w} height="60" viewBox={`0 0 ${w} 60`} preserveAspectRatio="none"><path d={path} className="hen-ekg-line" /></svg>
    {beats.map((b, i) => <button key={b.mint} type="button" tabIndex={k ? -1 : 0} className={`hen-beat is-${b.fate}`} style={{ left: i * BEAT_W + BEAT_W / 2 }} onClick={() => openCoin({ mint: b.mint, symbol: b.sym, pairAddress: b.pair })}
      data-tip={`$${b.sym} · ${FATE[b.fate]}${b.why ? ` — ${b.why}` : ''}`}>${b.sym}</button>)}</div>;
  return <div className="hen-ekg" data-testid="hen-ekg" style={{ '--ekg-sec': `${Math.max(18, beats.length * 1.6)}s` }}>
    <small className="hen-ekg-l">🫀 LIVE SCAN · every beat is a real launch coin read · up = passed · down = caught</small>
    <div className="hen-ekg-view"><div className="hen-ekg-run">{strip(0)}{strip(1)}</div></div>
    {caught.length ? <p className="hen-caught" data-testid="hen-caught">{caught.map(b => <button key={b.mint} type="button" onClick={() => openCoin({ mint: b.mint, symbol: b.sym, pairAddress: b.pair })}>🛡 caught <b>${b.sym}</b> · {b.why}</button>)}</p> : null}
  </div>;
}
const WX = { clear: '☀ CLEAR', rain: '🌧 RAIN', storm: '⛈ STORM' };
const FATE = { safe: 'passed the safety scan', fail: 'failed the safety scan', wait: 'holders not read yet' };
const num = v => (v == null ? '—' : Number(v).toLocaleString('en-US'));
function Meter({ l, v, tone, tip }) {
  const p = v == null ? 0 : Math.max(0, Math.min(100, Number(v)));
  return <span className={`hen-meter is-${tone || 'ok'}`} data-tip={tip}><small>{l}</small><b key={v}>{v == null ? '—' : `${Math.round(p)}%`}</b><i><u style={{ transform: `scaleX(${p / 100})` }} /></i></span>;
}
function Clock({ at }) {
  const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), 1000); return () => clearInterval(t); }, []);
  if (!at) return <b>—</b>; const s = Math.max(0, Math.round(at - n / 1000)); return <b>{Math.floor(s / 60)}:{String(s % 60).padStart(2, '0')}</b>;
}

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      Promise.all(['fuses/trench/open', 'fuses/forecast', 'runners'].map(u => sharedJson(`/api/reputation/${u}`, { maxAge: POLL - 2000 }).catch(() => null)))
        .then(([open, fc, run]) => { if (on && (open || fc || run)) setD(p => ({ open: open || p?.open, fc: fc || p?.fc, run: run || p?.run, at: Date.now() })); }); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  if (!d) return null;
  const v = engineVitals(d.open, d.fc, d.run); const drops = sieveDrops(d.open?.rows); const top = Math.max(1, Number(v.seen) || 1);
  const gates = [['🛰', 'SEEN', v.seen, 'Launch coins the feed carries right now'], ['🔬', 'SCANNED', v.read, 'Coins whose holders we have read (top-10, dev, bundles, snipers)'],
    ['✅', 'SAFE', v.safe, 'Coins that passed every safety check'], ['🏃', 'RUNNERS', v.runners, 'Coins passing every runner gate on the live board']];
  return <section className={`hen m-card is-${v.weather || 'none'}`} data-testid="home-engine">
    <div className="hen-sieve" data-testid="hen-belt" aria-label="Live launch coins falling through the safety gates">
      <span className="hen-scanline" aria-hidden="true" />
      {SIEVE_GATES.map(([ico, l], g) => <span key={l} className="hen-laser" style={{ '--g': g }} aria-hidden="true"><i /><small>{ico} {l}</small></span>)}
      {drops.map(p => <span key={p.mint} className={`hen-drop is-${p.fate}`} style={{ '--g': p.gate, '--lane': `${p.lane}%`, animationDelay: `${p.delay}s` }}>
        <button type="button" className={`hen-pod ${p.m5 >= 0 ? 'is-up' : 'is-dn'}`} onClick={() => openCoin({ mint: p.mint, symbol: p.sym, pairAddress: p.pair })} data-testid={`hen-pod-${p.sym}`}
          data-tip={`$${p.sym} · ${FATE[p.fate]}${p.why ? ` — caught at ${SIEVE_GATES[p.gate][1]}: ${p.why}` : ''} · ${p.m5 >= 0 ? '+' : ''}${p.m5.toFixed(1)}% in 5 min`}>${p.sym}</button></span>)}
      <span className="hen-pit" data-tip="The rug pit: coins a safety gate caught"><b>☠</b><small>PIT</small></span>
      <span className="hen-core" data-tip="The vault: coins that passed every gate fall in here. The number = runners live right now; it beats faster the more launch coins are green on the hour." style={{ '--beat': `${beatSec(v.green)}s` }}>
        <i aria-hidden="true" /><b key={v.runners}>{num(v.runners)}</b><small>🏦 RUNNERS</small></span>
    </div>
    <div className="hen-side">
      <header className="hen-head"><span className="hen-title"><b>🧪 THE TRENCH SIEVE <i className="hen-live" aria-hidden="true">● LIVE</i></b><small>every live launch coin falls through our safety gates — tap one</small></span>
        {v.weather ? <em className="hen-wx" data-testid="hen-weather" data-tip="Runner weather: how recent paper runs on real prices ended. A reading, never a promise.">{WX[v.weather] || String(v.weather).toUpperCase()}{v.trend ? ` · ${v.trend}` : ''}</em> : null}</header>
      <div className="hen-gates">{gates.map(([ico, l, n, tip], i) => <span key={l} className="hen-gate" style={{ '--i': i }} data-tip={tip} data-testid={`hen-gate-${l.toLowerCase()}`}><i aria-hidden="true">{ico}</i><small>{l}</small><b key={n}>{num(n)}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${n == null ? 0 : Math.max(0.03, Math.min(1, n / top))})` }} /></u></span>)}</div>
      <div className="hen-legend" aria-hidden="true"><span className="is-safe">● falls to the vault · safe</span><span className="is-wait">● hovers · not read yet</span><span className="is-fail">● zapped to the pit · failed</span></div>
      <div className="hen-vitals"><Meter l="GREEN 1H" v={v.green} tone={v.green != null && v.green < 40 ? 'bad' : 'ok'} tip="Share of live launch coins up on the hour" />
        <Meter l="BUYERS" v={v.buyers} tone={v.buyers != null && v.buyers < 50 ? 'bad' : 'ok'} tip="Typical share of trades that are buys across the board" />
        <Meter l="SAFE RATE" v={v.safePct} tone="ice" tip="Of the coins we scanned, the share that passed every safety check" />
        <span className="hen-meter is-clock" data-tip="Time to the runner board's next round"><small>NEXT ROUND</small><Clock at={v.nextAt} /><i><u className="hen-tick" /></i></span></div>
      <ScanPulse rows={d.open?.rows} />
      <a className="hen-go" href="/terminal/fuse?tab=runners" onClick={e => { if (onOpen) { e.preventDefault(); onOpen('/terminal/fuse?tab=runners'); } }}>Open the lists →</a>
    </div>
  </section>;
}
