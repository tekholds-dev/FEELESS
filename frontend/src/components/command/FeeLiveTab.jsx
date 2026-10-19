import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/feeLive.css';

// 🐱 FEE LIVE (owner, 2026-10-19: "finish her terminal tabs"): what Fee is doing right now, for everyone — her last scan (coins read → passed → held,
// the rules that stopped the rest), her open paper trades, the coin she holds on a live chart WITH her call bubbles, and her calls in her own words
// (they say where each call came from: the agents' desk or OSSY / G4). Public reads only (`/api/cats/leader`, `/api/cats/activity`), every 15s.
const PriceChart = React.lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
const n = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const ago = ms => { const s = Math.max(0, Math.round(Date.now() / 1000 - (n(ms) > 1e12 ? n(ms) / 1000 : n(ms) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

// pure: her scan as a funnel + the top reasons that stopped coins
export function scanFunnel(scan, held) {
  const s = scan || {}; const rej = Object.entries(s.rejections || {}).sort((a, b) => b[1] - a[1]); const max = Math.max(1, ...rej.map(r => r[1]));
  return { read: n(s.scanned) || 0, passed: n(s.passed) || 0, held: held || 0, reasons: rej.slice(0, 5).map(([k, c]) => ({ k, c, w: c / max })), next: (s.top || []).slice(0, 4) };
}
// pure: her calls (BUY / SELL) newest first, in plain words
export function feeCalls(events) {
  return (events || []).filter(e => e.type === 'BUY' || e.type === 'SELL').slice(0, 12)
    .map(e => ({ id: e.id, side: e.type, at: e.ts, pnl: n(e.pnlSol), text: String(e.detail || '').replace(/\s*\(paper[^)]*\)\.?/g, ''), pair: e.pairAddress }));
}

export function FeeLiveTab() {
  const [d, setD] = useState(null); const [ev, setEv] = useState([]); const [pick, setPick] = useState(0);
  useEffect(() => { let on = true; let t = null;
    const go = async () => { try { const [a, b] = await Promise.all([fetch('/api/cats/leader').then(r => r.json()), fetch('/api/cats/activity?catId=leader').then(r => r.json())]); if (on) { setD(a); setEv(b.events || []); } } catch { /* keep the last */ }
      if (on) t = setTimeout(go, document.hidden ? 60000 : 15000); };
    go(); return () => { on = false; clearTimeout(t); }; }, []);
  const pos = d?.cat?.positions || []; const f = useMemo(() => scanFunnel(d?.scan, pos.length), [d, pos.length]); const calls = useMemo(() => feeCalls(ev), [ev]);
  const coins = useMemo(() => [...pos.map(p => ({ pair: p.pairAddress, mint: p.mint, symbol: p.symbol, pct: n(p.currentChange), entry: n(p.entryPriceUsd), open: true })),
    ...f.next.map(t => ({ pair: t.pairAddress, mint: t.mint, symbol: t.symbol, open: false }))].filter(c => c.pair), [pos, f.next]);
  if (!d) return <p className="paper-muted" data-testid="fee-live-wait">🐱 reading Fee…</p>;
  const c = coins[Math.min(pick, Math.max(0, coins.length - 1))];
  return <section className="fcv" data-testid="fee-live">
    <article className="fcv-card fcv-funnel"><h3>🔎 HER LAST SCAN<small>{d.scan?.at ? `${ago(d.scan.at)} ago` : 'no scan yet'}</small></h3>
      <p className="fcv-flow"><span><b key={f.read}>{f.read}</b><small>coins read</small></span><i>→</i><span className={f.passed ? 'is-good' : ''}><b key={f.passed}>{f.passed}</b><small>passed</small></span><i>→</i><span><b key={f.held}>{f.held}</b><small>holding</small></span></p>
      {f.reasons.length ? <ul className="fcv-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }}><span>{r.k}</span><i><u style={{ transform: `scaleX(${Math.max(0.05, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="paper-muted">nothing stopped a coin this scan</p>}
      <small className="fcv-note">her coins come from the ten agents' desk; OSSY + G4 read them every few minutes — she skips what both call a skip</small></article>
    <article className="fcv-card fcv-chart"><h3>📈 {c ? `$${c.symbol}` : 'NO COIN YET'}<small>{c ? (c.open ? `holding${c.pct != null ? ` ${c.pct >= 0 ? '+' : ''}${c.pct.toFixed(1)}%` : ''}` : 'next up') : 'she charts her trades, then her next picks'}</small></h3>
      {coins.length > 1 ? <div className="fcv-coins">{coins.map((x, i) => <button key={x.pair} type="button" className={i === pick ? 'active' : ''} onClick={() => setPick(i)}>{x.open ? '📂' : '⏭'} ${x.symbol}</button>)}</div> : null}
      {c ? <div className="fcv-plot"><React.Suspense fallback={<p className="paper-muted">loading chart…</p>}><PriceChart key={c.pair} pair={{ chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.symbol } }} interval="1m" metric="price" showVolume={false} userEntry={c.entry || null} /></React.Suspense></div> : null}
      <small className="fcv-note">🐱 bubbles on the chart = her own calls</small></article>
    <article className="fcv-card fcv-calls"><h3>🐱 HER CALLS<small>{calls.length ? `newest ${ago(calls[0].at)} ago` : 'quiet so far'}</small></h3>
      {calls.length ? <ol>{calls.map((x, i) => <li key={x.id} className={`is-${x.side.toLowerCase()} ${i === 0 ? 'is-new' : ''}`}><b>{x.side}</b><span>{x.text.slice(0, 220)}</span><small>{ago(x.at)}{x.pnl != null ? ` · ${x.pnl >= 0 ? '+' : ''}${x.pnl.toFixed(4)} SOL` : ''}</small></li>)}</ol>
        : <p className="paper-muted">no calls yet on this paper trail — she waits for a coin that passes</p>}</article>
  </section>;
}
