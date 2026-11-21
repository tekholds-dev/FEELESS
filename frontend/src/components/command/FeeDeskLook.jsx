import React, { Suspense, useEffect, useState } from 'react';
import { DeskCabinet, DeskLook, DeskPop, Meter, stamp, useDeskLook } from '../desk/DeskLook';
import { DuoLearn } from './FeeCatLive';
import { AgentsDiagram } from './DeskShell';
import { AgentDesktop } from './CatWorkbench';
import { apiUrl } from '../../lib/api';
const CollectiveLandingLazy = React.lazy(() => import('./CollectiveLanding').then(m => ({ default: m.CollectiveLanding })));

// 🖥 FEE'S DESK + THE COLLECTIVE IN THE DESK LOOK (Slice 34, owner 2026-11-20: "make this the default look for Fee, agents and Collective").
// One screen with a Fee | The Collective switch. Every number comes from `GET /admin/feecat` (Fee) or `/api/cats/colony/flow` (The Collective);
// a missing one says so. Every folder of the classic owner desktops opens here as a popout (the rail), so nothing is lost.

const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const sol = v => { const n = num(v); return n == null ? '—' : `${n >= 0 ? '' : '−'}${Math.abs(n).toFixed(3)} SOL`; };
const pct = v => { const n = num(v); return n == null ? '—' : `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(1)}%`; };
const ago = ts => { const t = num(ts); if (!t) return ''; const s = Math.max(0, Date.now() / 1000 - (t > 1e12 ? t / 1000 : t)); return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
const dur = v => { const x = num(v); if (x == null) return '—'; return x < 60 ? `${Math.round(x)}s` : x < 3600 ? `${Math.round(x / 60)}m` : x < 86400 ? `${Math.round(x / 3600)}h` : `${Math.round(x / 86400)}d`; };
const secs = ts => { const t = num(ts); return t ? (t > 1e12 ? t / 1000 : t) : null; };
// every folder its own real 3D icon (no two share one)
export const FEE_RAIL_ICON = { lane: 'map-pin', brain: 'setting', prompts: 'chat-text', rails: 'shield', model: 'rocket', collective: 'sphere', pow: 'axe', allwork: 'folder', ideas: 'bulb', git: 'link', stash: 'locker', ready: 'key', adlab: 'video-cam', slots: 'credit-card' };
// 🗄 the cabinet's drawers: each its own icon, never one the rail already uses (icon audit, Slice 34 — deskIcons.test.js)
export const FEE_DRAWER_ICON = { moves: 'flash', skips: 'thumb-down', learn: 'notebook', agents: 'cube' };

export function useColonyFlow() {
  const [flow, setFlow] = useState(null);
  useEffect(() => { let on = true; const load = () => { if (!document.hidden) fetch(apiUrl('/api/cats/colony/flow?limit=20')).then(r => r.json()).then(x => on && setFlow(x)).catch(() => {}); };
    load(); const t = setInterval(load, 20000); return () => { on = false; clearInterval(t); }; }, []);
  return flow;
}

export function FeeDeskLook({ c, d, equity, roi, start, trades, wr, disc, pos, duo, f, running, cyc, busy, save, feeApps = [], agentApps = [] }) {
  const [who, setWho] = useState(() => { try { return localStorage.getItem('feeless.feeDesk.who') || 'fee'; } catch { return 'fee'; } });
  const pickWho = k => { setWho(k); try { localStorage.setItem('feeless.feeDesk.who', k); } catch { /* this visit only */ } };
  const [pop, setPop] = useState(null);   // a folder popped out over the desk: { k, label, body } | 'desktop'
  const flow = useColonyFlow();
  const [, setDeskLook] = useDeskLook();
  const events = d?.events || [];
  const stale = running && num(cyc) != null && cyc > 600;   // "running" but no cycle in 10 min: say so, never "live"
  const state = !running ? ['paused', 'warn'] : stale ? ['stale', 'warn'] : ['live', 'live'];
  const lives = num(disc?.lives); const maxLives = num(disc?.maxLives) || 9;
  const agents = flow?.tree?.agents || [];
  const all = [...feeApps.map(a => ({ ...a, side: 'fee' })), ...agentApps.map(a => ({ ...a, side: 'agents' }))];
  const rail = [{ k: 'desk', e: '🖥', icon: 'computer', label: who === 'fee' ? "Fee's desk" : 'The Collective', current: true, onClick: () => {} },
    { k: 'desktop', e: '🗂', icon: 'folder-new', label: 'Her whole desktop (every folder)', onClick: () => setPop('desktop') },
    { k: 'print', e: '🔮', icon: 'target', label: 'The living print (the Collective page)', onClick: () => setPop({ k: 'print', label: 'The living print', body: <Suspense fallback={<p className="dkl-empty">Opening the Collective…</p>}><CollectiveLandingLazy /></Suspense> }) }, { k: 'hr1', hr: true },
    ...feeApps.map(a => ({ k: `fee-${a.k}`, e: a.ic, icon: FEE_RAIL_ICON[a.k], label: a.label, onClick: () => setPop(a) })), { k: 'hr2', hr: true },
    ...agentApps.map(a => ({ k: `ag-${a.k}`, e: a.ic, icon: a.k === 'prompts' ? 'chat-bubble' : FEE_RAIL_ICON[a.k], label: a.label, onClick: () => setPop(a) }))];
  const pulse = who === 'fee'
    ? [{ k: 'equity', label: 'Equity', value: sol(equity), delta: pct(roi), up: (roi || 0) >= 0 }, { k: 'real', label: 'Realized', value: sol(c?.realizedPnlSol) }, { k: 'lives', label: 'Lives', value: lives == null ? '—' : `${lives}/${maxLives}` }]
    : [{ k: 'pnl', label: 'All agents', value: flow ? sol(flow.pnlSol) : '—' }, { k: 'agents', label: 'Agents', value: flow ? String(flow.agents ?? agents.length) : '—' }];

  const feeWidgets = [
    { k: 'equity', title: 'Equity', chip: realChip(c), body: <><span className="dkl-big"><b className="m-num" data-testid="fdl-equity">{sol(equity)}</b><small>{pct(roi)} vs {start} SOL</small></span><Meter v={num(roi) == null ? null : Math.min(1, Math.max(0, 0.5 + roi / 200))} tone={(roi || 0) >= 0 ? '' : 'bad'} /></> },
    { k: 'won', title: 'Won', chip: `${trades} trades`, body: <><span className="dkl-big"><b className="m-num">{wr == null ? '—' : `${Math.round(wr)}%`}</b><small>realized {sol(c?.realizedPnlSol)}</small></span><Meter v={wr == null ? null : wr / 100} /></> },
    { k: 'lives', title: 'Nine lives', chip: disc?.why && disc.why !== 'normal size' ? 'cut' : 'normal', chipTone: disc?.why && disc.why !== 'normal size' ? 'warn' : '', body: <><span className="dkl-big"><b className="m-num" data-testid="fdl-lives">{lives ?? '—'}</b><small>of {maxLives} · a loss takes one</small></span><Meter v={lives == null ? null : lives / maxLives} tone={lives != null && lives <= 3 ? 'bad' : ''} /></> },
    { k: 'duo', title: 'Duo read', chip: duo?.read ? `${ago(duo.read)} ago` : 'waiting', body: duo?.read ? <span className="dkl-rows"><span><span>Both say skip</span><span className="m-num">{(duo.avoid || []).length}</span></span><span><span>Both say exit</span><span className="m-num">{(duo.exit || []).length}</span></span></span> : <p className="dkl-empty">The first read lands within 4 minutes of the AI round.</p> },
    { k: 'open', title: 'Open trades', chip: `${pos.length} of ${d?.rules?.maxPositions ?? 5}`, body: pos.length ? <span className="dkl-rows">{pos.slice(0, 3).map(p => <span key={p.pairAddress}><span>${p.symbol}</span><span className={`m-num ${(num(p.currentChange) || 0) >= 0 ? 'is-up' : 'is-dn'}`}>{pct(p.currentChange)}</span></span>)}</span> : <p className="dkl-empty">Flat: waiting for a coin that passes.</p> },
  ];
  const sum = k => agents.reduce((s, a) => s + (num(a[k]) || 0), 0); const proofs = sum('proofs'); const right = sum('right'); const graded = sum('graded');   // graded right = the Collective's grade, not trades won
  const colWidgets = [
    { k: 'pool', title: 'All agents', chip: flow ? `${flow.agents ?? agents.length} agents` : 'reading', body: <span className="dkl-big"><b className="m-num">{flow ? sol(flow.pnlSol) : '—'}</b><small>{flow ? `${flow.pow?.won || 0} of ${flow.pow?.trades || 0} PoW trades won` : 'reading the Collective'}</small></span> },
    { k: 'proofs', title: 'Proofs', chip: `${proofs} filed`, body: <><span className="dkl-big"><b className="m-num">{graded ? `${Math.round((100 * right) / graded)}%` : '—'}</b><small>{graded ? `${right} of ${graded} graded right` : 'none graded yet'}</small></span><Meter v={graded ? right / graded : null} /></> },
    { k: 'top', title: 'Leading agent', chip: agents.length ? 'by result' : 'none yet', body: agents.length ? <span className="dkl-rows">{[...agents].sort((a, b) => (num(b.pnlSol) || 0) - (num(a.pnlSol) || 0)).slice(0, 3).map(a => <span key={a.id || a.name}><span>{a.name}</span><span className={`m-num ${(num(a.pnlSol) || 0) >= 0 ? 'is-up' : 'is-dn'}`}>{sol(a.pnlSol)}</span></span>)}</span> : <p className="dkl-empty">No agent has filed yet.</p> },
  ];
  const funnel = <div className="fdl-mon" data-testid="fdl-funnel"><p className="dkl-line"><b className="m-num">{f.scanned}</b> coins read → <b className={`m-num ${f.passed ? 'is-up' : 'is-dn'}`}>{f.passed}</b> passed her rules{d?.scan?.at ? ` · scan ${ago(d.scan.at)} ago` : ' · no scan yet'}</p>
    {f.reasons.length ? <span className="dkl-rows">{f.reasons.map(r => <span key={r.k}><span>{r.k}</span><Meter v={Math.max(0.04, r.w)} tone="warn" /></span>)}</span> : null}
    {f.top.length ? <p className="dkl-line">Next up: {f.top.map(t => <span key={t.symbol} className="dkl-chip" data-tip={t.reason}>${t.symbol}</span>)}</p> : null}
    {[...f.brain, ...f.safety].length ? <p className="dkl-line">Her brain / safety said no: {[...f.brain, ...f.safety].map((x, i) => <span key={`${x.symbol}-${i}`} className="dkl-chip is-warn" data-tip={x.why}>${x.symbol}</span>)}</p> : null}
    {duo?.why ? <p className="dkl-line">Duo: {duo.why}</p> : null}</div>;
  const book = <div className="fdl-mon" data-testid="fdl-book">{pos.length ? <span className="dkl-rows">{pos.map(p => <span key={p.pairAddress}><span>${p.symbol} · {sol(p.costSol)}</span><span className={`m-num ${(num(p.currentChange) || 0) >= 0 ? 'is-up' : 'is-dn'}`}>{pct(p.currentChange)}</span></span>)}</span> : <p className="dkl-empty">Flat: waiting for a coin that passes.</p>}</div>;
  const monitors = who === 'fee'
    ? [{ k: 'a', kind: 'Why', title: f.passed ? 'she trades' : "she isn't trading", chips: [{ text: state[0], tone: state[1] }], body: funnel },
      { k: 'b', kind: 'Book', title: 'open trades', chips: [{ text: realChip(c) }], body: book }]
    : [{ k: 'a', kind: 'Proofs', title: 'newest filings', chips: [{ text: `${(flow?.proofs || []).length}` }], body: <div className="fdl-mon" data-testid="fdl-proofs">{(flow?.proofs || []).length
        ? <span className="dkl-rows">{flow.proofs.map(p => <span key={p.id}><span><b>{p.kind}</b> · {p.agent} · {String(p.label || '').replace(/^\W+\s*/u, '').slice(0, 60)}</span><span className="m-num">{p.stamp?.state || ''} {secs(p.at) ? stamp(secs(p.at)) : ''}</span></span>)}</span>
        : <p className="dkl-empty">{flow ? 'No proof filed yet.' : 'Reading the Collective…'}</p>}</div> },
      { k: 'b', kind: 'Agents', title: 'side by side', chips: [{ text: `${agents.length}` }], body: <div className="fdl-mon"><AgentsDiagram agents={agents} /></div> }];
  const vitals = who === 'fee'
    ? [{ k: 'eq', label: 'Equity', value: sol(equity), meter: num(roi) == null ? null : Math.min(1, Math.max(0, 0.5 + roi / 200)) }, { k: 'real', label: 'Realized', value: sol(c?.realizedPnlSol), unit: `${trades} trades` },
      { k: 'wr', label: 'Won', value: wr == null ? '—' : `${Math.round(wr)}%`, meter: wr == null ? null : wr / 100 }, { k: 'lives', label: 'Lives', value: lives ?? '—', unit: `/ ${maxLives}`, meter: lives == null ? null : lives / maxLives },
      { k: 'cycle', label: 'Last cycle', value: dur(cyc), unit: `ago · ${state[0]}`, meter: state[0] === 'live' ? 1 : 0, tone: state[1] === 'warn' ? 'warn' : '' }]
    : [{ k: 'agents', label: 'Agents', value: flow?.agents ?? agents.length }, { k: 'proofs', label: 'Proofs filed', value: proofs }, { k: 'right', label: 'Graded right', value: graded ? `${Math.round((100 * right) / graded)}%` : '—', unit: graded ? `${right}/${graded}` : '', meter: graded ? right / graded : null },
      { k: 'pow', label: 'PoW trades', value: flow?.pow?.trades ?? '—', unit: `${flow?.pow?.won ?? 0} won` }, { k: 'pnl', label: 'All agents', value: flow ? sol(flow.pnlSol) : '—', spark: agents.map(a => num(a.pnlSol) || 0) }];
  const drawers = who === 'fee'
    ? [{ k: 'moves', e: '⚡', icon: FEE_DRAWER_ICON.moves, label: 'Moves', n: events.length, files: events.slice(0, 24).map(e => ({ tab: secs(e.ts) ? stamp(secs(e.ts)) : '', title: `${e.type || 'move'}${e.symbol ? ` $${e.symbol}` : ''}${e.detail || e.reason ? ` · ${e.detail || e.reason}` : ''}`, st: /sell|loss|stop/i.test(e.type || '') ? 'w' : '' })), empty: 'No moves yet on this paper trail.' },
      { k: 'skips', e: '🚫', icon: FEE_DRAWER_ICON.skips, label: 'Said no', n: [...f.brain, ...f.safety].length, files: [...f.brain, ...f.safety].map(x => ({ title: `$${x.symbol}`, sub: x.why, st: 'w' })), empty: 'Nothing refused in the last scan.' },
      { k: 'learn', e: '🎓', icon: FEE_DRAWER_ICON.learn, label: 'Learned', n: (d?.duoLearn?.lessons || []).length, body: <DuoLearn learn={d?.duoLearn} /> }]
    : [{ k: 'agents', e: '🤖', icon: FEE_DRAWER_ICON.agents, label: 'Agents', n: agents.length, files: agents.slice(0, 40).map(a => ({ title: a.name, sub: `${num(a.proofs) || 0} proofs · ${sol(a.pnlSol)}`, st: (num(a.pnlSol) || 0) < 0 ? 'w' : '' })), empty: 'No agents yet.' }];
  const chat = <>
    <header className="dkl-chat-h"><b>{who === 'fee' ? 'Her tape' : 'The Collective'}</b><span className="dkl-sp" />
      {who === 'fee' ? <><button type="button" className="dkl-chip" disabled={busy} onClick={() => save({ status: running ? 'paused' : 'running' })} data-testid="fch-toggle">{running ? 'Pause' : 'Resume'}</button>
        <button type="button" className="dkl-go" disabled={busy || !running} onClick={() => save({ action: 'run' })} data-testid="fch-run">Run a cycle</button></> : null}</header>
    <ol className="dkl-feed" aria-label={who === 'fee' ? 'Her live moves' : 'Agents'} data-testid="fdl-feed">
      {who === 'fee' ? (events.length ? events.slice(0, 40).map((e, i) => <li key={e.id || i} className="dkl-msg is-ai"><span className="dkl-who"><b>{e.type}</b>{e.symbol ? <span>· ${e.symbol}</span> : null}<time className="m-num">{secs(e.ts) ? stamp(secs(e.ts)) : ''}</time></span>{e.detail || e.reason || e.why ? <p>{e.detail || e.reason || e.why}</p> : null}</li>)
        : <li className="dkl-msg is-ai"><p className="dkl-empty">No moves yet on this paper trail.</p></li>)
        : agents.slice(0, 30).map(a => <li key={a.id || a.name} className="dkl-msg is-ai"><span className="dkl-who"><b>{a.name}</b><span className="m-num">· {num(a.proofs) || 0} proofs</span></span><p className={`m-num ${(num(a.pnlSol) || 0) >= 0 ? 'is-up' : 'is-dn'}`}>{sol(a.pnlSol)}</p></li>)}
    </ol></>;
  const popApp = pop && pop !== 'desktop' ? (pop.k === 'print' ? pop : all.find(a => a.k === pop.k && a.label === pop.label)) : null;
  return <DeskLook id={`fee-${who}`} name={who === 'fee' ? 'Fee' : 'The Collective'} crumb="HQ" agents={[{ id: 'fee', name: 'Fee', on: who === 'fee' }, { id: 'collective', name: 'The Collective', on: who === 'collective' }]} onAgent={a => pickWho(a.id)}
    pulse={pulse} rail={rail} widgets={who === 'fee' ? feeWidgets : colWidgets} monitors={monitors} vitals={vitals} cabinet={<DeskCabinet who={who === 'fee' ? 'Fee' : 'The Collective'} drawers={drawers} id={`fee-${who}`} />} chat={chat} testid="fdl"
    barEnd={<button type="button" className="dkl-chip" onClick={() => setDeskLook({ classic: true })} data-tip="Back to the classic Fee page (saved)" data-testid="fdl-classic">Classic</button>}>
    <DeskPop open={!!popApp} title={popApp?.label || ''} wide onClose={() => setPop(null)} testid="fdl-pop">{popApp ? <div className="fdl-popbody" data-testid={`fdl-pop-${popApp.k}`}>{popApp.body}</div> : null}</DeskPop>
    {pop === 'desktop' ? <AgentDesktop cat={c} over start="none" extra={feeApps} mood="fee" onClose={() => setPop(null)} /> : null}
  </DeskLook>;
}
function realChip(c) { return c?.real?.on || c?.realMode ? 'real' : 'paper'; }
export const _test = { sol, pct, ago };
FeeDeskLook.displayName = 'FeeDeskLook';
export default FeeDeskLook;
