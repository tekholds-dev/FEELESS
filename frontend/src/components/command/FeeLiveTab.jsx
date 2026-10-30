import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/feeLive.css';
import { AgentLive } from './AgentLive';
import { callThread } from '../../lib/feeCallChat';
import { useLeaderProfile } from '../../lib/feeLeader';
import { reasonChip, talkPins } from '../../lib/feeTape';

// 🐱 FEE LIVE (owner, 2026-10-19: "finish her terminal tabs"): what Fee is doing right now, for everyone — her last scan (coins read → passed → held,
// the rules that stopped the rest), her open paper trades, the coin she holds on a live chart WITH her call bubbles, and her calls in her own words
// (they say where each call came from: the agents' desk or 🔮 FeeCat AI). Public reads only (`/api/cats/leader`, `/api/cats/activity`), every 15s.
// 2026-10-23: calls + scan reasons are CHIP rows (lib/feeTape.js), and FeeCat AI's desk words ride the chart as 🔮 bubbles (`talk`).
const n = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const ago = ms => { const s = Math.max(0, Math.round(Date.now() / 1000 - (n(ms) > 1e12 ? n(ms) / 1000 : n(ms) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

// pure: her scan as a funnel + the top reasons that stopped coins
export function scanFunnel(scan, held) {
  const s = scan || {}; const by = {};
  Object.entries(s.rejections || {}).forEach(([k, c]) => { const r = reasonChip(k); const g = by[r.label] || (by[r.label] = { ...r, k, c: 0, all: [] }); g.c += n(c) || 0; g.all.push(`${k} (${c})`); });   // one chip per kind of reason
  const rej = Object.values(by).sort((a, b) => b.c - a.c); const max = Math.max(1, ...rej.map(r => r.c));
  return { read: n(s.scanned) || 0, passed: n(s.passed) || 0, held: held || 0, reasons: rej.slice(0, 5).map(r => ({ k: r.k, c: r.c, w: r.c / max, icon: r.icon, label: r.label, full: r.all.join(' · ') })), next: (s.top || []).slice(0, 4) };
}
export function FeeLiveTab() {
  const [d, setD] = useState(null); const [ev, setEv] = useState([]); 
  const prof = useLeaderProfile();   // the shared 15s poll her hero reads: napping (out of lives / a tilt pause) is the same word everywhere
  useEffect(() => { let on = true; let t = null;
    const go = async () => { try { const [a, b] = await Promise.all([fetch('/api/cats/leader').then(r => r.json()), fetch('/api/cats/activity?catId=leader').then(r => r.json())]); if (on) { setD(a); setEv(b.events || []); } } catch { /* keep the last */ }
      if (on) t = setTimeout(go, document.hidden ? 60000 : 15000); };
    go(); return () => { on = false; clearTimeout(t); }; }, []);
  const pos = d?.cat?.positions || []; const f = useMemo(() => scanFunnel(d?.scan, pos.length), [d, pos.length]);
  const coins = useMemo(() => [...pos.map(p => ({ pair: p.pairAddress, mint: p.mint, symbol: p.symbol, pct: n(p.currentChange), entry: n(p.entryPriceUsd), open: true })),
    ...f.next.map(t => ({ pair: t.pairAddress, mint: t.mint, symbol: t.symbol, open: false }))].filter(c => c.pair), [pos, f.next]);
  if (!d) return <p className="paper-muted" data-testid="fee-live-wait">🐱 reading Fee…</p>;
  const c = coins[0];
  // 🛸 the demo's layout on her real desk (owner 2026-10-30): Fee + FeeCat AI as live bubbles (their own latest words), her two coins charted,
  // her calls riding over both windows (the separate calls panel is gone — her wall carries the conversation)
  const hunting = d.cat?.status === 'running' && !(prof?.discipline || {}).pause;
  const aiWords = (d.talk || []).slice(-4).map(t => `${String(t.word || '').toUpperCase()} ${t.sym ? `$${t.sym}` : ''}`.trim()).filter(Boolean);
  const minds = [{ model: { id: 'fee', name: 'Fee', provider: 'FEE' }, thoughts: f.reasons.map(r => r.label).slice(0, 4), live: hunting, label: 'Fee', sub: hunting ? 'hunting · her rules' : 'napping' },
    { model: { id: 'ai', name: 'FeeCat AI', provider: 'AI' }, thoughts: aiWords, live: hunting, label: 'FeeCat AI', sub: 'reads every coin' }];
  const feed = callThread(ev, pos).slice(0, 3).reverse().map(m => `🐱 ${m.side}${m.coin && m.coin !== 'null' ? ` $${m.coin}` : ''}${m.why ? ` — ${String(m.why).slice(0, 64)}` : ''}`);
  return <section className="fcv" data-testid="fee-live">
    <AgentLive testId="fee-live-minds" title={`LIVE · Fee's desk · ${c ? (c.open ? `holding $${c.symbol}` : `next up $${c.symbol}`) : 'hunting'}`} minds={minds} coins={coins} feed={feed} callouts={pair => [...talkPins(d.talk, pair)]} />
    <article className="fcv-card fcv-funnel"><h3>🔎 HER LAST SCAN<small>{d.scan?.at ? `${ago(d.scan.at)} ago` : 'no scan yet'}</small></h3>
      <p className="fcv-flow"><span><b key={f.read}>{f.read}</b><small>coins read</small></span><i>→</i><span className={f.passed ? 'is-good' : ''}><b key={f.passed}>{f.passed}</b><small>passed</small></span><i>→</i><span><b key={f.held}>{f.held}</b><small>holding</small></span></p>
      {f.reasons.length ? <ul className="fcv-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }} data-tip={r.full}><span className="fcv-rc"><i aria-hidden="true">{r.icon}</i>{r.label}</span><i><u style={{ transform: `scaleX(${Math.max(0.05, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="paper-muted">nothing stopped a coin this scan</p>}
      <p className="fcv-src" data-tip="Where her coins come from: the ten agents' desk finds them, FeeCat AI reads them every few minutes, Fee skips what it calls a skip">
        <span>🤖 10 agents</span><i aria-hidden="true">→</i><span className="is-ai">🔮 FeeCat AI</span><i aria-hidden="true">→</i><span className="is-fee">🐱 Fee</span></p></article>
  </section>;
}
