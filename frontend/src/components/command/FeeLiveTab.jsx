import React, { useEffect, useMemo, useState } from 'react';
import '../../styles/feeLive.css';
import { AgentLive } from './AgentLive';
import { callThread } from '../../lib/feeCallChat';
import { useLeaderProfile } from '../../lib/feeLeader';
import { reasonChip, talkPins } from '../../lib/feeTape';
import { FirstTips } from '../FirstTips';

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
export function FeeLiveTab({ part }) {   // part: 'view' (her two charts) · 'scan' (her funnel) · both when unset
  const [d, setD] = useState(null); const [ev, setEv] = useState([]); 
  const prof = useLeaderProfile();   // the shared 15s poll her hero reads: napping (out of lives / a tilt pause) is the same word everywhere
  useEffect(() => { let on = true; let t = null;
    const go = async () => { try { const [a, b] = await Promise.all([fetch('/api/cats/leader').then(r => r.json()), fetch('/api/cats/activity?catId=leader').then(r => r.json())]); if (on) { setD(a); setEv(b.events || []); } } catch { /* keep the last */ }
      if (on) t = setTimeout(go, document.hidden ? 60000 : 15000); };
    go(); return () => { on = false; clearTimeout(t); }; }, []);
  const pos = d?.cat?.positions || []; const f = useMemo(() => scanFunnel(d?.scan, pos.length), [d, pos.length]);
  // 📈 her two windows ALWAYS chart live coins (owner 2026-10-30: "I don't want that preview — 2 live charts regardless if she's trading"):
  // what she holds → her next picks → the coins she last traded
  const coins = useMemo(() => { const seen = new Set(); const out = [];
    const add = c => { if (c.pair && !seen.has(c.pair) && out.length < 2) { seen.add(c.pair); out.push(c); } };
    pos.forEach(p => add({ pair: p.pairAddress, mint: p.mint, symbol: p.symbol, pct: n(p.currentChange), entry: n(p.entryPriceUsd), open: true }));
    f.next.forEach(t => add({ pair: t.pairAddress, mint: t.mint, symbol: t.symbol, open: false, note: 'next up' }));
    ev.filter(e => (e.type === 'BUY' || e.type === 'SELL') && e.pairAddress).forEach(e => add({ pair: e.pairAddress, symbol: e.symbol || (String(e.detail || '').match(/\bof\s+([A-Z0-9_$]{2,})/i) || String(e.detail || '').match(/^Sold\s+([A-Z0-9_$]{2,})/i) || [])[1] || 'COIN', open: false, note: `last ${e.type === 'BUY' ? 'bought' : 'sold'}` }));
    return out; }, [pos, f.next, ev]);
  if (!d) return <p className="paper-muted" data-testid="fee-live-wait">🐱 reading Fee…</p>;
  const c = coins[0];
  // 🛸 the demo's layout on her real desk (owner 2026-10-30): Fee + FeeCat AI as live bubbles (their own latest words), her two coins charted,
  // her calls riding over both windows (the separate calls panel is gone — her wall carries the conversation)
  const hunting = d.cat?.status === 'running' && !(prof?.discipline || {}).pause;
  const feed = callThread(ev, pos).slice(0, 3).reverse().map(m => `🐱 ${m.side}${m.coin && m.coin !== 'null' ? ` $${m.coin}` : ''}${m.why ? ` — ${String(m.why).slice(0, 64)}` : ''}`);
  return <section className="fcv" data-testid="fee-live">
    {part === 'scan' ? null : <AgentLive testId="fee-live-minds" title={`FEECAT'S VIEW · ${hunting ? 'hunting' : 'napping'}${c?.open ? ` · holding $${c.symbol}` : ''}`} coins={coins} feed={feed} callouts={pair => [...talkPins(d.talk, pair)]} />}
    {part === 'view' ? null : <article className="fcv-card fcv-funnel"><h3>🔎 HER LAST SCAN<small>{d.scan?.at ? `${ago(d.scan.at)} ago` : 'no scan yet'}</small></h3>
      <p className="fcv-flow"><span><b key={f.read}>{f.read}</b><small>coins read</small></span><i>→</i><span className={f.passed ? 'is-good' : ''}><b key={f.passed}>{f.passed}</b><small>passed</small></span><i>→</i><span><b key={f.held}>{f.held}</b><small>holding</small></span></p>
      {f.reasons.length ? <ul className="fcv-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }} data-tip={r.full}><span className="fcv-rc"><i aria-hidden="true">{r.icon}</i>{r.label}</span><i><u style={{ transform: `scaleX(${Math.max(0.05, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="paper-muted">nothing stopped a coin this scan</p>}
      <p className="fcv-src" data-tip="Where her coins come from: the ten agents' desk finds them, FeeCat AI reads them every few minutes, Fee skips what it calls a skip">
        <span>🤖 10 agents</span><i aria-hidden="true">→</i><span className="is-ai">🔮 FeeCat AI</span><i aria-hidden="true">→</i><span className="is-fee">🐱 Fee</span></p></article>}
  </section>;
}

// 🐱 THE FEECAT LANDING — one screen, no scroll (owner 2026-10-31: "no tab ever scroll heavy"): Fee's stage on top, then ONE of her view ·
// her last scan · her book behind a segmented switch (remembered on this device), with first-visit tip spots on what matters
const PARTS = [['view', '👁 HER VIEW', 'Her two live charts with her calls riding on them'], ['scan', '🔎 LAST SCAN', 'Coins she read → passed → held, and what stopped the rest'],
  ['book', '📖 HER BOOK', 'Her wall, every trade and what happened after each sell']];
const LAND_TIPS = [['[data-testid="fcl-seg"]', 'One screen', 'Her live view, her last scan and her book — tap to switch, nothing to scroll.'],
  ['[data-testid="fcx-state"]', 'Live state', 'Hunting = she is reading the board right now · napping = out of lives or cooling off.'],
  ['[data-testid="follow-fee"]', 'Follow Fee', 'A push on your phone every time she buys or sells.'],
  ['[data-testid="fcx-mine"]', 'Build yours', 'Make your own cat or agent — it trades or works next to her.']];
const PART_KEY = 'feeless:fee-landing';
export function FeeLanding({ book }) {
  const [p, setP] = useState(() => { try { const v = localStorage.getItem(PART_KEY); return PARTS.some(x => x[0] === v) ? v : 'view'; } catch { return 'view'; } });
  const pick = k => { setP(k); try { localStorage.setItem(PART_KEY, k); } catch { /* private window: this visit only */ } };
  return <div className="fcl" data-testid="fee-landing">
    <nav className="m-seg fcl-seg" role="tablist" aria-label="Fee live" data-testid="fcl-seg">{PARTS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={p === k}
      className={p === k ? 'active' : ''} onClick={() => pick(k)} data-tip={tip} data-testid={`fcl-${k}`}>{l}</button>)}</nav>
    <div className="fcl-pane" key={p} role="tabpanel">{p === 'book' ? book : <FeeLiveTab part={p} />}</div>
    <FirstTips id="fee-landing" tips={LAND_TIPS} />
  </div>;
}
