import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/feeLive.css';
import { tapeRow, reasonChip, talkPins } from '../../lib/feeTape';

// 🐱 FEE LIVE (owner, 2026-10-19: "finish her terminal tabs"): what Fee is doing right now, for everyone — her last scan (coins read → passed → held,
// the rules that stopped the rest), her open paper trades, the coin she holds on a live chart WITH her call bubbles, and her calls in her own words
// (they say where each call came from: the agents' desk or 🔮 FeeCat AI). Public reads only (`/api/cats/leader`, `/api/cats/activity`), every 15s.
// 2026-10-23: calls + scan reasons are CHIP rows (lib/feeTape.js), and FeeCat AI's desk words ride the chart as 🔮 bubbles (`talk`).
const PriceChart = React.lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
const n = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const ago = ms => { const s = Math.max(0, Math.round(Date.now() / 1000 - (n(ms) > 1e12 ? n(ms) / 1000 : n(ms) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

// pure: her scan as a funnel + the top reasons that stopped coins
export function scanFunnel(scan, held) {
  const s = scan || {}; const by = {};
  Object.entries(s.rejections || {}).forEach(([k, c]) => { const r = reasonChip(k); const g = by[r.label] || (by[r.label] = { ...r, k, c: 0, all: [] }); g.c += n(c) || 0; g.all.push(`${k} (${c})`); });   // one chip per kind of reason
  const rej = Object.values(by).sort((a, b) => b.c - a.c); const max = Math.max(1, ...rej.map(r => r.c));
  return { read: n(s.scanned) || 0, passed: n(s.passed) || 0, held: held || 0, reasons: rej.slice(0, 5).map(r => ({ k: r.k, c: r.c, w: r.c / max, icon: r.icon, label: r.label, full: r.all.join(' · ') })), next: (s.top || []).slice(0, 4) };
}
// pure: her calls (BUY / SELL) newest first, in plain words
export function feeCalls(events) {
  return (events || []).filter(e => e.type === 'BUY' || e.type === 'SELL').slice(0, 12)
    .map(e => ({ id: e.id, side: e.type, at: e.ts, pnl: n(e.pnlSol), text: String(e.detail || '').replace(/\s*\(paper[^)]*\)\.?/g, ''), pair: e.pairAddress, row: tapeRow(e) }));
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
  const talk = c ? talkPins(d.talk, c.pair) : [];
  return <section className="fcv" data-testid="fee-live">
    <article className="fcv-card fcv-funnel"><h3>🔎 HER LAST SCAN<small>{d.scan?.at ? `${ago(d.scan.at)} ago` : 'no scan yet'}</small></h3>
      <p className="fcv-flow"><span><b key={f.read}>{f.read}</b><small>coins read</small></span><i>→</i><span className={f.passed ? 'is-good' : ''}><b key={f.passed}>{f.passed}</b><small>passed</small></span><i>→</i><span><b key={f.held}>{f.held}</b><small>holding</small></span></p>
      {f.reasons.length ? <ul className="fcv-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }} data-tip={r.full}><span className="fcv-rc"><i aria-hidden="true">{r.icon}</i>{r.label}</span><i><u style={{ transform: `scaleX(${Math.max(0.05, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="paper-muted">nothing stopped a coin this scan</p>}
      <p className="fcv-src" data-tip="Where her coins come from: the ten agents' desk finds them, FeeCat AI reads them every few minutes, Fee skips what it calls a skip">
        <span>🤖 10 agents</span><i aria-hidden="true">→</i><span className="is-ai">🔮 FeeCat AI</span><i aria-hidden="true">→</i><span className="is-fee">🐱 Fee</span></p></article>
    <article className="fcv-card fcv-chart"><h3>📈 {c ? `$${c.symbol}` : 'NO COIN YET'}<small>{c ? (c.open ? `holding${c.pct != null ? ` ${c.pct >= 0 ? '+' : ''}${c.pct.toFixed(1)}%` : ''}` : 'next up') : 'she charts her trades, then her next picks'}</small></h3>
      {coins.length > 1 ? <div className="fcv-coins">{coins.map((x, i) => <button key={x.pair} type="button" className={i === pick ? 'active' : ''} onClick={() => setPick(i)}>{x.open ? '📂' : '⏭'} ${x.symbol}</button>)}</div> : null}
      {c ? <div className="fcv-plot"><React.Suspense fallback={<p className="paper-muted">loading chart…</p>}><PriceChart key={c.pair} pair={{ chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.symbol } }} interval="1m" metric="price" showVolume={false} userEntry={c.entry || null} callouts={talk} /></React.Suspense></div> : null}
      <p className="fcv-legend"><span className="is-fee" data-tip="Fee's own BUY / SELL calls, at the candle and cap she made them">🐱 her calls</span>
        <span className="is-ai" data-tip="FeeCat AI's desk words on this coin (YES / NO / HOLD / SELL / SKIM) — tap a bubble for the why">🔮 FeeCat AI <b key={talk.length}>{talk.length}</b></span></p></article>
    <article className="fcv-card fcv-calls"><h3>🐱 HER CALLS<small>{calls.length ? `newest ${ago(calls[0].at)} ago` : 'quiet so far'}</small></h3>
      {calls.length ? <ol>{calls.map((x, i) => <li key={x.id} className={`is-${x.side.toLowerCase()} ${i === 0 ? 'is-new' : ''}`} style={{ '--i': i }} data-tip={x.text}><b>{x.side}</b>
        <span className="fcv-chips">{x.row.coin ? <i className="fcv-coin">${x.row.coin}</i> : null}{x.row.sol != null ? <i>{x.row.sol} SOL</i> : null}
          {x.row.move != null ? <i className={x.row.move >= 0 ? 'is-up' : 'is-dn'}>{x.row.move > 0 ? '+' : ''}{x.row.move}%</i> : null}
          {x.pnl != null ? <i className={`fcv-pnl ${x.pnl >= 0 ? 'is-up' : 'is-dn'}`}>{x.pnl >= 0 ? '+' : ''}{x.pnl.toFixed(4)} SOL</i> : null}
          {x.row.ai ? <i className="fcv-ai">🔮 AI</i> : null}{x.row.tag ? <i className="fcv-tag">{x.row.tag}</i> : null}</span><small>{ago(x.at)}</small></li>)}</ol>
        : <p className="paper-muted">no calls yet on this paper trail — she waits for a coin that passes</p>}</article>
  </section>;
}
