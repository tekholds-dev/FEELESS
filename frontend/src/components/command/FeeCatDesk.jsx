import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ModelLab } from './ModelLab';
import SegTabs from '../SegTabs';
import { FeeOwnerBar } from './FeeOwnerBar';
import { IdeasFolder } from './IdeasFolder';
import { realView } from './CatReal';
import { toast } from 'sonner';
import { FeeTape, DuoLearn, readWords } from './FeeCatLive';
import { FeeModels } from './FeeModels';
import NumInput from '../NumInput';
import { FeeBrain } from './FeeBrain';
import { PromptStudio } from './PromptStudio';
import { AllWork, ColonyFlow, PowEngine } from './HiveBoard';
const CollectiveLandingLazy = React.lazy(() => import('./CollectiveLanding').then(m => ({ default: m.CollectiveLanding })));
import { CollectiveOwner } from './CollectiveOwner';
import { groupApps, useOwnerFolders } from './OwnerFolders';
import { AgentDesk } from './AgentDesk';
import '../../styles/collectiveSetup.css';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { StashWeb } from './StashWeb';
import { ProviderReady } from './ProviderReady';
import { AgentDesktop, work } from './CatWorkbench';
import { GitFolder } from './GitFolder';
import { AgentsDiagram, AppDesktop, PerfGlass, ShaderWall } from './DeskShell';
import { Ic3 } from '../../lib/icon3d';
import { apiUrl } from '../../lib/api';
import '../../styles/catWorkbench.css';
import '../../styles/feecatDesk.css';

// 🐱 FEE IN HQ (owner, 2026-10-16: "FeeCat's engine and HQ panel aren't remade, and the agent isn't trading"): one live board from ONE request
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
      <i aria-hidden="true" /><b><Ic3 e="⚡" /> FAST TRENCH</b><small>{on ? 'ON — copied from the agents' : 'tap: copy the agents\' configs'}</small></button>
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
// her header always, then ONE pane at a time — what she's doing · 👑 your platform tools · her agents lane · her brain + rules · her wallet + style
export const FCH_TABS = [['overview', '🛰 OVERVIEW', 'Why she trades or not, the duo read, open trades, her charts and tape'], ['owner', '👑 OWNER', 'Her owner desktop: every control you have, in folders']];
const flowApi = u => fetch(apiUrl(u)).then(r => r.json());
function useFlow() {
  const [flow, setFlow] = useState(null);
  useEffect(() => { let on = true; const load = () => { if (!document.hidden) fetch(apiUrl('/api/cats/colony/flow?limit=1')).then(r => r.json()).then(x => on && setFlow(x)).catch(() => {}); }; load(); const t = setInterval(load, 20000); return () => { on = false; clearInterval(t); }; }, []);
  return flow;
}
const agentsGlass = flow => { const n = Number(flow?.pnlSol) || 0; const trades = flow?.pow?.trades || 0; const rows = flow?.tree?.agents || []; let sum = 0;
  return { title: 'ALL AGENTS', value: flow ? `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(4)} SOL` : 'Reading…', sub: flow ? `${flow.pow?.won || 0} of ${trades} won · ${flow.agents} agents` : '', tone: !flow ? '' : n >= 0 ? 'up' : 'dn', vals: rows.map(a => { sum += Number(a.pnlSol) || 0; return sum; }) }; };
// 👑 THE OWNER'S TWO DESKTOPS (owner 2026-11-04): the same desktop a general agent gets. One is Fee's, one runs the whole agent system.
function OwnerDesk({ cat, trades, feeApps, agentApps, call }) {
  const flow = useFlow(); const [open, setOpen] = useState(''); const ownerApps = useOwnerFolders(call, open === 'agents');
  const feeGlass = useMemo(() => { const v = Number(cat?.realizedPnlSol) || 0; return { title: realView(cat).real ? 'FEE · REAL' : 'FEE · PAPER', value: `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(3)} SOL`, sub: `${trades} trades`, tone: v >= 0 ? 'up' : 'dn', vals: [] }; }, [cat?.realizedPnlSol, trades]);
  const close = useCallback(() => setOpen(''), []);
  const monitor = (k, mood, name, sub, ics, glass) => <button type="button" className="own-m" onClick={() => setOpen(k)} data-tip={`Open the ${name} desktop`} data-testid={`own-${k}`}>
    <ShaderWall mood={mood} /><i className="own-sheen" aria-hidden="true" />
    <span className="own-ics" aria-hidden="true">{ics.map((e, n) => <i key={e} style={{ '--i': n }}><i className="dsk-ico-art"><em><Ic3 e={e} size="30px" /></em></i></i>)}</span>
    <span className="own-go" aria-hidden="true">OPEN</span>
    <span className="own-name"><b>{name}</b><small>{sub}</small></span>
    <PerfGlass {...glass} testid={`own-glass-${k}`} /></button>;
  return <><div className="own" data-testid="fch-owner">
    {monitor('fee', 'fee', 'FEE', 'her desktop', ['🧠', '🎭', '🎚', '👛', '⛏', '📉', '🎲', '🔐'], feeGlass)}
    {monitor('agents', 'colony', 'AGENTS', 'the whole system', ['💎', '🏊', '💸', '🛟'], { ...agentsGlass(flow) })}
  </div>
    {open === 'fee' ? <AgentDesktop cat={cat} onClose={close} extra={feeApps} mood="fee" glassOver={feeGlass} /> : null}
    {open === 'agents' ? <AppDesktop id="owner-agents" title="AGENTS" sub="the whole system · only you see this" mood="colony" apps={[...groupApps(agentApps, ownerApps), { k: 'perf', ic: '📈', label: 'Performance', tip: 'Every agent side by side', body: <AgentsDiagram agents={flow?.tree?.agents} /> }]} glass={{ ...agentsGlass(flow), app: 'perf' }} onClose={close} /> : null}</>;
}
const FCH_KEY = 'feeless.fch.tab';
const FEE_ONLY = ['fee'];
// 🎟 AGENT SLOTS (owner 2026-10-31): at most 1,000 agents bought across every user — you open slots for new buyers here (staff agents never count)
export function AgentSlots({ call }) {
  const [s, setS] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const take = x => { if (Number.isFinite(x?.open) && Number.isFinite(x?.taken) && Number.isFinite(x?.max)) setS(x); else setErr('The agent service did not answer with slots.'); };
  useEffect(() => { call('/admin/agent-slots').then(take).catch(e => setErr(e.message)); }, [call]);   // eslint-disable-line react-hooks/exhaustive-deps
  const open = async n => { setBusy(true); setErr(''); try { take(await call('/admin/agent-slots', { method: 'POST', body: JSON.stringify({ open: n }) })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!s) return <article className="fch-card" data-testid="fch-slots"><h4><Ic3 e="🎟" /> AGENT SLOTS</h4><p className="fch-nil">{err || 'reading…'}</p></article>;
  return <article className="fch-card fch-slots" data-testid="fch-slots"><h4><Ic3 e="🎟" /> AGENT SLOTS<small>{s.taken} of {s.open} open taken · max {s.max.toLocaleString()}</small></h4>
    <p className="fch-flow"><span><b className="m-num" key={s.taken}>{s.taken}</b><small>bought</small></span><i aria-hidden>/</i><span className={s.left ? 'is-good' : 'is-bad'}><b className="m-num">{s.left}</b><small>left for new buyers</small></span><i aria-hidden>/</i><span><b className="m-num">{s.open}</b><small>open</small></span></p>
    <ul className="fch-bars"><li><span>open of {s.max.toLocaleString()}</span><i><u style={{ transform: `scaleX(${Math.max(0.02, s.open / s.max)})` }} /></i><b>{Math.round((100 * s.open) / s.max)}%</b></li>
      <li><span>taken of open</span><i><u style={{ transform: `scaleX(${Math.max(0.02, s.open ? s.taken / s.open : 1)})` }} /></i><b>{s.open ? Math.round((100 * s.taken) / s.open) : 100}%</b></li></ul>
    <div className="m-seg" role="group" aria-label="Open more agent slots">{[50, 100, 250].map(n => <button key={n} type="button" disabled={busy || s.open >= s.max} onClick={() => open(s.open + n)} data-tip={`Open ${n} more slots for new buyers`} data-testid={`fch-slots-${n}`}>+{n}</button>)}
      <button type="button" disabled={busy || s.open >= s.max} onClick={() => open(s.max)} data-tip="Open every slot up to the 1,000 cap" data-testid="fch-slots-all">All {s.max.toLocaleString()}</button>
      <button type="button" disabled={busy || s.open <= s.taken} onClick={() => open(s.taken)} data-tip="Close sales: no new agents until you open more (nobody loses an agent)" data-testid="fch-slots-close">Pause sales</button></div>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <SlotAgents /></article>;
}
// Every agent that holds a slot: what it is, what it has filed, how it did.
function SlotAgents() {
  const flow = useFlow(); const [q, setQ] = useState(''); const [by, setBy] = useState('proofs'); const all = flow?.tree?.agents || [];
  const rows = [...all].filter(a => !q || String(a.name).toLowerCase().includes(q.toLowerCase())).sort((a, b) => (by === 'pnl' ? (Number(b.pnlSol) || 0) - (Number(a.pnlSol) || 0) : by === 'won' ? (b.won || 0) - (a.won || 0) : (b.proofs || 0) - (a.proofs || 0)));
  const sort = (k, l, tip) => <button type="button" className={by === k ? 'active' : ''} aria-pressed={by === k} onClick={() => setBy(k)} data-tip={tip} data-testid={`slots-sort-${k}`}>{l}</button>;
  return <section className="fch-slot-agents" data-testid="slots-agents"><header><b>EVERY AGENT <em className="m-num">{all.length}</em></b><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="Find an agent" aria-label="Find an agent" data-testid="slots-find" /><span className="m-seg" role="group" aria-label="Sort by">{sort('proofs', 'Proofs', 'Most proofs first')}{sort('won', 'Won', 'Most wins first')}{sort('pnl', 'Result', 'Best result first')}</span></header>
    {rows.length ? <Table className="cs-t fch-slot-t"><TableHeader><TableRow><TableHead>Agent</TableHead><TableHead>Kind</TableHead><TableHead>Proofs</TableHead><TableHead>Won</TableHead><TableHead>Result</TableHead></TableRow></TableHeader><TableBody>{rows.map(a => { const v = Number(a.pnlSol) || 0; return <TableRow key={a.id}><TableCell>{a.name}</TableCell><TableCell>{a.kind === 'general' ? 'General' : 'Trader'}</TableCell><TableCell className="m-num">{a.proofs || 0}</TableCell><TableCell className="m-num">{a.won || 0} of {a.trades || 0}</TableCell><TableCell className={`m-num ${v > 0 ? 'is-up' : v < 0 ? 'is-dn' : ''}`}>{v ? `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(4)} SOL` : 'No result yet'}</TableCell></TableRow>; })}</TableBody></Table> : <p className="fch-nil">{flow ? 'No agent matches.' : 'Reading agents…'}</p>}</section>;
}

export function FeeCatDesk({ call }) {
  const [tab, setTab] = useState(() => { try { const k = localStorage.getItem(FCH_KEY); return FCH_TABS.some(t => t[0] === k) ? k : 'overview'; } catch { return 'overview'; } });
  const root = React.useRef(null);
  const [wantOwner, setWantOwner] = useState(false);
  useEffect(() => { const go = () => { setTab('owner'); setWantOwner(true); }; window.addEventListener('fee:owner', go); return () => window.removeEventListener('fee:owner', go); }, []);
  const pickTab = k => { setTab(k); try { localStorage.setItem(FCH_KEY, k); } catch { /* private window */ } };
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { if (wantOwner && d && root.current) { root.current.scrollIntoView({ behavior: 'smooth', block: 'start' }); setWantOwner(false); } }, [wantOwner, d]);
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
  const brainPane = () => <div className="fch-fold fch-brain" data-testid="fch-brain">
      <FeeModels />
      <FeeBrain />
      <FastDial d={d} busy={busy} onApply={vals => { setDraft(cur => ({ ...cur, ...vals })); save({ rules: { ...draft, ...vals }, strategyPreset: 'fast' }); }} />
      <div className="fch-groups">{RULE_GROUPS.map(([g, keys]) => { const ks = keys.filter(k => (d.bounds || {})[k]); if (!ks.length) return null;
        return <fieldset key={g} className="fch-group"><legend>{g}</legend>{ks.map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
          <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset>; })}
        <fieldset className="fch-group"><legend><Ic3 e="💵" /> SIZE</legend><label><span>Max SOL per trade<em>0.1–10</em></span><NumInput value={size} onChange={e => setSize(e.target.value)} /></label>
          {Object.keys(d.bounds || {}).filter(k => !RULE_GROUPS.some(([, ks]) => ks.includes(k))).map(k => { const [lo, hi] = d.bounds[k]; return <label key={k} data-tip={FEE_LABELS[k]?.[1] || ''}><span>{FEE_LABELS[k]?.[0] || k}<em>{lo}–{hi}</em></span>
            <NumInput value={draft[k] ?? ''} onChange={e => setDraft(x => ({ ...x, [k]: Number(e.target.value) }))} /></label>; })}</fieldset></div>
      <button type="button" className="m-btn m-go" disabled={busy} onClick={() => save({ strategyPreset: 'fast' })} data-testid="fch-save">Save my tuning</button>
    </div>;
  return <section className="fch" data-testid="feecat-desk">
    <header className="fch-hero m-card m-live">
      <span className={`fch-orb ${running ? 'is-on' : ''}`} aria-hidden>🐱</span>
      <span className="fch-who"><b>FEE</b><small className={running ? 'is-on' : 'is-off'} data-testid="fch-status">{running ? `● LIVE · cycle ${cyc == null ? '…' : `${cyc}s ago`}` : '⏸ PAUSED'}</small>
        <em>{realView(c).real ? 'REAL · she proposes, your wallet signs each' : 'paper desk · go real from 👛 FEE\'S WALLET'}</em></span>
      <span className="fch-kpi"><small>EQUITY</small><b data-testid="fch-equity">{sol(equity)}</b><i className={roi >= 0 ? 'm-pos' : 'm-neg'}>{roi >= 0 ? '+' : ''}{roi.toFixed(1)}% vs {start} SOL</i></span>
      <span className="fch-kpi"><small>REALIZED</small><b className={(n(c.realizedPnlSol) || 0) >= 0 ? 'm-pos' : 'm-neg'}>{sol(c.realizedPnlSol)}</b><i>{trades} trades</i></span>
      <span className="fch-kpi fch-ring" style={{ '--k': (wr ?? 0) / 100 }}><small>WON</small><b>{wr == null ? '—' : `${Math.round(wr)}%`}</b></span>
      <span className="fch-kpi fch-ring" style={{ '--k': (n(disc.lives) ?? 9) / (n(disc.maxLives) || 9) }} data-tip="Her 9 lives: a loss takes one, a win in 24h gives one back, 0 = she naps"><small>LIVES</small><b data-testid="fch-lives">{disc.lives ?? '—'}</b></span>
      <span className="fch-kpi"><small>OPEN</small><b>{pos.length}</b><i>{disc.why && disc.why !== 'normal size' ? disc.why : 'discipline normal'}</i></span>
      <span className="fch-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => save({ status: running ? 'paused' : 'running' })} data-testid="fch-toggle">{running ? '⏸ Pause' : '▶ Resume'}</button>
        <button type="button" className="m-btn m-go" disabled={busy || !running} onClick={() => save({ action: 'run' })} data-testid="fch-run"><Ic3 e="⚡" /> Run a cycle</button></span>
    </header>
    <div ref={root}><SegTabs items={FCH_TABS} value={tab} onChange={pickTab} label="Fee's desk" className="fch-tabs" testid={k => `fch-tab-${k}`} /></div>
    {tab === 'owner' ? <OwnerDesk cat={c} trades={trades} feeApps={[
      { k: 'lane', ic: '🎚', label: 'Lane', tip: 'The agents lane she follows and what the duo learned', body: <div className="fch-grid"><AgentLane d={d} busy={busy} onSave={lane => save({ agentLane: lane })} /><DuoLearn learn={d.duoLearn} /></div> },
      { k: 'brain', ic: '🧠', label: 'Brain', tip: 'Her style, her rules and what she learned', body: brainPane() },
      { k: 'prompts', ic: '🎭', label: 'Prompts', tip: 'Her record and the mindsets written from it', body: <PromptStudio call={call} only={FEE_ONLY} /> },
      { k: 'style', ic: '🎨', label: 'Wallet + style', tip: 'Her wallet and how she looks', body: <FeeOwnerBar cat={c} /> },
      { k: 'model', ic: '🧪', label: 'Model Lab', tip: 'Owner only: the plan for FEELESS\'s own AI model, built from the stash, and where the big models fall short', body: <ModelLab /> },
    ]} agentApps={[
      { k: 'colony', ic: '💎', label: 'Collective', tip: 'The living print, the Pool, every agent and every winning proof', body: <div className="cll-inwin"><React.Suspense fallback={null}><CollectiveLandingLazy more={<ColonyFlow api={flowApi} />} /></React.Suspense></div> },
      { k: 'collective', ic: '💎', label: 'Collective HQ', tip: 'Owner only: where the money stands, every split and fee with a hover that explains it, and the Pool wallet', body: <CollectiveOwner call={call} /> },
      { k: 'pow', ic: '⛏', label: 'PoW folders', tip: "Every agent's proofs", body: <PowEngine /> },
      { k: 'allwork', ic: '🗂', label: 'All work', tip: 'Every proof and every job from every agent, with how each scored', body: <AllWork cat={c} work={work} /> },
      { k: 'prompts', ic: '🎭', label: 'Prompts', tip: 'Every agent\'s record and the mindsets written from it', body: <PromptStudio call={call} /> },
      { k: 'ideas', ic: '💡', label: 'Ideas', tip: 'OSSY and G4 pitch vitals, mechanics and money ideas from real counts. You mark them. Nothing changes until you say', body: <IdeasFolder cat={c} work={work} /> },
      { k: 'git', ic: '🐙', label: 'Git', tip: 'The same Git folder as Fee\'s desktop: every kept proof, sorted, and your own repo', body: <GitFolder cat={c} work={work} scope="collective" /> },
      { k: 'stash', ic: '🧊', label: 'Stash', tip: 'Every proof kept sealed, with its web of sources', body: <StashWeb call={call} testid="own-stash" /> },
      { k: 'ready', ic: '🔌', label: 'Providers', tip: 'Which keys and services are ready', body: <ProviderReady call={call} /> },
      { k: 'slots', ic: '🎟', label: 'Agent slots', tip: 'Who can buy an agent, and how many are open', body: <AgentSlots call={call} /> },
    ]} call={call} /> : null}
    {tab === 'overview' ? <div className="fch-grid">
      <article className="fch-card" data-testid="fch-funnel"><h4><Ic3 e="🔎" /> WHY SHE {f.passed ? 'TRADES' : "ISN'T TRADING"}<small>{d.scan?.at ? `scan ${agoS(d.scan.at)}s ago` : 'no scan yet'}</small></h4>
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

      <article className="fch-card fch-wide" data-testid="fch-open"><h4><Ic3 e="📂" /> OPEN TRADES<small>{pos.length} of {d.rules?.maxPositions ?? 5}</small></h4>
        {pos.length ? <ul className="fch-pos">{pos.map(p => { const ch = n(p.currentChange) || 0; return <li key={p.pairAddress} className={ch >= 0 ? 'is-up' : 'is-dn'}>
          <b>${p.symbol}</b><span className="fch-pbar"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(ch) / 60)})` }} /></span><em>{ch >= 0 ? '+' : ''}{ch.toFixed(1)}%</em><small>{sol(p.costSol)} · {Math.round((Date.now() / 1000 - (n(p.openedAt) || 0)) / 60)}m</small><i className="fcl-tags">{readWords({ setups: p.setups, read: p.read, duo: p.duoAtEntry }).slice(0, 3).join(' · ')}</i></li>; })}</ul>
          : <p className="fch-nil">flat — waiting for a coin that passes</p>}
      </article>

      <FeeTape events={d.events} />
    </div> : null}

  </section>;
}
