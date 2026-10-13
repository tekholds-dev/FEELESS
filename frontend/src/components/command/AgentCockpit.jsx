import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { useHub, hubApply, hubLoad } from '../../lib/agentHub';
import { rankFill, READY_MIN, devilOf } from '../../lib/agentRead';
import { seatCards, focusMint, chartModel, decisionOf, tapeOf, tapeTone, TAPE_AGENT, AGE_BUCKETS, bucketCounts, reviewQueue, supplyWord,
  seatState, STATE_CLS, missionTiles, letterMarkers, inputsOf, traceOf, CHAIN, maxIdByAgent, newEvents, queueStatus, queueMc } from '../../lib/cockpit';
import { useEasedNumber } from '../../lib/easedNumber';
import { usd as cash, pct as pc, price as priceFmt } from '../../lib/num';
import { AG, activityOf } from './agentWords';
import { openCoin } from '../CoinDrawer';
import { AiProviders } from './AiProviders';
import { AiPane, AiVitals, AiCell } from './AiDecisions';
import { CockpitControls } from './CockpitControls';
import { tradeBar, tickDir, aiOf } from '../../lib/cockpitControls';
import '../../styles/agentCockpit.css';
import '../../styles/cockpitAi.css';   // after the cockpit sheet: it owns the plot's height + the meta pass

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
function useTick(ms = 1000) { const [n, setN] = useState(() => Date.now()); useEffect(() => { const t = setInterval(() => setN(Date.now()), ms); return () => clearInterval(t); }, [ms]); return n; }
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
function LivePulse({ o, onAi }) {
  const now = useTick(1000); const p = pulseOf(o, now); const [ic, nm] = TAPE_AGENT[p.last?.agent] || ['•', p.last?.agent || ''];
  const sec = v => (v == null ? '—' : v < 60 ? `${Math.floor(v)}s` : `${Math.floor(v / 60)}m ${Math.floor(v % 60)}s`);
  return <section className={`ack-pulse ${p.late ? 'is-late' : ''}`} data-testid="ack-pulse">
    <span className="ack-pz is-pass" data-tip="The agents' pass: the whole desk re-reads every coin. Between passes the live chart price wakes Reaper and Trigger within seconds."><small>PASS</small><b>{sec(p.passAge)} ago</b>
      <span className="ack-pzbar"><i style={{ transform: `scaleX(${p.fill})` }} /></span></span>
    <span className="ack-pz"><small>COINS TRACKED</small><LiveNum v={p.mints} fmt={x => String(Math.round(x))} cls="" testid="ack-pulse-mints" /><u>{p.newPerMin != null ? `${Math.round(p.newPerMin)} new / min` : ''}</u></span>
    <span className="ack-pz"><small>RE-JUDGED</small><LiveNum v={p.rejudged} fmt={x => String(Math.round(x))} cls="" /><u>{p.eps != null ? `${p.eps.toFixed(1)} events / s` : ''}</u></span>
    <span className="ack-pz"><small>FUNNEL</small><b><i className="ack-fz is-t">{p.tracking}</i>›<i className="ack-fz is-c">{p.contending}</i>›<i className="ack-fz is-r">{p.ready}</i>›<i className="ack-fz is-h">{p.held}</i></b><u>tracking › contending › ready › held</u></span>
    <span className="ack-pz"><small>BRAIN</small><b>{p.brainMs != null ? `${p.brainMs < 10 ? p.brainMs.toFixed(1) : Math.round(p.brainMs)}ms` : '—'}</b><u>{p.wakeMs != null ? `price → Reaper ${Math.round(p.wakeMs)}ms` : 'per coin, ten agents'}</u></span>
    <span className="ack-pz is-wide"><small>LAST DECISION</small><b key={p.last ? `${p.last.agent}-${p.last.action}-${p.last.symbol}` : 'x'} className="ack-pzlast">{p.last ? <>{ic} {nm} · {p.last.action}{p.last.symbol ? ` $${p.last.symbol}` : ''}</> : '—'}</b><u>{p.last ? `${sec(p.last.age)} ago` : 'a quiet tape is a quiet market'}</u></span>
    <button type="button" className="ack-pz is-ai" onClick={onAi} data-testid="ack-pulse-ai" data-tip="The model's decisions — tap to open"><small>🧠 MODEL</small><b>{p.ai ? `${p.ai.stance || '—'}${p.ai.symbol ? ` $${p.ai.symbol}` : ''}` : 'no answer yet'}</b><u>{p.ai ? `${sec(p.ai.age)} ago` : ''}</u></button>
  </section>;
}

// ── 💵 the mission ribbon ───────────────────────────────────────────────────────────────────────────────────────────────────────
export function MissionRibbon({ tiles, live, cold }) {
  return <section className="ack-ribbon m-live" data-testid="ack-ribbon">
    <span className="ack-rhead"><b>💵 REAL MONEY MISSION</b><i className={live ? 'is-live' : ''}>{cold ? 'waiting' : live ? '● live' : '● snapshot'}</i></span>
    {tiles.map(t => <span key={t.k} className="ack-rt" data-testid={`ack-rt-${t.k}`} data-tip={t.tip || undefined}><small>{t.label}</small>
      {t.fmt ? (t.live ? <LiveNum v={t.val} fmt={FMT[t.fmt]} cls={t.cls || ''} /> : <b className={`ack-num ${t.cls || ''}`}>{FMT[t.fmt](t.val)}</b>) : <b className={`ack-num ack-word ${t.cls || ''}`}>{t.text}</b>}
      {t.sub ? <u className={t.subCls || ''}>{t.sub}</u> : null}</span>)}
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
function SeatCard({ s, on, onPick, readyN }) {
  const st = seatState(s, readyN);
  if (s.open) return <div className={`ack-seat is-open ${on ? 'is-on' : ''}`} data-testid={`ack-seat-${s.seat}`}>
    <header><small>SEAT {s.seat}</small><i className={`ack-badge ${STATE_CLS[st]}`} data-testid={`ack-seat-state-${s.seat}`}>{st}</i></header>
    <p className="ack-open"><b>No position</b><span>{s.why}</span></p>
    {(s.refused || []).length ? <ul className="ack-refused" data-testid={`ack-seat-refused-${s.seat}`}>{s.refused.map(r => <li key={`${r.symbol}-${r.at}`} data-tip={`${r.by === 'keeper' ? "the keeper's own buy check" : 'the seat pre-check'} · ${ago(r.at)} ago`}><b>${r.symbol}</b><span>{r.why}</span></li>)}</ul> : null}</div>;
  const last = s.last; const [ic, nm] = TAPE_AGENT[last?.agent] || ['', ''];
  return <button type="button" className={`ack-seat ${on ? 'is-on' : ''} ${s.pct > 0 ? 'is-up' : s.pct < 0 ? 'is-dn' : ''}`} onClick={() => onPick(s.mint)} aria-pressed={on} data-testid={`ack-seat-${s.seat}`}
    data-tip={`${s.tag || s.kind}${s.rule ? ` · Reaper ${s.rule}` : ''}${s.why ? ` — ${s.why}` : ''}`}>
    <header><small>SEAT {s.seat}</small><i className={`ack-badge ${STATE_CLS[st]}`} data-testid={`ack-seat-state-${s.seat}`}>{st}</i></header>
    <p className="ack-coin"><b>${s.symbol}</b><span className="ack-pnl"><LiveNum v={s.pct} fmt={x => pc(x)} testid={`ack-seat-pct-${s.seat}`} /><LiveNum v={s.pnlUsd} fmt={signed} cls={`ack-usd ${tone(s.pnlUsd)}`} testid={`ack-seat-usd-${s.seat}`} /></span></p>
    <div className="ack-seatmid"><dl className="ack-kv">
      <dt>ENTRY MC</dt><dd>{mcWord(s.entryMc)}</dd><dt>AGE</dt><dd>{mins(s.ageMin)}</dd>
      <dt>NOW MC</dt><dd><LiveNum v={s.mc} fmt={mcWord} cls="" testid={`ack-seat-mc-${s.seat}`} /></dd><dt>HELD</dt><dd>{mins(s.heldMin)}</dd>
      <dt>IN SEAT</dt><dd>{money(s.usd)}</dd><dt>REALIZED</dt><dd>{s.realized == null ? '—' : signed(s.realized)}</dd></dl>
      <Spark path={s.path} /></div>
    <SeatBar s={s} />
    <p className="ack-now" data-testid={`ack-seat-now-${s.seat}`}><span>☠ Reaper · {s.reaper || '—'}{s.rule ? ` · ${s.rule}` : ''}</span><small>next review {secs(s.nextReview)}</small></p>
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
    <span className="thd-kv"><span><small>ENTRY → NOW</small><b>{k ? mcWord(Number(pos.entry) * k) : priceFmt(pos.entry)} → <LiveNum v={k ? m.mc : m?.price} fmt={k ? mcWord : priceFmt} cls="" /></b></span>
      <span><small>HELD</small><b data-testid="ack-trade-held">{heldW}</b></span>
      <span><small>☠ REAPER</small><b className={`thd-dec ${/EXIT|TAKE/.test(pos.decision || '') ? 'is-bad' : /PROTECT/.test(pos.decision || '') ? 'is-good' : ''}`}>{pos.decision || pos.state || 'HOLD'}</b>
        <u>{pos.rule || ''}{pos.nextReview != null ? ` · review ${secs(pos.nextReview)}` : ''}</u></span></span></div>;
}

// ── 📈 the chart: market cap, always ──────────────────────────────────────────────────────────────────────────────────────────────
export const IVS = [['1m', '1m'], ['5m', '5m'], ['15m', '15m']];
function CockpitChart({ m, iv, setIv, pos, cand, markers, onAgent }) {
  const pair = useMemo(() => (m?.pair ? { chainId: 'solana', pairAddress: m.pair, baseToken: { address: m.mint, symbol: m.symbol }, priceUsd: m.price, marketCap: m.mc } : null), [m?.pair, m?.mint, m?.symbol, m?.price, m?.mc]);
  const fuse = useMemo(() => ({ lines: m?.lines || [] }), [m?.lines]);
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
      <span className="ack-cstat ack-cmc"><small>MC</small><LiveNum v={m.mc} fmt={mcWord} cls="" testid="ack-chart-mc" /></span>
      <span className="ack-cstat"><small>5M VOL</small><em>{mcWord(vol)}</em></span>
      <span className="ack-cstat"><small>LIQ</small><em>{mcWord(liq)}</em></span>
      <span className="ack-cstat ack-cpx" data-tip="Price is secondary: the chart speaks market cap"><small>PRICE</small><em>{priceFmt(m.price)}</em></span>
      <span className="ack-cstat" data-tip="Market cap = live price × the supply the kernel resolved (token supply → a launchpad's fixed 1B → live cap ÷ price). Unknown supply = no chart."><small>SUPPLY</small><em>{m.supply ? `${supplyWord(m.supply)}${m.supplySrc ? ` · ${m.supplySrc}` : ''}` : 'UNKNOWN'}</em></span>
      <span className="ack-ctools"><span className="m-seg ack-iv" role="group" aria-label="Candle size">{IVS.map(([k, l]) => <button key={k} type="button" className={iv === k ? 'active' : ''} onClick={() => setIv(k)} data-testid={`ack-iv-${k}`}>{l}</button>)}</span>
        <button type="button" className="m-btn ack-wr" onClick={() => pair && window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: pair }))} data-testid="ack-warroom">⚔ war room</button>
        <i className="ack-livechip">● MC chart</i></span></header>
    {!m.pair ? <p className="ack-nil" data-testid="ack-nopool">No pool for this coin yet — nothing to chart.</p>
      : !m.mc ? <p className="ack-nil is-warn" data-testid="ack-mc-unavailable"><b>MC UNAVAILABLE</b> — no supply is known for this coin yet (no token supply, not a launchpad mint, no live cap). The raw price is never charted in its place.</p>
        : <div className="ack-plot">{pos ? <TradeHud pos={pos} m={m} /> : null}<Suspense fallback={<p className="ack-nil">loading the live chart…</p>}>
          <PriceChartLazy key={`${m.pair}-${iv}`} pair={pair} interval={iv} metric="marketCap" showVolume markers={chartMarkers} fuse={fuse} pnl={seatPnl} plain /></Suspense></div>}
    <div className="ack-mrail" data-testid="ack-mrail"><span className="ack-mkey"><i className="ack-ml is-B">▲<small>real buy</small></i><i className="ack-ml is-X">▼<small>real sell</small></i><small>on the chart · decisions →</small></span>
      {markers.length ? <span className="ack-mlist">{markers.slice(-12).map(k => <button key={k.id} type="button" className={`ack-ml is-${k.text}`} onClick={() => onAgent(k.agent)}
        data-tip={`${new Date(k.at * 1000).toLocaleTimeString()} · ${TAPE_AGENT[k.agent]?.[1] || k.agent} · ${k.action}${k.why ? ` — ${k.why}` : ''}${k.mc ? ` · MC ${mcWord(k.mc)}` : ''} · ${ago(k.at)} ago`}
        data-testid={`ack-mk-${k.id}`}>{TAPE_AGENT[k.agent]?.[1] || k.agent} {String(k.action || '').toLowerCase()}<small>{ago(k.at)}</small></button>)}</span> : <small className="ack-mnone">no real event on this coin yet — markers appear only for decisions and fills that happened</small>}</div>
  </div>;
}

// ── 📜 the live decisions strip ─────────────────────────────────────────────────────────────────────────────────────────────────
function TapeRow({ r, onPick, card, pulse }) {
  const [ic, nm] = TAPE_AGENT[r.agent] || ['•', r.agent];
  const Tag = card ? 'button' : 'li';
  const body = <><small className="ack-tage">{ago(r.at)} ago</small><b style={{ '--ag': AG[r.agent] || 'var(--m-accent)' }}>{ic} {nm}</b><em className={`ack-tact ${tapeTone(r)}`}>{r.action}</em>
    {r.symbol ? <span className="ack-tsym">${r.symbol}{r.mc ? <small> · {mcWord(r.mc)} MC</small> : null}</span> : null}<span className="ack-twhy">{r.why}</span></>;
  return card ? <Tag type="button" className={`ack-tcard ${tapeTone(r)} ${pulse ? 'is-new' : ''}`} onClick={() => onPick(r)} style={{ '--ag': AG[r.agent] || 'var(--m-accent)' }} data-testid={`ack-tape-${r.id}`}>{body}</Tag>
    : <li className={`ack-trow ${tapeTone(r)}`}><button type="button" onClick={() => onPick(r)} data-testid={`ack-tline-${r.id}`}>{body}</button></li>;
}
function DecisionTape({ rows, agent, setAgent, onPick, fresh }) {
  const [all, setAll] = useState(false);
  const list = tapeOf(rows, { agent, n: all ? 120 : 6 });
  return <section className="ack-tape" data-testid="ack-tape">
    <header><b>⚡ LIVE DECISIONS</b><small>{agent ? `${TAPE_AGENT[agent]?.[1] || agent} only · ` : ''}latest real agent actions across all seats — a line exists only when something real changed</small>
      {agent ? <button type="button" className="m-btn" onClick={() => setAgent(null)} data-testid="ack-tape-all-agents">✕ all agents</button> : null}
      <button type="button" className="m-btn ack-more" onClick={() => setAll(!all)} aria-expanded={all} data-testid="ack-tape-more">{all ? 'Show newest' : `View all decisions (${tapeOf(rows, { agent, n: 120 }).length}) →`}</button></header>
    {!list.length ? <p className="ack-nil" data-testid="ack-tape-empty">No decision lines yet — the tape writes only when an opinion, an order or a ruling really changes (a quiet market is a quiet tape).</p>
      : all ? <ol className="ack-tlist">{list.map(r => <TapeRow key={r.id} r={r} onPick={onPick} />)}</ol>
        : <div className="ack-tcards">{list.map(r => <TapeRow key={r.id} r={r} onPick={onPick} card pulse={fresh.has(r.id)} />)}</div>}
  </section>;
}

// ── 🧠 the agent decision panel ──────────────────────────────────────────────────────────────────────────────────────────────────
export const PANEL_TABS = [['live', 'Live'], ['ai', '🧠 AI'], ['inputs', 'Inputs'], ['seats', 'Seats'], ['review', 'Review'], ['trace', 'Trace']];
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
function Tile({ l, v, sub, cls }) { return <span className="ack-ptile"><small>{l}</small><b className={cls || ''}>{v}</b>{sub ? <u>{sub}</u> : null}</span>; }
const badgeOf = w => (/VETO|EXIT|BLOCK/.test(w) ? 'is-bad' : /WARN/.test(w) ? 'is-warn' : /ENTER|READY|PROTECT|PASS|FILLED|SIZE|SCAN|CONFIRMED/.test(w) ? 'is-good' : 'is-hold');

function DecisionPanel({ o, dec, pos, cand, mint, seats, readyN, agent, setAgent, tab, setTab, pulse, call, isOwner, onPick, aiNote, mcNow, onAi }) {
  const tr = useMemo(() => traceOf(o, mint), [o, mint]);
  const names = Object.fromEntries((o?.agents || []).map(a => [a.key, `${a.icon} ${a.name}`]));
  const line = tr?.lines.find(l => l.agent === agent);
  const [word, why] = activityOf(agent, o);
  const live = o?.livePx?.[mint];
  const verdictWord = line?.word || word;
  return <aside className="ack-panel" data-testid="ack-panel">
    <header><b>🧠 AGENT DECISION PANEL</b><i className="ack-livechip">● {dec?.symbol ? `$${dec.symbol}` : 'no coin'}</i>
      <select className="m-input ack-agsel" value={agent} onChange={e => setAgent(e.target.value)} aria-label="Agent" data-testid="ack-agent-sel">
        {CHAIN.map(a => <option key={a} value={a}>{names[a] || a}</option>)}</select></header>
    <div className="m-seg ack-ptabs" role="tablist" aria-label="Decision panel">{PANEL_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`ack-ptab-${k}`}>{l}</button>)}</div>
    {tab === 'live' ? (!dec ? <p className="ack-nil">Pick a seat, a decision or a coin in the queue.</p> : <div className="ack-pbody" data-testid="ack-pane-live">
      <div className="ack-verdict"><small>{(names[agent] || agent).toUpperCase()} · {line?.word ? 'ON THIS COIN' : 'THIS PASS'}</small>
        <em className={`ack-badge ${badgeOf(verdictWord)}`} data-testid="ack-verdict">{verdictWord}</em>
        <span className="ack-rule">{line?.why || why}{line?.at ? ` · ${ago(line.at)} ago` : ''}</span></div>
      <div className="ack-verdict is-kernel"><small>{dec.kind === 'position' ? "REAPER'S RULING" : dec.kind === 'review' ? 'YOUR REVIEW' : "THE KERNEL'S STATUS"}</small>
        <b data-testid="ack-kernel-verdict">{dec.verdict || '—'}</b>{dec.rule ? <span className="ack-rule">{dec.rule}{dec.obeying ? ` · obeying ${dec.obeying}` : ''}</span> : null}</div>
      {dec.kernel ? <div className="ack-rank" data-tip={`READY needs Trigger ENTER + inside the hard wall + execution healthy + rank ≥ ${READY_MIN}`}><small>RANK vs THE READY LINE ({READY_MIN})</small>
        <span className="ack-bar"><i style={{ transform: `scaleX(${rankFill(dec.kernel.rank)})` }} /><u /></span><em>{dec.kernel.rank ?? '—'}</em></div> : null}
      {(dec.reasons || []).length ? <><b className="ack-sub">REASONING</b><ul className="ack-why" data-testid="ack-why">{dec.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul></> : null}
      <div className="ack-ptiles">
        <Tile l="CHART QUALITY" v={pos?.quality || pos?.data?.state || dec.chart?.quality || '—'} sub={pos?.data?.conf != null ? `${pos.data.conf}% data conf` : pos?.structure || null} />
        <Tile l="CYCLE AGE" v={o?.cycle?.at ? ago(o.cycle.at) : '—'} sub={o?.cycle?.every ? `every ${Math.round(o.cycle.every)}s` : null} />
        <Tile l="RISK" v={dec.kernel ? devilOf(cand || {}).word : pos?.run || '—'} sub={dec.kernel ? 'Devil on this coin' : pos ? `stop ${pos.stop ?? '—'}%` : null}
          cls={dec.kernel?.devil?.verdict === 'veto' ? 'm-neg' : dec.kernel?.devil?.verdict === 'warn' ? 'ack-warn' : ''} />
        <Tile l="POSITION SIZE" v={pos ? money(pos.usd) : cand?.size != null ? `×${cand.size}` : '—'} sub={pos ? `Warden ×${pos.warden ?? '—'}` : cand?.sizeWhy || null} />
        <Tile l="NEXT ACTION" v={pos ? (pos.roundAction || pos.decision || '—') : dec.verdict === 'READY' ? 'TAKE A SEAT' : cand?.trigger === 'ENTER' ? 'CLEAR THE WALL' : 'KEEP READING'} sub={pos?.obeying || null} />
        <Tile l="NEXT WAKE" v={pos ? secs(pos.nextReview) : secs(o?.cycle?.nextIn)} sub={pos ? "Reaper's review (the live chart acts sooner)" : 'next agent pass'} /></div>
      {agent === 'devil' && cand?.devilConf != null ? <p className="ack-fresh">Devil confidence ×{cand.devilConf} (a weight on the rank, never a block)</p> : null}
      {aiNote?.advice ? <button type="button" className="ack-ai-note is-btn" onClick={() => setTab('ai')} data-testid="ack-ai-note" data-tip={`advisory only — ${aiNote.advice.stance} · priority ${aiNote.advice.priority} · tap = every model decision`}><i className="ack-src">{aiNote.label || aiNote.source}</i><em className="ack-ai-stance">{aiNote.advice.stance}</em>{aiNote.role} · {aiNote.advice.summary}</button>
        : <button type="button" className="ack-ai-note is-btn is-none" onClick={() => setTab('ai')} data-testid="ack-ai-none"><i className="ack-src">AI</i>the model has not been asked about this coin — ask it →</button>}
      {aiNote?.advice ? <AiVitals a={aiNote.advice} testid="ack-ai-vitals" /> : null}
    </div>) : null}
    {tab === 'ai' ? <div className="ack-pbody"><AiPane ai={o?.ai} call={call} isOwner={isOwner} focus={mint} focusSym={dec?.symbol} onPick={onPick} onProviders={onAi} /></div> : null}
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
function AgentMatrix({ o, gens, agent, setAgent, rows, pulse }) {
  const lastBy = useMemo(() => { const m = {}; (rows || []).forEach(r => { if (!m[r.agent] || r.id > m[r.agent].id) m[r.agent] = r; }); return m; }, [rows]);
  const ds = o?.deskStats || {}; const agents = o?.agents || []; const [filt, setFilt] = useState('all');
  const cards = agents.map(a => { const g = gens.find(x => x.role === a.key); const [word, why] = activityOf(a.key, o); return { a, g, word, why, l: lastBy[a.key], st: ds[a.key] }; });
  const active = cards.filter(c => c.word !== 'WAIT'); const idle = cards.filter(c => c.word === 'WAIT');
  const shown = filt === 'active' ? active : filt === 'idle' ? idle : cards;
  return <section className="ack-matrix" data-testid="ack-matrix"><header><b>🤖 AGENT MATRIX</b><small>{agents.length} agents · live status · tap = focus the panel</small>
    <span className="m-seg ack-mfilt" role="group" aria-label="Agents">{[['all', 'ALL'], ['active', `ACTIVE ${active.length}`], ['idle', `IDLE ${idle.length}`]].map(([k, l]) => <button key={k} type="button" className={filt === k ? 'active' : ''} onClick={() => setFilt(k)} data-testid={`ack-mf-${k}`}>{l}</button>)}</span></header>
    <div className="ack-agents">{shown.map(({ a, g, word, why, l, st }) => <button key={a.key} type="button" className={`ack-agent ${agent === a.key ? 'is-on' : ''} ${g?.status === 'PROBATION' ? 'is-prob' : ''}`} style={{ '--ag': AG[a.key] }} onClick={() => setAgent(a.key)} aria-pressed={agent === a.key}
        data-tip={`${a.job || ''} — ${why}${l ? ` · last line: ${l.action} ${l.symbol ? `$${l.symbol}` : ''} ${ago(l.at)} ago` : ''}`} data-testid={`ack-agent-${a.key}`}>
        <span className={`ack-aname ${pulse[a.key] ? 'is-pulse' : ''}`} key={pulse[a.key] || 'x'}>{a.icon} {a.name}</span>
        <small>{g ? `GEN ${g.generation} · ${g.status}` : '—'}</small>
        <small className="ack-acc" data-testid={`ack-rec-${a.key}`}>{st ? `${st.accuracy ?? '—'}% · ${st.winResp ?? 0}W ${st.lossResp ?? 0}L` : 'no real record yet'}</small>
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
  const own = o?.ownerReview || []; const ai = o?.ai?.notes || {};
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
        <td data-testid={`ack-qai-${c.symbol}`}><AiCell a={aiOf(o?.ai?.notes, c.mint)?.advice} /></td>
        <td><em className={`ack-st is-${st.toLowerCase()}`} data-testid={`ack-qst-${c.symbol}`}>{st}</em></td></tr>; })}</tbody></table></div>
      : <p className="ack-nil" data-testid="ack-queue-empty">No candidate in this age band right now.</p>}
  </section>;
}

export function AgentCockpit({ call, isOwner = true }) {
  const cc = useHub(); const d = cc?.d; const o = d?.office || null;
  const [pick, setPick] = useState(null); const [iv, setIv] = useState('1m'); const [agent, setAgentS] = useState(null); const [tapeAgent, setTapeAgent] = useState(null);
  const [tab, setTab] = useState('live'); const [aiOpen, setAiOpen] = useState(false);
  const seats = useMemo(() => seatCards(d, cc?.livePx), [d, cc?.livePx]);
  const mint = focusMint(d, pick);
  const model = useMemo(() => chartModel(d, mint, cc?.livePx), [d, mint, cc?.livePx]);
  const dec = useMemo(() => decisionOf(d, mint), [d, mint]);
  const pos = (o?.positions || []).find(p => p.mint === mint) || null; const cand = ((o?.kernel || {}).candidates || []).find(c => c.mint === mint) || null;
  const markers = useMemo(() => letterMarkers(tapeOf(o?.tape, { mint, n: 120 }), pos?.fills), [o?.tape, mint, pos?.fills]);
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
  useEffect(() => { const on = () => setAiOpen(true); window.addEventListener('feeless:agents-ai', on); return () => window.removeEventListener('feeless:agents-ai', on); }, []);
  if (!o || o.cold) return <section className="ack" data-testid="agent-cockpit"><MissionRibbon tiles={missionTiles(d, [])} cold /><p className="ack-nil">Waiting for the agents' first pass — the cockpit shows nothing it was not handed.</p></section>;
  const held = seats.filter(s => !s.open).length;
  const note = o.ai?.notes?.[mint]; const aiNote = note ? (note[agentNow] ? { ...note[agentNow], role: agentNow } : Object.entries(note).map(([role, v]) => ({ ...v, role }))[0]) : null;
  return <section className="ack" data-testid="agent-cockpit">
    <MissionRibbon tiles={tiles} live={!!cc?.live} />
    <LivePulse o={o} onAi={() => setTab('ai')} />
    <section className="ack-seats" data-testid="ack-seats"><header><b>🪑 SEAT BOARD</b><small><b className="m-pos">{held}/{seats.length || '—'} active</b> · live prices every 3s · tap a seat = its chart + the agent handling it</small></header>
      <div className="ack-seatrow">{seats.map(s => <SeatCard key={s.seat} s={s} on={!s.open && s.mint === mint} onPick={onPick} readyN={readyN} />)}</div></section>
    <div className="ack-main">
      <div className="ack-left"><CockpitChart m={model} iv={iv} setIv={setIv} pos={pos} cand={cand} markers={markers} onAgent={a => { setAgentS(a); setTab('live'); }} />
        <DecisionTape rows={o.tape} agent={tapeAgent} setAgent={setTapeAgent} fresh={freshIds} onPick={r => { if (r.mint) setPick(r.mint); setAgentS(r.agent in AG ? r.agent : null); setTab('live'); }} /></div>
      <DecisionPanel o={o} dec={dec} pos={pos} cand={cand} mint={mint} seats={seats} readyN={readyN} agent={agentNow} setAgent={a => { setAgentS(a); setTapeAgent(a); }} tab={tab} setTab={setTab}
        pulse={pulse} call={call} isOwner={isOwner} onPick={onPick} aiNote={aiNote} mcNow={model?.mc} onAi={() => setAiOpen(true)} /></div>
    <div className="ack-foot"><AgentMatrix o={o} gens={o?.generations || []} agent={agentNow} setAgent={a => { setAgentS(a); setTapeAgent(a); setTab('live'); }} rows={o.tape} pulse={pulse} />
      <ReviewQueue o={o} call={call} isOwner={isOwner} onPick={m => { onPick(m); if (m && !((o.kernel || {}).candidates || []).some(c => c.mint === m) && !(o.positions || []).some(p => p.mint === m) && !(o.ownerReview || []).some(r => r.mint === m)) openCoin({ mint: m }); }} sel={mint} /></div>
    <CockpitControls o={o} call={call} isOwner={isOwner} ai={o.ai} onAi={() => setAiOpen(true)} />
    {aiOpen ? createPortal(<AiProviders call={call} isOwner={isOwner} ai={o.ai} close={() => setAiOpen(false)} />, document.body) : null}
  </section>;
}
