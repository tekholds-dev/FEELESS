import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { openCoin } from '../CoinDrawer';
import { openWarRoom } from '../WarRoomHost';
import { pct, tone, VERD, rowState, rowWhy, pipsOf, leanFill } from '../../lib/agentRead';
import '../../styles/agentScreens.css';

// 🖥 THE AGENTS' SCREENS (owner, 2026-10-10: "degen complex but simple — click to zoom to see their screens, click through lists, not so
// much reading, more meta visuals, realtime data"). Each agent has ONE screen that IS its work this pass, drawn — not written:
//   📊 Tally  = HEAT WALL: every coin it read as a tile, green / pink by its 5-min move, brighter = bigger
//   🔍 Sherlock = REASON BARS: the reasons it weighed, longest = most coins; tap a reason → only the coins that carry it
//   ⏱ Trigger = SCOPE: every coin as a dot (→ 5-min move, ↑ Sherlock's lean), the line is its bar — dots above it are ENTER
//   ⚖ Devil  = DOCKET: every ENTER as a stamped ticket (✓ agrees · ✕ objects) with the coin's rug meter
// A mini screen sits on each agent's card; a tap ZOOMS it (portal, Esc / outside closes, tabs switch agent). In the zoom every mark is a
// coin: tap it, or step with ‹ › / ← →, and its DOSSIER (meters, the four pips, the one fact that decided it) follows.
// Also here: 🎮 CardNow (the creator's real card as seats — who holds each, what the agents are doing with theirs), 🧬 GrowthCards
// (level · XP · earned-vs-born brain · genes · scars · skills) and 🪜 PowerLadder (how many real seats the team has earned).
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const num = v => (Number.isFinite(Number(v)) ? Number(v) : 0);
export const heat = v => clamp(Math.abs(num(v)) / 10, 0.12, 1);
// reasons this pass: how many coins carry each, their average weight, and which coins
export const reasonsOf = table => { const m = {};
  (table || []).forEach(x => (x.why?.drivers || []).forEach(dd => { const r = (m[dd[0]] = m[dd[0]] || { key: dd[0], words: dd[2], n: 0, w: 0, mints: [] }); r.n += 1; r.w += num(dd[1]); r.mints.push(x.mint); }));
  return Object.values(m).map(r => ({ ...r, w: r.w / r.n })).sort((a, b) => b.n - a.n); };
// the scope: x = 5-min move (−10 … +20), y = lean (−bar … +3 bars) → 0 … 1; the bar sits at 0.5
export const scopeOf = (table, bar) => { const b = Math.max(0.5, num(bar) || 1.5);
  return (table || []).map(x => ({ mint: x.mint, sym: x.symbol, call: x.trigger?.[0] || 'wait', go: !!x.go,
    x: clamp((num(x.nums?.d5) + 10) / 30, 0.02, 0.98), y: clamp((num(x.why?.lean) + b) / (4 * b), 0.03, 0.97) })); };
export const docketOf = table => (table || []).filter(x => x.trigger?.[0] === 'enter').map(x => ({ mint: x.mint, sym: x.symbol, ok: x.devil?.[0] === 'agree', go: !!x.go, why: x.devil?.[1] || '', rug: x.vitals?.rug }));
// the order ‹ › walks for each screen
export const listFor = (agent, table, reason) => { const t = table || [];
  if (agent === 'devil') { const e = t.filter(x => x.trigger?.[0] === 'enter'); return (e.length ? e : t).map(x => x.mint); }
  if (agent === 'trigger') return [...t].sort((a, b) => num(b.why?.lean) - num(a.why?.lean)).map(x => x.mint);
  if (agent === 'sherlock' && reason) return t.filter(x => (x.why?.drivers || []).some(dd => dd[0] === reason)).map(x => x.mint);
  return t.map(x => x.mint); };
const NAMES = { tally: ['📊', 'Tally', 'HEAT WALL'], sherlock: ['🔍', 'Sherlock', 'REASONS'], trigger: ['⏱', 'Trigger', 'SCOPE'], devil: ['⚖', 'Devil', 'DOCKET'] };

// ── the four screens (mini = on the card, no labels · big = in the zoom, every mark tappable) ──
function Heat({ t, big, cur, pick }) {
  return <div className={`ags-heat ${big ? 'is-big' : ''}`}>{t.slice(0, big ? 48 : 24).map(x => { const v = num(x.nums?.d5); const st = { '--h': heat(v) };
    return big ? <button type="button" key={x.mint} className={`ags-tile ${v >= 0 ? 'is-up' : 'is-dn'} ${cur === x.mint ? 'is-cur' : ''}`} style={st} onClick={() => pick(x.mint)} data-testid={`tile-${x.symbol}`}><b>${x.symbol}</b><em>{pct(x.nums?.d5)}</em></button>
      : <i key={x.mint} className={`ags-tile ${v >= 0 ? 'is-up' : 'is-dn'}`} style={st} />; })}</div>;
}
function Reasons({ t, big, reason, setReason }) {
  const rs = reasonsOf(t).slice(0, big ? 12 : 5); const top = Math.max(1, ...rs.map(r => r.n));
  if (!rs.length) return <div className="ags-empty">no reasons this pass</div>;
  return <div className={`ags-reasons ${big ? 'is-big' : ''}`}>{rs.map(r => big
    ? <button type="button" key={r.key} className={`ags-reason ${r.w >= 0 ? 'is-up' : 'is-dn'} ${reason === r.key ? 'is-cur' : ''}`} onClick={() => setReason(reason === r.key ? null : r.key)} data-testid={`reason-${r.key}`}>
      <span>{r.words}</span><u><i style={{ transform: `scaleX(${r.n / top})` }} /></u><em>×{r.n}</em></button>
    : <u key={r.key} className={r.w >= 0 ? 'is-up' : 'is-dn'}><i style={{ transform: `scaleX(${r.n / top})` }} /></u>)}</div>;
}
function Scope({ t, bar, big, cur, pick }) {
  const dots = scopeOf(t, bar);
  return <div className={`ags-scope ${big ? 'is-big' : ''}`}><span className="ags-bar" data-tip={big ? `Trigger's bar ${num(bar || 1.5).toFixed(1)} — above it is an ENTER` : undefined}>{big && <small>BAR {num(bar || 1.5).toFixed(1)}</small>}</span><span className="ags-zero" />
    {big && <><small className="ags-ax is-x">5-min move →</small><small className="ags-ax is-y">lean ↑</small></>}
    {dots.map(p => { const st = { left: `${p.x * 100}%`, bottom: `${p.y * 100}%` }; const cls = `ags-dot is-${p.go ? 'go' : p.call} ${cur === p.mint ? 'is-cur' : ''}`;
      return big ? <button type="button" key={p.mint} className={cls} style={st} onClick={() => pick(p.mint)} data-tip={`$${p.sym}`} aria-label={`$${p.sym}`} data-testid={`dot-${p.sym}`} /> : <i key={p.mint} className={cls} style={st} />; })}</div>;
}
function Docket({ t, big, cur, pick }) {
  const ds = docketOf(t);
  if (!ds.length) return <div className="ags-empty">{big ? 'Trigger sent no ENTER this pass — nothing to argue' : 'nothing to argue'}</div>;
  return <div className={`ags-docket ${big ? 'is-big' : ''}`}>{ds.slice(0, big ? 16 : 8).map(x => big
    ? <button type="button" key={x.mint} className={`ags-ticket ${x.ok ? 'is-ok' : 'is-no'} ${cur === x.mint ? 'is-cur' : ''}`} onClick={() => pick(x.mint)} data-testid={`ticket-${x.sym}`}>
      <b className="ags-stamp">{x.ok ? (x.go ? 'GO' : '✓') : '✕'}</b><span>${x.sym}</span>{x.rug != null && <u data-tip={`rug meter ${Math.round(x.rug)}`}><i style={{ transform: `scaleX(${clamp(x.rug / 100, 0.03, 1)})` }} /></u>}</button>
    : <i key={x.mint} className={`ags-stamp ${x.ok ? 'is-ok' : 'is-no'}`}>{x.ok ? '✓' : '✕'}</i>)}</div>;
}
const stat = (k, d) => { const t = d?.table || []; const e = t.filter(x => x.trigger?.[0] === 'enter');
  return k === 'tally' ? [d?.perf?.coins ?? t.length, 'read'] : k === 'sherlock' ? [reasonsOf(t).length, 'reasons'] : k === 'trigger' ? [e.length, 'ENTER'] : [`${e.filter(x => x.devil?.[0] === 'object').length}/${e.length}`, 'objected']; };
export function MiniScreen({ k, d }) {
  const t = d?.table || []; const [n, l] = stat(k, d);
  return <span className={`ags-screen is-${k}`}><span className="ags-face" aria-hidden>
    {k === 'tally' ? <Heat t={t} /> : k === 'sherlock' ? <Reasons t={t} /> : k === 'trigger' ? <Scope t={t} bar={d?.bar} /> : <Docket t={t} />}<span className="ags-sweep" /></span>
    <span className="ags-stat"><b>{n}</b>{l}</span></span>;
}

// ── a coin's dossier: meters, not sentences ──
const Meter = ({ label, val, fill, cls = '', mark, split }) => <div className={`ags-meter ${cls}`}><small>{label}</small>
  <u className={split ? 'is-split' : ''}><i style={{ transform: `scaleX(${clamp(fill, 0, 1)})` }} />{mark != null && <s style={{ left: `${clamp(mark, 0, 1) * 100}%` }} />}</u><em>{val}</em></div>;
export function Dossier({ x, bar, idx, n, step }) {
  if (!x) return <div className="ags-dossier"><div className="ags-empty">tap a coin on the screen</div></div>;
  const st = rowState(x); const v = x.vitals || {}; const d5 = x.nums?.d5; const lean = num(x.why?.lean);
  return <div className="ags-dossier" data-testid="ags-dossier">
    <div className="ags-dtop"><button type="button" className="ags-step" onClick={() => step(-1)} aria-label="Previous coin" data-testid="ags-prev">‹</button>
      <span className="ags-dsym"><b>${x.symbol}</b><small>{idx + 1} / {n}</small></span>
      <button type="button" className="ags-step" onClick={() => step(1)} aria-label="Next coin" data-testid="ags-next">›</button></div>
    <div className="ags-dhead"><em className={`ags-d5 ${tone(d5)}`} key={String(d5)}>{pct(d5)}<small>5 MIN</small></em><span className={`agd-verdict is-${st}`}>{VERD[st]}</span></div>
    <div className="ags-chain">{pipsOf(x).map(([k, ic, s, tip], i) => <React.Fragment key={k}>{i > 0 && <span className={`ags-link is-${s === 'idle' ? 'idle' : 'on'}`} />}<i className={`is-${s} is-${k}`} data-tip={tip}>{ic}</i></React.Fragment>)}</div>
    <p className="ags-fact">{rowWhy(x)}</p>
    <div className="ags-meters">
      <Meter label="LEAN" val={lean.toFixed(1)} fill={leanFill(lean, bar)} mark={0.5} cls={lean >= 0 ? 'is-up' : 'is-dn'} />
      {x.nums?.pace != null && <Meter label="PACE" val={`${x.nums.pace}×`} fill={num(x.nums.pace) / 4} cls="is-up" />}
      {x.nums?.buy != null && <Meter label="BUYERS" val={`${Math.round(x.nums.buy)}%`} fill={num(x.nums.buy) / 100} split cls={x.nums.buy >= 50 ? 'is-up' : 'is-dn'} />}
      {v.top10 != null && <Meter label="TOP-10" val={`${Math.round(v.top10)}%`} fill={num(v.top10) / 60} cls={v.top10 >= 35 ? 'is-dn' : 'is-up'} />}
      {v.rug != null && <Meter label="RUG" val={Math.round(v.rug)} fill={num(v.rug) / 100} cls={v.rug >= 50 ? 'is-dn' : 'is-up'} />}
      {v.organic != null && <Meter label="ORGANIC" val={`${Math.round(v.organic)}%`} fill={num(v.organic) / 40} cls={v.organic < 5 ? 'is-dn' : 'is-up'} />}
    </div>
    <div className="ags-dacts"><button type="button" className="m-btn m-go" onClick={() => openCoin({ mint: x.mint, pairAddress: x.pair, symbol: x.symbol })} data-testid="ags-coin">🪙 Coin</button>
      {x.pair && <button type="button" className="m-btn" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: x.pair, baseToken: { address: x.mint, symbol: x.symbol } })}>📈 Chart</button>}</div>
  </div>;
}

export function ZoomScreen({ d, agent, setAgent, close }) {
  const t = useMemo(() => d?.table || [], [d]); const [cur, setCur] = useState(null); const [reason, setReason] = useState(null);
  const list = useMemo(() => listFor(agent, t, reason), [agent, t, reason]);
  const at = list.includes(cur) ? cur : list[0]; const idx = Math.max(0, list.indexOf(at)); const x = t.find(r => r.mint === at);
  useEffect(() => { const k = e => { if (e.key === 'Escape') close(); else if (e.key === 'ArrowRight' && list.length) setCur(list[(idx + 1) % list.length]); else if (e.key === 'ArrowLeft' && list.length) setCur(list[(idx - 1 + list.length) % list.length]); };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [close, list, idx]);
  const step = n => list.length && setCur(list[(idx + n + list.length) % list.length]); const [n, l] = stat(agent, d);
  return createPortal(<div className="ags-shade" onClick={e => e.target === e.currentTarget && close()} role="dialog" aria-label={`${NAMES[agent][1]}'s screen`} data-testid="ags-zoom">
    <div className={`ags-zoom is-${agent}`}>
      <div className="ags-ztop"><div className="m-seg" role="tablist" aria-label="Whose screen">{Object.entries(NAMES).map(([k, [ic, name]]) => <button key={k} type="button" role="tab" aria-selected={agent === k} className={agent === k ? 'active' : ''} onClick={() => { setAgent(k); setReason(null); }} data-testid={`zoom-${k}`}>{ic} {name}</button>)}</div>
        <span className="ags-ztitle"><b>{NAMES[agent][2]}</b><em>{n}</em> {l}{d?.tasks?.[agent] ? <small data-tip={d.tasks[agent]}>ⓘ</small> : null}</span>
        <button type="button" className="ags-x" onClick={close} aria-label="Close" data-testid="ags-close">✕</button></div>
      <div className="ags-zbody"><div className="ags-big" key={agent}>
        {agent === 'tally' ? <Heat t={t} big cur={at} pick={setCur} /> : agent === 'sherlock' ? <><Reasons t={t} big reason={reason} setReason={setReason} />
          <div className="ags-chips">{list.map(m => { const r = t.find(q => q.mint === m); return r ? <button type="button" key={m} className={`ags-chip is-${rowState(r)} ${at === m ? 'is-cur' : ''}`} onClick={() => setCur(m)} data-testid={`chip-${r.symbol}`}>${r.symbol}</button> : null; })}</div></>
          : agent === 'trigger' ? <Scope t={t} bar={d?.bar} big cur={at} pick={setCur} /> : <Docket t={t} big cur={at} pick={setCur} />}</div>
        <Dossier x={x} bar={d?.bar} idx={idx} n={list.length} step={step} /></div>
    </div></div>, document.body);
}

// 🎮 ON YOUR CARD NOW — the real card as seats; an agent seat shows how far it is to their take line and what they are doing with it
const KIND = { agent: ['🤖', 'agents'], suggested: ['🤝', 'their pick, your tap'], yours: ['👤', 'yours'], engine: ['⚙', 'engine'], open: ['▫', 'open'] };
const ACT = { hold: '⏳', pull: '💰', swap: '⇄' };
export function CardNow({ card, power, cfg, onMore }) {
  const seats = card?.seats || []; const pw = power || {}; const on = cfg?.agentLearn || cfg?.agentFeed;
  if (!seats.length) return <div className="ags-card is-off" data-testid="ags-card"><b>🎮 ON YOUR CARD</b><small>{on ? 'waiting for the card’s next tick' : 'no real card is funded — the agents trade paper only'}</small></div>;
  return <div className="ags-card" data-testid="ags-card"><span className="ags-cardh"><b>🎮 ON YOUR CARD NOW</b>
    <button type="button" className="ags-pow" onClick={onMore} data-tip="Seats the agents may hold right now — earned, see ⚙ Control / 🧬 Growth" data-testid="ags-pow">🤖 {pw.held ?? 0} / {pw.seats ?? 0} seats</button></span>
    <div className="ags-seats">{seats.map((s, i) => { const k = KIND[s.kind] || KIND.engine; const prog = s.kind === 'agent' && s.pct != null && s.take ? clamp(s.pct / s.take, 0, 1) : null;
      return s.kind === 'open' ? <span key={`o${i}`} className="ags-seat is-open" data-tip={pw.seats > (pw.held || 0) ? 'Open — the agents may take it with their next GO' : 'Open seat'}><i>▫</i><b>open</b></span>
        : <button type="button" key={s.pair || i} className={`ags-seat is-${s.kind}`} onClick={() => openCoin({ mint: s.mint, pairAddress: s.pair, symbol: s.symbol })} data-tip={s.kind === 'agent' ? (s.why || 'the agents hold this seat') : `${k[1]}${s.tag ? ` · ${s.tag}` : ''}`} data-testid={`seat-${s.symbol}`}>
          <i>{k[0]}</i><b>${s.symbol}</b><em className={tone(s.pct)} key={String(s.pct)}>{s.buying ? '⏳' : pct(s.pct)}</em>
          {prog != null && <u data-tip={`${pct(s.pct)} of the +${s.take}% they hold for`}><s style={{ transform: `scaleX(${Math.max(0.03, prog)})` }} /></u>}
          {s.kind === 'agent' && <span className={`ags-act is-${s.action}`}>{ACT[s.action] || '⏳'}{s.toSym ? ` $${s.toSym}` : ''}</span>}</button>; })}</div></div>;
}

// 🧬 GROWTH — an agent grows only by surviving judged calls; a level is HELD only while it is alive
const LV = ['🥚', '🐣', '🧒', '🦾', '🧠', '👑'];
export function GrowthCards({ growth, agents, onZoom }) {
  if (!growth) return null;
  return <div className="ags-grow" data-testid="ags-grow">{(agents || []).map(a => { const g = growth[a.key]; if (!g) return null;
    return <div key={a.key} className={`ags-g is-${a.key} ${g.stunted ? 'is-stunted' : ''}`} data-testid={`grow-${a.key}`}>
      <button type="button" className="ags-gtop" onClick={() => onZoom && onZoom(a.key)} data-tip={`Open ${a.name}'s screen`}><span className="ags-lv">{g.icon}</span><span><b>{a.icon} {a.name}</b><small>{g.name} · gen {g.gen}{g.scars ? ` · ☠×${g.scars}` : ''}</small></span></button>
      <div className="ags-track" aria-hidden>{LV.map((ic, i) => <i key={ic} className={i < g.level ? 'is-done' : i === g.level ? 'is-now' : ''}>{ic}</i>)}</div>
      <div className="ags-xp" data-tip={g.stunted ? 'On probation — the level is held back until its record recovers' : g.next ? `${g.xp} of ${g.next} judged calls to ${g.nextName}` : 'top level'}><u><i style={{ transform: `scaleX(${Math.max(0.02, g.pct / 100)})` }} /></u><em>{g.stunted ? '⚠ stunted' : g.next ? `${g.xp}/${g.next}` : 'MAX'}</em></div>
      <div className="ags-brain" data-tip={`${g.earned}% of its judgement is its own record · ${100 - g.earned}% is still the belief it was born with`}><small>🧠</small><u><i style={{ transform: `scaleX(${Math.max(0.02, g.earned / 100)})` }} /></u><em>{g.earned}% earned</em></div>
      <div className="ags-genes">{(g.genes || []).map(w => <i key={w} className="is-gene" data-tip="inherited from its last life">🧬 {w}</i>)}{(g.skills || []).map(w => <i key={w} className="is-skill" data-tip="a tactic you approved">✦ {w}</i>)}
        {!(g.genes || []).length && !(g.skills || []).length && <small>no genes yet · first life</small>}</div></div>; })}</div>;
}
const RUNG = { learn: 'LEARNING', trust: 'TRUSTED', proven: 'PROVEN' };
export function PowerLadder({ power }) {
  if (!power?.steps) return null;
  return <div className="ags-ladder" data-testid="ags-ladder"><b>🪜 SEATS THEY'VE EARNED ON YOUR CARD · {power.held} held of {power.seats}</b>
    <div className="ags-rungs">{power.steps.map(s => <div key={s.key} className={`ags-rung ${s.done ? 'is-done' : s.on ? 'is-on' : ''}`} data-testid={`rung-${s.key}`} data-tip={s.key === 'learn' ? 'Your switch: one real seat to learn on' : s.key === 'trust' ? 'A 2nd seat once the suggestions you took prove out — and you switch it on' : 'Their full seat count once the paper desk 10×s — and the feed is on'}>
      <span>{s.icon}</span><b>{RUNG[s.key]}<small>{s.seats} seat{s.seats === 1 ? '' : 's'}</small></b><u><i style={{ transform: `scaleX(${Math.max(0.02, s.pct / 100)})` }} /></u><em>{s.done ? '✓ live' : s.need}{!s.on && s.key !== 'learn' ? ' · switch off' : ''}</em></div>)}</div></div>;
}
