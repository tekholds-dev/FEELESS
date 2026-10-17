import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import NumInput from '../NumInput';
import { FeeBrain } from './FeeBrain';
import '../../styles/feecatDesk.css';

// 🐱 FEE IN HQ (owner, 2026-10-16: "FeeCat's engine and HQ panel aren't remade, and the cat isn't trading"): one live board from ONE request
// (`GET /admin/feecat`, re-read every 15s) — who she is right now, WHY she is or isn't trading (her own last scan: scanned → passed →
// bought, the rules that stopped the rest, the lanes she can buy through), the duo AI read, her open trades and her latest moves. Her
// brain (style + rules + what she learned) sits in a fold. Paper money: she never signs or moves real SOL.

export const FEE_LABELS = {
  minLiquidity: ['Min liquidity ($)', 'Skip pools thinner than this — she must be able to get out.'],
  minVolume24h: ['Min 24h volume ($)', 'A coin nobody trades is a coin nobody buys from her.'],
  minMarketCap: ['Min market cap ($)', 'Smaller than this is the curve still being sniped.'],
  maxMarketCap: ['Max market cap ($)', 'Bigger than this rarely moves enough for a trench cat.'],
  minAgeHours: ['Min pool age (h)', 'Fresh pools are the rug zone — her fresh lane covers the youngest with its own rules.'],
  maxPositions: ['Max open positions', 'How many coins she holds at once.'],
  maxTop10Pct: ['Max top-10 holders (%)', 'Too concentrated = one wallet can dump it.'],
  maxSnipers: ['Max snipers', 'Launch snipers still holding = exit liquidity risk.'],
  maxBundled: ['Max bundled wallets', 'Bundles at launch = coordinated sellers.'],
  maxM5Chase: ['Max 5-min move she buys (%)', 'Never into a vertical 5-minute candle.'],
  add1At: ['First dip buy at (%)', 'She adds here only if liquidity, volume and buyers still hold.'],
  add2At: ['Second dip buy at (%)', 'The deeper add, same conditions.'],
  hardStop: ['Emergency stop (%)', 'From her average entry — the last line.'],
  takeProfit1: ['First profit at (+%)', 'She sells part of the position here to lock in gains.'],
  takeProfit2: ['Second profit at (+%)', 'She sells more here; the rest keeps running.'],
  runnerTrail: ['Runner trailing stop (%)', 'After taking profit, sell the rest if it falls this far from its peak. Never below break-even.'],
  maxHoldHours: ['Max hold (h)', 'Give up on a coin that never reached a profit target after this long.'],
  maxExposure: ['Max capital at work (0–1)', 'Share of her balance allowed in open trades. 0.4 = 40%.'],
};
// ⚡ ONE DIAL (owner, 2026-10-16): FAST TRENCH, seeded from the agents' own live configs (server `fastTrench`), each value clamped to her bounds
export const RULE_GROUPS = [['🎯 ENTRY', ['minMarketCap', 'minAgeHours', 'minLiquidity', 'minVolume24h', 'maxM5Chase', 'maxSnipers', 'maxTop10Pct']],
  ['💰 EXITS', ['takeProfit1', 'takeProfit2', 'runnerTrail', 'hardStop', 'maxHoldHours']], ['🪜 ADDS & SEATS', ['add1At', 'add2At', 'maxPositions', 'maxExposure']]];
export function fastValues(fast, bounds) {
  const out = {};
  for (const [k, v] of Object.entries(fast || {})) {
    if (k === 'from' || !Number.isFinite(Number(v))) continue;
    const b = (bounds || {})[k]; out[k] = b ? Math.min(b[1], Math.max(b[0], Number(v))) : Number(v);
  }
  return out;
}
function FastDial({ d, busy, onApply }) {
  const vals = fastValues(d.fastTrench, d.bounds); const from = d.fastTrench?.from || {}; const on = d.strategyPreset === 'fast';
  const chips = [['MC ≥', from.agentMcMin ? `$${Math.round(from.agentMcMin / 1000)}K` : '—'], ['age ≥', from.agentMinAgeH ? `${Math.round(from.agentMinAgeH * 60)}m` : 'any'], ['pool ≥', `$${Math.round((vals.minLiquidity || 0) / 1000)}K`],
    ['TP', vals.takeProfit1 ? `+${vals.takeProfit1}%` : '—'], ['SL', vals.hardStop ? `${vals.hardStop}%` : '—'], ['seats', vals.maxPositions || '—']];
  return <div className={`fch-dial ${on ? 'is-on' : ''}`} data-testid="fch-dial">
    <button type="button" className="fch-dialbtn" disabled={busy || !d.fastTrench} onClick={() => onApply(vals)} data-testid="fch-fast" aria-pressed={on}
      data-tip="One tap: her rules = the agents' own live limits (MC band floor, youngest age, pool floor, 1h volume, take / stop, 4 seats), clamped to her safety bounds. Tune below after.">
      <i aria-hidden="true" /><b>⚡ FAST TRENCH</b><small>{on ? 'ON — copied from the agents' : 'tap: copy the agents\' configs'}</small></button>
    <p className="fch-dialchips">{chips.map(([l, v]) => <span key={l}><small>{l}</small><b>{v}</b></span>)}</p>
  </div>;
}
const LANES = [['core', '🏛 CORE', 'coins 3+ days old, deep pools — her own record says these pay'], ['fresh', '🚀 FRESH', 'launches under 3h with X + site, buyers in control'],
  ['learn', '🎓 LEARNING', '3h – 3 days old, quarter size — the gap the other two skip']];

const n = v => (v == null || !Number.isFinite(Number(v)) ? null : Number(v));
const sol = v => (n(v) == null ? '—' : `${n(v) >= 0 ? '' : '−'}${Math.abs(n(v)).toFixed(Math.abs(n(v)) < 10 ? 3 : 1)} SOL`);
const agoS = t => (t ? Math.max(0, Math.round(Date.now() / 1000 - t)) : null);

// the scan as a funnel + the reasons ranked (pure — tested)
export function feeFunnel(scan) {
  const s = scan || {}; const rej = Object.entries(s.rejections || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rej.map(r => r[1]));
  return { scanned: n(s.scanned) || 0, passed: n(s.passed) || 0, reasons: rej.slice(0, 7).map(([k, c]) => ({ k, c, w: c / max })), top: s.top || [],
    brain: (s.brainRejects || []).slice(-4).reverse(), safety: (s.safetyRejects || []).slice(-4).reverse() };
}

export function FeeCatDesk({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [draft, setDraft] = useState({}); const [size, setSize] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback((first) => call('/admin/feecat').then(x => { setD(x); setErr(''); if (first) { setDraft(x.rules || {}); setSize(x.leader?.risk?.maxPositionSol ?? ''); } })
    .catch(e => setErr(e.message || 'Fee service did not answer')), [call]);
  useEffect(() => { load(true); const t = setInterval(() => { if (!document.hidden) load(false); }, 15000); return () => clearInterval(t); }, [load]);
  if (!d) return <section className="fch" data-testid="feecat-desk"><p className="fch-wait">{err ? <>Couldn't reach Fee: {err} <button type="button" className="m-btn" onClick={() => load(true)}>Retry</button></> : '🐱 waking Fee up…'}</p></section>;
  const save = extra => { setBusy(true); return call('/admin/feecat', { method: 'POST', body: JSON.stringify({ rules: draft, maxPositionSol: Number(size) || undefined, ...extra }) })
    .then(() => { toast.success(extra.action === 'run' ? '🐱 Fee ran a cycle' : '🐱 Fee updated'); return load(false); }).catch(e => toast.error(e.message)).finally(() => setBusy(false)); };
  const c = d.cat || {}; const running = d.leader?.status === 'running' || c.status === 'running'; const cyc = agoS(c.lastTick);
  const start = n(c.startingBalanceSol) || 25; const bal = n(c.balanceSol) || 0; const pos = c.positions || [];
  const inTrades = pos.reduce((a, p) => a + (n(p.costSol) || 0) * (1 + (n(p.currentChange) || 0) / 100), 0);
  const equity = bal + inTrades; const roi = ((equity / start) - 1) * 100;
  const f = feeFunnel(d.scan); const duo = d.duo || {}; const disc = d.discipline || {}; const wr = n(c.winRate);
  const trades = (n(c.wins) || 0) + (n(c.losses) || 0);
  return <section className="fch" data-testid="feecat-desk">
    <header className="fch-hero m-card m-live">
      <span className={`fch-orb ${running ? 'is-on' : ''}`} aria-hidden>🐱</span>
      <span className="fch-who"><b>FEE</b><small className={running ? 'is-on' : 'is-off'} data-testid="fch-status">{running ? `● LIVE · cycle ${cyc == null ? '…' : `${cyc}s ago`}` : '⏸ PAUSED'}</small>
        <em>paper desk · she never signs or moves real SOL</em></span>
      <span className="fch-kpi"><small>EQUITY</small><b data-testid="fch-equity">{sol(equity)}</b><i className={roi >= 0 ? 'm-pos' : 'm-neg'}>{roi >= 0 ? '+' : ''}{roi.toFixed(1)}% vs {start} SOL</i></span>
      <span className="fch-kpi"><small>REALIZED</small><b className={(n(c.realizedPnlSol) || 0) >= 0 ? 'm-pos' : 'm-neg'}>{sol(c.realizedPnlSol)}</b><i>{trades} trades</i></span>
      <span className="fch-kpi fch-ring" style={{ '--k': (wr ?? 0) / 100 }}><small>WON</small><b>{wr == null ? '—' : `${Math.round(wr)}%`}</b></span>
      <span className="fch-kpi"><small>OPEN</small><b>{pos.length}</b><i>{disc.why && disc.why !== 'normal size' ? disc.why : 'discipline normal'}</i></span>
      <span className="fch-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => save({ status: running ? 'paused' : 'running' })} data-testid="fch-toggle">{running ? '⏸ Pause' : '▶ Resume'}</button>
        <button type="button" className="m-btn m-go" disabled={busy || !running} onClick={() => save({ action: 'run' })} data-testid="fch-run">⚡ Run a cycle</button></span>
    </header>

    <div className="fch-grid">
      <article className="fch-card" data-testid="fch-funnel"><h4>🔎 WHY SHE {f.passed ? 'TRADES' : "ISN'T TRADING"}<small>{d.scan?.at ? `scan ${agoS(d.scan.at)}s ago` : 'no scan yet'}</small></h4>
        <p className="fch-flow"><span><b>{f.scanned}</b><small>coins read</small></span><i aria-hidden>→</i><span className={f.passed ? 'is-good' : 'is-bad'}><b>{f.passed}</b><small>passed her rules</small></span><i aria-hidden>→</i><span><b>{pos.length}</b><small>holding</small></span></p>
        {f.reasons.length ? <ul className="fch-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }}><span>{r.k}</span><i><u style={{ transform: `scaleX(${Math.max(0.04, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="fch-nil">nothing stopped — every coin read passed</p>}
        <p className="fch-lanes">{LANES.map(([k, l, t]) => <span key={k} data-tip={t}>{l}</span>)}</p>
        {f.top.length ? <p className="fch-top"><small>NEXT UP</small>{f.top.map(t => <span key={t.symbol} data-tip={t.reason}>${t.symbol}</span>)}</p> : null}
        {[...f.brain, ...f.safety].length ? <p className="fch-skip"><small>HER BRAIN / SAFETY SAID NO</small>{[...f.brain, ...f.safety].map((x, i) => <span key={`${x.symbol}-${i}`} data-tip={x.why}>${x.symbol} · {String(x.why || '').slice(0, 38)}</span>)}</p> : null}
      </article>

      <article className="fch-card" data-testid="fch-duo"><h4>🤝 DUO AI READ<small>{duo.read ? `${agoS(duo.read)}s ago · ${(duo.models || []).join(' + ')}` : 'every 10 min'}</small></h4>
        {duo.read ? <>
          <p className="fch-duo"><span className={(duo.avoid || []).length ? 'is-bad' : ''}><b>{(duo.avoid || []).length}</b><small>both say skip</small></span><span className={(duo.exit || []).length ? 'is-warn' : ''}><b>{(duo.exit || []).length}</b><small>both say bank</small></span><span><b>{(duo.split || []).length}</b><small>split (ignored)</small></span></p>
          <p className="fch-why">{duo.why || 'nothing clearly wrong — no coin named'}</p></> : <p className="fch-nil">the first read lands within 10 minutes of the AI round</p>}
        <small className="fch-note">she acts only on what BOTH models agree on — it can only make her trade less or bank sooner</small>
      </article>

      <article className="fch-card fch-wide" data-testid="fch-open"><h4>📂 OPEN TRADES<small>{pos.length} of {d.rules?.maxPositions ?? 5}</small></h4>
        {pos.length ? <ul className="fch-pos">{pos.map(p => { const ch = n(p.currentChange) || 0; return <li key={p.pairAddress} className={ch >= 0 ? 'is-up' : 'is-dn'}>
          <b>${p.symbol}</b><span className="fch-pbar"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(ch) / 60)})` }} /></span><em>{ch >= 0 ? '+' : ''}{ch.toFixed(1)}%</em><small>{sol(p.costSol)} · {Math.round((Date.now() / 1000 - (n(p.openedAt) || 0)) / 60)}m</small></li>; })}</ul>
          : <p className="fch-nil">flat — waiting for a coin that passes</p>}
      </article>

      <article className="fch-card fch-wide" data-testid="fch-moves"><h4>🧾 LATEST MOVES</h4>
        {(d.events || []).length ? <ul className="fch-moves">{d.events.map((e, i) => <li key={e.id || i} className={`is-${String(e.type || '').toLowerCase()}`} style={{ '--i': i }}><b>{e.type}</b><span>{String(e.detail || e.message || e.symbol || '').split('\n')[0].slice(0, 120)}</span></li>)}</ul> : <p className="fch-nil">no moves yet on this paper trail</p>}
      </article>
    </div>

    <details className="fch-fold"><summary>🧠 Her brain — style, rules, what she learned</summary>
      <FeeBrain />
      <FastDial d={d} busy={busy} onApply={vals => { setDraft(cur => ({ ...cur, ...vals })); save({ rules: { ...draft, ...vals }, strategyPreset: 'fast' }); }} />
      <div className="fch-groups">{RULE_GROUPS.map(([g, keys]) => { const ks = keys.filter(k => (d.bounds || {})[k]); if (!ks.length) return null;
        return <fieldset key={g} className="fch-group"><legend>{g}</legend>{ks.map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
          <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset>; })}
        <fieldset className="fch-group"><legend>💵 SIZE</legend><label><span>Max SOL per trade<em>0.1–10</em></span><NumInput value={size} onChange={e => setSize(e.target.value)} /></label>
          {Object.keys(d.bounds || {}).filter(k => !RULE_GROUPS.some(([, ks]) => ks.includes(k))).map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
            <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset></div>
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => save({ strategyPreset: 'fast' })} data-testid="fch-save">Save my tuning</button>
    </details>
  </section>;
}
