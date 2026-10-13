import React, { useState } from 'react';
import { useLivePrices } from '../../lib/livePrices';
import { freshness, useOffice } from '../../lib/agentHub';
import { devilOf } from '../../lib/agentRead';
import { sgn } from './OfficeBoard';
import '../../styles/seatOps.css';

// 🪑 THE FOUR-SEAT OPERATING MODEL on the Agents tab (`backend/seat_ops.py` → the one office payload: seatBoard · bench · seatSummary ·
// cycleLog · fresh · social). Every number is a field the office already decided with — this file draws, it never decides.

const secs = (now, at) => (at ? `${Math.max(0, Math.round(now - at))}s` : '—');
const pct = v => (v == null ? '—' : sgn(v));
const short = (s, n = 64) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s || '');

// ── ⏱ THE ROUND BAR: the desk's 5-minute clock + everything the spec asks to see at a glance (one payload, nothing fetched) ──────────
const AGE_BANDS = ['0–5m', '5–15m', '15–60m', '1–3h', '3–6h'];
const mmss = s => (s == null ? '—' : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`);
// ⏱ ROUND HISTORY (Archivist): each finished candidate — round 1 read · round 2 read · round 3 decision — so patience is judged, not assumed
const DEC_CLS = { ENTER: 'is-ok', REJECT: 'is-bad', COOLDOWN: 'is-wait' };
// ⚙ THE KERNEL: four hunter lanes (HUNTING · ARMED · HELD) + the candidates the ten-agent brain ranks — one row each: rank · trigger ·
// Devil's WORST severity · Warden's size · Courier · Reaper · and how old the MARKET data vs the last DECISION vs the evidence are.
const LANE_CLS = { HELD: 'is-ok', ARMED: 'is-ready', HUNTING: 'is-wait' };
const DEVIL_CLS = { veto: 'is-bad', warn: 'is-warn', clear: '' };
const SCAN_WORD = { FRESH: 'fresh', STALE: 'stale', PENDING: 'pending', RATE_LIMITED: 'rate-limited', UNAVAILABLE: 'unavailable' };   // the EVIDENCE state of the holder scan — never a verdict on the coin
export function KernelBoard({ o: o0, onCoin }) {
  const o = useOffice(o0); const k = o?.kernel; const cands = (k?.candidates || []).slice(0, 8);
  const px = useLivePrices(cands.map(c => c.pair).filter(Boolean));
  if (!k) return null;
  const age = v => (v == null ? '—' : v < 60 ? `${Math.round(v)}s` : `${Math.round(v / 60)}m`);
  return <div className="sop-kernel" data-testid="kernel-board">
    <div className="sop-sum">{(k.lanes || []).map(l => <span key={l.lane} className={`sop-chip ${LANE_CLS[l.state] || ''}`} data-testid={`hunter-${l.lane}`} data-tip={l.state === 'HUNTING' ? 'searching — the best contender so far is shown' : l.state === 'ARMED' ? 'a READY coin is lined up for this lane' : 'capital deployed'}>
      <small>HUNTER {l.lane}</small><b>{l.state}{l.symbol ? ` · $${l.symbol}` : ''}</b></span>)}</div>
    <ul className="sop-board">{cands.map(c => { const dv = devilOf(c); const f = freshness(c, px.get(c.pair));
      return <li key={c.mint} data-testid={`kc-${c.symbol}`}>
        <span className="sop-k"><button type="button" className="sop-coin" onClick={() => onCoin && onCoin(c.symbol, c.mint)}>${c.symbol}</button></span>
        <span className="sop-v"><i className={`sop-tag ${c.status === 'READY' || c.status === 'HELD' ? 'is-ok' : 'is-wait'}`}>{c.status}</i> rank {Math.round(c.rank)} · {c.narrative?.toLowerCase()} · trigger {c.trigger}
          {dv.verdict !== 'clear' ? <i className={`sop-tag ${DEVIL_CLS[dv.verdict]}`} data-testid={`kc-devil-${c.symbol}`} data-tip={dv.objections.map(x => `${String(x.severity).replace(/_/g, ' ').toLowerCase()}: ${x.evidence}`).join(' · ')}>{dv.word}</i> : null}
          <u> size ×{c.size}</u>{c.courier ? null : <i className="sop-tag is-bad">EXECUTION BLOCKED</i>}{c.reaper ? <u> · reaper {c.reaper.action}</u> : null}</span>
        <span className="sop-full" data-testid={`kc-fresh-${c.symbol}`}>market {age(f.market)} ago · decision {age(f.decision)} ago · research {age(f.research)} · holders {age(f.holders)}{f.scan ? ` (scan ${SCAN_WORD[f.scan] || f.scan})` : ''}{c.unknown?.length ? ` · researching: ${c.unknown.join(', ')}` : ''}</span></li>; })}</ul>
  </div>;
}

// ── 🆕 THE FRESH-TRENCH PIPELINE: is the attention (and the buying) on 0–12h coins? ─────────────────────────────────────────────────
const hm = m => (m == null ? '—' : m < 90 ? `${Math.round(m)}m` : m < 2880 ? `${(m / 60).toFixed(1)}h` : `${Math.round(m / 1440)}d`);
export const FRESH_BUCKETS = ['0–5m', '5–15m', '15–60m', '1–3h', '3–6h', '6h+'];
export function FreshBlock({ f }) {
  if (!f) return null;
  const al = f.candles?.allocFirst || {}; const ab = f.candles?.allocBefore || {};
  return <div className="sop-fresh" data-testid="sop-fresh"><small>🆕 FRESH TRENCH · where the agents' attention went this cycle</small>
    <table className="sop-log"><thead><tr><th>age</th>{FRESH_BUCKETS.map(b => <th key={b}>{b}</th>)}</tr></thead><tbody>
      {[['on the desk', f.buckets], ['deep reviewed', f.deep], ['cleared', f.cleared]].map(([k, v]) => <tr key={k}><td>{k}</td>{FRESH_BUCKETS.map(b => <td key={b} className={b === '6h+' ? 'is-old' : ''}>{v?.[b] ?? 0}</td>)}</tr>)}</tbody></table>
    <div className="sop-ages">
      <span data-tip="coins on the desk this cycle · how many were already on it last cycle · how many are new · rejects cooled until something changes"><small>UNIQUE · REPEAT · NEW · COOLED</small><b>{f.unique} · {f.repeats} · {f.newUnique} · {f.cooled}</b></span>
      <span><small>MEDIAN AGE REVIEWED</small><b>{hm(f.ageReviewedMin)}</b></span>
      <span><small>MEDIAN AGE CLEARED · HELD</small><b>{hm(f.ageClearedMin)} · {hm(f.ageHeldMin)}</b></span>
      <span data-tip={`median launch age at ENTRY of the agents' real buys — last 24h (${f.bought24h} buys) vs before`}><small>AGE AT ENTRY · 24H vs BEFORE</small><b>{hm(f.boughtAgeMin24h)} vs {hm(f.boughtAgeMinBefore)}</b></span>
      <span data-tip="the first 24 coins asked for real candles (the candles service builds new histories in request order) — now vs the old order"><small>CANDLES FIRST 24 · fresh / old / held</small><b>{al.fresh ?? 0} / {al.old ?? 0} / {al.held ?? 0}</b><u>old order {ab.fresh ?? 0} / {ab.old ?? 0} / {ab.held ?? 0}</u></span>
    </div>
    {f.top?.length ? <table className="sop-log" data-testid="sop-fresh-top"><thead><tr><th>top 5</th><th>age</th><th>MC</th><th>source</th><th>$/min</th><th>buys/min</th><th>tier</th></tr></thead>
      <tbody>{f.top.map(t => <tr key={t.symbol}><td>${t.symbol}</td><td>{hm(t.ageMin)}</td><td>{t.mc ? `$${Math.round(t.mc / 1000)}K` : '—'}</td><td>{(t.src || []).join(' · ') || 'board'}</td><td>{t.vpm ?? '—'}</td><td>{t.bpm ?? '—'}</td><td>{t.tier} {t.score != null ? Math.round(t.score) : ''}</td></tr>)}</tbody></table>
      : <p className="sop-note">no coin ranked A / B / C this cycle — the seats wait in cash rather than take a reject</p>}
  </div>;
}

// ── 📡 RPC LANES: provider + in / out of quota (never a URL) ─────────────────────────────────────────────────────────────────────
export function RpcLanes({ r }) {
  if (!r?.lanes?.length) return null;
  return <div className="sop-ages" data-testid="sop-rpc" data-tip={r.note}><span><small>📡 RPC LANES</small><b>{r.lanes.length}</b></span>
    {r.lanes.map(l => <span key={l.lane} className={l.spent ? 'is-bad' : 'is-ok'}><small>LANE {l.lane}</small><b>{l.provider}</b><u>{l.spent ? `out of quota · back in ${l.backInMin}m` : 'answering'}</u></span>)}</div>;
}

// ── 🗂 THE ONE ACTIVE CANDIDATE INDEX: every desk reads this pass's row; eligibility recomputed every pass ─────────────────────────
export function ActiveIndex({ rows }) {
  const [all, setAll] = React.useState(false);
  if (!rows?.length) return null;
  const shown = all ? rows : rows.slice(0, 12);
  return <div className="sop-logwrap" data-testid="sop-index"><table className="sop-log"><thead><tr><th>🗂 active index ({rows.filter(r => r.eligible).length} eligible / {rows.length})</th><th>age</th><th>MC</th><th>$/min</th><th>buys/min</th><th>holders</th><th>chart</th><th>phase</th><th>sources</th><th>cooldown</th><th>status</th></tr></thead>
    <tbody>{shown.map(r => <tr key={r.mint} className={r.eligible ? '' : 'is-old'}><td>${r.symbol}</td><td>{hm(r.launchAgeMin)}</td><td>{r.liveMC ? `$${Math.round(r.liveMC / 1000)}K` : '—'}</td><td>{r.volVelocity ?? '—'}</td><td>{r.buyerVelocity ?? '—'}</td>
      <td>{r.holderStatus}</td><td>{r.realCandles ? r.chartQuality || 'candles' : 'tape'}</td><td>{r.marketPhase || '—'}</td><td>{(r.sources || []).slice(0, 3).join(' · ') || 'board'}</td><td>{r.cooldownLeft ? secTxt(r.cooldownLeft) : '—'}</td><td>{r.eligible ? 'eligible' : r.why}</td></tr>)}</tbody></table>
    {rows.length > 12 ? <button type="button" className="m-btn" onClick={() => setAll(a => !a)} data-testid="sop-index-all">{all ? 'Show 12' : `Show all ${rows.length}`}</button> : null}</div>;
}

// ── 🕸 THE ONE LIVE INTAKE: this cycle's turnover, the latencies, every outlet's funnel ────────────────────────────────────────────
const secTxt = v => (v == null ? '—' : v >= 120 ? `${Math.round(v / 60)}m` : `${Math.round(v)}s`);
const safeUrl = u => (typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null);
