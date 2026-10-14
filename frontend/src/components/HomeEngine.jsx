// ⚙ THE ENGINE, LIVE (Home): what FEELESS does in the background, drawn from its own public numbers — every launch coin the feed sees flows
// through the scan; each pod is a REAL coin (tap = its drawer): ✅ passed the safety scan rides to the end, ⚠ failed drops at the scan,
// ❔ not read yet waits there. Vitals beside it: weather, coins green on the hour, buyers, safe rate, runners live, next round.
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
const WX = { clear: '☀ CLEAR', rain: '🌧 RAIN', storm: '⛈ STORM' };
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
  const v = engineVitals(d.open, d.fc, d.run); const pods = enginePods(d.open?.rows);
  const gates = [['🛰', 'SEEN', v.seen, 'Launch coins the feed carries right now'], ['🔬', 'SCANNED', v.read, 'Coins whose holders we have read (top-10, dev, bundles, snipers)'],
    ['✅', 'SAFE', v.safe, 'Coins that passed every safety check'], ['🏃', 'RUNNERS', v.runners, 'Coins passing every runner gate on the live board']];
  return <section className={`hen m-card is-${v.weather || 'none'}`} data-testid="home-engine">
    <header className="hen-head"><span className="hen-core" aria-hidden="true"><i /><i /><b>⚙</b></span>
      <span className="hen-title"><b>THE ENGINE · LIVE</b><small>every launch coin, scanned before anything is bought — tap a coin</small></span>
      {v.weather ? <em className="hen-wx" data-testid="hen-weather" data-tip="Runner weather: how recent paper runs on real prices ended. A reading, never a promise.">{WX[v.weather] || String(v.weather).toUpperCase()}{v.trend ? ` · ${v.trend}` : ''}</em> : null}
      <a className="hen-go" href="/terminal/fuse?tab=runners" onClick={e => { if (onOpen) { e.preventDefault(); onOpen('/terminal/fuse?tab=runners'); } }}>Open the lists →</a></header>
    <div className="hen-belt" data-testid="hen-belt">
      <div className="hen-gates">{gates.map(([ico, l, n, tip], i) => <span key={l} className="hen-gate" style={{ '--i': i }} data-tip={tip} data-testid={`hen-gate-${l.toLowerCase()}`}><i aria-hidden="true">{ico}</i><b key={n}>{num(n)}</b><small>{l}</small></span>)}</div>
      <div className="hen-track" aria-label="Live coins moving through the scan">{pods.map((p, i) => <span key={p.mint} className={`hen-run is-${p.fate}`} style={{ '--i': i, '--lane': i % 4 }}>
        <button type="button" className={`hen-pod ${p.m5 >= 0 ? 'is-up' : 'is-dn'}`} onClick={() => openCoin({ mint: p.mint, symbol: p.sym, pairAddress: p.pair })} data-testid={`hen-pod-${p.sym}`}
          data-tip={`$${p.sym} · ${p.fate === 'safe' ? 'passed the safety scan' : p.fate === 'fail' ? 'failed the safety scan' : 'holders not read yet'} · ${p.m5 >= 0 ? '+' : ''}${p.m5.toFixed(1)}% in 5 min`}>${p.sym}</button></span>)}</div>
    </div>
    <div className="hen-vitals"><Meter l="GREEN 1H" v={v.green} tone={v.green != null && v.green < 40 ? 'bad' : 'ok'} tip="Share of live launch coins up on the hour" />
      <Meter l="BUYERS" v={v.buyers} tone={v.buyers != null && v.buyers < 50 ? 'bad' : 'ok'} tip="Typical share of trades that are buys across the board" />
      <Meter l="SAFE RATE" v={v.safePct} tone="ice" tip="Of the coins we scanned, the share that passed every safety check" />
      <span className="hen-meter is-clock" data-tip="Time to the runner board's next round"><small>NEXT ROUND</small><Clock at={v.nextAt} /><i><u className="hen-tick" /></i></span></div>
  </section>;
}
