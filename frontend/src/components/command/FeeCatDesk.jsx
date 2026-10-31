import React, { useCallback, useEffect, useState } from 'react';
import { FeeOwnerBar } from './FeeOwnerBar';
import { realView } from './CatReal';
import { toast } from 'sonner';
import { FeeTape, DuoLearn, readWords } from './FeeCatLive';
import { FeeModels } from './FeeModels';
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
// 🤖 HER AGENTS LANE (owner, 2026-10-19: "she has the settings I have in agents, but I can tune hers separately"): each value = the agents' live one
// unless you type her own; empty = follow the agents. Saved as cat `agentLane` (feecat_service.clean_lane).
export const LANE_KEYS = [['mcMin', 'MC floor', '$'], ['mcMax', 'MC top', '$'], ['minAgeH', 'Youngest (h)', 'h'], ['maxAgeH', 'Oldest (h)', 'h'], ['minVol1h', '1h volume', '$'], ['poolMin', 'Pool floor', '$']];
export const laneWord = (v, unit) => (v == null || v === '' ? '—' : !Number.isFinite(Number(v)) ? 'any' : unit === '$' ? (Number(v) >= 1e6 ? `$${(Number(v) / 1e6).toFixed(1)}M` : `$${Math.round(Number(v) / 1000)}K`) : `${Number(v) < 1 ? `${Math.round(Number(v) * 60)}m` : `${Number(v)}h`}`);
export function laneSave(draft) { const o = {}; Object.entries(draft || {}).forEach(([k, v]) => { if (v !== '' && v != null && Number.isFinite(Number(v))) o[k] = Number(v); }); return o; }
function AgentLane({ d, busy, onSave }) {
  const lim = d.agentLimits || {}; const own = d.agentLane || {};
  const [draft, setDraft] = useState(() => Object.fromEntries(LANE_KEYS.map(([k]) => [k, own[k] ?? ''])));
  const yours = LANE_KEYS.filter(([k]) => own[k] != null).length;
  return <article className="fch-card fch-wide" data-testid="fch-lane"><h4>🤖 HER AGENTS LANE<small>{yours ? `${yours} of yours on top of the agents` : "following the agents' own settings"} · READY coins full size, CONTENDING half</small></h4>
    <div className="fch-lane">{LANE_KEYS.map(([k, l, u]) => { const mine = draft[k] !== '' && draft[k] != null;
      return <label key={k} className={mine ? 'is-mine' : ''} data-tip={`Agents now: ${laneWord(lim[k], u)}. Type her own to override; empty = follow the agents.`}>
        <span>{l}<em>{mine ? '✋ hers' : `🤖 ${laneWord(lim[k], u)}`}</em></span>
        <NumInput value={draft[k]} placeholder={lim[k] != null && Number.isFinite(Number(lim[k])) ? String(lim[k]) : 'any'} onChange={e => setDraft(x => ({ ...x, [k]: e.target.value }))} /></label>; })}</div>
    <p className="fch-lanebar"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onSave(laneSave(draft))} data-testid="fch-lane-save">Save her lane</button>
      <button type="button" className="m-btn" disabled={busy || !yours} onClick={() => { setDraft(Object.fromEntries(LANE_KEYS.map(([k]) => [k, '']))); onSave({}); }} data-testid="fch-lane-reset">Follow the agents</button></p>
  </article>;
}
const LANES = [['agents', '🤖 AGENTS', 'coins the ten agents put READY / CONTENDING — judged on the agents\' own band (+ your overrides)'], ['core', '🏛 CORE', 'coins 3+ days old, deep pools — her own record says these pay'], ['fresh', '🚀 FRESH', 'launches under 3h with X + site, buyers in control'],
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

// 🐱 the creator's Fee desk as TABS (owner 2026-10-30: "clean this up to the new look, less clutter / scrolling — I need more behind the scenes, but tidy"):
// her header always, then ONE pane at a time — what she's doing · her agents lane · her brain + rules · her wallet + style
export const FCH_TABS = [['overview', '🛰 OVERVIEW', 'Why she trades or not, the duo read, open trades, her charts and tape'],
  ['lane', '🎚 LANE', 'The agents lane she follows + what the duo learned'], ['brain', '🧠 BRAIN', 'Her style, rules and what she learned — edit and save'], ['wallet', '👛 WALLET + STYLE', "Her wallet (Circle / Crossmint) and her look"]];
const FCH_KEY = 'feeless.fch.tab';
export function FeeCatDesk({ call }) {
  const [tab, setTab] = useState(() => { try { const k = localStorage.getItem(FCH_KEY); return FCH_TABS.some(t => t[0] === k) ? k : 'overview'; } catch { return 'overview'; } });
  const pickTab = k => { setTab(k); try { localStorage.setItem(FCH_KEY, k); } catch { /* private window */ } };
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [draft, setDraft] = useState({}); const [size, setSize] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback((first) => call('/admin/feecat').then(x => { setD(x); setErr(''); if (first) { setDraft(x.rules || {}); setSize(x.leader?.risk?.maxPositionSol ?? ''); } })
    .catch(e => setErr(e.message || 'Fee service did not answer')), [call]);
  useEffect(() => { load(true); const t = setInterval(() => { if (!document.hidden) load(false); }, 6000); return () => clearInterval(t); }, [load]);
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
        <em>{realView(c).real ? 'REAL · she proposes, your wallet signs each' : 'paper desk · go real from 👛 FEE\'S WALLET'}</em></span>
      <span className="fch-kpi"><small>EQUITY</small><b data-testid="fch-equity">{sol(equity)}</b><i className={roi >= 0 ? 'm-pos' : 'm-neg'}>{roi >= 0 ? '+' : ''}{roi.toFixed(1)}% vs {start} SOL</i></span>
      <span className="fch-kpi"><small>REALIZED</small><b className={(n(c.realizedPnlSol) || 0) >= 0 ? 'm-pos' : 'm-neg'}>{sol(c.realizedPnlSol)}</b><i>{trades} trades</i></span>
      <span className="fch-kpi fch-ring" style={{ '--k': (wr ?? 0) / 100 }}><small>WON</small><b>{wr == null ? '—' : `${Math.round(wr)}%`}</b></span>
      <span className="fch-kpi"><small>OPEN</small><b>{pos.length}</b><i>{disc.why && disc.why !== 'normal size' ? disc.why : 'discipline normal'}</i></span>
      <span className="fch-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => save({ status: running ? 'paused' : 'running' })} data-testid="fch-toggle">{running ? '⏸ Pause' : '▶ Resume'}</button>
        <button type="button" className="m-btn m-go" disabled={busy || !running} onClick={() => save({ action: 'run' })} data-testid="fch-run">⚡ Run a cycle</button></span>
    </header>
    <nav className="m-seg fch-tabs" role="tablist" aria-label="Fee's desk">{FCH_TABS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={tab === k}
      className={tab === k ? 'active' : ''} onClick={() => pickTab(k)} data-tip={tip} data-testid={`fch-tab-${k}`}>{l}</button>)}</nav>
    {tab === 'wallet' ? <FeeOwnerBar cat={c} /> : null}
    {tab === 'lane' ? <div className="fch-grid"><AgentLane d={d} busy={busy} onSave={lane => save({ agentLane: lane })} /><DuoLearn learn={d.duoLearn} /></div> : null}

    {tab === 'overview' ? <div className="fch-grid">
      <article className="fch-card" data-testid="fch-funnel"><h4>🔎 WHY SHE {f.passed ? 'TRADES' : "ISN'T TRADING"}<small>{d.scan?.at ? `scan ${agoS(d.scan.at)}s ago` : 'no scan yet'}</small></h4>
        <p className="fch-flow"><span><b>{f.scanned}</b><small>coins read</small></span><i aria-hidden>→</i><span className={f.passed ? 'is-good' : 'is-bad'}><b>{f.passed}</b><small>passed her rules</small></span><i aria-hidden>→</i><span><b>{pos.length}</b><small>holding</small></span></p>
        {f.reasons.length ? <ul className="fch-bars">{f.reasons.map((r, i) => <li key={r.k} style={{ '--i': i }}><span>{r.k}</span><i><u style={{ transform: `scaleX(${Math.max(0.04, r.w)})` }} /></i><b>{r.c}</b></li>)}</ul> : <p className="fch-nil">nothing stopped — every coin read passed</p>}
        <p className="fch-lanes">{LANES.map(([k, l, t]) => <span key={k} data-tip={t}>{l}</span>)}</p>
        {f.top.length ? <p className="fch-top"><small>NEXT UP</small>{f.top.map(t => <span key={t.symbol} data-tip={t.reason}>${t.symbol}</span>)}</p> : null}
        {[...f.brain, ...f.safety].length ? <p className="fch-skip"><small>HER BRAIN / SAFETY SAID NO</small>{[...f.brain, ...f.safety].map((x, i) => <span key={`${x.symbol}-${i}`} data-tip={x.why}>${x.symbol} · {String(x.why || '').slice(0, 38)}</span>)}</p> : null}
      </article>

      <article className="fch-card" data-testid="fch-duo"><h4>🤝 DUO AI READ<small>{duo.read ? `${agoS(duo.read)}s ago · ${(duo.models || []).join(' + ')}` : 'every 4 min'}</small></h4>
        {duo.read ? <>
          <p className="fch-duo"><span className={(duo.avoid || []).length ? 'is-bad' : ''}><b>{(duo.avoid || []).length}</b><small>both say skip</small></span><span className={(duo.exit || []).length ? 'is-warn' : ''}><b>{(duo.exit || []).length}</b><small>both say bank</small></span><span><b>{(duo.split || []).length}</b><small>split (ignored)</small></span></p>
          <p className="fch-why">{duo.why || 'nothing clearly wrong — no coin named'}</p></> : <p className="fch-nil">the first read lands within 4 minutes of the AI round</p>}
        <small className="fch-note">she acts only on what BOTH models agree on — it can only make her trade less or bank sooner</small>
      </article>

      <article className="fch-card fch-wide" data-testid="fch-open"><h4>📂 OPEN TRADES<small>{pos.length} of {d.rules?.maxPositions ?? 5}</small></h4>
        {pos.length ? <ul className="fch-pos">{pos.map(p => { const ch = n(p.currentChange) || 0; return <li key={p.pairAddress} className={ch >= 0 ? 'is-up' : 'is-dn'}>
          <b>${p.symbol}</b><span className="fch-pbar"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(ch) / 60)})` }} /></span><em>{ch >= 0 ? '+' : ''}{ch.toFixed(1)}%</em><small>{sol(p.costSol)} · {Math.round((Date.now() / 1000 - (n(p.openedAt) || 0)) / 60)}m</small><i className="fcl-tags">{readWords({ setups: p.setups, read: p.read, duo: p.duoAtEntry }).slice(0, 3).join(' · ')}</i></li>; })}</ul>
          : <p className="fch-nil">flat — waiting for a coin that passes</p>}
      </article>

      <FeeTape events={d.events} />
    </div> : null}

    {tab === 'brain' ? <div className="fch-fold fch-brain" data-testid="fch-brain">
      <FeeModels />
      <FeeBrain />
      <FastDial d={d} busy={busy} onApply={vals => { setDraft(cur => ({ ...cur, ...vals })); save({ rules: { ...draft, ...vals }, strategyPreset: 'fast' }); }} />
      <div className="fch-groups">{RULE_GROUPS.map(([g, keys]) => { const ks = keys.filter(k => (d.bounds || {})[k]); if (!ks.length) return null;
        return <fieldset key={g} className="fch-group"><legend>{g}</legend>{ks.map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
          <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset>; })}
        <fieldset className="fch-group"><legend>💵 SIZE</legend><label><span>Max SOL per trade<em>0.1–10</em></span><NumInput value={size} onChange={e => setSize(e.target.value)} /></label>
          {Object.keys(d.bounds || {}).filter(k => !RULE_GROUPS.some(([, ks]) => ks.includes(k))).map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
            <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset></div>
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => save({ strategyPreset: 'fast' })} data-testid="fch-save">Save my tuning</button>
    </div> : null}
  </section>;
}
