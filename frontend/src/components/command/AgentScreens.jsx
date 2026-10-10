import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { openCoin } from '../CoinDrawer';
import { toast } from 'sonner';
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
const NAMES = { tally: ['📊', 'Tally', 'HEAT WALL'], sherlock: ['🔍', 'Sherlock', 'REASONS'], trigger: ['⏱', 'Trigger', 'SCOPE'], devil: ['⚖', 'Devil', 'DOCKET'], judge: ['👨‍⚖️', 'Judge', 'COURT'] };

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
  if (k === 'judge') return [`${d?.judge?.wins ?? 0}–${d?.judge?.losses ?? 0}`, 'ruled'];
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
          : agent === 'trigger' ? <Scope t={t} bar={d?.barNow || d?.bar} big cur={at} pick={setCur} /> : agent === 'judge' ? <Court judge={d?.judge} onPick={setCur} /> : <Docket t={t} big cur={at} pick={setCur} />}</div>
        <Dossier x={x} bar={d?.bar} idx={idx} n={list.length} step={step} /></div>
    </div></div>, document.body);
}

// 🎮 ON YOUR CARD NOW — the real card as seats, and every seat is a CONTROL: tap it → what the agents can do with it right now.
//   ▫ open → 🤖 fill it with one of their GO coins · any held seat → ⇄ swap one of their GO coins in · 🤖 their own seat → 💰 pull to cash.
// Every action is the creator's own tap through the card's normal paths (POST /admin/arena/prime fillSeat / pickSwap / manualSell): the
// same checks, and a ⚠ warning comes back as "do it anyway" — never a silent buy. An agent seat shows its bar to their take line.
const KIND = { agent: ['🤖', 'agents'], suggested: ['🤝', 'their pick, your tap'], yours: ['👤', 'yours'], engine: ['⚙', 'engine'], open: ['▫', 'open'] };
const ACT = { hold: '⏳', pull: '💰', swap: '⇄' };
export const seatMoves = (seat, tpl, gos) => { if (!seat || !tpl) return [];
  const g = (gos || []).slice(0, 3);
  if (seat.kind === 'open') return g.map(x => ({ key: `fill-${x.symbol}`, label: `🤖 $${x.symbol}`, tip: `Fill this seat with their GO coin $${x.symbol} now`, go: true, body: { fillSeat: { tpl, to: x.mint, toPair: x.pair, via: 'agents' } }, k: 'fillSeat' }));
  const swaps = seat.state ? [] : g.map(x => ({ key: `swap-${x.symbol}`, label: `⇄ $${x.symbol}`, tip: `Swap $${seat.symbol} out for their GO coin $${x.symbol} now`, body: { pickSwap: { tpl, pairAddress: seat.pair, to: x.mint, toPair: x.pair, via: 'agents', now: true } }, k: 'pickSwap' }));
  return seat.kind === 'agent' ? [{ key: 'pull', label: '💰 Pull', tip: `Sell $${seat.symbol} to card cash now — the seat opens`, go: true, body: { manualSell: { tpl, pairAddress: seat.pair, pct: 100 } }, k: 'manualSell' }, ...swaps] : swaps; };
export function CardNow({ card, power, cfg, gos, call, isOwner = true, onDone, onMore }) {
  const seats = card?.seats || []; const pw = power || {}; const on = cfg?.agentLearn || cfg?.agentFeed;
  const [at, setAt] = useState(null); const [busy, setBusy] = useState(false); const [warn, setWarn] = useState(null);
  if (!seats.length) return <div className="ags-card is-off" data-testid="ags-card"><b>🎮 ON YOUR CARD</b><small>{on ? 'waiting for the card’s next tick' : 'no real card is funded — the agents trade paper only'}</small></div>;
  const cur = at != null ? seats[at] : null; const free = (gos || []).filter(x => !seats.some(s => s.mint === x.mint)); const moves = seatMoves(cur, card.tpl, free);
  const send = async (m, body) => { if (!call) return; setBusy(true); setWarn(null);
    try { await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }); toast.success(`${m.label} — sent to your card`); setAt(null); if (onDone) onDone(); }
    catch (e) { if (!body[m.k].ack && String(e.message || '').startsWith('⚠')) setWarn({ text: e.message, m, body: { [m.k]: { ...body[m.k], ack: true } } }); else toast.error(e.message); }
    finally { setBusy(false); } };
  return <div className={`ags-card ${cur ? 'is-open' : ''}`} data-testid="ags-card"><span className="ags-cardh"><b>🎮 ON YOUR CARD NOW</b>
    <button type="button" className="ags-pow" onClick={onMore} data-tip="Seats the agents may hold right now — earned (🧬 Growth)" data-testid="ags-pow">🤖 {pw.held ?? 0} / {pw.seats ?? 0} seats</button></span>
    <div className="ags-seats">{seats.map((s, i) => { const k = KIND[s.kind] || KIND.engine; const prog = s.kind === 'agent' && s.pct != null && s.take ? clamp(s.pct / s.take, 0, 1) : null;
      return <button type="button" key={s.pair || `o${i}`} className={`ags-seat is-${s.kind} ${at === i ? 'is-cur' : ''}`} aria-expanded={at === i} onClick={() => { setAt(at === i ? null : i); setWarn(null); }}
        data-tip={s.kind === 'open' ? 'Open seat — tap to fill it' : s.kind === 'agent' ? (s.why || 'the agents hold this seat') : `${k[1]}${s.tag ? ` · ${s.tag}` : ''}`} data-testid={s.kind === 'open' ? `seat-open-${i}` : `seat-${s.symbol}`}>
        <i>{k[0]}</i><b>{s.kind === 'open' ? 'open' : `$${s.symbol}`}</b>{s.kind !== 'open' && <em className={tone(s.pct)} key={String(s.pct)}>{s.buying ? '⏳' : pct(s.pct)}</em>}
        {prog != null && <u><s style={{ transform: `scaleX(${Math.max(0.03, prog)})` }} /></u>}
        {s.kind === 'agent' && <span className={`ags-act is-${s.action}`}>{ACT[s.action] || '⏳'}{s.toSym ? ` $${s.toSym}` : ''}</span>}</button>; })}</div>
    {cur && <div className="ags-tray m-pop" data-testid="ags-tray"><span className="ags-trayh">{(KIND[cur.kind] || KIND.engine)[0]} {cur.kind === 'open' ? 'OPEN SEAT' : `$${cur.symbol}`}{cur.state ? ` · ${cur.state === 'ride' ? '❄ riding' : '🧊 frozen'}` : ''}</span>
      {warn ? <><small className="ags-warn">{warn.text}</small><button type="button" className="m-btn" disabled={busy} onClick={() => send(warn.m, warn.body)} data-testid="seat-ack">I understand — do it anyway</button><button type="button" className="m-btn" onClick={() => setWarn(null)}>Cancel</button></>
        : <>{moves.map(m => <button type="button" key={m.key} className={`m-btn ${m.go ? 'm-go' : ''}`} disabled={busy || !isOwner || !call} data-tip={m.tip} onClick={() => send(m, m.body)} data-testid={`move-${m.key}`}>{m.label}</button>)}
          {!moves.length && <small>{cur.state ? 'locked — a riding / frozen coin is never swapped from here' : 'no GO coin from the agents right now'}</small>}
          {cur.kind !== 'open' && <button type="button" className="m-btn" onClick={() => openCoin({ mint: cur.mint, pairAddress: cur.pair, symbol: cur.symbol })} data-testid="move-coin">🪙</button>}</>}</div>}</div>;
}

// 👨‍⚖️ THE JUDGE + 🏆 PROOF — one band. Left: the court (W–L, who is ON TRIAL and its handicap, who wears the 👑, the ruling tape — each
// chip = one call ruled 5 min after its final decision, with the bot that called it / takes the L). Right: wins and losses as pips —
// PAPER (every GO) and CARD (every coin that left a real seat) — and the stake the next paper GO gets (🔥 heater / 🧊 cold).
const BOT = { tally: '📊', sherlock: '🔍', trigger: '⏱', devil: '⚖' };
const Pips = ({ last, syms }) => <span className="ags-pips">{(last || []).slice(0, 16).map((v, i) => <i key={i} className={v > 0 ? 'is-up' : 'is-dn'} data-tip={`${syms?.[i] ? `$${syms[i]} ` : ''}${pct(v)}`} />)}{!(last || []).length && <small>none yet</small>}</span>;
export function CourtBand({ judge, proof, desk, onPick, onCourt }) {
  const j = judge || {}; const pr = proof || {}; const heat = desk?.heat || 'even';
  return <div className="ags-court" data-testid="ags-court">
    <div className="ags-judge"><button type="button" className="ags-jhead" onClick={onCourt} data-tip="Open the court: every ruling and each bot's score" data-testid="ags-judge"><span className="ags-gavel" key={j.n || 0}>👨‍⚖️</span><b>JUDGE</b><em><i className="m-pos">{j.wins ?? 0}W</i> <i className="m-neg">{j.losses ?? 0}L</i></em></button>
      <span className="ags-sent">{j.trial ? <i className="is-trial" data-tip={`Worst net over the last rulings — plays under a handicap until it recovers: ${j.handicap}`} data-testid="ags-trial">🔨 {BOT[j.trial]} ON TRIAL · {j.handicap}</i> : <i className="is-clear">no bot on trial</i>}
 {j.missed > 0 && <i className="is-miss" data-tip="Coins Trigger said WAIT on that ran 10%+ in 5 min. Never counted toward a trial — your 🔥 dial lowers its bar." data-testid="ags-missed">😴 {j.missed} missed</i>}
        {j.mvp && <i className="is-mvp" data-tip="Best net over the last rulings" data-testid="ags-mvp">👑 {BOT[j.mvp]}</i>}</span>
      <span className="ags-tape">{(j.rulings || []).slice(0, 10).map((r, i) => <button type="button" key={`${r.mint}-${r.at}`} className={`ags-rule is-${r.verdict}`} style={{ '--i': Math.min(i, 8) }} onClick={() => onPick && onPick(r.sym)}
        data-tip={`${r.kind === 'go' ? 'GO' : r.kind === 'objected' ? 'objected' : 'waited — it ran'} · ${r.credit ? `${BOT[r.credit]} called it` : ''}${r.credit && r.blame ? ' · ' : ''}${r.blame ? `${BOT[r.blame]} takes the L` : ''}`} data-testid={`rule-${r.sym}`}>
        {r.verdict === 'win' ? '🏆' : r.verdict === 'miss' ? '😴' : '🔨'} ${r.sym} <em>{pct(r.pct)}</em><u>{BOT[r.verdict === 'win' ? r.credit : r.blame] || ''}</u></button>)}
        {!(j.rulings || []).length && <small>first ruling lands 5 min after their first final call</small>}</span></div>
    <div className="ags-proof" data-testid="ags-proof">
      <span className="ags-prow" data-tip="Every GO the team made on paper, judged 5 minutes later — newest first"><b>📜 PAPER</b><em><i className="m-pos">{pr.paper?.w ?? 0}</i>–<i className="m-neg">{pr.paper?.l ?? 0}</i></em><Pips last={pr.paper?.last} syms={pr.paper?.syms} /></span>
      <span className="ags-prow" data-tip="Every coin that left a real seat you allowed, on the card's own ledger — newest first"><b>💵 CARD</b><em><i className="m-pos">{pr.card?.w ?? 0}</i>–<i className="m-neg">{pr.card?.l ?? 0}</i></em><Pips last={pr.card?.last} /></span>
      <span className={`ags-heat2 is-${heat}`} data-tip="Paper desk only: the next GO's stake follows the streak — 25% even · 35% after 2 wins · 45% after 3+ · 15% right after a loss" data-testid="ags-stake">{heat === 'heater' ? '🔥' : heat === 'cold' ? '🧊' : '▪'} next stake {desk?.stake ?? 25}%</span></div></div>;
}
// the court, zoomed: every ruling as a card + each bot's credit / blame
export function Court({ judge, onPick }) {
  const j = judge || {}; const top = Math.max(1, ...Object.values(j.score || {}).map(v => Math.max(v.credit, v.blame)));
  return <div className="ags-courtz" data-testid="ags-courtz">
    <div className="ags-scores">{Object.entries(j.score || {}).map(([k, v]) => <div key={k} className={`ags-score ${j.trial === k ? 'is-trial' : j.mvp === k ? 'is-mvp' : ''}`} data-testid={`score-${k}`}>
      <b>{BOT[k]}{j.mvp === k ? ' 👑' : j.trial === k ? ' 🔨' : ''}</b><u className="is-up"><i style={{ transform: `scaleX(${v.credit / top})` }} /></u><u className="is-dn"><i style={{ transform: `scaleX(${v.blame / top})` }} /></u><em className={tone(v.net)}>{v.net > 0 ? '+' : ''}{v.net}</em></div>)}</div>
    <div className="ags-cases">{(j.rulings || []).map(r => <button type="button" key={`${r.mint}-${r.at}`} className={`ags-case is-${r.verdict}`} onClick={() => onPick && onPick(r.mint)} data-testid={`case-${r.sym}`}>
      <b>{r.verdict === 'win' ? '🏆' : r.verdict === 'miss' ? '😴' : '🔨'} ${r.sym}</b><em className={tone(r.pct)}>{pct(r.pct)}</em><small>{r.kind === 'go' ? 'GO' : r.kind === 'objected' ? 'OBJ' : 'WAIT'}</small>
      <span>{r.credit && <i className="is-up">{BOT[r.credit]}✓</i>}{r.blame && <i className="is-dn">{BOT[r.blame]}✕</i>}</span></button>)}
      {!(j.rulings || []).length && <div className="ags-empty">no rulings yet — the first lands 5 minutes after a final call</div>}</div></div>;
}

// 🎯 THE MISSION + ⚡ SCALP — what the agents are FOR right now, as two bars and one plan:
//   1 💵 BREAKEVEN: your real card vs what you put in (a distance — the × it needs — never a promise) · 2 📜 the paper 10×.
//   ⚡ the scalp plan they learned from their own 5-minute paths (take line · stop), its average against just holding, or how many
//   paths they still need before a plan may be adopted.
export function MissionBar({ mission, scalp, desk }) {
  const m = mission || {}; const sp = scalp || {}; const live = sp.live; const be = m.key === 'breakeven'; const x = Number(desk?.x) || 1;
  const fmt = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
  return <div className="ags-mission" data-testid="ags-mission">
    <div className={`ags-goal ${be ? 'is-now' : 'is-done'}`} data-tip="Your real card's value against everything you put in. The agents work one seat of it; this is a distance, not a forecast." data-testid="goal-breakeven">
      <b>1 · 💵 BREAKEVEN{be ? ' · NOW' : ' ✓'}</b><em>{m.putIn ? <>${Number(m.value).toFixed(2)} <small>of ${Number(m.putIn).toFixed(2)}{be ? ` · needs ${m.needX}×` : ''}</small></> : <small>no real card funded</small>}</em>
      <u><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, be ? (m.pct || 0) / 100 : m.putIn ? 1 : 0))})` }} /></u></div>
    <div className={`ags-goal ${be ? '' : 'is-now'}`} data-tip="The paper desk must 10× in one run (25% a GO, pressed on a streak)." data-testid="goal-tenx">
      <b>2 · 📜 10× PAPER{be ? '' : ' · NOW'}</b><em>{x.toFixed(2)}× <small>of 10×</small></em><u><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, Math.log10(Math.max(1, x))))})` }} /></u></div>
    <div className={`ags-scalp ${live ? 'is-live' : ''}`} data-testid="ags-scalp" data-tip={live ? 'Learned from their own 5-minute paths and played only on calls made after it was adopted. On your card an agent seat banks at this take line; no stop is added.' : 'Every ENTER keeps its 5-minute path. A plan is adopted only when it beats holding on 20+ of their own paths.'}>
      <b>⚡ SCALP{live ? ' · LIVE' : ' · LEARNING'}</b>
      {live ? <em>TP +{live.tp}% <small>· {live.sl ? `SL −${live.sl}%` : 'no stop'}</small></em> : <em>{sp.n ?? 0}<small> / {sp.needN ?? 20} paths</small></em>}
      {sp.best && sp.n ? <span className="ags-vs"><i className={sp.best.avg > 0 ? 'm-pos' : 'm-neg'}>⚡ {fmt(sp.best.avg)}</i><small>vs hold</small><i className={(sp.flat?.avg ?? 0) > 0 ? 'm-pos' : 'm-neg'}>{fmt(sp.flat?.avg)}</i>{sp.peak != null && <small>· peak {fmt(sp.peak)}</small>}</span>
        : <u><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, (sp.n || 0) / (sp.needN || 20)))})` }} /></u>}</div></div>;
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
