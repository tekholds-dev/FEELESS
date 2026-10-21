import { symOf, tapSym } from '../../lib/symTap';
import { addTip } from '../../lib/agentTips';
import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { DuoSeat } from './DuoSeat';
import { createPortal } from 'react-dom';
import { AddMyCoin, SeatStudy, MySeatsRecord, SeatControls } from './MySeat';
import { QuickTrade } from './QuickTrade';
import { OwnerStudy } from './OwnerStudy';
import { BrainLearned } from './BrainLearned';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import { toast } from 'sonner';
import { grabOrder } from '../../lib/chartGrab';
import { useHub, hubApply, hubLoad, useAi } from '../../lib/agentHub';
import { rankFill, READY_MIN, devilOf } from '../../lib/agentRead';
import { seatCards, flowBar, focusMint, chartModel, decisionOf, tapeOf, tapeTone, TAPE_AGENT, AGE_BUCKETS, bucketCounts, reviewQueue, supplyWord,
  seatState, STATE_CLS, missionTiles, letterMarkers, inputsOf, traceOf, CHAIN, maxIdByAgent, newEvents, queueStatus, queueMc, openPnl, groupTape, lossMap, measureRead, recWord, voteSplit , moneyOf, exitTags } from '../../lib/cockpit';
import { useEasedNumber } from '../../lib/easedNumber';
import { STANCE_TONE } from '../../lib/aiRead';
import { usd as cash, pct as pc, price as priceFmt } from '../../lib/num';
import { AG, activityOf } from './agentWords';
import { openCoin } from '../CoinDrawer';
import { AiProviders, AiChipBtn } from './AiProviders';
import { AiPane, AiIntel, AiCell } from './AiDecisions';
import { CockpitControls } from './CockpitControls';
import { IntakeBand } from './IntakeBand';
import { TeachBox } from './TeachBox';
import { VitalBoard } from './VitalBoard';
import { TradeTape, CoachBox } from './CoachTape';
import { CopyCa } from './CopyCa';
import { tradeBar, tickDir, aiOf } from '../../lib/cockpitControls';
import '../../styles/agentCockpit.css';
import { AiChat } from './AiChat';
import '../../styles/cockpitAi.css';   // after the cockpit sheet: it owns the plot's height + the meta pass
import '../../styles/cockpitDeck.css';   // last: the one-screen layout (deck, tight chart strip, short AI log)
import '../../styles/agentFx.css';   // ⚡ hover sheen · press ring · winner glow · paint containment for scrolling
import { GermChip } from '../GermBadge';
import { useRemembered } from '../../lib/remember';
import { avatarOf } from '../../lib/aiAvatars';
import { ghostMarkers, rugMark, diamondOf, leagueOf, rideCard } from '../../lib/cockpitPlus';
import { recentResults } from '../../lib/coachTape';
import { ShareGifButton } from '../ShareGif';
import '../../styles/cockpitPlus.css';

// 🎛 THE AGENTS COCKPIT (HQ › Agents, the whole top of the tab — built to the owner's reference, 2026-10-12): REAL MONEY MISSION ribbon ·
// the four SEATS · ONE chart in MARKET CAP with the agents' real events lettered on it (T D W B R X) · the LIVE DECISIONS strip · the
// AGENT DECISION PANEL (live decision · inputs · seats · review · trace) · the ten-agent MATRIX · the REVIEW QUEUE with the owner's coin
// review · OPERATOR CONTROLS. One store (the agent hub), one request; every number is the payload's or the shared live-price poller's.
// MC / % / $ glide between two REAL reads at ≤ 30fps (display only — `useEasedNumber`); an agent pulses only when ITS tape id moves.
const PriceChartLazy = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
const money = v => (v == null ? '—' : cash(v));
// market cap / volume in the reference's compact words: $14.2K · $1.21M (the cent-level `usd` is for a seat's dollars)
export const mcWord = v => (v == null || !Number.isFinite(v) ? '—' : Math.abs(v) >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : Math.abs(v) >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : Math.abs(v) >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const signed = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}$${Math.abs(v) < 1e4 ? Math.abs(v).toFixed(2) : cash(Math.abs(v)).replace('$', '')}`);
const mins = m => (m == null ? '—' : m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${(m / 60).toFixed(1)}h` : `${(m / 1440).toFixed(1)}d`);
const secs = s => (s == null ? '—' : s < 60 ? `${Math.round(s)}s` : `${Math.round(s / 60)}m`);
const ago = (at, now = Date.now() / 1000) => { if (!at) return '—'; const s = Math.max(0, Math.round(now - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${(s / 3600).toFixed(1)}h`; };
const tone = v => (v == null ? '' : v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');
const money2 = v => (v == null ? '—' : Math.abs(v) < 1e4 ? `${v < 0 ? '−' : ''}$${Math.abs(v).toFixed(2)}` : cash(v));   // the card's own dollars, to the cent
const FMT = { usd: money2 };

// 🎞 a live number that glides to each REAL value (≤ 30fps, display only)
export function LiveNum({ v, fmt, cls, testid }) {
  const shown = useEasedNumber(v);
  return <b className={`ack-num ${cls ?? tone(v)}`} data-testid={testid}>{shown == null ? '—' : fmt(shown)}</b>;
}

// ── ⚡ the live pulse: the desk working, second by second ──────────────────────────────────────────────────────────────────────────
// ONE 1-second clock for the whole strip. Every figure is the kernel's own (coins tracked, re-judged, events / s, the ten-agent brain's
// latency) or an age counted from a real timestamp (the last pass, the last decision line, the model's last answer) — nothing invented.
// 🩸 WHERE THE LOSSES COME FROM + 👨‍⚖️ the Judge's real record — owner-approved build items b1 / b2 / b3 / b6, drawn from the Judge's reviews of
// confirmed real exits (court) and the capital desk's leaks. Bars, not paragraphs.
function LossMap({ court, capital }) {
  const m = lossMap(court, capital); if (!m.causes.length && !m.leaks.length && m.pct == null) return null;
  return <section className="ack-loss" data-testid="ack-lossmap">
    <header><b>🩸 WHERE THE LOSSES COME FROM</b>{m.pct != null ? <span className="ack-jm" data-testid="ack-judge-meter" data-tip="The Judge's reviews of confirmed real exits: wins vs losses"><small>👨‍⚖️ JUDGE · REAL</small><b>{m.w}W · {m.l}L</b><i><u style={{ transform: `scaleX(${m.pct / 100})` }} /></i><em>{m.pct}%</em></span> : null}</header>
    {m.causes.length ? <ul className="ack-lcause">{m.causes.map(x => <li key={x.cause}><span>{x.cause}</span><i><u style={{ transform: `scaleX(${x.fill})` }} /></i><b>{x.n}×</b><small>{x.desk}</small></li>)}</ul> : null}
    {m.leaks.length ? <p className="ack-lleak">{m.leaks.slice(0, 3).map(x => <span key={x.rule} className="m-neg">{x.rule} · {x.n}× · avg {x.avg}%</span>)}</p> : null}
    {m.last?.lesson ? <p className="ack-llast" data-tip={m.last.lesson}>last loss ${m.last.sym} {m.last.pct}% → {m.last.lesson}</p> : null}
  </section>;
}
// 🗂 ONE deck instead of three stacked boxes: the trade tape · the coach · teach share a tab row beside the Brain (less scroll). Every pane stays
// mounted (hidden) so a half-typed lesson or an open trade story survives a tab switch; the count on each tab is the payload's own.
const DECK_KEY = 'feeless.agentDeck'; const NAV_KEY = 'feeless.agentNav';
// 🏷 a tab = icon first, one short word, a live badge, a mini meter that fills with the tab's own number (transform only)
export function TabChip({ label, n, meter }) {
  const sp = String(label || '').indexOf(' '); const ic = sp > 0 ? label.slice(0, sp) : ''; const w = sp > 0 ? label.slice(sp + 1) : label;
  return <span className="ack-tchip"><span className="ack-tic" aria-hidden>{ic}</span><span className="ack-tw">{w}</span>{n != null && n !== 0 ? <i key={n} className="ack-tbadge">{n}</i> : null}
    {meter != null ? <span className="ack-tmeter" aria-hidden><b style={{ transform: `scaleX(${Math.max(0, Math.min(1, meter)).toFixed(3)})` }} /></span> : null}</span>;
}
// each deck tab's mini meter, from numbers the payload already carries: trades = share of closed real trades that won · desk = share of
// the ten agents ACTIVE · feed = how fresh the tape is (full = a line in the last minute, empty = 10 min quiet)
export function deckMeters(o, tabs, nowS = Date.now() / 1000) {
  const rows = o?.tradeTape?.rows || []; const resOf = r => (r.result && typeof r.result === 'object' ? r.result.pct : r.result) ?? r.pct;   // the tape's result is {pct, usd, rule…}
  const closed = rows.filter(r => resOf(r) != null); const won = closed.filter(r => Number(resOf(r)) > 0).length;
  const gens = o?.generations || []; const act = gens.filter(g => g.status === 'ACTIVE').length;
  const last = Math.max(0, ...(o?.tape || []).map(r => Number(r.at) || 0)); const age = last ? nowS - last : null;
  const m = { tape: closed.length ? won / closed.length : null, agents: gens.length ? act / gens.length : null, live: age == null ? null : Math.max(0, 1 - Math.max(0, age - 60) / 540) };
  const tips = { tape: closed.length ? `${won} of ${closed.length} closed real trades won` : 'real trade tape', agents: gens.length ? `${act} of ${gens.length} agents active` : 'the agents', live: 'the live decision feed' };
  return tabs.map(([k, l, n, node, meter, tip, lazy]) => [k, l, n, node, meter != null ? meter : m[k] ?? null, tip || tips[k] || null, lazy]);
}
// a deck pane: re-renders while it is open (or the moment it opens / closes) — a hidden one keeps its last render and skips live updates
const Pane = React.memo(function Pane({ node }) { return node; }, (a, b) => !a.on && !b.on);

const DECK_ALIAS = { agents: 'live' };   // 🧩 the old Desk tab now lives inside ⚡ Live desk
function Deck({ tabs, testid = 'ack-deck', on: onC, setOn: setOnC, bare }) {
  const [onS, setOnS] = useState(() => { try { const v = DECK_ALIAS[localStorage.getItem(DECK_KEY)] || localStorage.getItem(DECK_KEY); return tabs.some(t => t[0] === v) ? v : tabs[0][0]; } catch { return tabs[0][0]; } });
  const on = onC && tabs.some(t => t[0] === onC) ? onC : onS;
  const pick = k => { (setOnC || setOnS)(k); try { localStorage.setItem(DECK_KEY, k); } catch { /* private window */ } };
  return <section className="ack-deck" data-testid={testid} data-on={on}>
    {!bare && tabs.length > 1 ? <div className="ack-decktabs m-seg" role="tablist" aria-label="Cockpit deck">{tabs.map(([k, l, n, , meter, tip]) => <button key={k} type="button" role="tab" aria-selected={on === k} className={on === k ? 'active' : ''} onClick={() => pick(k)} data-testid={`ack-deck-${k}`} data-tip={tip || undefined}><TabChip label={l} n={n} meter={meter} /></button>)}</div> : null}
    {/* ⚡ HIDDEN PANES ARE FROZEN (2026-10-16 lag fix): they stay mounted (state kept) but skip every live update until opened — each
        hidden pane used to re-render on every paint (22.6 → 5 ms per update on the real payload). A `lazy` pane mounts only while open. */}
    {tabs.map(([k, , , node, , , lazy]) => <div key={k} role="tabpanel" className="ack-deckpane" hidden={on !== k} data-testid={`ack-deckpane-${k}`}>{lazy && on !== k ? null : <Pane on={on === k} node={node} />}</div>)}
  </section>;
}
function useTick(ms = 1000) { const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => { if (!(typeof document !== 'undefined' && document.hidden)) setN(Date.now()); }, ms); return () => clearInterval(t); }, [ms]); return n; }
export function pulseOf(o, nowMs = Date.now()) {
  const now = nowMs / 1000; const k = (o?.kernel || {}).metrics || {}; const cy = o?.cycle || {}; const every = Number(cy.nextIn) > 0 ? Number(cy.nextIn) : Number(cy.every) || 18;
  const passAge = cy.at ? Math.max(0, now - cy.at) : null; const last = (o?.tape || []).reduce((m, r) => (r.at > (m?.at || 0) ? r : m), null);
  const lg = (o?.ai?.log || []); const ai = lg.length ? lg[lg.length - 1] : null; const by = k.byStatus || {};
  return { passAge, every, fill: passAge == null ? 0 : Math.max(0, Math.min(1, passAge / every)), late: passAge != null && passAge > every * 2,
    mints: k.mints ?? null, rejudged: k.rejudged ?? null, eps: k.eventsPerSec ?? null, newPerMin: k.uniqueMintsPerMin ?? null,
    brainMs: k.latencyMs?.agents?.p50 != null ? k.latencyMs.agents.p50 * 1000 : null, wakeMs: k.latencyMs?.priceToReaper?.p50 != null ? k.latencyMs.priceToReaper.p50 * 1000 : null,
    tracking: by.TRACKING ?? 0, contending: by.CONTENDING ?? 0, ready: by.READY ?? 0, held: by.HELD ?? 0,
    last: last ? { age: Math.max(0, now - last.at), agent: last.agent, action: last.action, symbol: last.symbol } : null,
    ai: ai ? { age: Math.max(0, now - ai.at), stance: ai.stance, symbol: ai.symbol } : null };
}
// 🧠 the model's chip on the pulse — reads the AI STORE (its own subscriber): its newest stance, how long ago, the queue and the latency
function PulseAi({ o, now, onAi, sec }) {
  const ai = useAi(o?.ai); const lg = ai?.log || []; const last = lg.length ? lg[lg.length - 1] : null; const m = ai?.metrics || {};
  const age = last ? Math.max(0, now / 1000 - last.at) : null;
  return <button type="button" className="ack-pz is-ai" onClick={onAi} data-testid="ack-pulse-ai" data-tip="The model's decisions — tap to open (queue · average answer time)"><small>🧠 MODEL</small>
    <b>{last ? `${last.stance || '—'}${last.symbol ? ` $${last.symbol}` : ''}` : 'no answer yet'}</b>
    <u>{[last ? `${sec(age)} ago` : null, m.queue ? `queue ${m.queue}` : null, m.avgMs ? `${(m.avgMs / 1000).toFixed(1)}s avg` : null].filter(Boolean).join(' · ')}</u></button>;
}
// the funnel as four live bars (each scaled to the biggest stage; transform only)
function FunnelBars({ p }) {
  const v = [p.tracking, p.contending, p.ready, p.held].map(x => Number(x) || 0); const mx = Math.max(1, ...v);
  return <span className="ack-fbars" aria-hidden>{['t', 'c', 'r', 'h'].map((k, i) => <i key={k} className={`is-${k}`} style={{ transform: `scaleY(${Math.max(0.06, v[i] / mx).toFixed(3)})` }} />)}</span>;
}
function LivePulse({ o, onAi }) {
  const now = useTick(1000); const p = pulseOf(o, now); const [ic, nm] = TAPE_AGENT[p.last?.agent] || ['•', p.last?.agent || ''];
  const sec = v => (v == null ? '—' : v < 60 ? `${Math.floor(v)}s` : `${Math.floor(v / 60)}m ${Math.floor(v % 60)}s`);
  return <section className={`ack-pulse ${p.late ? 'is-late' : ''}`} data-testid="ack-pulse">
    <span className="ack-pz is-pass" data-tip="The agents' pass: the whole desk re-reads every coin. Between passes the live chart price wakes Reaper and Trigger within seconds."><small>PASS</small><b>{sec(p.passAge)} ago</b>
      <span className="ack-pzbar"><i style={{ transform: `scaleX(${p.fill})` }} /></span></span>
    <span className="ack-pz"><small>COINS TRACKED</small><LiveNum v={p.mints} fmt={x => String(Math.round(x))} cls="" testid="ack-pulse-mints" /><u>{p.newPerMin != null ? `${Math.round(p.newPerMin)} new / min` : ''}</u></span>
    <span className="ack-pz"><small>RE-JUDGED</small><LiveNum v={p.rejudged} fmt={x => String(Math.round(x))} cls="" /><u>{p.eps != null ? `${p.eps.toFixed(1)} events / s` : ''}</u></span>
    <span className="ack-pz" data-tip="tracking › contending › ready › held"><small>FUNNEL</small><b><i className="ack-fz is-t">{p.tracking}</i>›<i className="ack-fz is-c">{p.contending}</i>›<i className="ack-fz is-r">{p.ready}</i>›<i className="ack-fz is-h">{p.held}</i></b><u>tracking › contending › ready › held</u>
      <FunnelBars p={p} /></span>
    <span className="ack-pz"><small>BRAIN</small><b>{p.brainMs != null ? `${p.brainMs < 10 ? p.brainMs.toFixed(1) : Math.round(p.brainMs)}ms` : '—'}</b><u>{p.wakeMs != null ? `price → Reaper ${Math.round(p.wakeMs)}ms` : 'per coin, ten agents'}</u></span>
    <span className="ack-pz is-wide"><small>LAST DECISION</small><b key={p.last ? `${p.last.agent}-${p.last.action}-${p.last.symbol}` : 'x'} className="ack-pzlast">{p.last ? <>{ic} {nm} · {p.last.action}{p.last.symbol ? ` $${p.last.symbol}` : ''}</> : '—'}</b><u>{p.last ? `${sec(p.last.age)} ago` : 'a quiet tape is a quiet market'}</u></span>
    <PulseAi o={o} now={now} onAi={onAi} sec={sec} />
  </section>;
}

// ── 💵 THE MONEY STRIP + the nav (sticky): card value · today's real result · the seats it holds with their live % · night state ──────
export function ExitChips({ s, mini }) {
  const t = exitTags(s); if (!t.length) return null;
  return <span className={`ack-xchips ${mini ? 'is-mini' : ''}`}>{t.map(x => <i key={x.k} className={`ack-xchip is-${x.k}`} data-tip={x.tip} data-testid={`ack-xchip-${x.k}`}>{x.ic}{mini ? null : <b>{x.word}</b>}</i>)}</span>;
}
const sgn = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(2)}`);
function MoneyStrip({ d, seats, mint, onPick, nav, go, navTabs, ai = null, brain = null }) {
  const now = useTick(5000); const m = moneyOf(d, seats, now);
  const rows = d?.office?.tradeTape?.rows; const rr = useMemo(() => recentResults(rows), [rows]); const dia = useMemo(() => diamondOf(rows), [rows]); const lg = leagueOf(d?.duo);
  const tTone = m.today.usd == null ? '' : m.today.usd >= 0 ? 'm-pos' : 'm-neg';
  return <header className={`ack-money is-${m.night.state}`} data-testid="ack-money">
    <div className="ack-mrow">
      <span className="ack-mcell is-card" data-tip={`card value now · put in ${m.putIn != null ? `$${m.putIn.toFixed(2)}` : '—'}${m.netPct != null ? ` · ${m.netPct >= 0 ? '+' : ''}${m.netPct.toFixed(1)}% all time` : ''}`}>
        <small>💵 CARD</small><LiveNum v={m.value} fmt={x => `$${x.toFixed(2)}`} cls="" testid="ack-money-value" />{m.netPct != null ? <u className={tone(m.netPct)}>{m.netPct >= 0 ? '+' : ''}{m.netPct.toFixed(0)}%</u> : null}</span>
      <span className="ack-mcell" data-tip={m.today.n ? `real trades closed since midnight: ${m.today.won} of ${m.today.n} won${m.today.partial ? ' (the tape holds only its newest trades)' : ''}` : 'no real trade closed since midnight'}>
        <small>📅 TODAY</small><LiveNum v={m.today.usd} fmt={sgn} cls={tTone} testid="ack-money-today" />
        <span className="ack-mwin" aria-hidden>{m.today.n ? <i style={{ transform: `scaleX(${(m.today.won / m.today.n).toFixed(3)})` }} /> : null}</span></span>
      <span className="ack-mcell is-split" data-tip="realized in the last 24h — your own trades apart from the agents' (fees apart)" data-testid="ack-money-split">
        <small>👤 YOU · 🤖 AGENTS</small><b><em className={tone(rr.you.usd)}>{rr.you.usd == null ? '—' : sgn(rr.you.usd)}</em><i>·</i><em className={tone(rr.agents.usd)}>{rr.agents.usd == null ? '—' : sgn(rr.agents.usd)}</em></b></span>
      <span className="ack-mcell is-dia" data-tip={dia.n ? `on ${dia.n} of your closed trades, holding past the agents' first sell call made ${dia.avg >= 0 ? '+' : ''}${dia.avg.toFixed(1)} pts a trade · best $${dia.best.sym} ${dia.best.gain >= 0 ? '+' : ''}${dia.best.gain.toFixed(0)} pts · worst $${dia.worst.sym} ${dia.worst.gain.toFixed(0)} pts` : 'no closed trade of yours with an agent sell call yet'} data-testid="ack-money-diamond">
        <small>💎 DIAMOND HANDS</small><b className={dia.n ? tone(dia.avg) : 'm-dim'}>{dia.n ? `${dia.avg >= 0 ? '+' : ''}${dia.avg.toFixed(1)} pts` : '—'}</b></span>
      <span className="ack-mcell is-league" data-tip={`G4 ${lg.a.n ? `${lg.a.n} · ${lg.a.won}% won · typical ${lg.a.med}%` : 'no trades'} vs OSSY ${lg.b.n ? `${lg.b.n} · ${lg.b.won}% won · typical ${lg.b.med}%` : 'no trades'} (paper seat)`} data-testid="ack-money-league">
        <small>🔁 G4 vs OSSY</small><b className={lg.lead ? 'm-pos' : 'm-dim'}>{lg.word}</b></span>
      <span className="ack-mcell is-open" data-tip={m.openUsd != null ? `open seats right now: ${sgn(m.openUsd)} (live)` : 'no seat held'}><small>🪑 HOLDING {m.open.length}/{m.seats || '—'}</small>
        <span className="ack-mseats">{m.open.length ? m.open.map(x => <button key={x.seat} type="button" className={`ack-mseat ${x.pct == null ? '' : x.pct >= 0 ? 'is-up' : 'is-dn'} ${x.mint === mint ? 'is-on' : ''}`} onClick={() => { onPick(x.mint); go('chart'); }} data-testid={`ack-money-seat-${x.seat}`}>
          <b>${x.sym || '—'}</b><LiveNum v={x.pct} fmt={v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`} cls="" /><ExitChips s={(seats || []).find(z => z.seat === x.seat)} mini />
          <span className="ack-mbar" aria-hidden><i style={{ transform: `scaleX(${Math.min(1, Math.abs(x.pct || 0) / 20).toFixed(3)})` }} /></span></button>) : <em className="m-dim">cash — no coin held</em>}</span></span>
      <span className={`ack-mcell is-night is-${m.night.state}`} data-tip={m.night.tip} data-testid="ack-money-night"><small>{m.late ? '⚠ DESK BEHIND' : 'SHIFT'}</small><b key={m.night.word} className="ack-vpop">{m.night.word}</b></span>
      {brain}{ai}
    </div>
    <nav className="ack-nav m-seg" role="tablist" aria-label="Agents tab">
      <button type="button" role="tab" aria-selected={nav === 'chart'} className={nav === 'chart' ? 'active' : ''} onClick={() => go('chart')} data-testid="ack-nav-chart" data-tip="the chart + the decision panel (top of the page)"><TabChip label="📈 Chart" /></button>
      {navTabs.map(([k, l, n, , meter, tip]) => <button key={k} type="button" role="tab" aria-selected={nav === k} className={nav === k ? 'active' : ''} onClick={() => go(k)} data-testid={`ack-deck-${k}`} data-tip={tip || undefined}><TabChip label={l} n={n} meter={meter} /></button>)}
    </nav>
  </header>;
}

// ── 💵 the mission ribbon ───────────────────────────────────────────────────────────────────────────────────────────────────────
export function MissionRibbon({ tiles, live, cold }) {
  return <section className="ack-ribbon m-live" data-testid="ack-ribbon">
    <span className="ack-rhead"><b>💵 REAL MONEY MISSION</b><i className={live ? 'is-live' : ''}>{cold ? 'waiting' : live ? '● live' : '● snapshot'}</i></span>
    {tiles.map(t => <span key={t.k} className={`ack-rt ${t.meter != null ? 'has-meter' : ''}`} data-testid={`ack-rt-${t.k}`} data-tip={[t.sub, t.tip].filter(Boolean).join(' · ') || undefined}><small>{t.label}</small>
      {t.fmt ? (t.live ? <LiveNum v={t.val} fmt={FMT[t.fmt]} cls={t.cls || ''} /> : <b className={`ack-num ${t.cls || ''}`}>{FMT[t.fmt](t.val)}</b>) : <b className={`ack-num ack-word ${t.cls || ''}`}>{t.text}</b>}
      {t.sub ? <u className={t.subCls || ''}>{t.sub}</u> : null}
      {t.meter != null ? <span className={`ack-rtm ${t.meterCls || ''}`} aria-hidden><i style={{ transform: `scaleX(${Math.max(0, Math.min(1, t.meter)).toFixed(3)})` }} /></span> : null}</span>)}
  </section>;
}

// a tiny line of the seat's real % path (the position's own readings since entry; nothing drawn when there are < 2)
export function Spark({ path, w = 64, h = 18 }) {
  const p = (path || []).filter(Number.isFinite); if (p.length < 2) return null;
  const lo = Math.min(0, ...p); const hi = Math.max(0, ...p); const sp = hi - lo || 1;
  const pts = p.map((v, i) => `${((i / (p.length - 1)) * w).toFixed(1)},${(h - ((v - lo) / sp) * h).toFixed(1)}`).join(' ');
  const zero = h - ((0 - lo) / sp) * h;
  return <svg className={`ack-spark ${p[p.length - 1] >= 0 ? 'is-up' : 'is-dn'}`} viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden data-testid="ack-spark">
    <line x1="0" x2={w} y1={zero} y2={zero} className="ack-spark-0" /><polyline points={pts} fill="none" /></svg>;
}

// ── 🪑 the seats ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
// 📡 an empty seat reads as a live radar: what it is hunting + the ONE thing holding it (head = the blocker, the rest = its numbers)
export const huntSplit = why => { const w = String(why || '').trim(); const i = w.indexOf(':'); return i > 0 && i < 60 ? [w.slice(0, i), w.slice(i + 1).trim()] : [w || 'waiting for a coin that clears every check', '']; };
function HuntLine({ why, ready, same }) {
  const [head, rest] = same ? [`same blocker as seat ${same}`, ''] : huntSplit(why);   // one blocker is read once, not four times
  return <div className={`ack-hunt ${ready ? 'is-ready' : ''}`} data-tip={why || ''}><span className="ack-radar" aria-hidden="true"><i /><b /></span>
    <p><b>{ready ? `${ready} READY · ` : ''}{head}</b>{rest ? <small>{rest}</small> : null}</p></div>;
}
// 🎨 the chart's scene, picked right here (ONE choice for every chart on the site — lib/chartBg); every scene tints with the live tick
function ThemePick() {
  const v = useChartBg();
  return <select className="ack-theme" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart theme" data-testid="ack-theme" data-tip="Chart theme — every scene breathes green / red with each real tick">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
// ✋ REAPER ASKS (owner, 2026-10-15: "if I adjust SL / TP they respect it or give me a reason to approve"): on a coin with YOUR line, a soft
// exit waits here with its reason — ✅ approve = it sells on the next tick · ✋ keep my line = that rule is quiet 10 min. Your answers are graded.
export function asksOf(o) { return (o?.positions || []).filter(p => p.ask).map(p => ({ mint: p.mint, symbol: p.symbol || p.sym, ...p.ask })); }
export function askRecWord(r) {
  if (!r) return null; const [kn, kr] = r.kept || [0, 0]; const [an, ar] = r.approved || [0, 0];
  return kn || an ? `your answers: kept your line ${kn}× (${kr} right) · approved ${an}× (${ar} right) — judged 15 min later` : null;
}
function ReaperAsks({ o, call, isOwner, reload }) {
  const [busy, setBusy] = useState(null); const asks = asksOf(o); const rec = askRecWord(o?.askRec);
  if (!asks.length && !rec) return null;
  const answer = async (a, ok) => { setBusy(a.mint); try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ reaperAsk: { mint: a.mint, ok } }) }); reload?.(); } catch (e) { reload?.(); /* the question had closed */ } finally { setBusy(null); } };
  return <div className="ack-asks" data-testid="ack-asks">
    {asks.map(a => <div key={a.mint} className="ack-ask" data-testid={`ack-ask-${a.mint}`}>
      <span><b>☠ Reaper asks · ${a.symbol}</b><small>{a.name} at {pc(a.pct)} — {a.why}</small></span>
      <button type="button" className="m-btn" disabled={!isOwner || busy === a.mint} onClick={() => answer(a, true)} data-testid={`ack-ask-ok-${a.mint}`}>✅ Approve</button>
      <button type="button" className="m-btn m-go" disabled={!isOwner || busy === a.mint} onClick={() => answer(a, false)} data-testid={`ack-ask-keep-${a.mint}`}>✋ Keep my line</button></div>)}
    {rec ? <small className="ack-askrec" data-testid="ack-ask-rec">{rec}</small> : null}</div>;
}

// ✋ / 👍 ONE CLICK ON A SEAT (owner, 2026-10-17: "suggest to the agents and they learn — one-click hold or good entry"): Reaper holds the coin's
// soft exits 30 min (stops, rug, −45%, the take still act), it lands in the OSSY × G4 chat, and it is graded 30 min later into the record the
// agents and the models read. Spans with role=button: the seat card itself is a button.
export function SeatHints({ s, call }) {
  const [on, setOn] = useState(null); const [busy, setBusy] = useState(false);
  if (!call || !s?.mint) return null;
  const send = async (kind, e) => { e.stopPropagation(); e.preventDefault(); if (busy) return; setBusy(true);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ seatHint: { mint: s.mint, kind } }) }); setOn(kind === 'clear' ? null : kind); }
    catch (er) { window.dispatchEvent(new CustomEvent('feeless:toast', { detail: String(er?.message || er) })); } finally { setBusy(false); } };
  const btn = (kind, label, tip) => <span role="button" tabIndex={0} className={`ack-hint ${on === kind ? 'is-on' : ''}`} aria-pressed={on === kind} data-tip={tip} data-testid={`ack-hint-${kind}-${s.seat}`}
    onClick={e => send(on === kind ? 'clear' : kind, e)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') send(on === kind ? 'clear' : kind, e); }}>{label}</span>;
  return <span className="ack-hints" data-testid={`ack-hints-${s.seat}`}>{btn('hold', '✋ Hold', 'Reaper holds its soft exits 30 min — only stops, a rug, −45% or the take sell it. Graded 30 min later.')}
    {btn('good', '👍 Good entry', 'Tell the agents + OSSY / G4 this is a good entry: held 30 min like Hold, filed as a lesson, graded 30 min later.')}</span>;
}

function SeatCard({ s, on, onPick, readyN, same, call }) {
  const st = seatState(s, readyN);
  if (s.open) return <div className={`ack-seat is-open ${on ? 'is-on' : ''}`} data-testid={`ack-seat-${s.seat}`}>
    <header><small>SEAT {s.seat}{s.kind === 'g4' ? <i className="ack-g4tag" data-tip={`${s.model || 'the model'}'s seat: it decides — the agents only argue`}>🧠 {s.model || '…'}</i> : null}</small><i className={`ack-badge ${STATE_CLS[st]}`} data-testid={`ack-seat-state-${s.seat}`}>{st}</i></header>
    <HuntLine why={s.why} ready={readyN} same={same} />
    {(s.refused || []).length ? <ul className="ack-refused" data-testid={`ack-seat-refused-${s.seat}`}>{s.refused.map(r => <li key={`${r.symbol}-${r.at}`} data-tip={`${r.by === 'keeper' ? "the keeper's own buy check" : 'the seat pre-check'} · ${ago(r.at)} ago`}><b>${r.symbol}</b><span>{r.why}</span></li>)}</ul> : null}
    {(s.tapeWait || []).length ? <ul className="ack-refused is-tape" data-testid={`ack-seat-tape-${s.seat}`}>{s.tapeWait.map(r => <li key={r.symbol} data-tip="🌊 the live tape held this READY coin back this tick — it is re-read on the next one"><b>🌊 ${r.symbol}</b><span>{r.why}</span></li>)}</ul> : null}</div>;
  const last = s.last; const [ic, nm] = TAPE_AGENT[last?.agent] || ['', '']; const rug = rugMark(s);
  return <button type="button" className={`ack-seat ${on ? 'is-on' : ''} ${s.kind === 'g4' ? 'is-g4' : ''} ${s.pct > 0 ? 'is-up' : s.pct < 0 ? 'is-dn' : ''}`} onClick={() => onPick(s.mint)} aria-pressed={on} data-testid={`ack-seat-${s.seat}`}
    data-tip={`${s.tag || s.kind}${s.rule ? ` · Reaper ${s.rule}` : ''}${s.why ? ` — ${s.why}` : ''}`}>
    <header><small>SEAT {s.seat}{s.kind === 'g4' ? <i className="ack-g4tag" data-testid={`ack-seat-model-${s.seat}`}>🧠 {s.model || '…'}</i> : null}{rug ? <i className={`ack-rugdot is-${rug.level}`} data-tip={`${rug.level === 'bad' ? '🔴 RUG RISK' : '🟡 POOL THINNING'} — ${rug.why}`} aria-label={rug.level === 'bad' ? 'rug risk' : 'pool thinning'} data-testid={`ack-seat-rug-${s.seat}`} /> : null}</small><i className={`ack-badge ${STATE_CLS[st]}`} data-testid={`ack-seat-state-${s.seat}`}>{st}</i></header>
    <p className="ack-coin"><b>${s.symbol}<CopyCa mint={s.mint} sym={s.symbol} testid={`ack-seat-ca-${s.seat}`} /><GermChip mint={s.mint} compact /></b><span className="ack-pnl"><LiveNum v={s.pct} fmt={x => pc(x)} testid={`ack-seat-pct-${s.seat}`} /><LiveNum v={s.pnlUsd} fmt={signed} cls={`ack-usd ${tone(s.pnlUsd)}`} testid={`ack-seat-usd-${s.seat}`} /></span></p>
    <div className="ack-seatmid"><dl className="ack-kv">
      <dt>ENTRY MC</dt><dd>{mcWord(s.entryMc)}</dd><dt>AGE</dt><dd>{mins(s.ageMin)}</dd>
      <dt>NOW MC</dt><dd><LiveNum v={s.mc} fmt={mcWord} cls="" testid={`ack-seat-mc-${s.seat}`} /></dd><dt>HELD</dt><dd>{mins(s.heldMin)}</dd>
      <dt>PUT IN</dt><dd data-tip={`worth now ${money(s.usd)}`}>{s.usd != null && s.pnlUsd != null ? money(s.usd - s.pnlUsd) : money(s.usd)}</dd><dt>REALIZED</dt><dd>{s.realized == null ? '—' : signed(s.realized)}</dd></dl>
      <Spark path={s.path} /></div>
    <SeatBar s={s} />
    <SeatFlow s={s} />
    <p className="ack-now" data-testid={`ack-seat-now-${s.seat}`}><span>☠ Reaper · {s.reaper || '—'}{s.rule ? ` · ${s.rule}` : ''}<ExitChips s={s} /></span><small>next review {secs(s.nextReview)}</small></p>
    <SeatStudy s={s} />
    <SeatHints s={s} call={call} />
    <footer data-testid={`ack-seat-last-${s.seat}`}>{last ? <><span style={{ '--ag': AG[last.agent] || 'var(--m-accent)' }}>{ic} {nm} · {last.action}</span><small>{ago(last.at)} ago</small></> : <span className="m-dim">no decision line yet</span>}</footer>
  </button>;
}

// 💹 THE LIVE TRADE HUD (owner, 2026-10-12: "the live pnl tracker can be way more meta"): live P&L % and $ glide to every real tick (the
// shared 3s price poller — no request of its own) and flash its direction; one bar from the stop to the take carries now, the PEAK it
// reached, the worst it saw, and the trail line once Reaper armed it; the held clock ticks; Reaper's ruling + its next review. Every
// number is the position's own record or the live price.
function useDir(v) {
  const prev = useRef(null); const [f, setF] = useState({ dir: 0, n: 0 });
  useEffect(() => { const d = tickDir(prev.current, v); prev.current = v; if (d) setF(x => ({ dir: d, n: x.n + 1 })); }, [v]);
  return f;
}
const pctW = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0)}%`);
function Rail({ b, mini }) {
  const up = b.at >= b.zero;
  return <span className={`thd-rail ${mini ? 'is-mini' : ''}`}>
    <span className="thd-fill is-up" style={{ left: `${b.zero * 100}%`, width: `${(1 - b.zero) * 100}%`, transform: `scaleX(${up && b.zero < 1 ? (b.at - b.zero) / (1 - b.zero) : 0})` }} />
    <span className="thd-fill is-dn" style={{ left: 0, width: `${b.zero * 100}%`, transform: `scaleX(${!up && b.zero > 0 ? (b.zero - b.at) / b.zero : 0})` }} />
    <u className="thd-zero" style={{ left: `${b.zero * 100}%` }} />
    {b.stopAt != null ? <s className="thd-line is-stop" style={{ left: `${b.stopAt * 100}%` }} /> : null}
    {b.takeAt != null ? <s className="thd-line is-take" style={{ left: `${b.takeAt * 100}%` }} /> : null}
    {b.trailAt != null ? <s className="thd-line is-trail" style={{ left: `${b.trailAt * 100}%` }} /> : b.armAt != null && !mini ? <s className="thd-line is-arm" style={{ left: `${b.armAt * 100}%` }} /> : null}
    {b.peak > b.pct + 0.5 ? <em className="thd-peak" style={{ left: `${b.peakAt * 100}%` }} /> : null}
    <i className="thd-now" style={{ transform: `translateX(${(b.at * 100).toFixed(2)}cqw)` }} /></span>;
}
// 🌊 the seat's buy / sell vital — the same reading Reaper rules on (R4f sellers took over · R4c buying climax · a tighter stop on a red seat)
export function SeatFlow({ s }) {
  const f = flowBar(s.flow);
  if (!f) return null;
  return <span className={`thd-flow ${f.tone}`} data-testid={`ack-seat-flow-${s.seat}`} data-state={f.state} data-tip={`🌊 last 90s of real swaps — ${f.why}. Reaper reads this: sellers on a green seat = banked, on a red seat = a tighter stop.`}>
    <b>🌊 {f.word}</b><span className="thd-flowbar"><i style={{ transform: `scaleX(${f.buy.toFixed(3)})` }} /></span><small>{f.line}</small></span>;
}
export function SeatBar({ s }) {
  const b = tradeBar({ entry: s.entry, stop: s.stop, take: s.take, mfe: s.peak, trailAt: s.trailAt, armAt: s.armAt }, s.px);
  if (!b) return null;
  return <span className="thd-seat" data-testid={`ack-seat-bar-${s.seat}`} data-tip={`${b.hasStop ? `stop ${pctW(b.stop)}` : 'no stop line'} · now ${pctW(b.pct)} · peak ${pctW(b.peak)}${b.trail != null ? ` · trail banks under ${pctW(b.trail)}` : ''} · ${b.hasTake ? `take ${pctW(b.take)}` : 'no take line'}`}>
    <Rail b={b} mini /></span>;
}
function TradeHud({ pos, m }) {
  const now = useTick(1000); const fl = useDir(m?.price);
  const b = tradeBar(pos, m?.price); if (!b) return null;
  const k = m?.mc && m?.price ? m.mc / m.price : null;
  const usdNow = Number(pos.usd) > 0 && Number(pos.px) > 0 && Number(m?.price) > 0 ? Number(pos.usd) * Number(m.price) / Number(pos.px) : Number(pos.usd) || null;
  const pnlUsd = usdNow != null && b.pct > -100 ? usdNow - usdNow / (1 + b.pct / 100) : null;
  const heldS = Number(pos.since) > 0 ? now / 1000 - Number(pos.since) : Number(pos.heldMin) * 60;
  const heldW = !(heldS >= 0) ? '—' : heldS < 3600 ? `${Math.floor(heldS / 60)}m ${String(Math.floor(heldS % 60)).padStart(2, '0')}s` : `${(heldS / 3600).toFixed(1)}h`;
  return <div className={`ack-trade thd ${b.pct >= 0 ? 'is-up' : 'is-dn'}`} data-testid="ack-trade">
    <span className="thd-pnl"><small>LIVE P&amp;L</small><LiveNum v={b.pct} fmt={x => pc(x)} testid="ack-trade-pct" />
      <LiveNum v={pnlUsd} fmt={signed} cls={`thd-usd ${tone(pnlUsd)}`} testid="ack-trade-usd" />
      <i key={fl.n} className={`thd-flash ${fl.dir > 0 ? 'is-up' : fl.dir < 0 ? 'is-dn' : ''}`} aria-hidden /></span>
    <span className="thd-bar" data-tip={`${b.hasStop ? `stop ${pctW(b.stop)}` : 'no stop line'} ← now ${pctW(b.pct)} → ${b.hasTake ? `take ${pctW(b.take)}` : 'no take line'} · peak ${pctW(b.peak)} · worst ${pctW(b.low)}${b.trail != null ? ` · trail banks under ${pctW(b.trail)}` : b.arm != null ? ` · trail arms at ${pctW(b.arm)}` : ''}`}>
      <Rail b={b} />
      <span className="thd-legend"><small className="is-stop">{b.hasStop ? `STOP ${pctW(b.stop)}` : 'NO STOP'}</small>
        <small className="is-peak" data-testid="ack-trade-peak">PEAK {pctW(b.peak)}{b.giveBack > 0.5 ? ` · gave back ${b.giveBack.toFixed(1)}` : ''}</small>
        {b.trail != null ? <small className="is-trail">TRAIL {pctW(b.trail)}</small> : null}
        <small className="is-take">{b.hasTake ? `TAKE ${pctW(b.take)}${b.toTake > 0 ? ` · ${b.toTake.toFixed(1)} to go` : ''}` : 'NO TAKE'}</small></span></span>
    <span className="thd-kv" data-tip={`entry → now: ${k ? mcWord(Number(pos.entry) * k) : priceFmt(pos.entry)} → ${k ? mcWord(m.mc) : priceFmt(m?.price)}`}><span><small>HELD</small><b data-testid="ack-trade-held">{heldW}</b></span>
      <span data-tip={`☠ Reaper ${pos.decision || pos.state || 'HOLD'}${pos.rule ? ` · ${pos.rule}` : ''}${pos.nextReview != null ? ` · next review ${secs(pos.nextReview)}` : ''}`}><small>☠ REAPER</small><b className={`thd-dec ${/EXIT|TAKE/.test(pos.decision || '') ? 'is-bad' : /PROTECT/.test(pos.decision || '') ? 'is-good' : ''}`}>{pos.decision || pos.state || 'HOLD'}</b><ExitChips s={pos} mini /></span></span></div>;
}

// ── 📈 the chart: market cap, always ──────────────────────────────────────────────────────────────────────────────────────────────
export const IVS = [['1m', '1m'], ['5m', '5m'], ['15m', '15m']];
// ⚡ LIVE DESK = three views, one on screen (owner: "organize all tabs clean, not scroll heavy"); every view stays mounted, the pick is remembered
const LIVE_VIEWS = [['duo', '🔁 OSSY ⚔ G4'], ['matrix', '🧩 Ten agents'], ['tape', '🎬 Decisions']];
function LiveDesk({ duo, matrix, tape, tapeN }) {
  const [v, setV] = useRemembered('feeless.ack.livedesk', 'duo');
  const views = { duo, matrix, tape };
  return <div className="ack-livedesk"><span className="m-seg ack-lvseg" role="tablist" aria-label="Live desk view">{LIVE_VIEWS.map(([k, w]) =>
    <button key={k} type="button" role="tab" aria-selected={v === k} className={v === k ? 'active' : ''} onClick={() => setV(k)} data-testid={`ack-lv-${k}`}>{w}{k === 'tape' && tapeN ? <small> {tapeN}</small> : null}</button>)}</span>
    {LIVE_VIEWS.map(([k]) => <div key={k} className="ack-lvpane" hidden={v !== k}>{views[k]}</div>)}</div>;
}

// 📍 OSSY / G4 ON THE CHART (owner, 2026-10-16: Pump-style pins + cards, not a box): their calls on THIS coin → pins at the call's candle + cap
// 📣 the Agents chart's comments (owner, 2026-10-17): ONLY Reaper, OSSY and G4 on THIS coin — a run of the same word = one pin, newest CHART_PINS
const PIN_WHO = new Set(['REAPER', 'OSSY', 'G4', 'YOU']);
export const CHART_PINS = 60;   // 📜 the coin's WHOLE comment history the server kept (owner, 2026-10-17) — a run of the same word folds into one pin "×N"
export function chartCalls(rows, mint, liveCap) {
  const capOf = r => (Number(r.cap) > 0 ? Number(r.cap) : Number(liveCap) > 0 ? Number(liveCap) : 0);   // a line with no cap of its own pins at the coin's live cap (history was hidden)
  const keep = [];
  (rows || []).filter(r => r.mint && r.mint === mint && capOf(r) > 0 && PIN_WHO.has(String(r.model || '').toUpperCase())).forEach(r => {
    const p = keep[keep.length - 1];
    if (p && p.model === r.model && (p.view || p.action) === (r.view || r.action)) { p.rep = (p.rep || 1) + 1; return; }
    keep.push({ ...r });
  });
  return keep.slice(-CHART_PINS).map((r, i) => { const who = String(r.model).toUpperCase(); const reaper = who === 'REAPER'; const you = who === 'YOU';
    return { id: `${r.at}-${i}`, at: r.at, cap: capOf(r), who: reaper ? 'Reaper' : you ? 'You' : who, kind: reaper ? 'agent' : you ? 'user' : r.talk ? 'talk' : 'ai', rep: r.rep,
      action: reaper ? String(r.view || 'NOTE').toUpperCase() : r.talk ? (r.view ? String(r.view).toUpperCase() : 'TALK') : r.action, text: r.talk && !reaper && !you ? `${r.view || ''} — ${r.why || ''}` : r.why, pct: r.pct,
      icon: who === 'OSSY' ? 'OS' : who === 'G4' ? 'G4' : you ? 'YOU' : undefined, img: avatarOf(who) || undefined }; });
}

// 🤖 the agents' REAL moves on this coin (the marker rail: Trigger entered · Courier filled · Reaper ruled) as small avatar pins — owner, 2026-10-17:
// "agent trades and thoughts were showing on chart, what happened?" — they stay, beside Reaper / OSSY / G4's lines, newest AGENT_PINS
const VITAL_PIN = new Set(['trigger', 'courier', 'reaper']);
export const AGENT_PINS = 5;
export function agentPins(markers) {
  return (markers || []).filter(k => Number(k.mc) > 0 && VITAL_PIN.has(k.agent) && avatarOf(k.agent)).slice(-AGENT_PINS)
    .map(k => ({ id: `ag-${k.id}`, at: k.at, cap: k.mc, who: k.agent[0].toUpperCase() + k.agent.slice(1), kind: 'agent', action: String(k.action || '').toUpperCase(), text: k.why, img: avatarOf(k.agent) }));
}

function CockpitChart({ m, iv, setIv, pos, cand, markers, onAgent, tid, call, isOwner, duo }) {
  const calls = useMemo(() => [...agentPins(markers), ...chartCalls(duo?.chart, m?.mint, m?.mc)], [duo?.chart, m?.mint, m?.mc, markers]);   // 🐋 wallet bubbles come from PriceChart itself (every chart)
  const pair = useMemo(() => (m?.pair ? { chainId: 'solana', pairAddress: m.pair, baseToken: { address: m.mint, symbol: m.symbol }, priceUsd: m.price, marketCap: m.mc } : null), [m?.pair, m?.mint, m?.symbol, m?.price, m?.mc]);
  // ✋ YOUR LINES on an agent seat: its stop + take are grabbable on the chart; a drop asks, saves that coin's own TP / SL, Reaper obeys it,
  // and the position is filed as "your hand" so the record shows whether your adjustments helped
  const grab = !!(pos && isOwner && tid && m?.pair && Number(pos.entry) > 0);
  const fuse = useMemo(() => ({ lines: m?.lines || [], ...(grab ? { tpl: tid, src: 'cockpit', pairAddress: m.pair, symbol: m.symbol, entry: Number(pos.entry),
    slPct: Math.round(Math.abs(Number(pos.stop) || 0)) || null, tpPct: Math.round(Number(pos.take) || 0) || null, ghost: pos.takeSource === 'yours' } : {}) }), [m?.lines, grab, tid, m?.pair, m?.symbol, pos?.entry, pos?.stop, pos?.take, pos?.takeSource]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!grab) return undefined;
    const on = e => { const dd = e.detail || {}; if (dd.src !== 'cockpit' || !['stop', 'tp'].includes(dd.kind)) return;
      const o = grabOrder(dd); if (!o || !window.confirm(`${o.ask} The agents obey your line on this seat; your adjustments are graded apart ("did your hand help?").`)) return;
      call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(o.body) }).then(() => { toast.success(o.ok); window.dispatchEvent(new CustomEvent('feeless:fuse-level-done', { detail: dd })); hubLoad(); })
        .catch(err => toast.error(err.message)); };
    window.addEventListener('feeless:fuse-level', on); return () => window.removeEventListener('feeless:fuse-level', on);
  }, [grab, call]);
  // ON the plot: only confirmed FILLS, as small arrows at the real fill price (no letters, no decision blocks over the candles);
  // every decision stays readable in the rail under the chart
  const chartMarkers = useMemo(() => markers.filter(k => k.text === 'B' || (k.text === 'X' && k.agent === 'courier')).map(({ id, agent, action, why, mc, at, text, ...k }) => ({ ...k, text: '' })), [markers]);
  // 🟢 the seat's own trade on the candles: a BUY chip at its entry + a P&L tag riding the live candle (the strip above carries the numbers)
  const seatPnl = useMemo(() => { const e = Number(pos?.entry); const u = Number(pos?.usd); const p = Number(pos?.pct);
    if (!(e > 0) || !(u > 0) || !Number.isFinite(p) || p <= -100) return false;
    const cost = u / (1 + p / 100); return { label: 'SEAT', tagOnly: true, pos: { tokensHeld: cost / e, avgEntry: e, investedPoolUsd: cost, at: pos?.at || pos?.since || null } }; }, [pos?.entry, pos?.usd, pos?.pct, pos?.at, pos?.since]);
  if (!m) return <div className="ack-chart is-empty" data-testid="ack-chart"><p className="ack-nil">No coin on the desk yet — the chart opens on the first seat or READY candidate.</p></div>;
  const vol = cand?.vol5m; const liq = pos?.liq ?? cand?.liq;
  return <div className="ack-chart" data-testid="ack-chart">
    <header className="ack-chead"><b className="ack-csym">${m.symbol || '—'}</b>
      {pos ? <LiveNum v={pos.pct} fmt={x => pc(x)} testid="ack-chart-pct" /> : null}
      <span className="ack-cstat ack-cmc" data-tip={`Market cap = live price × the supply the kernel resolved · price ${priceFmt(m.price)} · supply ${m.supply ? `${supplyWord(m.supply)}${m.supplySrc ? ` (${m.supplySrc})` : ''}` : 'UNKNOWN'}`}><small>MC</small><LiveNum v={m.mc} fmt={mcWord} cls="" testid="ack-chart-mc" /></span>
      <span className="ack-cstat"><small>5M VOL</small><em>{mcWord(vol)}</em></span>
      <span className="ack-cstat"><small>LIQ</small><em>{mcWord(liq)}</em></span>
      <span className="ack-ctools"><span className="m-seg ack-iv" role="group" aria-label="Candle size">{IVS.map(([k, l]) => <button key={k} type="button" className={iv === k ? 'active' : ''} onClick={() => setIv(k)} data-testid={`ack-iv-${k}`}>{l}</button>)}</span>
        <button type="button" className="m-btn ack-wr" onClick={() => pair && window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: pair }))} data-testid="ack-warroom">⚔ war room</button>
        <ThemePick /></span></header>
    {!m.pair ? <p className="ack-nil" data-testid="ack-nopool">No pool for this coin yet — nothing to chart.</p>
      : !m.mc ? <p className="ack-nil is-warn" data-testid="ack-mc-unavailable"><b>MC UNAVAILABLE</b> — no supply is known for this coin yet (no token supply, not a launchpad mint, no live cap). The raw price is never charted in its place.</p>
        : <div className="ack-plot">{pos ? <TradeHud pos={pos} m={m} /> : null}<Suspense fallback={<p className="ack-nil">loading the live chart…</p>}>
          <PriceChartLazy key={`${m.pair}-${iv}`} pair={pair} interval={iv} metric="marketCap" showVolume markers={chartMarkers} fuse={fuse} pnl={seatPnl} callouts={calls} /></Suspense></div>}
    <div className="ack-mrail" data-testid="ack-mrail"><span className="ack-mkey" data-tip="▲ real buy · ▼ real sell on the chart; the chips are the newest decisions on this coin"><i className="ack-ml is-B">▲</i><i className="ack-ml is-X">▼</i></span>
      {markers.length ? <span className="ack-mlist">{markers.slice(-6).reverse().map(k => <button key={k.id} type="button" className={`ack-ml is-${k.text}`} onClick={() => onAgent(k.agent)}
        data-tip={`${new Date(k.at * 1000).toLocaleTimeString()} · ${TAPE_AGENT[k.agent]?.[1] || k.agent} · ${k.action}${k.why ? ` — ${k.why}` : ''}${k.mc ? ` · MC ${mcWord(k.mc)}` : ''} · ${ago(k.at)} ago`}
        data-testid={`ack-mk-${k.id}`}>{TAPE_AGENT[k.agent]?.[1] || k.agent} {String(k.action || '').toLowerCase()}<small>{ago(k.at)}</small></button>)}</span> : <small className="ack-mnone">no real event on this coin yet</small>}</div>
  </div>;
}

// ── 📜 the live decisions strip ─────────────────────────────────────────────────────────────────────────────────────────────────
function TapeRow({ r, onPick, card, pulse }) {
  const [ic, nm] = TAPE_AGENT[r.agent] || ['•', r.agent];
  const Tag = card ? 'button' : 'li';
  const body = <><small className="ack-tage">{ago(r.at)} ago</small><b style={{ '--ag': AG[r.agent] || 'var(--m-accent)' }}>{ic} {nm}</b><em className={`ack-tact ${tapeTone(r)}`}>{r.action}</em>
    {r.n > 1 ? <span className="ack-tsym ack-tgrp" data-testid={`ack-tgrp-${r.id}`}>×{r.n} · {r.syms.slice(0, 5).map(x => `$${x}`).join(' ')}{r.syms.length > 5 ? ' …' : ''}</span>
      : r.symbol ? <span className="ack-tsym">${r.symbol}{r.mc ? <small> · {mcWord(r.mc)} MC</small> : null}</span> : null}<span className="ack-twhy">{r.why}</span></>;
  return card ? <Tag type="button" className={`ack-tcard ${tapeTone(r)} ${pulse ? 'is-new' : ''}`} onClick={() => onPick(r)} data-tip={r.why || undefined} style={{ '--ag': AG[r.agent] || 'var(--m-accent)' }} data-testid={`ack-tape-${r.id}`}>{body}</Tag>
    : <li className={`ack-trow ${tapeTone(r)}`}><button type="button" onClick={() => onPick(r)} data-testid={`ack-tline-${r.id}`}>{body}</button></li>;
}
function DecisionTape({ rows, agent, setAgent, onPick, fresh }) {
  const [all, setAll] = useState(false);
  const list = groupTape(tapeOf(rows, { agent, n: all ? 120 : 24 })).slice(0, all ? 120 : 6);   // repeats fold into one line
  return <section className="ack-tape" data-testid="ack-tape">
    <header data-tip="the latest real agent actions across all seats — a line exists only when something real changed"><b>⚡ LIVE DECISIONS</b><small>{agent ? `${TAPE_AGENT[agent]?.[1] || agent} only · ` : ''}latest real agent actions across all seats — a line exists only when something real changed</small>
      {agent ? <button type="button" className="m-btn" onClick={() => setAgent(null)} data-testid="ack-tape-all-agents">✕ all agents</button> : null}
      <button type="button" className="m-btn ack-more" onClick={() => setAll(!all)} aria-expanded={all} data-testid="ack-tape-more">{all ? 'Show newest' : `View all decisions (${tapeOf(rows, { agent, n: 120 }).length}) →`}</button></header>
    {!list.length ? <p className="ack-nil" data-testid="ack-tape-empty">No decision lines yet — the tape writes only when an opinion, an order or a ruling really changes (a quiet market is a quiet tape).</p>
      : all ? <ol className="ack-tlist">{list.map(r => <TapeRow key={r.id} r={r} onPick={onPick} />)}</ol>
        : <div className="ack-tcards">{list.map(r => <TapeRow key={r.id} r={r} onPick={onPick} card pulse={fresh.has(r.id)} />)}</div>}
  </section>;
}

// ── 🧠 the agent decision panel ──────────────────────────────────────────────────────────────────────────────────────────────────
export const PANEL_TABS = [['live', '⚡ Live'], ['ai', '🧠 AI'], ['inputs', '🧾 In'], ['seats', '🪑 Seats'], ['review', '📝 Rev'], ['trace', '🧵 Trace']];
// the agent that answers for this coin right now: Reaper for a held coin, else the first desk standing in its way, else Trigger / Sherlock
export function leadAgent(dec) {
  if (!dec) return 'tally';
  if (dec.kind === 'position') return 'reaper';
  const k = dec.kernel; if (!k) return 'sherlock';
  if (k.devil?.verdict === 'veto') return 'devil';
  if (!k.courier) return 'courier';
  if (k.trigger === 'ENTER') return dec.state === 'go' ? 'warden' : 'trigger';
  if ((k.unknown || []).length) return 'sherlock';
  return 'trigger';
}
const FRESH_CLS = { LIVE: 'is-live', FRESH: 'is-fresh', PARTIAL: 'is-part', STALE: 'is-stale', PENDING: 'is-pend', UNAVAILABLE: 'is-na' };
function Tile({ l, v, sub, cls }) { return <span className="ack-ptile" data-tip={sub || undefined}><small>{l}</small><b className={cls || ''}>{v}</b>{sub ? <u>{sub}</u> : null}</span>; }
const badgeOf = w => (/VETO|EXIT|BLOCK/.test(w) ? 'is-bad' : /WARN/.test(w) ? 'is-warn' : /ENTER|READY|PROTECT|PASS|FILLED|SIZE|SCAN|CONFIRMED/.test(w) ? 'is-good' : 'is-hold');

// 🧠 the model's vital intel on THIS coin — its own AI-store subscriber: an AI answer repaints this card only
export function AiNote({ o, mint, agent, onOpen }) {
  const ai = useAi(o?.ai); const note = ai?.notes?.[mint];
  const n = note ? (note[agent] ? { ...note[agent], role: agent } : Object.entries(note).map(([role, v]) => ({ ...v, role })).sort((a, b) => (b.at || 0) - (a.at || 0))[0]) : null;
  if (!n?.advice) return <button type="button" className="ack-ai-note is-btn is-none" onClick={onOpen} data-testid="ack-ai-none"><i className="ack-src">AI</i>the model has not been asked about this coin — ask it →</button>;
  return <><button type="button" className="ack-ai-note is-btn" onClick={onOpen} data-testid="ack-ai-note" data-tip={`advisory only — ${n.advice.stance} (confidence ${Number(n.advice.confidence_delta || 0) >= 0 ? '+' : ''}${Number(n.advice.confidence_delta || 0).toFixed(2)}) · tap = every model decision`}>
    <i className="ack-src">{n.label || n.source}</i><em className={`ack-ai-stance cai-stance ${STANCE_TONE[n.advice.stance] || 'is-hold'}`}>{n.advice.stance}</em>{n.role} · {n.advice.summary}</button>
    <AiIntel a={n.advice} testid="ack-ai-intel" /></>;
}

function DecisionPanel({ o, dec, pos, cand, mint, seats, readyN, agent, setAgent, tab, setTab, pulse, call, isOwner, onPick, mcNow, onAi }) {
  const tr = useMemo(() => traceOf(o, mint), [o, mint]);
  const names = Object.fromEntries((o?.agents || []).map(a => [a.key, `${a.icon} ${a.name}`]));
  const line = tr?.lines.find(l => l.agent === agent);
  const [word, why] = activityOf(agent, o);
  const live = o?.livePx?.[mint];
  const verdictWord = line?.word || word;
  return <aside className="ack-panel" data-testid="ack-panel">
    <header><b>🧠 DECISION</b><i className="ack-livechip">● {dec?.symbol ? `$${dec.symbol}` : 'no coin'}</i><CopyCa mint={mint} sym={dec?.symbol} testid="ack-dec-ca" /><GermChip mint={mint} />
      <select className="m-input ack-agsel" value={agent} onChange={e => setAgent(e.target.value)} aria-label="Agent" data-testid="ack-agent-sel">
        {CHAIN.map(a => <option key={a} value={a}>{names[a] || a}</option>)}</select></header>
    <div className="m-seg ack-ptabs" role="tablist" aria-label="Decision panel">{PANEL_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`ack-ptab-${k}`}><TabChip label={l} n={k === 'seats' && (seats || []).length ? `${(seats || []).filter(z => !z.open).length}/${seats.length}` : k === 'trace' ? (tr?.lines || []).length || null : null}
      meter={k === 'seats' && (seats || []).length ? (seats || []).filter(z => !z.open).length / seats.length : null} /></button>)}</div>
    {tab === 'live' ? (!dec ? <p className="ack-nil">Pick a seat, a decision or a coin in the queue.</p> : <div className="ack-pbody" data-testid="ack-pane-live">
      <div className="ack-vpair">
        <span className={`ack-verdict ack-vcell ${badgeOf(verdictWord)}`} data-tip={`${line?.why || why || ''}${line?.at ? ` · ${ago(line.at)} ago` : ''}`}><small>{(names[agent] || agent).toUpperCase()}</small>
          <em key={verdictWord} className={`ack-badge ack-vpop ${badgeOf(verdictWord)}`} data-testid="ack-verdict">{verdictWord}</em><i key={`w-${verdictWord}`} className="ack-vwave" aria-hidden />
          <span className="ack-rule">{line?.why || why}{line?.at ? ` · ${ago(line.at)} ago` : ''}</span></span>
        <span className={`ack-verdict is-kernel ack-vcell ${badgeOf(String(dec.verdict || ''))}`} data-tip={dec.rule ? `${dec.rule}${dec.obeying ? ` · obeying ${dec.obeying}` : ''}` : undefined}><small>{dec.kind === 'position' ? 'RULING' : dec.kind === 'review' ? 'YOUR REVIEW' : 'STANDS'}</small>
          <b key={dec.verdict} className="ack-vpop" data-testid="ack-kernel-verdict">{dec.verdict || '—'}</b><i key={`w-${dec.verdict}`} className="ack-vwave" aria-hidden />
          {dec.rule ? <span className="ack-rule">{dec.rule}{dec.obeying ? ` · obeying ${dec.obeying}` : ''}</span> : null}{pos ? <ExitChips s={pos} /> : null}</span></div>
      {dec.kernel ? <div className="ack-rank" data-tip={`Over the buy line + every check passed = the agents buy. READY needs Trigger ENTER + inside the hard wall + execution healthy + rank ≥ ${READY_MIN}`}><small>SCORE · BUY LINE {READY_MIN}</small>
        <span className="ack-bar"><i style={{ transform: `scaleX(${rankFill(dec.kernel.rank)})` }} /><u /></span><em>{dec.kernel.rank ?? '—'}</em></div> : null}
      {cand || pos ? <VitalBoard c={cand || { mint, symbol: dec?.symbol }} pos={pos} rules={o?.teach?.rules} call={call} isOwner={isOwner} /> : null}
      {(dec.reasons || []).length ? <details className="ack-whyfold"><summary><b className="ack-sub">WHY · {dec.reasons.length}</b></summary><ul className="ack-why" data-testid="ack-why">{dec.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul></details> : null}
      <div className="ack-ptiles">
        <Tile l="CHART DATA" v={pos?.quality || pos?.data?.state || dec.chart?.quality || '—'} sub={pos?.data?.conf != null ? `${pos.data.conf}% data conf` : pos?.structure || null} />
        <Tile l="LAST READ" v={o?.cycle?.at ? ago(o.cycle.at) : '—'} sub={o?.cycle?.every ? `every ${Math.round(o.cycle.every)}s` : null} />
        <Tile l="DEVIL SAYS" v={dec.kernel ? devilOf(cand || {}).word : pos?.run || '—'} sub={dec.kernel ? 'Devil on this coin' : pos ? `stop ${pos.stop ?? '—'}%` : null}
          cls={dec.kernel?.devil?.verdict === 'veto' ? 'm-neg' : dec.kernel?.devil?.verdict === 'warn' ? 'ack-warn' : ''} />
        <Tile l="SEAT SIZE" v={pos ? money(pos.usd) : cand?.size != null ? `×${cand.size}` : '—'} sub={pos ? `Warden ×${pos.warden ?? '—'}` : cand?.sizeWhy || null} />
        <Tile l="NEXT STEP" v={pos ? (pos.roundAction || pos.decision || '—') : dec.verdict === 'READY' ? 'TAKE A SEAT' : cand?.trigger === 'ENTER' ? 'CLEAR THE WALL' : 'KEEP READING'} sub={pos?.obeying || null} />
        <Tile l="NEXT CHECK" v={pos ? secs(pos.nextReview) : secs(o?.cycle?.nextIn)} sub={pos ? "Reaper's review (the live chart acts sooner)" : 'next agent pass'} /></div>
      {agent === 'devil' && cand?.devilConf != null ? <p className="ack-fresh">Devil confidence ×{cand.devilConf} (a weight on the rank, never a block)</p> : null}
      <AiNote o={o} mint={mint} agent={agent} onOpen={() => setTab('ai')} />
    </div>) : null}
    {tab === 'ai' ? <div className="ack-pbody"><AiPane ai={o?.ai || null} lab={o?.lab || null} call={call} isOwner={isOwner} focus={mint} focusSym={dec?.symbol} onPick={onPick} onProviders={onAi} /></div> : null}
    {tab === 'inputs' ? <div className="ack-pbody" data-testid="ack-pane-inputs"><ul className="ack-inputs">{inputsOf({ c: cand, pos, live, mc: mcNow }).map(([l, w, s, what]) =>
      <li key={l} data-testid={`ack-in-${l.replace(/\W+/g, '-')}`}><span>{l}</span><i className={`ack-fw ${FRESH_CLS[w]}`}>{w}</i><small>{s == null ? '' : `${secs(s)} old · `}{what}</small></li>)}</ul></div> : null}
    {tab === 'seats' ? <div className="ack-pbody" data-testid="ack-pane-seats"><table className="ack-queue"><thead><tr><th>SEAT</th><th>COIN</th><th>STATE</th><th>AGENT</th><th>CHALLENGER</th><th>NEXT</th></tr></thead>
      <tbody>{seats.map(s => { const sb = (o?.seatBoard || []).find(b => b.seat === s.seat) || {};
        return <tr key={s.seat} onClick={() => s.mint && onPick(s.mint)} className={s.mint === mint ? 'is-on' : ''}><td>{s.seat}</td><td>{s.symbol ? `$${s.symbol}` : '—'}</td><td><em className={`ack-st ${STATE_CLS[seatState(s, readyN)]}`}>{seatState(s, readyN)}</em></td>
          <td>{s.open ? '⏱ Trigger · 🛡 Warden' : `☠ ${s.reaper || 'Reaper'}`}</td><td>{sb.challenger ? `$${sb.challenger}${sb.margin != null ? ` +${sb.margin}` : ''}` : '—'}</td><td>{s.open ? (s.why || '').slice(0, 40) : secs(s.nextReview)}</td></tr>; })}</tbody></table></div> : null}
    {tab === 'review' ? <div className="ack-pbody" data-testid="ack-pane-review"><OwnerReview o={o} call={call} isOwner={isOwner} onPick={onPick} focus={mint} compact /></div> : null}
    {tab === 'trace' ? <div className="ack-pbody" data-testid="ack-pane-trace">{!tr ? <p className="ack-nil">No coin selected.</p> : <ol className="ack-trace">
      {tr.lines.map((l, i) => <li key={l.agent} className={`${l.word ? '' : 'is-empty'} ${agent === l.agent ? 'is-on' : ''}`} style={{ '--ag': AG[l.agent] }} data-testid={`ack-tr-${l.agent}`}>
        <button type="button" onClick={() => setAgent(l.agent)}><b className={pulse[l.agent] ? 'is-pulse' : ''} key={pulse[l.agent] || 'x'}>{names[l.agent] || l.agent}</b>
          <em>{l.word || '— no line on this coin'}</em><small>{l.why || ''}{l.at ? ` · ${ago(l.at)} ago` : ''}{l.src ? ` · ${l.src}` : ''}</small></button>{i < tr.lines.length - 1 ? <i aria-hidden className="ack-flow">↓</i> : null}</li>)}
      {tr.final ? <li className="ack-final"><b>FINAL</b><em>{tr.final}</em><small>{tr.why}</small></li> : null}</ol>}</div> : null}
  </aside>;
}

// ── 🤖 the ten agents ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
// 🗳 a desk's own vote, drawn: the typical real % of the trades it said GO to vs the ones it doubted — a desk worth its vote has GO above DOUBT
function VoteBar({ st }) {
  const v = voteSplit(st); if (!v) return null;
  const w = x => `${Math.min(50, Math.abs(x || 0) * 2.5)}%`;
  return <span className={`ack-vote ${v.edge == null ? '' : v.edge > 0 ? 'is-good' : 'is-bad'}`} data-testid="ack-vote" data-tip={`Own vote on real money: said GO ${v.goN}× (typical ${v.go ?? '—'}%) · doubted ${v.doubtN}× (typical ${v.doubt ?? '—'}%)${v.edge != null ? ` · its GO is worth ${v.edge > 0 ? '+' : ''}${v.edge} pts over its doubt` : ''}`}>
    <i className={`is-go ${(v.go || 0) < 0 ? 'is-neg' : ''}`} style={{ width: w(v.go) }} /><i className={`is-doubt ${(v.doubt || 0) < 0 ? 'is-neg' : ''}`} style={{ width: w(v.doubt) }} /></span>;
}
function AgentMatrix({ o, gens, agent, setAgent, rows, pulse }) {
  const lastBy = useMemo(() => { const m = {}; (rows || []).forEach(r => { if (!m[r.agent] || r.id > m[r.agent].id) m[r.agent] = r; }); return m; }, [rows]);
  const ds = o?.deskStats || {}; const agents = o?.agents || []; const [filt, setFilt] = useState('all'); const perf = o?.performance?.agents || {};
  const cards = agents.map(a => { const g = gens.find(x => x.role === a.key); const [word, why] = activityOf(a.key, o); return { a, g, word, why, l: lastBy[a.key], st: ds[a.key] }; });
  const active = cards.filter(c => c.word !== 'WAIT'); const idle = cards.filter(c => c.word === 'WAIT');
  const shown = filt === 'active' ? active : filt === 'idle' ? idle : cards;
  const mr = measureRead(agents, ds);
  return <section className="ack-matrix" data-testid="ack-matrix"><header data-tip="the ten agents in chain order · live status · a packet runs into a desk when it acts · tap = focus the panel"><b>🤖 AGENT MATRIX</b><small>{agents.length} agents · live status · tap = focus the panel</small>
    {mr.unmeasured.length ? <span className="ack-unm" data-testid="ack-unmeasured" data-tip={`No real decision on record yet: ${mr.unmeasured.join(' · ')}`}>📏 {mr.unmeasured.length} unmeasured</span> : null}
    {mr.sameN > 2 ? <span className="ack-unm is-same" data-tip="These desks share one record: they are credited per TEAM decision, not for what each one changed">🔁 {mr.sameN} share one record</span> : null}
    <span className="m-seg ack-mfilt" role="group" aria-label="Agents">{[['all', 'ALL'], ['active', `ACTIVE ${active.length}`], ['idle', `IDLE ${idle.length}`]].map(([k, l]) => <button key={k} type="button" className={filt === k ? 'active' : ''} onClick={() => setFilt(k)} data-testid={`ack-mf-${k}`}>{l}</button>)}</span></header>
    <div className={`ack-agents ${filt === 'all' ? 'is-flow' : ''}`}>{shown.map(({ a, g, word, why, l, st }, i) => <button key={a.key} type="button" className={`ack-agent ${agent === a.key ? 'is-on' : ''} ${g?.status === 'PROBATION' ? 'is-prob' : ''}`} style={{ '--ag': AG[a.key] }} onClick={() => setAgent(a.key)} aria-pressed={agent === a.key}
        data-tip={`${a.job || ''} — ${why}${l ? ` · last line: ${l.action} ${l.symbol ? `$${l.symbol}` : ''} ${ago(l.at)} ago` : ''}`} data-testid={`ack-agent-${a.key}`}>
        {filt === 'all' && i > 0 ? <span className="ack-ain" key={`in-${pulse[a.key] || 'x'}`} aria-hidden><i /></span> : null}
        <span className={`ack-aname ${pulse[a.key] ? 'is-pulse' : ''}`} key={pulse[a.key] || 'x'}>{a.icon} {a.name}</span>
        {(perf[a.key]?.series || []).length > 1 ? <span className="ack-awork" data-tip={`work per pass: ${perf[a.key].last ?? '—'} ms now · ${perf[a.key].p50 ?? '—'} ms typical`}><Spark path={perf[a.key].series} w={72} h={14} /></span> : null}
        <small>{g ? `GEN ${g.generation} · ${g.status}` : '—'}</small>
        <small className="ack-acc" data-testid={`ack-rec-${a.key}`}>{recWord(st)}</small><VoteBar st={st} />
        <small className={`ack-anet ${tone(g?.netImpact)}`}>{g?.netImpact != null ? `net ${g.netImpact > 0 ? '+' : ''}${g.netImpact}%` : ''}</small>
        <em className="ack-aword">{word}</em><small className="ack-atgt">{l?.symbol ? `$${l.symbol}` : ''}</small><small className="ack-awhy">{why}</small></button>)}</div></section>;
}

// ── 👤 owner review + the review queue ──────────────────────────────────────────────────────────────────────────────────────────
export const OWNER_ACTS = [['review', '🔎 Review', 'The same ten agents read it on the next pass (30 min). Judged and shown — never bought from a review.'],
  ['track', '📌 Track', 'Kept on your watch list until you ignore it. Judged and shown — never bought from a track.'],
  ['arm', '🎯 Arm', 'Priority only: among coins the kernel has READY on its own rules, an armed one goes first. Arming never makes a coin READY — the wall, Trigger, Devil, the Warden, Courier and the keeper still decide.'],
  ['ignore', '✕ Ignore', 'Off your list.']];
function useOwnerAct(call, onPick) {
  const [busy, setBusy] = useState(false);
  const act = async (action, input) => {
    const v = String(input || '').trim(); if (!v || busy) return null;
    setBusy(true);
    try { const r = await call('/admin/agents', { method: 'POST', body: JSON.stringify({ owner: { input: v, action } }) });
      if (r?.owner?.list) hubApply({ kind: 'owner_update', data: r.owner.list });
      if (r?.owner?.mint && action !== 'ignore') onPick(r.owner.mint);
      toast.success({ review: '🔎 sent to the agents', track: '📌 tracking', arm: '🎯 armed — priority only', ignore: 'off your list' }[action]);
      return r;
    } catch (e) { toast.error(e.message); return null; } finally { setBusy(false); }
  };
  return [act, busy];
}
function OwnerReview({ o, call, isOwner, onPick, focus, compact }) {
  const [txt, setTxt] = useState(''); const [act, busy] = useOwnerAct(call, onPick);
  const own = o?.ownerReview || []; const ai = useAi(o?.ai)?.notes || {};
  const list = compact && focus ? own.filter(r => r.mint === focus) : own;
  return <div className="ack-owner" data-testid={compact ? 'ack-owner-pane' : 'ack-owner'}>
    {!compact ? <form className="ack-intake" onSubmit={e => { e.preventDefault(); act('review', txt).then(r => r && setTxt('')); }}>
      <b className="ack-sub">👤 OWNER REVIEW</b>
      <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} placeholder="Solana CA / mint, or a pump.fun / dexscreener / birdeye link" aria-label="Coin to review" disabled={!isOwner || busy} data-testid="ack-intake" spellCheck={false} />
      {OWNER_ACTS.filter(([k]) => k !== 'ignore').map(([k, l, tip]) => <button key={k} type={k === 'review' ? 'submit' : 'button'} className={`m-btn ${k === 'arm' ? 'is-arm' : ''}`} disabled={!isOwner || busy || !txt.trim()}
        onClick={k === 'review' ? undefined : () => act(k, txt).then(r => r && setTxt(''))} data-tip={tip} data-testid={`ack-act-${k}`}>{l}</button>)}
      <small className="ack-never">never buys — ARM is priority only</small></form>
      : focus ? <p className="ack-oacts is-row">{OWNER_ACTS.map(([k, l, tip]) => <button key={k} type="button" className={`m-btn ${k === 'arm' ? 'is-arm' : ''}`} disabled={!isOwner || busy} onClick={() => act(k, focus)} data-tip={tip} data-testid={`ack-pact-${k}`}>{l}</button>)}</p> : null}
    {list.length ? <ul className="ack-own-list" data-testid="ack-own-list">{list.map(r => { const n = ai[r.mint]?.owner; return <li key={r.mint} className={focus === r.mint ? 'is-on' : ''}>
      <button type="button" className="ack-orow" onClick={() => onPick(r.mint)} data-testid={`ack-own-${r.mint.slice(0, 6)}`}>
        <i className={`ack-mode is-${r.mode}`}>{r.mode?.toUpperCase()}</i><b>${r.symbol || `${r.mint.slice(0, 4)}…`}</b><em className={`ack-st is-${String(r.state || '').toLowerCase()}`}>{r.state}</em>
        <span>{r.mc == null ? 'MC —' : `${mcWord(r.mc)} MC`}{r.trigger?.state ? ` · ⏱ ${r.trigger.state}` : ''}{r.devil?.severity ? ` · ⚖ ${r.devil.severity.replace('_', ' ')}` : ''}</span>
        <small>{r.why}{(r.pending || []).length ? ` · pending: ${r.pending.join(', ')}` : ''}</small>
        {n?.advice ? <small className="ack-ai-line"><i className="ack-src">{n.label}</i>{n.advice.summary}</small> : null}</button>
      {!compact ? <span className="ack-oacts">{OWNER_ACTS.filter(([k]) => k !== r.mode && k !== 'review').map(([k, l]) => <button key={k} type="button" className="m-btn" disabled={!isOwner || busy} onClick={() => act(k, r.mint)} data-testid={`ack-own-${k}-${r.mint.slice(0, 6)}`}>{k === 'ignore' ? '✕' : l}</button>)}</span> : null}</li>; })}</ul>
      : compact ? <p className="ack-nil">{focus ? 'This coin is not on your review list — Review / Track / Arm it above (none of them buys).' : 'No coin selected.'}</p> : null}
  </div>;
}
function QueueAi({ o, mint }) { const ai = useAi(o?.ai); return <AiCell a={aiOf(ai?.notes, mint)?.advice} />; }   // its own AI-store subscriber
function ReviewQueue({ o, call, isOwner, onPick, sel }) {
  const [bk, setBk] = useState('all');
  const cands = (o?.kernel || {}).candidates || []; const counts = bucketCounts(cands.filter(c => !['HELD', 'EXIT_PENDING'].includes(c.status)));
  const queue = reviewQueue(cands, bk).slice(0, 14);
  return <section className="ack-review" data-testid="ack-review">
    <header><b>📋 REVIEW QUEUE</b><small>coins the agents are weighing · tap = chart + panel</small></header>
    <OwnerReview o={o} call={call} isOwner={isOwner} onPick={onPick} focus={sel} />
    <div className="m-seg ack-buckets" role="group" aria-label="Launch age">{AGE_BUCKETS.map(([k, l]) => <button key={k} type="button" className={bk === k ? 'active' : ''} onClick={() => setBk(k)} data-testid={`ack-bk-${k}`}>{l} <small>{counts[k]}</small></button>)}</div>
    {queue.length ? <div className="ack-qwrap"><table className="ack-queue" data-testid="ack-queue"><thead><tr><th>COIN</th><th>AGE</th><th>MC</th><th>5M VOL</th><th>SCORE</th><th data-tip="The model's newest read of this coin: its rug-risk meter + where it is in its run (advisory — weighs only once proven)">🧠 AI</th><th>STATUS</th></tr></thead>
      <tbody>{queue.map(c => { const st = queueStatus(c); return <tr key={c.mint} className={sel === c.mint ? 'is-on' : ''} onClick={() => onPick(c.mint)} data-testid={`ack-q-${c.symbol}`}>
        <td><button type="button" className="ack-qcoin" onClick={e => { e.stopPropagation(); onPick(c.mint); }}>${c.symbol}</button>{c.owner ? <i className={`ack-mode is-${c.owner}`}>{c.owner}</i> : null}</td>
        <td>{mins(c.ageMin)}</td><td data-testid={`ack-qmc-${c.symbol}`}>{mcWord(queueMc(c))}</td><td>{mcWord(c.vol5m)}</td><td>{c.rank != null ? Math.round(c.rank) : '—'}</td>
        <td data-testid={`ack-qai-${c.symbol}`}><QueueAi o={o} mint={c.mint} /></td>
        <td><em className={`ack-st is-${st.toLowerCase()}`} data-testid={`ack-qst-${c.symbol}`}>{st}</em></td></tr>; })}</tbody></table></div>
      : <p className="ack-nil" data-testid="ack-queue-empty">No candidate in this age band right now.</p>}
  </section>;
}

function AiProvidersLive({ o, ...rest }) { const ai = useAi(o?.ai); return <AiProviders {...rest} ai={ai} />; }

// 💹 the open book in one glance: every held seat's live P&L together ($ and % glide to each real tick) + the seat doing best
// 🧠 the Brain as a slide-out drawer on the right (owner, 2026-10-16) — Esc or ✕ closes; the page stays usable beside it
function BrainDrawer({ close, children }) {
  useEffect(() => { const on = e => { if (e.key === 'Escape') close(); }; window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on); }, [close]);
  return <aside className="ack-drawer" data-testid="ack-brain-drawer" aria-label="Brain"><div className="ack-drawerbody">{children}</div></aside>;
}

// 🎞 the selected seat's ride (share card) + its rug marker, under the chart
function RideBar({ s, pos }) {
  const card = useMemo(() => rideCard(s, pos), [s, pos]); const rug = rugMark(s);
  if (!card) return null;
  return <div className="ack-ride" data-testid="ack-ride"><span>🎞 ${s.symbol} · {s.pct == null ? '—' : pc(s.pct)}{(pos?.ghosts || []).length ? ` · ✂ ${(pos.ghosts || []).length} would-sell${pos.ghosts.length > 1 ? 's' : ''} on the chart` : ''}</span>
    {rug ? <em className={`ack-rugtag is-${rug.level}`} data-tip={rug.why} data-testid="ack-ride-rug"><i className={`ack-rugdot is-${rug.level}`} />{rug.level === 'bad' ? 'RUG RISK' : 'POOL THINNING'}</em> : null}
    <ShareGifButton card={card} label="🎞 Share the ride" className="ack-ridebtn" /></div>;
}

function OpenPnl({ seats, onPick }) {
  const p = useMemo(() => openPnl(seats), [seats]);
  if (!p) return null;
  return <span className={`ack-open ${p.pnl >= 0 ? 'is-up' : 'is-dn'}`} data-testid="ack-open-pnl" data-tip="Every held seat together, on live prices against each seat's own entry. Price result only — fees are apart.">
    <small>OPEN P&L</small><LiveNum v={p.pnl} fmt={v => `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(Math.abs(v) < 1 ? 3 : 2)}`} testid="ack-open-usd" />
    {p.pct != null ? <LiveNum v={p.pct} fmt={v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`} testid="ack-open-pct" /> : null}
    <i>${p.usd.toFixed(2)} at work</i>
    {p.best && p.n > 1 ? <button type="button" onClick={() => onPick(p.best.mint)} data-testid="ack-open-best">🔥 ${p.best.symbol} {p.best.pct >= 0 ? '+' : ''}{p.best.pct.toFixed(1)}%</button> : null}</span>;
}

export const LENS_TAB = { live: 'office', review: 'office', limits: 'office', board: 'office', missed: 'missed', learn: 'paper', ctl: 'paper', life: 'gens' };
export function AgentCockpit({ call, isOwner = true, head = null, extra = [], limits = null }) {
  const cc = useHub(); const d = cc?.d; const o = d?.office || null;
  const [pick, setPick] = useRemembered('feeless.ack.pick', null); const [iv, setIv] = useRemembered('feeless.ack.iv', '1m'); const [agent, setAgentS] = useState(null); const [tapeAgent, setTapeAgent] = useState(null);
  const [tab, setTab] = useRemembered('feeless.ack.tab', 'live'); const [aiOpen, setAiOpen] = useState(false); const [brainOpen, setBrainOpen] = useRemembered('feeless.ack.brain', false); const [side, setSide] = useRemembered('feeless.ack.side', 'decision');   // 🔁 a refresh comes back to the same coin, timeframe and panel tab
  // 🧭 the nav: 📈 chart = the top of the page; any other tab opens its pane under the chart and brings it into view (no hunting)
  const [nav, setNav] = useState(() => { try { return localStorage.getItem(NAV_KEY) || 'chart'; } catch { return 'chart'; } });
  const [navPane, setNavPane] = useState(() => { try { const v = localStorage.getItem(DECK_KEY); return v && v !== 'chart' ? v : 'live'; } catch { return 'live'; } });
  const deckRef = useRef(null);
  const go = k => { setNav(k); if (k !== 'chart') setNavPane(k); try { localStorage.setItem(NAV_KEY, k); if (k !== 'chart') localStorage.setItem(DECK_KEY, k); } catch { /* private window */ }
    const smooth = !(typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) ? 'smooth' : 'auto';
    if (k === 'chart') window.scrollTo?.({ top: 0, behavior: smooth }); else deckRef.current?.scrollIntoView?.({ behavior: smooth, block: 'start' }); };
  const seats = useMemo(() => seatCards(d, cc?.livePx), [d, cc?.livePx]);
  const mint = focusMint(d, pick);
  const model = useMemo(() => chartModel(d, mint, cc?.livePx), [d, mint, cc?.livePx]);
  const dec = useMemo(() => decisionOf(d, mint), [d, mint]);
  const pos = (o?.positions || []).find(p => p.mint === mint) || null; const cand = ((o?.kernel || {}).candidates || []).find(c => c.mint === mint) || null;
  const markers = useMemo(() => [...letterMarkers(tapeOf(o?.tape, { mint, n: 120 }), pos?.fills), ...ghostMarkers(pos)].sort((a, b) => a.time - b.time), [o?.tape, mint, pos?.fills, pos?.ghosts, pos?.entry]);   // ✂ where the agents would have sold
  const readyN = ((o?.kernel || {}).candidates || []).filter(c => c.status === 'READY').length;
  const tiles = useMemo(() => missionTiles(d, seats), [d, seats]);
  // ⚡ real-event pulses: an agent lights only when ITS newest tape id moves (never on a timer, never on first paint)
  const seen = useRef(null); const [pulse, setPulse] = useState({}); const [freshIds, setFreshIds] = useState(() => new Set());
  useEffect(() => {
    const n = newEvents(seen.current, o?.tape); seen.current = maxIdByAgent(o?.tape);
    if (Object.keys(n).length) { const ids = new Set(Object.values(n)); setPulse(p => ({ ...p, ...n })); setFreshIds(ids); }
  }, [o?.tape]);
  const agentNow = agent || leadAgent(dec);
  const onPick = m => { setPick(m); setAgentS(null); };
  useEffect(() => { const on = e => { const m = e.detail?.mint; if (m) { setPick(m); setAgentS(null); } }; window.addEventListener('feeless:cockpit-coin', on); return () => window.removeEventListener('feeless:cockpit-coin', on); }, []);
  // 🧠 a $COIN chip in a Brain answer → that coin on the chart (a held seat first, then the desk's candidates)
  useEffect(() => { const on = e => { const y = String(e.detail?.sym || '').toUpperCase(); const hit = seatsRef.current.find(x => !x.open && String(x.symbol || '').toUpperCase() === y)
    || (((d?.office?.kernel || {}).candidates) || []).find(c => String(c.symbol || '').toUpperCase() === y)
    || (((d?.office?.tradeTape || {}).rows) || []).find(c => String(c.sym || c.symbol || '').toUpperCase() === y)   // a coin you already traded
    || ((d?.office?.positions) || []).find(c => String(c.sym || c.symbol || '').toUpperCase() === y); if (hit?.mint) { setPick(hit.mint); setAgentS(null); setTab('live'); } };
    window.addEventListener('feeless:cockpit-coin-sym', on); return () => window.removeEventListener('feeless:cockpit-coin-sym', on); });   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const on = e => go(LENS_TAB[e.detail] || e.detail); window.addEventListener('feeless:agents-lens', on); return () => window.removeEventListener('feeless:agents-lens', on); });   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const on = () => setAiOpen(true); window.addEventListener('feeless:agents-ai', on); return () => window.removeEventListener('feeless:agents-ai', on); }, []);
  // 🧠 the Brain's Coach / Teach panes change only when coaching, teaching or the HELD coins change — a 3s price tick or a hub paint
  // never re-renders the Brain (it is memoized; a new extras array every paint made it redraw its whole log ~2.5×/s)
  const heldKey = seats.filter(s => !s.open).map(s => `${s.mint}:${s.pair}:${s.buying ? 1 : 0}`).join('|'); const sym = model?.sym || model?.symbol;
  const seatsRef = useRef(seats); seatsRef.current = seats;
  const brainExtras = useMemo(() => [['coach', `👑 Coach${(o?.coach?.rules || []).length ? ` · ${o.coach.rules.length}` : ''}`, <CoachBox coach={o?.coach} seats={seatsRef.current} tpl={d?.card?.tpl} call={call} isOwner={isOwner} />],
    ['teach', `🎓 Teach${(o?.teach?.items || []).length ? ` · ${o.teach.items.length}` : ''}`, <TeachBox o={{ teach: o?.teach, ai: o?.ai }} mint={mint} sym={sym} call={call} isOwner={isOwner} />],
    // 👤 everything the desk learned from YOUR trades, inside the Brain (owner, 2026-10-15: "chat log show all learnings from my trades")
    ['you', `👤 Your trades${(o?.ownerStudy?.findings || []).length ? ` · ${o.ownerStudy.findings.length}` : ''}`, <OwnerStudy study={o?.ownerStudy} memory={o?.aiMemory} />],
    ['learned', '🎓 Learned', <BrainLearned call={call} />]],
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [o?.coach, o?.teach, o?.ai, o?.ownerStudy, o?.aiMemory, heldKey, d?.card?.tpl, mint, sym, call, isOwner]);
  if (!o || o.cold) return <section className="ack" data-testid="agent-cockpit">{head}<MissionRibbon tiles={missionTiles(d, [])} cold /><p className="ack-warm" data-testid="ack-warm"><i aria-hidden />warming up — the cockpit opens with the agents' first pass (≈ 1 min after a restart)</p></section>;   /* 🧹 no old desk while cold (owner, 2026-10-15: "not the current layout") */
  const held = seats.filter(s => !s.open).length;
  const navTabs = deckMeters(o, [
      ['seats', '🪑 Seats', seats.length ? `${held}/${seats.length}` : null, <section className="ack-seats" data-testid="ack-seats"><header><b>🪑 SEAT BOARD</b><OpenPnl seats={seats} onPick={onPick} /><small><b className="m-pos">{held}/{seats.length || '—'} active</b> · live prices every 3s · tap a seat = its chart + the agent handling it</small></header>
      <ReaperAsks o={o} call={call} isOwner={isOwner} reload={cc?.load} />
      {isOwner ? <><AddMyCoin call={call} tpl={d?.card?.tpl} seats={seats} reload={cc?.load} /><SeatControls call={call} tpl={d?.card?.tpl} seats={seats} reload={cc?.load} /><MySeatsRecord rec={o.ownerSeats} /></> : null}
</section>, seats.length ? held / seats.length : null, 'the seats: live P&L, Reaper\'s word, tap = its chart'],
      ['you', '👤 You', o.ownerStudy?.score != null ? `${o.ownerStudy.score}%` : null, <OwnerStudy study={o.ownerStudy} memory={o.aiMemory} />, null, 'your own moves graded, your seats vs the agents, what the study suggests'],
      ['live', '⚡ Live desk', (o.tape || []).length || null, <LiveDesk duo={<DuoSeat duo={d?.duo} call={call} />} matrix={<AgentMatrix o={o} gens={o?.generations || []} agent={agentNow} setAgent={a => { setAgentS(a); setTapeAgent(a); }} rows={o.tape} pulse={pulse} />}
        tape={<DecisionTape rows={o.tape} agent={tapeAgent} setAgent={setTapeAgent} fresh={freshIds} onPick={r => { if (r.mint) setPick(r.mint); setAgentS(r.agent in AG ? r.agent : null); setTab('live'); }} />} tapeN={(o.tape || []).length} />, null, 'G4 × OSSY on their seat, the ten agents and every live decision — one place'],
      ['tape', '🎬 Trades', (o.tradeTape?.rows || []).length, <><LossMap court={o.court} capital={o.capital} /><TradeTape tape={o.tradeTape} mint={mint} onPick={onPick} /></>],
      ['review', '📋 Queue', (o.ownerReview || []).length || null, <ReviewQueue o={o} call={call} isOwner={isOwner} onPick={m => { onPick(m); if (m && !((o.kernel || {}).candidates || []).some(c => c.mint === m) && !(o.positions || []).some(p => p.mint === m) && !(o.ownerReview || []).some(r => r.mint === m)) openCoin({ mint: m }); }} sel={mint} />],
      ['controls', '🎛 Limits', null, <><CockpitControls o={o} call={call} isOwner={isOwner} onAi={() => setAiOpen(true)} />{limits}</>, null, 'EVERY control in one place: universe, exits, seats, buy gate, model + your creator limits (TP / SL / trail / hold / size / switching)'],
      ['stats', '📊 Stats', null, <>{head}<MissionRibbon tiles={tiles} live={!!cc?.live} /><LivePulse o={o} onAi={() => setTab('ai')} /></>, null, 'mission numbers, the desk pulse, stage + dial'],
      ...extra,
    ]);
  const symClick = e => { const y = symOf(e.target, e.currentTarget); if (y) { e.stopPropagation(); tapSym(y); } };   // 🪙 any bare $TICKER opens its chart
  const symHover = e => { if (symOf(e.target, e.currentTarget)) e.target.classList.add('ack-symtap'); addTip(e.target); };   // 💬 every button explains itself
  return <section className="ack" data-testid="agent-cockpit" onClick={symClick} onMouseOver={symHover}>
    {/* 💵 ONE sticky strip: the money at a glance + the icon nav; nothing else above the chart. Every other section is a pane behind the nav */}
    <MoneyStrip d={d} seats={seats} mint={mint} onPick={onPick} nav={nav} go={go} navTabs={navTabs} ai={<AiChipBtn o={o} onClick={() => setAiOpen(true)} testid="ack-money-ai" />}
      brain={<button type="button" className={`ack-brainbtn ${brainOpen ? 'is-on' : ''}`} onClick={() => setBrainOpen(!brainOpen)} aria-pressed={brainOpen} data-testid="ack-brain-open" data-tip="the Brain — talk to G4 / OSSY, coach, teach, code lab (slides out on the right)">🧠 BRAIN</button>} />
    <div className="ack-topseats" data-testid="ack-topseats">
      <div className="ack-seatrow">{seats.map((s, i) => <div key={s.seat} className="ack-seatwrap"><SeatCard s={s} call={call} on={!s.open && s.mint === mint} onPick={onPick} readyN={readyN} same={s.open ? seats.slice(0, i).find(x => x.open && x.why === s.why)?.seat : undefined} />{isOwner ? <QuickTrade s={s} call={call} tpl={d?.card?.tpl} /> : null}</div>)}</div></div>
    <div className="ack-main">
      <div className="ack-left"><CockpitChart duo={d?.duo} m={model} iv={iv} setIv={setIv} pos={pos} cand={cand} markers={markers} onAgent={a => { setAgentS(a); setTab('live'); }} tid={o?.tid} call={call} isOwner={isOwner} />
        <RideBar s={seats.find(x => !x.open && x.mint === mint)} pos={pos} />
        <IntakeBand o={o} mint={mint} onPick={onPick} call={call} isOwner={isOwner} imp={d?.impostors} /></div>
      <div className="ack-right"><div className="ack-sidetabs m-seg" role="tablist" aria-label="Right column">{[['decision', '🧠 Decision'], ['desk', '⚡ Live desk']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={side === k} className={side === k ? 'active' : ''} onClick={() => setSide(k)} data-testid={`ack-side-${k}`}>{l}</button>)}</div>
      {side === 'desk' ? <div className="ack-sidedesk" data-testid="ack-sidedesk"><DuoSeat duo={d?.duo} call={call} /><DecisionTape rows={o.tape} agent={tapeAgent} setAgent={setTapeAgent} fresh={freshIds} onPick={r => { if (r.mint) setPick(r.mint); setSide('decision'); }} /></div> : <DecisionPanel o={o} dec={dec} pos={pos} cand={cand} mint={mint} seats={seats} readyN={readyN} agent={agentNow} setAgent={a => { setAgentS(a); setTapeAgent(a); }} tab={tab} setTab={setTab}
        pulse={pulse} call={call} isOwner={isOwner} onPick={onPick} mcNow={model?.mc} onAi={() => setAiOpen(true)} />}</div></div>
    <div ref={deckRef} className="ack-deckwrap"><Deck testid="ack-tapezone" bare on={nav === 'chart' ? navPane : nav} setOn={go} tabs={navTabs} /></div>
    {brainOpen ? createPortal(<BrainDrawer close={() => setBrainOpen(false)}><AiChat call={call} isOwner={isOwner} focus={mint} focusSym={dec?.symbol} variant="drawer" extras={brainExtras} onClose={() => setBrainOpen(false)} /></BrainDrawer>, document.body) : null}
    {aiOpen ? createPortal(<AiProvidersLive o={o} call={call} isOwner={isOwner} close={() => setAiOpen(false)} />, document.body) : null}
  </section>;
}
