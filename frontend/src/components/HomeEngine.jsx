// ⚛ THE FUSE REACTOR (Home): what FEELESS does in the background, drawn from its own public numbers. Real launch coins ORBIT the core
// (tap = its drawer): ⚠ failed the safety scan = the outer ring, ❔ holders not read yet = the middle ring, ✅ passed = the inner ring,
// next to the core. The core beats with the market (faster the more coins are green) and holds the runners live right now.
// Three shared reads every 30s (first load always; repeats pause in a hidden tab). transform / opacity only.
import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
export const fateOf = r => (r?.safe === true ? 'safe' : (r?.safe === false || (r?.fails || []).length) ? 'fail' : 'wait');
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
// pure: the three rings of the reactor — a few real coins per fate (outer = failed, middle = not read, inner = safe)
export const RINGS = [['fail', 5, 38], ['wait', 4, 30], ['safe', 5, 22]];   // fate · seats · seconds per orbit
export function reactorRings(rows) {
  const pods = enginePods(rows, 60);
  return RINGS.map(([fate, n, sec]) => ({ fate, sec, pods: pods.filter(p => p.fate === fate).slice(0, n) }));
}
// pure: the core's beat — 0.7s when the whole board is green, 2.4s when nothing is (no reading = a slow 2s)
export const beatSec = green => (green == null ? 2 : Math.round((2.4 - 1.7 * Math.max(0, Math.min(100, green)) / 100) * 100) / 100);
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
  const v = engineVitals(d.open, d.fc, d.run); const rings = reactorRings(d.open?.rows); const top = Math.max(1, Number(v.seen) || 1);
  const gates = [['🛰', 'SEEN', v.seen, 'Launch coins the feed carries right now'], ['🔬', 'SCANNED', v.read, 'Coins whose holders we have read (top-10, dev, bundles, snipers)'],
    ['✅', 'SAFE', v.safe, 'Coins that passed every safety check'], ['🏃', 'RUNNERS', v.runners, 'Coins passing every runner gate on the live board']];
  return <section className={`hen m-card is-${v.weather || 'none'}`} data-testid="home-engine">
    <div className="hen-reactor" data-testid="hen-belt" aria-label="Live coins orbiting the Fuse core" style={{ '--beat': `${beatSec(v.green)}s` }}>
      {rings.map((r, ri) => <span key={r.fate} className={`hen-ring is-${r.fate}`} style={{ '--r': ri }} aria-hidden="true" />)}
      {rings.map((r, ri) => r.pods.map((p, i) => { const ang = Math.round((360 * i) / Math.max(1, r.pods.length)); const delay = `${-(r.sec * i) / Math.max(1, r.pods.length)}s`; const dir = ri === 1 ? 'reverse' : 'normal';
        return <span key={p.mint} className={`hen-orb is-${r.fate}`} style={{ '--r': ri, transform: `rotate(${ang}deg)`, animationDuration: `${r.sec}s`, animationDelay: delay, animationDirection: dir }}>
          <span className="hen-seat" style={{ transform: `rotate(${-ang}deg)`, animationDuration: `${r.sec}s`, animationDelay: delay, animationDirection: dir }}>
            <button type="button" className={`hen-pod ${p.m5 >= 0 ? 'is-up' : 'is-dn'}`} onClick={() => openCoin({ mint: p.mint, symbol: p.sym, pairAddress: p.pair })} data-testid={`hen-pod-${p.sym}`}
              data-tip={`$${p.sym} · ${FATE[p.fate]} · ${p.m5 >= 0 ? '+' : ''}${p.m5.toFixed(1)}% in 5 min`}>${p.sym}</button></span></span>; }))}
      <span className="hen-core" data-tip="Runners live right now. The core beats faster the more launch coins are green on the hour."><i aria-hidden="true" /><i aria-hidden="true" /><b key={v.runners}>{num(v.runners)}</b><small>RUNNERS</small></span>
    </div>
    <div className="hen-side">
      <header className="hen-head"><span className="hen-title"><b>⚛ THE FUSE REACTOR</b><small>real coins orbit until they earn the core — tap one</small></span>
        {v.weather ? <em className="hen-wx" data-testid="hen-weather" data-tip="Runner weather: how recent paper runs on real prices ended. A reading, never a promise.">{WX[v.weather] || String(v.weather).toUpperCase()}{v.trend ? ` · ${v.trend}` : ''}</em> : null}</header>
      <div className="hen-gates">{gates.map(([ico, l, n, tip], i) => <span key={l} className="hen-gate" style={{ '--i': i }} data-tip={tip} data-testid={`hen-gate-${l.toLowerCase()}`}><i aria-hidden="true">{ico}</i><small>{l}</small><b key={n}>{num(n)}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${n == null ? 0 : Math.max(0.03, Math.min(1, n / top))})` }} /></u></span>)}</div>
      <div className="hen-legend" aria-hidden="true"><span className="is-safe">● inner · safe</span><span className="is-wait">● middle · not read</span><span className="is-fail">● outer · failed</span></div>
      <div className="hen-vitals"><Meter l="GREEN 1H" v={v.green} tone={v.green != null && v.green < 40 ? 'bad' : 'ok'} tip="Share of live launch coins up on the hour" />
        <Meter l="BUYERS" v={v.buyers} tone={v.buyers != null && v.buyers < 50 ? 'bad' : 'ok'} tip="Typical share of trades that are buys across the board" />
        <Meter l="SAFE RATE" v={v.safePct} tone="ice" tip="Of the coins we scanned, the share that passed every safety check" />
        <span className="hen-meter is-clock" data-tip="Time to the runner board's next round"><small>NEXT ROUND</small><Clock at={v.nextAt} /><i><u className="hen-tick" /></i></span></div>
      <a className="hen-go" href="/terminal/fuse?tab=runners" onClick={e => { if (onOpen) { e.preventDefault(); onOpen('/terminal/fuse?tab=runners'); } }}>Open the lists →</a>
    </div>
  </section>;
}
