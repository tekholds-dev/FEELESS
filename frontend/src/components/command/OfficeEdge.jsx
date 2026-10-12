import React, { useState } from 'react';
import { sgn, ago, clock } from './OfficeBoard';
import '../../styles/officeEdge.css';

// ⚡ THE OFFICE'S EDGE PASS on screen (HQ › Agents): restart readiness · the empty seats · the switch test · YOUR limits on the agents ·
// the review queue · the winners we missed · launch context. Every number is a field of the ONE office payload (`backend/office_edge.py`,
// served with GET /admin/agents) — nothing here fetches, computes a trade number or places an order. The creator's buttons post to the
// existing POST /admin/agents (limits → realCfg via clean_cfg · review marks → display state the office never reads back).

export const WHO_CLS = { 'AGENTS CHOOSE': 'is-agents', 'CREATOR OVERRIDE': 'is-you' };
const SEAT_CLS = { FULL: 'is-ok', FILLING: 'is-go', 'NO VALID ENTRY': 'is-wait', 'OFFICE WARMING UP': 'is-warm', 'CREATOR MANUAL': 'is-you', 'AGENT CONTROL OFF': 'is-you' };

// 🔎 THE NARRATIVE PACKET — what the website / X research found for one coin (every source opens the real page)
const SOC_CLS = { ACTIVE: 'is-ok', STALE: 'is-wait', UNAVAILABLE: '', UNKNOWN: '' };
const MATCH_CLS = { yes: 'is-ok', no: 'is-bad', unknown: '' };
export function SocialLine({ p, now }) {
  if (!p) return <p className="oed-soc oed-soc-nil" data-testid="oed-social"><small>NARRATIVE</small><span>not researched yet — only the strongest candidates are read</span></p>;
  const t = now || Date.now() / 1000; const n = p.narrative || {}; const cc = p.cross || {}; const w = p.website || {}; const x = p.x || {};
  const ago_ = s => (s ? `${Math.max(0, Math.round((t - s) / 60))}m ago` : '—');
  const link = (u, l) => (u && /^https?:\/\//.test(u) ? <a href={u} target="_blank" rel="noopener noreferrer">{l}</a> : <span>{l}</span>);
  const cell = (k, l, v, cls, tip) => <span key={k} className={`oed-op ${cls || ''}`} data-testid={`oed-soc-${k}`} data-tip={tip}><small>{l}</small><b>{v}</b></span>;
  return <div className="oed-soc" data-testid="oed-social">
    {cell('narr', 'NARRATIVE', `${n.class || 'UNKNOWN'}${n.confidence ? ` ${Math.round(n.confidence * 100)}%` : ''}`, '', (n.keywords || []).join(', '))}
    {cell('id', 'IDENTITY', cc.confidence == null ? 'unknown' : `${cc.confidence}/100`, cc.confidence == null ? '' : cc.confidence >= 70 ? 'is-ok' : cc.confidence < 40 ? 'is-bad' : 'is-wait', (cc.flags || []).join(' · ') || 'no conflicts found')}
    {cell('site', 'WEBSITE', w.url ? link(w.url, w.reachable === false ? 'unreachable' : (w.title || 'open')) : 'none', w.reachable === false ? 'is-wait' : '')}
    {cell('x', 'SOCIAL', x.url ? link(x.url, `${p.social}${x.followers != null ? ` · ${x.followers.toLocaleString()}` : ''}`) : p.social || 'UNKNOWN', SOC_CLS[p.social])}
    {cell('mint', 'MINT MATCH', cc.mintMatch || 'unknown', MATCH_CLS[cc.mintMatch], cc.conflict ? 'the website shows another contract' : '')}
    {cell('last', 'LAST SOCIAL', ago_(x.lastPostAt), '')}
    {cell('age', 'RESEARCH AGE', ago_(p.at), '')}
  </div>;
}

// 🩺 LIVE OPERATION HEALTH — why the agents are (or are not) filling seats, in one line of real fields
const EX_CLS = { HEALTHY: 'is-ok', DEGRADED: 'is-wait', BLOCKED: 'is-bad', UNKNOWN: '' };
// 🔁 THE 60s CYCLE — what the desk looked at this pass and what each seat is doing
const ACT_CLS = { HOLD: 'is-ok', REVIEW: '', 'CHALLENGER FOUND': 'is-wait', SWITCHING: 'is-go', 'TAKE / EXIT': 'is-wait', FILLING: 'is-go', 'CASH — NO VALID ENTRY': '' };
export function CycleLine({ c, acts, now, fresh, load }) {
  if (!c || !c.at) return null;
  const t = now || Date.now() / 1000; const ago = Math.max(0, Math.round(t - c.at)); const next = Math.max(0, Math.round(c.at + (c.every || 60) - t));
  const cell = (k, l, v, tip) => <span key={k} className={`oed-op ${typeof tip === 'string' && tip.startsWith('is-') ? tip : ''}`} data-testid={`oed-cy-${k}`} data-tip={typeof tip === 'string' && tip.startsWith('is-') ? '' : tip}><small>{l}</small><b>{v ?? '—'}</b></span>;
  const best = c.best ? `$${c.best.symbol} ${c.best.cleared ? '✓' : '·'} rank ${Math.round(Number(c.best.lean || 0))}` : 'none';
  return <div className="oed-cycle" data-testid="oed-cycle">
    <div className="oed-ops">
      {cell('last', 'LAST CYCLE', `${ago}s ago`, `cycle #${c.n ?? '—'}`)}{cell('next', 'NEXT CYCLE', `${next}s`)}
      {cell('new', 'NEW LAUNCHES', c.newLaunches, `≤ 1h old on the board · ${c.newToDesk ?? 0} new to the desk this pass`)}{cell('board', 'BOARD', c.board, 'every launch coin the feed holds')}
      {cell('screened', 'CHEAP SCREENED', c.screened, Object.entries(c.by || {}).map(([k, v]) => `${k} ${v}`).join(' · '))}{cell('reviewed', 'DEEP REVIEWED', c.reviewed, 'read on real 1-minute candles')}
      {cell('cleared', 'CLEARED', c.cleared, `of ${c.cases ?? 0} case files`)}{cell('best', 'BEST CHALLENGER', best, c.best?.blocked || (c.best?.cleared ? 'cleared every desk' : ''))}
      {cell('unique', 'UNIQUE THIS CYCLE', c.read, `${c.freshVsLast ?? '—'} not read last cycle`)}
      {load ? <>{cell('scans', 'HOLDER SCANS', load.scans, `${load.scanWakes ?? 0} landed and woke their case`)}{cell('social', 'SOCIAL RESEARCHED', load.browser, 'browser page reads this cycle (strongest candidates only)')}</> : null}
    </div>
    {fresh ? <div className="oed-ops oed-fresh" data-testid="oed-fresh">{[['price', 'PRICE AGE'], ['tape', 'TAPE AGE'], ['candle', 'CANDLE AGE'], ['liquidity', 'LIQUIDITY AGE'], ['agentInput', 'AGENT INPUT AGE'], ['decision', 'DECISION AGE']].map(([k, l]) =>
      cell(`f-${k}`, l, fresh[k] == null ? '—' : `${Math.round(fresh[k])}s`, fresh[k] != null && fresh[k] > 180 ? 'is-wait' : ''))}</div> : null}
    {(acts || []).length > 0 && <ul className="oed-acts" data-testid="oed-acts">{acts.map((a, i) => <li key={i} className={ACT_CLS[a.action] || ''} data-tip={a.why || ''}>
      <small>SEAT {i + 1}</small><b>{a.symbol ? `$${a.symbol}` : '▫ open'}</b><em>{a.action}{a.to ? ` → $${a.to}` : ''}</em></li>)}</ul>}
  </div>;
}

export function OpsLine({ o }) {
  if (!o) return null;
  const cell = (k, l, v, cls, tip) => <span key={k} className={`oed-op ${cls || ''}`} data-testid={`oed-op-${k}`} data-tip={tip}><small>{l}</small><b>{v}</b></span>;
  return <div className="oed-ops" data-testid="oed-ops">
    {cell('office', 'OFFICE', o.office, o.office === 'LIVE' ? 'is-ok' : 'is-wait')}
    {cell('keeper', 'KEEPER', o.keeper, o.keeper === '1 active' ? 'is-ok' : 'is-bad')}
    {cell('open', 'OPEN SEATS', o.openSeats, o.openSeats ? 'is-wait' : 'is-ok')}
    {cell('valid', 'VALID', o.valid, o.valid ? 'is-ok' : '')}
    {cell('cleared', 'CLEARED', o.cleared, '')}
    {cell('next', 'NEXT SEAT ACTION', o.nextIn != null ? `${o.nextIn}s` : '—', '')}
    {cell('exec', 'EXECUTION', o.execution, EX_CLS[o.execution])}
    {cell('budget', 'BUY BUDGET', `${o.budget?.left ?? '—'} / ${o.budget?.of ?? '—'}`, o.budget?.left === 0 ? 'is-bad' : '', 'real buys left this hour')}
    {cell('cash', 'CASH', o.cash != null ? `$${Number(o.cash).toFixed(2)}` : '—', '')}
    {o.block ? <span className="oed-op oed-op-block is-wait" data-testid="oed-op-block" data-tip={o.block}><small>SEAT BLOCK</small><b>{o.code}</b><em>{o.block}</em></span> : null}
  </div>;
}
const tag = (cls, text, tip, key) => <i key={key} className={`oed-tag ${cls || ''}`} data-tip={tip}>{text}</i>;
const pctCls = v => (v == null ? '' : Number(v) > 0 ? 'oed-up' : Number(v) < 0 ? 'oed-dn' : '');

// 🔌 RESTART READINESS — four lamps; discretionary moves wait for the last one
export function ReadyStrip({ r, compact }) {
  if (!r) return null;
  return <div className={`oed-ready ${r.live ? 'is-live' : 'is-warm'} ${compact ? 'is-compact' : ''}`} data-testid="oed-ready" data-tip={r.live ? 'Every seat and exit rule is active.' : `Until LIVE: no fill, no switch, no read or time exit — price, pool and safety exits still act. ${r.why}`}>
    <small>RESTART READINESS</small>
    <ol>{(r.steps || []).map(([w, ok], i) => <li key={w} className={ok ? 'is-on' : ''} style={{ '--i': i }}><span aria-hidden />{w.replace('OFFICE ', '')}</li>)}</ol>
    {!compact && <em>{r.live ? `LIVE${r.sinceSec != null ? ` · process up ${clock(r.sinceSec)}` : ''}` : r.why}</em>}
  </div>;
}

// 🪑 THE EMPTY SEATS — why a seat is empty right now, how long, and what would fill it (cash is a valid position)
export function SeatState({ s, speed }) {
  if (!s) return <div className="oed-box" data-testid="oed-seat"><b>🪑 EMPTY SEATS</b><span className="oed-nil">the real card's seats are read on the next tier tick</span></div>;
  const late = s.emptyFor != null && s.target && s.emptyFor > s.target; const fill = s.emptyFor != null && s.target ? Math.min(1, s.emptyFor / (s.target * 2)) : 0;
  const total = (s.blockers || []).reduce((a, b) => a + b[2], 0) || 1; const sp = speed || {};
  const st = (k, l) => { const v = sp[k] || {}; return <span key={k} data-tip={`${v.n || 0} measured · avg ${v.avg ?? '—'}s · worst ${v.max ?? '—'}s`}><small>{l}</small><b>{v.med != null ? `${v.med}s` : '—'}</b><u>median · n {v.n || 0}</u></span>; };
  return <div className={`oed-box oed-seat ${SEAT_CLS[s.state] || ''}`} data-testid="oed-seat">
    <header><b>🪑 EMPTY SEATS</b>{tag(SEAT_CLS[s.state], s.state)}<em>{s.held} of {s.want} held{s.empty ? ` · ${s.empty} open` : ''}</em></header>
    <p className="oed-why" data-testid="oed-seat-why">{s.reason}</p>
    {(s.seats || []).length > 0 && <ul className="oed-seats" data-testid="oed-seat-list">{s.seats.map(x => <li key={x.seat}><small>SEAT {x.seat}</small>{tag(x.code === 'FILLING' ? 'is-go' : 'is-wait', x.code)}<em>{x.reason}</em></li>)}</ul>}
    {s.empty ? <div className="oed-meter" data-tip={`empty ${s.emptyFor ?? 0}s · your target ${s.target}s`}><small>EMPTY FOR</small><span className={`oed-bar ${late ? 'is-late' : ''}`}><i style={{ transform: `scaleX(${Math.max(0.02, fill)})` }} /><u style={{ left: '50%' }} /></span>
      <b className={late ? 'oed-dn' : ''}>{s.emptyFor != null ? `${s.emptyFor}s` : '—'}<u> / target {s.target}s</u></b>{s.nextIn != null && <em>next tick in {s.nextIn}s</em>}</div> : null}
    {(s.validSyms || []).length > 0 && <p className="oed-chips">{s.validSyms.map(x => tag('is-go', `$${x}`, 'cleared every desk — takes the next empty seat', x))}</p>}
    {(s.blockers || []).length > 0 && <ul className="oed-bars" data-testid="oed-blockers">{s.blockers.map(([k, w, n]) => <li key={k}><span>{w}</span><span className="oed-bar"><i style={{ transform: `scaleX(${n / total})` }} /></span><em>{n}</em></li>)}</ul>}
    <div className="oed-tiles">{st('seatEmpty', 'seat empty')}{st('validToFill', 'valid → fill')}{st('exitToFill', 'exit → next fill')}<span><small>wake-ups</small><b>{sp.seatWakes ?? 0}</b><u>tick every {sp.tickEvery ?? s.tickEvery ?? '—'}s</u></span></div>
  </div>;
}

// ⇄ THE SWITCH TEST — every line of the superiority test for the weakest held coin vs the strongest cleared challenger
export function SwitchEval({ e }) {
  if (!e) return <div className="oed-box" data-testid="oed-switch"><b>⇄ SWITCH TEST</b><span className="oed-nil">no held coin to test this tick</span></div>;
  const c = e.current || {}; const n = e.challenger; const need = Number(e.need) || 0; const span = Math.max(3, need * 2, Math.abs(Number(e.edge) || 0));
  return <div className={`oed-box oed-switch ${e.switch ? 'is-go' : 'is-hold'}`} data-testid="oed-switch">
    <header><b>⇄ SWITCH TEST</b>{tag(e.switch ? 'is-go' : 'is-wait', e.switch ? 'SWITCH' : 'SEAT KEPT')}<em>{e.mode ? `mode ${e.mode}` : ''}{e.dueIn != null ? ` · next duty ${clock(e.dueIn)}` : ''}</em></header>
    <div className="oed-vs">
      <span className="oed-side"><small>HELD</small><b>${c.symbol || '—'}</b><em className={pctCls(c.pnl)}>{sgn(c.pnl)}</em><u>{c.heldMin != null ? `${Math.round(c.heldMin)} min` : '—'} · rank {c.score ?? '—'} · thesis {c.thesis || 'unread'}</u></span>
      <span className="oed-arrow" aria-hidden>{e.switch ? '⇄' : '⇸'}</span>
      <span className="oed-side"><small>CHALLENGER</small>{n ? <><b>${n.symbol}</b><em>{n.cleared ? 'READY' : 'not ready'}</em><u>rank {n.score ?? '—'} · {n.structure || 'no chart'}{n.data ? ` · data ${String(n.data).replace(/_/g, ' ').toLowerCase()}` : ''}</u></> : <b className="oed-nil">none</b>}</span>
    </div>
    <div className="oed-meter" data-tip="Rank margin = the READY challenger's kernel rank − the held coin's. The tick is what your switching mode needs."><small>RANK MARGIN</small><span className="oed-bar is-mid"><i className={Number(e.edge) >= need ? '' : 'is-short'} style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.max(0, Number(e.edge) || 0) / span))})` }} /><u style={{ left: `${Math.min(100, (need / span) * 100)}%` }} /></span>
      <b>{sgn(e.edge, 1, '')}<u> / need {sgn(need, 1, '')}</u></b></div>
    <ul className="oed-lines" data-testid="oed-lines">{(e.lines || []).map(([l, ok, d]) => <li key={l} className={ok ? 'is-ok' : 'is-no'}><span aria-hidden>{ok ? '✓' : '✕'}</span><b>{l}</b><em>{d}</em></li>)}</ul>
    <p className="oed-why" data-testid="oed-switch-why">{e.why}</p>
  </div>;
}

// the compact strip on the office itself: one chip per edge-pass state, each opens its full panel
export function EdgeBand({ o, onOpen }) {
  if (!o || o.cold) return null;
  const pol = o.policy || {}; const ctl = pol.controls || []; const yours = ctl.filter(c => c.who === 'CREATOR OVERRIDE').length; const s = o.seat; const e = o.switchEval; const rv = o.review || {};
  const open = Object.values(rv.open || {}).reduce((a, b) => a + b, 0); const ms = rv.missedSummary || {};
  const chip = (k, cls, label, val, sub, tip) => <button type="button" className={`oed-chip ${cls || ''}`} onClick={() => onOpen && onOpen(k)} data-tip={tip} data-testid={`oed-chip-${k}`}><small>{label}</small><b>{val}</b><u>{sub}</u></button>;
  return <div className="oed-band" data-testid="oed-band">
    {chip('ready', o.ready?.live ? 'is-ok' : 'is-warm', 'READINESS', o.ready?.live ? 'LIVE' : (o.ready?.state || '—').replace('OFFICE ', ''), o.ready?.live ? 'every rule active' : 'no fill / switch / time exit', o.ready?.why)}
    {chip('seat', SEAT_CLS[s?.state], 'SEATS', s ? `${s.held}/${s.want}` : '—', s?.state || 'next tick', s?.reason)}
    {chip('switch', e?.switch ? 'is-go' : '', 'SWITCH TEST', e ? (e.switch ? 'SWITCH' : 'KEEP') : '—', e ? `margin ${sgn(e.edge, 1, '')} / ${sgn(e.need, 1, '')}` : 'no test', e?.why)}
    {chip('limits', pol.manual ? 'is-you' : '', 'YOUR LIMITS', pol.manual ? 'MANUAL' : `${yours} set`, pol.manual ? 'agents make no move' : `${ctl.length - yours} agents choose`, 'Who decides each control: you (CREATOR OVERRIDE) or the agents (AGENTS CHOOSE)')}
    {chip('review', open ? 'is-warm' : '', 'REVIEW', open, 'waiting · never blocks', rv.note)}
    {chip('missed', '', 'MISSED WINNERS', ms.n ?? 0, `${ms.correct ?? 0} correct skips · 6h`, ms.note)}
  </div>;
}

// 🎛 YOUR LIMITS — per control AGENTS CHOOSE (0 / 'agents') or CREATOR OVERRIDE (a value), plus the master authority
const OPT_WORD = { agents: '🤖 agents', off: 'off', conservative: 'conservative', normal: 'normal', aggressive: 'aggressive', go: 'GO only', auto: '🤖 agents', custom: 'custom' };
export const optLabel = (key, v, unit) => (key === 'agentMinAgeH' && v > 0 ? (v < 1 ? `${Math.round(v * 60)}m+` : `${v}h+`) : key === 'agentMinAgeH' ? '🐣 any age' : v === 0 || v === 'agents' || (key === 'agentTrail' && v === 'auto') ? '🤖 agents' : typeof v === 'number' ? `${key === 'agentSl' ? '−' : key === 'agentTp' ? '+' : ''}${v}${unit === '%' || unit === '% of card' ? '%' : unit === 'min' ? 'm' : unit === 's' ? 's' : ''}` : OPT_WORD[v] || String(v));
const TRAIL_SUB = [['agentTrailArm', 'arm at +', [5, 10, 15, 20, 30]], ['agentTrailPct', 'points off the peak', [3, 5, 8, 10, 15]]];
export const LIMIT_GROUPS = [['EXITS', 'when a coin leaves', ['agentTp', 'agentSl', 'agentTrail', 'agentMaxHold']], ['SIZE & SEATS', 'how much goes in, and where', ['agentSizePct', 'agentSeats', 'agentSeatTarget']],
  ['MOVES', 'when a seat is filled or handed over', ['agentSwitch', 'agentEntry', 'agentMinAgeH']]];
// the rule IN FORCE on each open position right now (what Reaper is obeying): take · stop · hold · trail, each with who set it
export function positionPolicy(o) {
  const pol = o?.policy || {};
  return (o?.positions || []).map(p => ({ symbol: p.symbol, owner: p.owner, take: p.take, takeWho: pol.tp ? 'you' : p.takeSource === 'learned' ? 'agents (learned)' : 'agents (base read)', stop: p.stop, stopWho: p.limits?.sl && Math.abs(p.stop) >= p.limits.sl - 1e-9 ? 'you' : 'agents',
    hold: p.granted != null ? p.granted * 5 : p.limits?.maxHold || null, holdWho: p.limits?.maxHold && p.granted != null && p.granted * 5 >= p.limits.maxHold ? 'you' : 'agents', trail: p.limits?.trail || 'auto', decision: p.decision, rule: p.rule, pct: p.pct }));
}
export function CreatorLimits({ policy, mission, cfg, positions, isOwner = true, busy, save, o }) {
  const pol = policy || {}; const ctl = Object.fromEntries((pol.controls || []).map(c => [c.key, c])); const hard = pol.hard || {}; const [open, setOpen] = useState(null);
  const set = (k, v) => save && save({ cfg: { [k]: v } }); const c0 = cfg || {};
  const cur = k => (ctl[k] || {}).value;
  const row = c => { const mine = c.who === 'CREATOR OVERRIDE';
    return <li key={c.key} className={mine ? 'is-you' : 'is-agents'} data-testid={`oed-ctl-${c.key}`}>
      <span className="oed-ctl-h"><b>{c.label}</b><i className={`oed-who ${mine ? 'is-you' : 'is-agents'}`}>{mine ? '✋ YOUR OVERRIDE' : '🤖 AGENTS CHOOSE'}</i><button type="button" className="oed-info" aria-expanded={open === c.key} onClick={() => setOpen(open === c.key ? null : c.key)} data-tip={c.means} aria-label={`What ${c.label} means`}>?</button></span>
      <span className="m-seg" role="group" aria-label={c.label}>{c.options.map(v => <button key={String(v)} type="button" disabled={busy || !isOwner} className={String(c.value) === String(v) ? 'active' : ''} onClick={() => set(c.key, v)} data-testid={`oed-opt-${c.key}-${v}`}>{optLabel(c.key, v, c.unit)}</button>)}</span>
      {c.key === 'agentTrail' && c.value === 'custom' && TRAIL_SUB.map(([k, l, vs]) => <span key={k} className="m-seg oed-sub" role="group" aria-label={l}><small>{l}</small>{vs.map(v => <button key={v} type="button" disabled={busy || !isOwner} className={Number(cur(k) ?? pol.trail?.[k === 'agentTrailArm' ? 'arm' : 'pct']) === v ? 'active' : ''} onClick={() => set(k, v)} data-testid={`oed-opt-${k}-${v}`}>{v}{k === 'agentTrailArm' ? '%' : ' pts'}</button>)}</span>)}
      {c.key === 'agentTp' && !mine && <span className="m-seg oed-sub" role="group" aria-label="Base read line"><small>they read at</small>{((c0.options || {}).take || [5, 10, 20, 30, 50]).map(v => <button key={v} type="button" disabled={busy || !isOwner} className={Number(c0.agentTakePct) === v ? 'active' : ''} onClick={() => set('agentTakePct', v)} data-testid={`oed-opt-agentTakePct-${v}`}>+{v}%</button>)}</span>}
      <small className="oed-now">{mine ? `in force: ${optLabel(c.key, c.value, c.unit)} — yours` : c.agentsNow ? `now: ${c.agentsNow}` : 'now: not read yet'}</small>
      {open === c.key && <p className="oed-means m-pop">{c.means}</p>}</li>; };
  const seats = <li key="agentSeats" className="is-you" data-testid="oed-ctl-agentSeats"><span className="oed-ctl-h"><b>Seats they hold</b><i className="oed-who is-you">✋ YOURS</i></span>
    <span className="m-seg" role="group" aria-label="Seats">{((c0.options || {}).seats || [1, 2, 3, 4]).map(v => <button key={v} type="button" disabled={busy || !isOwner} className={Number(c0.agentSeats) === v ? 'active' : ''} onClick={() => set('agentSeats', v)} data-testid={`oed-opt-agentSeats-${v}`}>{v}</button>)}</span>
    <small className="oed-now">in force: {pol.seats ?? '—'} seat{pol.seats === 1 ? '' : 's'} (never more than the card's coins)</small></li>;
  const pp = positionPolicy(o || { policy: pol, positions });
  return <div className="oed-box oed-limits" data-testid="oed-limits">
    <header><b>🎛 YOUR LIMITS ON THE AGENTS · real Fuse card</b><span className="m-seg oed-auth" role="group" aria-label="Who decides">
      <button type="button" disabled={busy || !isOwner} className={!pol.manual ? 'active' : ''} onClick={() => set('agentAuthority', 'agents')} data-testid="oed-auth-agents">🤖 Agents decide inside my limits</button>
      <button type="button" disabled={busy || !isOwner} className={pol.manual ? 'active is-manual' : ''} onClick={() => set('agentAuthority', 'manual')} data-testid="oed-auth-manual">✋ Creator manual</button></span></header>
    <p className="oed-why">{pol.manual ? 'MANUAL: the agents make no discretionary move — no fill, no switch, no bank on a read. Only the hard safety exits and the limits YOU set below act.' : 'Blue = 🤖 the agents decide it from their own record and the chart. Gold = ✋ your number — a boundary they stay inside, never a target.'}</p>
    <div className="oed-groups">{LIMIT_GROUPS.map(([g, sub, keys]) => <section key={g} className="oed-group"><h4>{g}<small>{sub}</small></h4>
      <ul className="oed-ctl">{keys.map(k => (k === 'agentSeats' ? seats : ctl[k] ? row(ctl[k]) : null))}</ul></section>)}</div>
    <div className="oed-sub-box" data-testid="oed-inforce"><small>IN FORCE ON EACH OPEN POSITION · what Reaper obeys right now</small>
      {pp.length ? <table className="oed-cf is-wide"><thead><tr><th>coin</th><th>take</th><th>stop</th><th>hold</th><th>trail</th><th>now</th></tr></thead>
        <tbody>{pp.map(r => <tr key={r.symbol}><td><b>${r.symbol}</b> <span className={pctCls(r.pct)}>{sgn(r.pct)}</span></td><td>+{r.take}% <i className={`oed-by is-${r.takeWho === 'you' ? 'you' : 'agents'}`}>{r.takeWho}</i></td>
          <td>{r.stop}% <i className={`oed-by is-${r.stopWho === 'you' ? 'you' : 'agents'}`}>{r.stopWho}</i></td><td>{r.hold != null ? `${r.hold}m` : '—'} <i className={`oed-by is-${r.holdWho === 'you' ? 'you' : 'agents'}`}>{r.holdWho}</i></td>
          <td>{r.trail === 'custom' ? 'yours' : r.trail === 'off' ? 'off' : 'theirs'}</td><td data-tip={r.rule}>{r.decision}</td></tr>)}</tbody></table>
        : <span className="oed-nil">no open position — the next seat is filled under these limits</span>}</div>
    <p className="oed-hard" data-testid="oed-hard"><b>HARD LIMITS · no setting moves them</b><span>catastrophic stop −{hard.catastrophicStop ?? 45}%</span><span>≤ {hard.movesPerHour ?? 6} real buys / hour</span><span>pool ≥ ${Math.round((hard.minPool ?? 20000) / 1000)}K</span>
      <span>stage {mission?.stage ?? 5} min until real equity ≥ 2× put-in{mission?.doubleTarget != null ? ` ($${Number(mission.doubleTarget).toFixed(2)})` : ''}</span><span>{pol.seats ?? '—'} seats</span></p>
  </div>;
}

// 📝 THE REVIEW QUEUE — asynchronous: marks are display state, the office never reads them back and never waits
const MARK = [['agree', '👍 Right call'], ['disagree', '👎 Wrong call'], ['seen', '👁 Seen']];
const CF = [['firstCleared', 'at first clear'], ['firstPullback', 'first pullback'], ['confirmedBreakout', 'confirmed breakout']];
function CounterRow({ counter }) {
  const rows = CF.filter(([k]) => counter?.[k]);
  if (!rows.length) return <small className="oed-nil">no paper entry moment on file</small>;
  return <table className="oed-cf"><thead><tr><th>paper entry</th>{[5, 15, 60].map(h => <th key={h}>{h}m</th>)}</tr></thead>
    <tbody>{rows.map(([k, l]) => <tr key={k}><td>{l}</td>{[5, 15, 60].map(h => { const v = counter[k][`p${h}`]; return <td key={h} className={pctCls(v)}>{v == null ? '—' : sgn(v)}</td>; })}</tr>)}</tbody></table>;
}
export function ReviewItem({ it, cat, isOwner, save, onCoin }) {
  const [note, setNote] = useState(it.mark?.note || ''); const k = it.knew || {};
  const mark = m => save && save({ review: { key: it.key, mark: m, note } });
  return <li className={`oed-item ${it.mark ? `is-${it.mark.mark}` : ''}`} data-testid={`oed-item-${it.key}`}>
    <span className="oed-ih">{it.sym ? <button type="button" className="oed-sym" onClick={() => onCoin && onCoin(it)}>${it.sym}</button> : <b className="oed-sym">{it.launch || it.rule || '—'}</b>}
      {it.launch && it.sym && tag('', it.launch, 'launch context of the decision')}{it.move != null && <em className={pctCls(it.move)}>{cat === 'missed' ? `peak ${sgn(it.move, 0)}` : sgn(it.move)}</em>}<u>{it.at ? ago(it.at) : ''}</u>
      {it.reason && tag(it.correct === true ? 'is-ok' : it.correct === false ? 'is-no' : 'is-wait', it.reason, it.correct === true ? 'The block was right from a risk view — it stays.' : it.correct === false ? 'A block to re-examine on its own record.' : 'An opportunity cost, not proof a rule is wrong.')}</span>
    <p className="oed-what">{it.what}</p>
    <p className="oed-knew">{it.agent && <b>{it.agent}</b>}{it.rule && <code>{String(it.rule)}</code>}{k.lean != null && <span>lean {sgn(k.lean, 1, '')}</span>}{k.structure && <span>{k.structure}</span>}{k.entry && <span>{k.entry}</span>}{k.data && <span>data {String(k.data).replace(/_/g, ' ').toLowerCase()}</span>}
      {(k.drivers || []).length > 0 && <span>{k.drivers.slice(0, 3).join(' · ')}</span>}{k.n != null && <span>n {k.n}</span>}{it.n != null && <span>{it.n} records</span>}</p>
    {cat === 'missed' && <CounterRow counter={it.counter} />}
    <p className="oed-lesson">→ {it.lesson}</p>
    <span className="oed-mark"><span className="m-seg" role="group" aria-label="Your mark">{MARK.map(([m, l]) => <button key={m} type="button" disabled={!isOwner} className={it.mark?.mark === m ? 'active' : ''} onClick={() => mark(m)} data-testid={`oed-mark-${m}-${it.key}`}>{l}</button>)}</span>
      <input className="m-input oed-note" value={note} maxLength={280} onChange={ev => setNote(ev.target.value)} onKeyDown={ev => { if (ev.key === 'Enter' && it.mark) mark(it.mark.mark); }} placeholder="note (optional)" aria-label="Your note" disabled={!isOwner} />
      {it.mark && <button type="button" className="m-btn oed-clear" disabled={!isOwner} onClick={() => mark('clear')}>✕</button>}</span>
  </li>;
}
export function ReviewQueue({ review, isOwner = true, save, onCoin }) {
  const rv = review || {}; const order = rv.order || []; const [cat, setCat] = useState(() => order.find(k => (rv.open || {})[k]) || order[0] || 'missed');
  const items = (rv.items || {})[cat] || [];
  return <div className="oed-box oed-review" data-testid="oed-review">
    <header><b>📝 REVIEW QUEUE</b>{tag('is-ok', 'NON-BLOCKING', 'The agents keep working while items wait — nothing reads your marks back.')}<em>{Object.values(rv.open || {}).reduce((a, b) => a + b, 0)} waiting · {Object.values(rv.counts || {}).reduce((a, b) => a + b, 0)} on file</em></header>
    <p className="oed-why">{rv.note || 'Review is asynchronous.'}</p>
    <div className="m-seg oed-cats" role="tablist" aria-label="Review category">{order.map(k => <button key={k} type="button" role="tab" aria-selected={cat === k} className={cat === k ? 'active' : ''} onClick={() => setCat(k)} data-testid={`oed-cat-${k}`}>{(rv.labels || {})[k] || k}<small>{(rv.open || {})[k] ?? 0}</small></button>)}</div>
    {items.length ? <ul className="oed-items">{items.map(it => <ReviewItem key={it.key} it={it} cat={cat} isOwner={isOwner} save={save} onCoin={onCoin} />)}</ul> : <span className="oed-nil" data-testid="oed-review-empty">nothing in this category on the records of the last 6h</span>}
  </div>;
}

// 🔎 THE WINNERS WE MISSED — paper study only: why each was not held, which desk, whether the block was still right
const Bars = ({ rows, total, label }) => <div className="oed-sub-box"><small>{label}</small>{(rows || []).length ? <ul className="oed-bars">{rows.map(r => <li key={r.key}><span>{r.key}</span><span className="oed-bar"><i style={{ transform: `scaleX(${r.n / (total || 1)})` }} /></span><em>{r.n}</em><u>{r.medPeak != null ? `peak ${sgn(r.medPeak, 0)}` : ''}</u></li>)}</ul> : <span className="oed-nil">none</span>}</div>;
export function MissedWinners({ review, onCoin }) {
  const ms = review?.missedSummary || {}; const items = review?.items?.missed || []; const cf = ms.counter || {};
  return <div className="oed-box oed-missed" data-testid="oed-missed">
    <header><b>🔎 WINNERS WE MISSED · last {ms.hours ?? 6}h · peaked ≥ +{ms.winnerPct ?? 50}%</b>{tag('', 'PAPER ONLY', 'A study of what happened — it never trades and never loosens a rule.')}</header>
    <div className="oed-tiles is-big">
      <span><small>missed</small><b>{ms.n ?? 0}</b><u>{ms.seen ?? 0} seen · {ms.never ?? 0} never found</u></span>
      <span><small>typical peak</small><b className="oed-up">{ms.medPeak != null ? sgn(ms.medPeak, 0) : '—'}</b><u>of the coins we missed</u></span>
      <span><small>head start</small><b>{ms.medLeadMin != null ? `${ms.medLeadMin}m` : '—'}</b><u>seen before +{ms.winnerPct ?? 50}%</u></span>
      <span data-tip="Blocks that kept the card out of an unsafe coin stay right even when the coin pumped."><small>correct skips</small><b className="oed-up">{ms.correct ?? 0}</b><u>{ms.falseBlock ?? 0} blocks to re-examine</u></span></div>
    <div className="oed-split"><Bars rows={ms.byReason} total={ms.n} label="WHY" /><Bars rows={ms.byAgent} total={ms.n} label="WHICH DESK" /><Bars rows={ms.byRule} total={ms.n} label="WHICH RULE" /></div>
    <div className="oed-sub-box"><small>PAPER COUNTERFACTUALS · typical result of entries we could have made</small>
      <table className="oed-cf is-wide"><thead><tr><th>entry</th><th>n</th>{[5, 10, 15, 30, 60].map(h => <th key={h}>{h}m</th>)}</tr></thead>
        <tbody>{CF.map(([k, l]) => { const r = cf[k] || {}; return <tr key={k}><td>{l}</td><td>{r.n ?? 0}</td>{[5, 10, 15, 30, 60].map(h => <td key={h} className={pctCls(r[`p${h}`])}>{r[`p${h}`] == null ? '—' : sgn(r[`p${h}`])}</td>)}</tr>; })}</tbody></table></div>
    {items.length ? <ul className="oed-items is-missed">{items.map(it => <li key={it.key} className="oed-item"><span className="oed-ih"><button type="button" className="oed-sym" onClick={() => onCoin && onCoin(it)}>${it.sym}</button>{it.launch && tag('', it.launch)}<em className="oed-up">peak {sgn(it.move, 0)}</em><u>{ago(it.at)}</u>
      {tag(it.correct === true ? 'is-ok' : it.correct === false ? 'is-no' : 'is-wait', it.reason)}{it.agent && <b>{it.agent}</b>}{it.rule && <code>{String(it.rule)}</code>}</span><p className="oed-what">{it.what}</p><CounterRow counter={it.counter} /></li>)}</ul>
      : <span className="oed-nil">no winner missed in the window — or none settled yet (the brain judges each coin an hour after it is watched)</span>}
    <p className="oed-why">{ms.note}</p>
  </div>;
}

// 🚀 LAUNCH CONTEXT — each measurable launch mechanism on its own record (our judged calls), unknown stays unknown
export function LaunchRecord({ launch }) {
  const rec = Object.entries(launch?.record || {}).sort((a, b) => b[1].n - a[1].n); const max = Math.max(5, ...rec.map(([, v]) => Math.abs(v.med5 || 0)));
  return <div className="oed-box oed-launch" data-testid="oed-launch">
    <header><b>🚀 LAUNCH CONTEXT · each one on its own record</b><em>{Object.values(launch?.pads || {}).join(' · ') || '—'} identified · everything else UNKNOWN</em></header>
    {rec.length ? <table className="oed-cf is-wide"><thead><tr><th>pad · type</th><th>calls</th><th>5m typical</th><th /><th>15m</th><th>up</th><th>ENTER</th></tr></thead>
      <tbody>{rec.map(([k, v]) => <tr key={k} className={v.known ? '' : 'is-thin'}><td>{k.replace(':', ' · ')}</td><td>{v.n}</td><td className={pctCls(v.med5)}>{sgn(v.med5)}</td>
        <td><span className="oed-bar is-mid"><i className={v.med5 < 0 ? 'is-short' : ''} style={{ transform: `scaleX(${Math.min(1, Math.abs(v.med5 || 0) / max)})` }} /></span></td>
        <td className={pctCls(v.med15)}>{v.med15 == null ? '—' : sgn(v.med15)}</td><td>{v.won}%</td><td>{v.enterN ? `${v.enterN} · ${sgn(v.enterMed5)}` : '—'}</td></tr>)}</tbody></table>
      : <span className="oed-nil">no judged call carries its launch context yet — calls store it from this version on</span>}
    <p className="oed-why">{launch?.source} · fewer than 5 calls = “too few”, never a verdict · the paper Devil refuses a context only on ≥ 15 of our own ENTER calls with a typical 5-min result ≤ −3%.</p>
  </div>;
}
