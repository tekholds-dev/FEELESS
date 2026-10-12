import React, { Suspense, lazy, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ChartBox, DataLine, dqWord, dump, sgn, usd, ago, clock, ms, STRUCT_CLS } from './OfficeBoard';
import { tiny } from '../../lib/num';
import { useLiveCandles } from '../../lib/liveCandles';
import { useLivePrices } from '../../lib/livePrices';
import { EdgeBand, SocialLine } from './OfficeEdge';
import { SeatStrip, SeatsPane, ProofSources } from './SeatOps';
import '../../styles/officeRoom.css';

const OfficeRoom3D = lazy(() => import('./OfficeRoom3D'));
export const has3D = () => { try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); } catch (e) { return false; } };

// 🏢 THE AGENT OFFICE (HQ › Agents › 🏢 Office): the control room. LEFT = the room: ten stations in chain order, each showing what that
// desk did with the CURRENT candidate this pass, the candidate's own candles on the wall and the queue of case files. RIGHT = the
// selected desk live: its decision, the chart the agents read with their levels drawn on it, chart intelligence, last rulings,
// runtime and the code that runs it. BOTTOM = the roster of all ten. Every mark is a field of the one office payload
// (`backend/office.py` + `chart_intel.py`) — nothing here computes a trade number of its own.

export const AG = { tally: '#1fd178', sherlock: '#a07bff', weather: '#4fd8ff', trigger: '#f5c451', devil: '#ff6b86', warden: '#6c9bff', courier: '#ffb02e', reaper: '#c77dff', archivist: '#9fb3c8', judge: '#ffd166' };
export const TAG_WORD = { PASS: 'PASS', WAITING: 'WAIT', WORKING: 'REVIEW', OBJECT: 'OBJECT', VETO: 'VETO', DONE: 'DONE', ERROR: 'ERROR', STALE: 'STALE' };
export const TAG_CLS = { PASS: 'is-pass', DONE: 'is-pass', WAIT: 'is-wait', REVIEW: 'is-work', OBJECT: 'is-obj', STALE: 'is-obj', VETO: 'is-veto', ERROR: 'is-veto', EXIT: 'is-veto', 'TAKE PROFIT': 'is-work', PROTECT: 'is-obj', HOLD: 'is-pass', 'HOLD 5 MORE': 'is-pass', SIZED: 'is-pass' };
const URGENT = ['EXIT', 'TAKE PROFIT', 'PROTECT', 'HOLD 5 MORE', 'HOLD'];

// the position Reaper is most pressed on (an exit before a take before a protect before a hold)
export const hotPosition = positions => [...(positions || [])].sort((a, b) => URGENT.indexOf(a.decision) - URGENT.indexOf(b.decision) || (a.nextReview ?? 1e9) - (b.nextReview ?? 1e9))[0] || null;
// what each desk is doing NOW, in one word: its stage of the line for the current candidate — Reaper speaks for its most urgent
// open position, the Warden for the seat it last sized
export function agentTag(key, o) {
  const st = (o?.pipeline || []).find(s => s.agent === key);
  if (key === 'reaper') { const p = hotPosition(o?.positions); if (p) return [p.decision || p.state, `$${p.symbol}: ${p.rule} — ${p.evidence}`]; }
  if (key === 'warden' && o?.currentCase?.warden) { const w = o.currentCase.warden; return [w.veto ? 'VETO' : 'SIZED', `${usd(w.requested)} → ${usd(w.allowed)} (${w.decided})`]; }
  return [TAG_WORD[st?.state] || 'WAIT', st?.word || 'no candidate this pass'];
}
// ⚡ what each desk is DOING this pass — the word the room reacts to. Every word is read from the payload: Tally's coins read, a desk's
// stage for the candidate, the Warden's last sizing, the Courier's ledger (an order in flight = SUBMITTED, the last real action confirmed
// on the ledger = CONFIRMED), Reaper's most urgent position, the Archivist's filed cases, the Judge's rulings. → [word, why]
export const ACT_FX = { SCAN: '#45e486', PASS: '#45e486', WAIT: '#4d6a5c', REVIEW: '#6cc7ff', OBJECT: '#f5c451', VETO: '#ff4466', SIZED: '#6c9bff', SUBMITTED: '#ffb02e', CONFIRMED: '#45e486',
  PROTECT: '#f5c451', TAKE: '#6cc7ff', EXIT: '#ff4466', HOLD: '#45e486', LOGGING: '#9fb3c8', 'JUDGE REVIEW': '#ffd166', ERROR: '#ff4466', STALE: '#f5c451' };
const STAGE_ACT = { PASS: 'PASS', DONE: 'PASS', WAITING: 'WAIT', WORKING: 'REVIEW', OBJECT: 'OBJECT', VETO: 'VETO', ERROR: 'ERROR', STALE: 'STALE' };
export function activityOf(key, o) {
  const st = (o?.pipeline || []).find(s => s.agent === key); const stage = [STAGE_ACT[st?.state] || 'WAIT', st?.word || 'nothing this pass'];
  if (key === 'tally') return (o?.office?.coins ?? 0) > 0 && st?.state !== 'STALE' ? ['SCAN', `${o.office.coins} coins read this pass`] : stage;
  if (key === 'warden' && o?.currentCase?.warden) { const w = o.currentCase.warden; return [w.veto ? 'VETO' : 'SIZED', `${usd(w.requested)} → ${usd(w.allowed)} (${w.decided})`]; }
  if (key === 'courier') { const x = o?.execution || {}; const la = o?.mission?.lastAction;
    if (x.pending) return ['SUBMITTED', `${x.pending.side} $${x.pending.sym} in flight`];
    if (x.health === 'BAD') return ['VETO', `execution BAD — ${x.why || 'no new money until sends land'}`];
    if (la?.result?.state === 'confirmed' && o?.at && o.at - (la.result.at || la.at) <= 900) return ['CONFIRMED', `$${la.sym} ${la.move} confirmed on the ledger`];
    return stage; }
  if (key === 'reaper') { const p = hotPosition(o?.positions); if (!p) return ['WAIT', 'no open position'];
    const d = p.decision || p.state; return [d === 'TAKE PROFIT' ? 'TAKE' : d === 'EXIT' ? 'EXIT' : d === 'PROTECT' ? 'PROTECT' : 'HOLD', `$${p.symbol}: ${p.rule} — ${p.evidence}`]; }
  if (key === 'archivist') return (o?.office?.cases ?? 0) > 0 ? ['LOGGING', `${o.office.cases} case file${o.office.cases === 1 ? '' : 's'} filed this pass`] : stage;
  if (key === 'judge') return (o?.judge?.rulings ?? 0) > 0 ? ['JUDGE REVIEW', `${o.judge.rulings} rulings on the book · on trial: ${o.judge.trial || 'nobody'}`] : stage;
  return stage;
}
// where the current candidate stands: the first desk that has not passed it
export const focusOf = o => o?.queue?.[0]?.at || (o?.pipeline || []).find(s => !['PASS', 'DONE'].includes(s.state) && !['archivist', 'judge'].includes(s.agent))?.agent || 'tally';
export function ticker(o) {
  const names = Object.fromEntries((o?.agents || []).map(a => [a.key, a.name])); const c = o?.currentCase; const p = hotPosition(o?.positions);
  if (p && ['EXIT', 'TAKE PROFIT', 'PROTECT'].includes(p.decision)) return `Reaper: ${p.decision} $${p.symbol} — ${p.rule}`;
  if (c) { const at = focusOf(o); const st = (o.pipeline || []).find(s => s.agent === at); return `$${c.symbol} at ${names[at] || at} — ${st?.state || ''}: ${st?.word || ''}`; }
  return p ? `Reaper: ${p.decision} $${p.symbol}` : 'no candidate this pass';
}

// candles → SVG geometry. `levels` = [{ px, label, cls }] drawn as lines; everything is scaled to the candles AND the levels in view.
export function candleGeom(rows, levels = [], w = 420, h = 170, pad = 4) {
  const rs = (rows || []).filter(r => r && r[4] > 0); if (rs.length < 2) return null;
  const lv = (levels || []).filter(l => l && l.px > 0);
  let hi = Math.max(...rs.map(r => r[2])); let lo = Math.min(...rs.map(r => r[3])); const room = Math.max(hi - lo, hi * 0.004) * 1.5;   // a level joins the scale only when it is near the candles
  const cHi = hi; const cLo = lo; lv.forEach(l => { if (l.px <= cHi + room && l.px >= cLo - room) { hi = Math.max(hi, l.px); lo = Math.min(lo, l.px); } });
  const span = (hi - lo) || hi * 0.01 || 1; const y = px => pad + (1 - (px - lo) / span) * (h - 2 * pad); const step = (w - 54) / rs.length; const bw = Math.max(1.2, step * 0.62);
  const vmax = Math.max(0, ...rs.map(r => (r[5] > 0 ? r[5] : 0)));   // a volume bar exists ONLY where that row carries its own measured figure — never a filler
  return { w, h, hi, lo, last: rs[rs.length - 1][4], y, volN: rs.filter(r => r[5] > 0).length,
    vols: vmax > 0 ? rs.map((r, i) => (r[5] > 0 ? { x: i * step + step / 2, hgt: Math.max(1, (r[5] / vmax) * h * 0.16), up: r[4] >= r[1], bw } : null)).filter(Boolean) : [],
    bars: rs.map((r, i) => ({ x: i * step + step / 2, o: y(r[1]), h: y(r[2]), l: y(r[3]), c: y(r[4]), up: r[4] >= r[1], bw })),
    lines: lv.filter(l => l.px <= hi && l.px >= lo).map(l => ({ ...l, y: y(l.px) })),
    off: lv.filter(l => l.px > hi || l.px < lo).map(l => ({ ...l, up: l.px > hi })) };   // too far to draw to scale: named at the edge it lies beyond, never squashed in
}

const PriceChartLazy = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
const LV_COLOR = { 'is-entry': '#15d16a', 'is-take': '#9fe3ff', 'is-stop': '#ff8fa3', 'is-sup': '#f5c542' };
// 👁 THE LIVE CHART: the same FEELESS PriceChart the war room and the mini chart draw (live 1-minute candles, its own stream), with the
// agents' levels on it; under it, the data-quality line of what the agents themselves read on their last pass
export function LiveChart({ view, big }) {
  const live = useLivePrices(view?.pair ? [view.pair] : []).get(view?.pair);   // 📊 every chart opens on MARKET CAP (the shared live-price record carries `mc`)
  const mc = live?.mc > 0 && live?.price > 0 ? live.mc : null;
  const pair = useMemo(() => (view?.pair ? { chainId: 'solana', pairAddress: view.pair, baseToken: { address: view.mint, symbol: view.symbol }, priceUsd: live?.price ?? view.px ?? null, marketCap: mc } : null), [view?.pair, view?.mint, view?.symbol, view?.px, live?.price, mc]);
  const lines = useMemo(() => ({ lines: (view?.levels || []).map(l => ({ px: l.px, title: l.label, color: LV_COLOR[l.cls] })) }), [view?.levels]);
  if (!pair) return <div className="ofr-nochart" data-testid="ofr-nochart">no pool for this coin — nothing to chart</div>;
  const q = view.bars?.q;
  return <figure className={`ofr-chart ${big ? 'is-big' : ''}`} data-testid="ofr-chart" data-tip="The live FEELESS chart of this coin — the same chart the war room draws — with the agents' levels on it.">
    <div className="ofr-live-chart"><Suspense fallback={<div className="ofr-nochart">loading the live chart…</div>}>
      <PriceChartLazy key={`${view.pair}-${mc ? 'mc' : 'px'}`} pair={pair} interval="1m" metric={mc ? 'marketCap' : 'price'} /* the agents' levels are scaled to the cap by the chart itself */ showVolume fuse={lines} />
    </Suspense></div>
    <figcaption>LIVE · the FEELESS chart{view.note ? ` · ${view.note}` : ''} · <button type="button" className="ofr-wr" onClick={() => window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: pair }))} data-testid="ofr-warroom">⚔ war room</button></figcaption>
    {q ? <DataLine q={q} compact noVol /> : null}
  </figure>;
}

// the coin on screen: the current candidate, or an open position (then its entry / take / stop / invalidation are drawn)
export function coinView(o, sym) {
  const p = (o?.positions || []).find(x => x.symbol === sym);
  if (p) { const e = p.entry; const th = p.thesis;
    return { kind: 'position', symbol: p.symbol, pair: p.pair, mint: p.mint, px: p.px, bars: p.bars, pos: p, structure: p.structure, note: `REAPER: ${p.decision}`,
      levels: [e && { px: e, label: 'entry', cls: 'is-entry' }, e && p.take && { px: e * (1 + p.take / 100), label: `take +${p.take}%`, cls: 'is-take' }, e && p.stop && { px: e * (1 + p.stop / 100), label: `stop ${p.stop}%`, cls: 'is-stop' },
        th?.invalidation && { px: th.invalidation, label: 'invalid', cls: 'is-stop' }, th?.support && { px: th.support, label: 'support', cls: 'is-sup' }].filter(Boolean) }; }
  const cc = o?.currentCase; const c = cc && (!sym || cc.symbol === sym) ? cc : (o?.queue || []).find(x => x.symbol === sym && x.chart);   // any candidate of the pass: its own rows + chart read
  if (!c) return null; const f = c.chart?.f || {};
  return { kind: 'case', symbol: c.symbol, pair: c.pair, mint: c.mint, px: c.px, bars: c.bars, cur: c, structure: c.chart?.state, note: c.chart ? `TRIGGER: ${c.chart.entry?.[0]}` : null,
    levels: [f.resistance && { px: f.resistance, label: 'resist', cls: 'is-take' }, f.support && { px: f.support, label: 'support', cls: 'is-sup' },
      f.px && c.chart?.stop && { px: f.px * (1 - c.chart.stop / 100), label: `stop −${c.chart.stop}%`, cls: 'is-stop' }].filter(Boolean) };
}

// the ONE line each desk's monitor shows this pass — a field of the payload per desk, never a canned phrase
export function deskLine(key, o) {
  const a = (o?.agents || []).find(x => x.key === key) || {}; const c = o?.currentCase; const wx = (o?.agents || []).find(x => x.key === 'weather')?.output || {}; const x = o?.execution || {}; const p = hotPosition(o?.positions);
  if (key === 'tally') return `${o?.office?.coins ?? 0} coins read${c ? ` · $${c.symbol} ${c.tally?.readings ?? 0} readings` : ''}`;
  if (key === 'sherlock') return c ? `$${c.symbol} ${c.chart?.state || 'no chart'} · lean ${sgn(c.lean, 1, '')}` : 'no candidate';
  if (key === 'weather') return wx.regime ? `${wx.regime} · bar ${sgn(wx.mods?.barAdj, 2, '')} · size ×${wx.mods?.size ?? '—'}` : 'no regime yet';
  if (key === 'trigger') return c ? `$${c.symbol} ${c.chart?.entry?.[0] || String(c.trigger?.call?.[0] || '').toUpperCase()}` : 'no candidate';
  if (key === 'devil') return c ? (c.devil?.objections?.length ? `OBJECT ${c.devil.objections[0].rule}` : 'no objection') : 'no candidate';
  if (key === 'warden') { const w = c?.warden; return w ? `${w.eff}× · ${usd(w.requested)} → ${usd(w.allowed)}` : c?.chart ? `chart risk ${c.chart.risk?.[0]}× · sizes when a seat opens` : 'waits for a seat'; }
  if (key === 'courier') { const l = x.last?.[0]; return `${x.health || '—'} · ${x.fills ?? 0}/${x.sends ?? 0} confirmed${x.pending ? ` · ${x.pending.side} $${x.pending.sym} in flight` : l ? ` · last ${l.state}` : ''}`; }
  if (key === 'reaper') return p ? `$${p.symbol} ${sgn(p.pct)} · ${p.structure || 'no chart'} · ${p.obeying}` : 'no open position';
  if (key === 'archivist') return a.decision || 'nothing filed yet';
  return a.decision || 'no ruling yet';
}
// THE REAL CARD as the room draws it: one slot per seat — who holds it (agents · suggested · yours · engine · open), its % since entry,
// what the desk decided for it, Reaper's ruling — and the open seats with the seat state (FILLING / NO VALID ENTRY / WARMING UP …)
export function seatsOf(o, card, coin) {
  const rep = Object.fromEntries((o?.positions || []).map(p => [p.symbol, p])); const seat = o?.seat || {};
  const rows = (card?.seats || []).length ? card.seats : (o?.positions || []).map(p => ({ symbol: p.symbol, kind: p.owner === 'agents' ? 'agent' : 'engine', pct: p.pct }));
  // 🪑 this cycle's result per seat (velocity · score · best challenger · next candidate): a held seat by its coin, an open one by order
  const sbHeld = Object.fromEntries((o?.seatBoard || []).filter(b => !b.empty && b.symbol).map(b => [b.symbol, b])); const sbOpen = (o?.seatBoard || []).filter(b => b.empty); let k = 0;
  const out = rows.slice(0, 6).map((x, i) => { const r = x.symbol ? rep[x.symbol] : null; const open = x.kind === 'open' || !x.symbol; const b = open ? (sbOpen[k++] || null) : (sbHeld[x.symbol] || null);
    return { i, symbol: open ? null : x.symbol, kind: open ? 'open' : x.kind, pct: open ? null : (x.pct ?? r?.pct ?? null), action: x.action || null, toSym: x.toSym || null,
      decision: open ? (b?.code || seat.state || 'OPEN') : b?.result || r?.decision || (x.action ? String(x.action).toUpperCase() : 'HOLD'), rule: r?.rule || null, state: x.state || '', buying: !!x.buying, selected: !!coin && coin === x.symbol,
      vel: b?.vel || null, score: b?.score ?? null, chal: b?.challenger?.symbol || null, margin: b?.margin ?? null, need: b?.need ?? null, next: b?.next?.symbol || null, ready: !!b?.ready, sb: b }; });
  const want = seat.want || 0;
  for (let i = out.length; i < Math.min(6, want); i += 1) out.push({ i, symbol: null, kind: 'open', pct: null, decision: seat.state || 'OPEN', rule: null, state: '', selected: false });
  return out;
}
// everything the 3D room draws, as plain data: ten stations (action word · state · monitor line · focus · selected), the wall monitor
// (coin · stage · structure · decision · Warden · Devil · review clock · the candles + levels), the pipeline counts, and the edge pass:
// the card's seats, restart readiness, the switch test, who decides each control, the winners we missed
export function roomModel(o, sel, coin, card) {
  const focus = focusOf(o); const names = Object.fromEntries((o?.agents || []).map(a => [a.key, a.name])); const hot = hotPosition(o?.positions);
  const view = coinView(o, coin) || coinView(o, o?.currentCase?.symbol) || (hot ? coinView(o, hot.symbol) : null); const c = view?.cur; const p = view?.pos;
  const wall = !view ? null : { kind: view.kind, symbol: view.symbol, pair: view.pair, mint: view.mint, bars: view.bars, levels: view.levels, structure: view.structure || 'NO CHART', move: p ? p.pct : c?.chart?.f?.r5 ?? null,
    stage: p ? 'Reaper' : names[focus] || focus, decision: p ? p.decision : c?.chart?.entry?.[0] || String(c?.trigger?.call?.[0] || '—').toUpperCase(),
    warden: p ? (p.warden != null ? `${p.warden}×` : 'not sized') : c?.warden ? `${c.warden.eff}×${c.warden.veto ? ' VETO' : ''}` : c?.chart ? `${c.chart.risk?.[0]}× chart risk` : '—',
    devil: p ? (p.devil === 'object' ? 'OBJECT' : p.devil === 'agree' ? 'NO OBJECTION' : '—') : c?.devil?.verdict === 'agree' ? 'NO OBJECTION' : c?.devil ? 'OBJECT' : '—',
    reviewAt: p?.nextReview != null ? Math.max(0, p.nextReview - (Date.now() / 1000 - (o?.at || Date.now() / 1000))) : null,
    facts: p ? [['ENTRY', tiny(p.entry)], ['PEAK', sgn(p.peak)], ['HELD', p.heldMin != null ? `${Math.round(p.heldMin)}m` : '—'], ['TAKE', p.take != null ? `+${p.take}%` : '—'], ['STOP', p.stop != null ? `${p.stop}%` : '—'], ['LIQ', p.liq != null ? `$${Math.round(p.liq / 1000)}K` : '—']]
      : [['LIQ', c?.sherlock?.vitals?.liq != null ? `$${Math.round(c.sherlock.vitals.liq / 1000)}K` : '—'], ['AGE', c?.sherlock?.vitals?.ageH != null ? `${Number(c.sherlock.vitals.ageH).toFixed(1)}h` : '—'], ['BUYS', c?.chart?.f?.buy != null ? `${Math.round(c.chart.f.buy)}%` : '—'],
         ['TOP-10', c?.sherlock?.vitals?.top10 != null ? `${Math.round(c.sherlock.vitals.top10)}%` : '—'], ['LEAN', c?.lean != null ? sgn(c.lean, 1, '') : '—'], ['TREND', c?.chart?.trend != null ? `${c.chart.trend}/100` : '—']],
    data: view.bars?.q || c?.chart?.q || p?.data || null,
    caption: view.bars ? `${view.bars.q ? `DATA ${dqWord(view.bars.q)} ${view.bars.q.conf}% · ` : ''}${view.bars.src === 'candles' ? `${view.bars.rows.length} one-minute candles` : `RECONSTRUCTED FROM TAPE · ${view.bars.rows.length} readings`} · VOLUME ${view.bars.volume || 'UNAVAILABLE'}` : 'no candles this pass' };
  return { wall, focus,
    stations: (o?.agents || []).map(a => { const [tag] = agentTag(a.key, o); const [act, actWhy] = activityOf(a.key, o); const c = a.card || {}; const pf = o?.performance?.agents?.[a.key] || {};
      return { key: a.key, name: a.name, icon: a.icon, tag, cls: TAG_CLS[tag] || 'is-wait', act, actWhy, color: ACT_FX[act] || '#4d6a5c', line: deskLine(a.key, o), focus: focus === a.key, selected: sel === a.key,
        gen: c.gen ?? 1, status: c.status || null, acc: c.accuracy ?? null, n: c.n ?? 0, ms: pf.last ?? c.latency?.last ?? null, series: (pf.series || []).slice(-24) }; }),
    cases: (o?.queue || []).slice(0, 6).map((x, i) => ({ symbol: x.symbol, mint: x.mint, at: x.at, state: TAG_WORD[x.state] || x.state, cleared: !!x.cleared, go: !!x.go, structure: x.structure || null, current: i === 0, selected: !!coin && coin === x.symbol })),
    status: [[o?.seatSummary ? `${o.seatSummary.occupancy}/${o.seatSummary.target}` : (o?.positions || []).length, 'seats held', '#a07bff'], [o?.seatSummary ? `${o.seatSummary.benchReady}/${o.seatSummary.bench}` : '—', 'bench ready', '#6cc7ff'],
      [o?.office?.cleared ?? 0, 'cleared', '#45e486'], [(o?.office?.cases ?? 0) - (o?.office?.cleared ?? 0), 'blocked', '#f5c451'], [o?.cycle?.read ?? o?.office?.coins ?? 0, 'coins read this pass', '#7d998b'], [o?.execution?.health || '—', 'execution', o?.execution?.health === 'HEALTHY' ? '#45e486' : '#ff6b86']],
    summary: o?.seatSummary || null, turnover: (o?.cycleLog || []).slice(-14).map(l => [l.n, l.intake?.newUnique ?? null, l.intake?.deskNew ?? null]),
    seats: seatsOf(o, card, coin), seat: o?.seat ? { state: o.seat.state, reason: o.seat.reason, emptyFor: o.seat.emptyFor, target: o.seat.target } : null,
    ready: o?.ready ? { state: o.ready.state, live: !!o.ready.live, steps: o.ready.steps || [], why: o.ready.why } : null,
    swap: o?.switchEval ? { from: o.switchEval.current?.symbol || null, to: o.switchEval.challenger?.symbol || null, ok: !!o.switchEval.switch, edge: o.switchEval.edge, need: o.switchEval.need, why: o.switchEval.why,
      lines: (o.switchEval.lines || []).map(l => [l[0], !!l[1]]) } : null,
    limits: o?.policy ? { manual: !!o.policy.manual, rows: (o.policy.controls || []).map(c => [c.label, c.who === 'CREATOR OVERRIDE', c.who === 'CREATOR OVERRIDE' ? String(c.value) : 'agents']) } : null,
    missed: o?.review ? { n: o.review.missedSummary?.n ?? 0, correct: o.review.missedSummary?.correct ?? 0, reasons: (o.review.missedSummary?.byReason || []).slice(0, 4).map(r => [r.key, r.n]),
      open: Object.values(o.review.open || {}).reduce((a, b) => a + b, 0) } : null };
}
// the office's latest rulings, newest first, every desk in one list (each line is that desk's own recorded decision)
export function rulingsOf(o, n = 8) {
  const now = (o?.agents || []).filter(a => a.decision && a.decisionAt).map(a => ({ at: a.decisionAt, key: a.key, name: a.name, text: a.decision })).sort((x, y) => y.at - x.at);
  const seen = new Set(now.map(r => `${r.key}|${r.text}`));
  const past = (o?.agents || []).flatMap(a => (a.recent || []).filter(r => r.at && !seen.has(`${a.key}|${r.text}`)).map(r => ({ at: r.at, key: a.key, name: a.name, text: r.text }))).sort((x, y) => y.at - x.at);
  return [...now, ...past].slice(0, n);
}
// 🧵 the team decision trace of ONE candidate: each desk's answer to its own question, then FINAL + WHY (a field of the payload)
export const traceOf = (o, sym) => (o?.queue || []).find(x => x.symbol === sym)?.trace || (o?.currentCase?.symbol === sym ? o.currentCase.trace : null) || null;
export function TeamTrace({ t, pos }) {
  if (!t && !pos) return null;
  const lines = t ? t.lines : [['reaper', pos.decision, pos.rule]];
  return <div className="ofr-trace" data-testid="ofr-trace"><small>TEAM TRACE · ${t ? t.symbol : pos.symbol} · one mission, each desk its own question</small>
    {t ? <p data-tip={t.why} className={`ofr-final ${{ GO: 'is-go', CLEARED: 'is-cleared', SKIP: 'is-skip', BLOCKED: 'is-blocked' }[String(t.final).split(' ')[0]] || ''}`} data-testid="ofr-final"><b>FINAL</b><em>{t.final}</em><span><u>WHY</u> {t.why}</span></p> : null}
    <ul>{lines.map(l => <li key={l[0]} style={{ '--ag': AG[l[0]] }} data-tip={l[2] || undefined}><b>{l[0].toUpperCase()}</b><span>{l[1]}</span></li>)}</ul></div>;
}
export const hhmm = at => { const d = new Date(at * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const Tag = ({ cls, children, tip }) => <i className={`ofr-tag ${cls || ''}`} data-tip={tip}>{children}</i>;
const Bot = () => <span className="ofr-bot" aria-hidden><i className="ofr-ant" /><i className="ofr-head"><u /><u /></i><i className="ofr-body" /></span>;
const Spark = ({ xs, cls }) => { const v = (xs || []).filter(x => x != null); if (v.length < 2) return <svg className="ofr-spark" viewBox="0 0 60 18" aria-hidden />;
  const hi = Math.max(...v); const lo = Math.min(...v); const sp = (hi - lo) || 1;
  return <svg className={`ofr-spark ${cls || ''}`} viewBox="0 0 60 18" preserveAspectRatio="none" aria-hidden><polyline points={v.map((x, i) => `${(i / (v.length - 1)) * 60},${16 - ((x - lo) / sp) * 14}`).join(' ')} /></svg>; };

export function RoomScene({ o, sel, onSel, coin, onCoin, card, onSeat }) {
  const focus = focusOf(o); const c = o.currentCase; const view = coinView(o, coin) || coinView(o, c?.symbol) || (o.positions?.[0] ? coinView(o, o.positions[0].symbol) : null);
  const q = o.queue || []; const f = view?.cur?.chart?.f || {}; const vit = view?.cur?.sherlock?.vitals || {};
  const r5 = view?.kind === 'position' ? view.pos.pct : f.r5;
  return <div className="ofr-room" data-testid="ofr-room">
    <i className="ofr-floor" aria-hidden /><i className="ofr-glow" aria-hidden /><i className="ofr-lights" aria-hidden />
    <div className="ofr-wall">
      <div className="ofr-sign" aria-hidden><b>FEELESS HQ</b><span>AGENT OFFICE</span></div>
      <div className="ofr-screen" data-testid="ofr-screen">
        <small>{view?.kind === 'position' ? 'OPEN POSITION' : 'CURRENT CANDIDATE'}</small>
        {view ? <><div className="ofr-shead"><b>${view.symbol}</b>{view.structure ? <Tag cls={STRUCT_CLS[view.structure]}>{view.structure}</Tag> : null}
          <em className={r5 > 0 ? 'ofr-pos' : r5 < 0 ? 'ofr-neg' : ''}>{r5 == null ? '—' : sgn(r5)}<u>{view.kind === 'position' ? ' since entry' : ' 5m'}</u></em></div>
          <LiveChart view={view} />
          {view.kind === 'case' ? <p className="ofr-facts"><span>liq <b>{vit.liq != null ? `$${(vit.liq / 1000).toFixed(0)}K` : '—'}</b></span><span>age <b>{vit.ageH != null ? `${Number(vit.ageH).toFixed(1)}h` : '—'}</b></span><span>buy <b>{f.buy != null ? `${Math.round(f.buy)}%` : '—'}</b></span><span>top-10 <b>{vit.top10 != null ? `${Math.round(vit.top10)}%` : '—'}</b></span></p>
            : <p className="ofr-facts"><span>peak <b>{sgn(view.pos.peak)}</b></span><span>held <b>{clock((view.pos.heldMin || 0) * 60)}</b></span><span>obeying <b>{view.pos.obeying}</b></span></p>}</>
          : <span className="ofr-nil">no candidate and no open position this pass</span>}
      </div>
      <div className="ofr-status" data-testid="ofr-status"><small>PIPELINE STATUS</small>
        <span><i className="is-pass" />{o.office?.cleared ?? 0}<u>cleared</u></span><span><i className="is-obj" />{(o.office?.cases ?? 0) - (o.office?.cleared ?? 0)}<u>blocked</u></span>
        <span><i className="is-work" />{(o.positions || []).length}<u>open positions</u></span><span><i className="is-wait" />{o.office?.coins ?? 0}<u>coins read</u></span>
        <span className={`ofr-health ${o.execution?.health === 'HEALTHY' ? 'is-pass' : o.execution?.health === 'BAD' ? 'is-veto' : 'is-obj'}`}>📮 {o.execution?.health || '—'}</span></div>
    </div>
    <ol className="ofr-desks">{(o.agents || []).map((a, i) => { const [tag, word] = agentTag(a.key, o); const st = (o.pipeline || []).find(s => s.agent === a.key);
      return <li key={a.key} className={`ofr-desk ${TAG_CLS[tag] || 'is-wait'} ${focus === a.key ? 'is-focus' : ''} ${sel === a.key ? 'is-on' : ''}`} style={{ '--ag': AG[a.key], '--i': i }}>
        <button type="button" onClick={() => onSel(a.key)} aria-pressed={sel === a.key} data-tip={`${a.name}: ${word}`} data-testid={`desk-${a.key}`}>
          <span className="ofr-chip"><b>{a.name}</b><em>{tag}</em></span>
          <span className="ofr-station"><i className="ofr-pad" aria-hidden /><Bot /><span className="ofr-rig"><span className="ofr-mon"><i>{tag}</i><u /></span><span className="ofr-mon is-b"><i>{st?.ms != null ? ms(st.ms) : '—'}</i><u /></span></span><i className="ofr-slab" aria-hidden /></span>
          <span className="ofr-word">{word}</span></button>
        {i < 9 && i !== 4 ? <i className="ofr-arrow" aria-hidden /> : null}</li>; })}</ol>
    <div className="ofr-queue" data-testid="ofr-queue"><small>CASE FILES THIS PASS</small>{q.length ? q.map(x => <button key={x.mint} type="button" className={`ofr-case ${coin === x.symbol ? 'is-on' : ''} ${x.cleared ? 'is-pass' : 'is-obj'}`} style={{ '--ag': AG[x.at] }}
      onClick={() => { onCoin(x.symbol); onSel(x.at); }} data-tip={x.word} data-testid={`case-${x.symbol}`}><b>${x.symbol}</b><em>{x.structure || 'no chart'}</em><u>at {x.at} · {TAG_WORD[x.state] || x.state}</u></button>) : <span className="ofr-nil">no case file this pass</span>}</div>
    <div className="ofr-cardrow" data-testid="ofr-cardrow"><small>THE REAL CARD · {o.seat ? `${o.seat.held}/${o.seat.want} seats · ${o.seat.state}` : 'seats'}{o.ready && !o.ready.live ? ` · ${o.ready.state}` : ''}</small>
      {seatsOf(o, card, coin).map(x => <button key={x.i} type="button" className={`ofr-seat is-${x.kind} ${x.selected ? 'is-on' : ''}`} onClick={() => (onSeat ? onSeat(x.sb || (x.symbol ? { symbol: x.symbol } : { empty: true, seat: x.i + 1 })) : x.symbol && onCoin(x.symbol))} data-tip={x.rule ? `${x.rule}` : x.symbol ? x.decision : `open seat — ${x.decision}${x.next ? ` · next $${x.next}` : ''}`} data-testid={`seat-${x.i}`}>
        <b>{x.symbol ? `$${x.symbol}` : 'open'}</b><em className={x.pct > 0 ? 'ofr-pos' : x.pct < 0 ? 'ofr-neg' : ''}>{x.pct == null ? '—' : sgn(x.pct)}</em><u>{x.kind} · {x.decision}</u></button>)}</div>
    <p className="ofr-flow"><span>Flow: {(o.office?.chain || []).join(' → ')}</span><b data-testid="ofr-ticker">{ticker(o)}</b></p>
  </div>;
}

// 🎛 YOUR LIMIT vs WHAT THE AGENTS CHOOSE vs THE RULE IN FORCE, for the coin on screen — every cell is a field of the payload
// (policy.controls · take · the position's own take / stop / granted windows / limits / Warden size). Nothing here decides anything.
const fmtYours = (k, v) => (k === 'agentTp' ? `+${v}%` : k === 'agentSl' ? `−${v}%` : k === 'agentMaxHold' ? `${v} min` : k === 'agentSizePct' ? `≤ ${v}%` : String(v));
export function policyRows(o, p) {
  const pol = o?.policy || {}; const c = Object.fromEntries((pol.controls || []).map(x => [x.key, x])); const tk = o?.take || {};
  const yours = k => (c[k]?.who === 'CREATOR OVERRIDE' ? fmtYours(k, c[k].value) : null); const now = k => c[k]?.agentsNow || null;
  return [['Take profit', yours('agentTp'), now('agentTp'), p ? `+${p.take}% · ${p.takeSource} line` : tk.active != null ? `+${tk.active}% · ${tk.source} line` : '—'],
    ['Stop-loss', yours('agentSl'), now('agentSl'), p?.stop != null ? `${p.stop}%${p.limits?.sl ? ' · your stop binds' : ''}` : yours('agentSl') ? `their structure stop, never past ${yours('agentSl')}` : 'their structure stop, set at entry'],
    ['Max hold', yours('agentMaxHold'), now('agentMaxHold'), p?.granted != null ? `${p.granted * 5} min · ${p.granted} windows` : p?.limits?.maxHold ? `${p.limits.maxHold} min` : yours('agentMaxHold') ? `≤ ${yours('agentMaxHold')}` : 'their thesis windows'],
    ['Trailing', c.agentTrail?.who === 'CREATOR OVERRIDE' ? (pol.trail?.mode === 'custom' ? `+${pol.trail.arm}% / ${pol.trail.pct} pts` : 'off') : null, now('agentTrail'), (p ? p.limits?.trail : pol.trail?.mode) === 'off' ? 'off' : (p ? p.limits?.trail : pol.trail?.mode) === 'custom' ? 'your trail' : 'their trail'],
    ['Seat size', yours('agentSizePct'), now('agentSizePct'), p?.warden != null ? `${p.warden}× by the Warden` : yours('agentSizePct') ? `the Warden, ${yours('agentSizePct')} of the card` : 'the Warden sizes it'],
    ['Switching', yours('agentSwitch'), now('agentSwitch'), pol.switch ? (pol.switch.on ? `margin ≥ ${pol.switch.edge} after ${pol.switch.holdMin} min` : 'off') : '—']];
}
export function PolicyBlock({ o, p }) {
  const pol = o?.policy; if (!pol) return null;
  return <div className="ofr-policy" data-testid="ofr-policy"><small>POLICY · {p ? `$${p.symbol}` : 'the next seat'}{pol.manual ? ' · ✋ CREATOR MANUAL — the agents make no move' : ''}</small>
    <table><thead><tr><th>control</th><th className="is-you">YOU</th><th className="is-agents">AGENTS</th><th>IN FORCE</th></tr></thead>
      <tbody>{policyRows(o, p).map(([l, y, ag, eff]) => <tr key={l} className={y ? 'is-you' : 'is-agents'}><td>{l}</td><td className="is-you">{y || '—'}</td><td className="is-agents" data-tip={ag || undefined}>{y ? 'overridden' : ag || 'not read yet'}</td><td><b>{eff}</b></td></tr>)}</tbody></table></div>;
}
// 🚀 the launch context of the coin on screen — only what is measured (office_edge.launch_context); unknown stays UNKNOWN
export const launchOf = (o, sym) => (o?.positions || []).find(x => x.symbol === sym)?.launch || (o?.queue || []).find(x => x.symbol === sym)?.launch || null;
export const PANEL_TABS = [['live', 'Live decision'], ['seats', '🪑 Seats'], ['beliefs', 'Beliefs & ethics'], ['inputs', 'Current inputs'], ['chart', 'Chart intel'], ['code', 'Source code']];

export function AgentPanel({ o, a, coin, onCoin, tabReq }) {
  const [tab, setTab] = useState(() => tabReq?.tab || 'live'); const [, tick] = useState(0);
  useEffect(() => { if (tabReq?.tab) setTab(tabReq.tab); }, [tabReq]);   // a seat / board clicked in the room opens the view that explains it
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(t); }, []);
  if (!a) return null;
  const c = a.card || {}; const [tag, word] = agentTag(a.key, o); const hot = hotPosition(o.positions);
  const view = (a.key === 'reaper' && !coin && hot ? coinView(o, hot.symbol) : coinView(o, coin)) || coinView(o, o.currentCase?.symbol) || (hot ? coinView(o, hot.symbol) : null);
  const p = view?.pos; const ch = view?.cur?.chart; const wd = view?.cur?.warden; const tk = o.take || {};
  const review = p?.nextReview != null ? Math.max(0, p.nextReview - (Date.now() / 1000 - (o.at || 0))) : null;
  const coins = [...new Set([o.currentCase?.symbol, ...(o.positions || []).map(x => x.symbol), ...(o.queue || []).filter(x => x.chart).map(x => x.symbol)].filter(Boolean))].slice(0, 6);
  return <aside className="ofr-panel" style={{ '--ag': AG[a.key] }} data-testid="ofr-panel">
    <header className="ofr-phead"><span className="ofr-pname" data-tip={a.role}><b>{a.icon} {a.name.toUpperCase()}</b><small>gen {c.gen ?? 1} · {a.role}</small></span>
      <Tag cls={c.status === 'alive' ? 'is-pass' : 'is-obj'} tip={c.why}>● {c.status === 'alive' ? 'LIVE' : (c.status || '—').toUpperCase()}</Tag></header>
    <div className="m-seg ofr-tabs" role="tablist" aria-label={`${a.name} views`}>{PANEL_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`ptab-${k}`}>{l}</button>)}</div>
    {tab === 'live' && <div className="ofr-pane" data-testid="pane-live">
      <div className="ofr-decision" data-tip={`${a.decision || word}${a.rule ? ` · rule: ${a.rule}` : ''}`}><small>CURRENT DECISION · {ago(a.decisionAt)}{a.rule ? ` · rule: ${a.rule}` : ''}</small><b><Tag cls={TAG_CLS[tag]}>{tag}</Tag>{a.decision || word}</b>
        {review != null ? <em className="ofr-count" data-tip="Reaper's next 5-minute review of this position">⏱ {clock(review)}</em> : null}</div>
      <div className="ofr-tiles">
        <span data-tip="How much judged record stands behind this desk (samples ÷ (samples + 30)) and how often it was right."><small>RECORD</small><em>{c.accuracy == null ? '—' : `${c.accuracy}%`}</em><u>{c.n ?? 0} samples · conf {c.confidence != null ? `${Math.round(c.confidence * 100)}%` : '—'}</u></span>
        <span data-tip="The lines this coin trades inside: the active take line and the stop for this entry. Not a forecast."><small>TAKE / STOP</small><em>{p ? `+${p.take}% / ${p.stop}%` : ch ? `+${tk.active ?? '—'}% / −${ch.stop}%` : '—'}</em><u>{p ? `${p.takeSource} take` : `${tk.source || '—'} take`}</u></span>
        <span><small>RISK</small><em>{ch ? `${ch.risk?.[0]}×` : p?.warden != null ? `${p.warden}×` : '—'}</em><u>{ch ? ch.risk?.[1] : p ? `sized by the Warden` : 'no chart risk read'}</u></span>
        <span><small>POSITION SIZE</small><em>{p ? usd(p.usd) : wd ? usd(wd.allowed) : '—'}</em><u>{p ? 'on the card now' : wd ? `asked ${usd(wd.requested)} · ${wd.decided}` : 'sized when a seat opens'}</u></span></div>
      <div className="ofr-csel"><small>CHART</small>{coins.map(s => <button key={s} type="button" className={view?.symbol === s ? 'is-on' : ''} onClick={() => onCoin(s)} data-testid={`coin-${s}`}>${s}</button>)}
        {review != null ? <em data-testid="ofr-review">⏱ next review {clock(review)}</em> : null}</div>
      {view ? <LiveChart view={view} big /> : <div className="ofr-nochart">no candidate and no open position this pass</div>}
      <div className="ofr-intel" data-testid="ofr-intel"><small>CHART INTELLIGENCE{view ? ` · $${view.symbol}` : ''}</small>
        {(() => { const s = ch || p?.chart; const st = view?.structure; return <div className="ofr-igrid">
          <span><u>Structure</u><b>{st ? <Tag cls={STRUCT_CLS[st]}>{st}</Tag> : '—'}</b></span><span><u>Trend</u><b>{s?.trend ?? '—'}<i>/100</i></b></span><span><u>Chop</u><b>{s?.chop ?? '—'}<i>/100</i></b></span>
          <span><u>Momentum</u><b>{s?.mom ?? '—'}<i>/100</i></b></span><span><u>Extension</u><b>{s?.ext ?? '—'}<i>/100</i></b></span>
          <span><u>Flow</u><b>{ch?.f?.buy != null ? `${Math.round(ch.f.buy)}% buy` : '—'}</b></span><span><u>Liquidity</u><b>{ch?.f?.liq != null ? `$${(ch.f.liq / 1000).toFixed(0)}K` : p?.liq != null ? `$${(p.liq / 1000).toFixed(0)}K` : '—'}</b></span>
          <span><u>Warden size</u><b>{wd ? `${wd.eff}×` : p?.warden != null ? `${p.warden}×` : ch ? `${ch.risk?.[0]}× chart` : '—'}</b></span>
          <span><u>Reaper next review</u><b>{review != null ? clock(review) : '—'}</b></span><span><u>Active take source</u><b>{p?.takeSource || tk.source || '—'} +{p?.take ?? tk.active ?? '—'}%</b></span>
          <span className="is-wide"><u>{p ? 'Thesis' : 'Entry call'}</u><b>{p ? (p.thesis ? `${p.thesis.structure} · ${p.thesis.triggerRule} → now ${p.verdict || 'unchecked'}` : 'no thesis on file') : ch ? `${ch.entry?.[0]} — ${ch.entry?.[2]}` : '—'}</b></span></div>; })()}</div>
      <PolicyBlock o={o} p={p} />
      {(() => { const ln = view ? launchOf(o, view.symbol) : null; return ln ? <p className="ofr-launch" data-testid="ofr-launch"><small>LAUNCH</small><b>{ln.pad}</b><span>{ln.type}</span>{ln.curvePct != null ? <span>curve {Math.round(ln.curvePct)}%</span> : null}{ln.ageH != null ? <span>{Number(ln.ageH).toFixed(1)}h old</span> : null}{ln.graduated != null ? <span>{ln.graduated ? 'graduated' : 'pre-graduation'}</span> : null}<u>measured from the mint + the launch board · anything else UNKNOWN</u></p> : null; })()}
      {view ? <SocialLine p={(o.social || {})[view.cur?.mint || p?.mint]} /> : null}
      {view ? <ProofSources p={(o.social || {})[view.cur?.mint || p?.mint]} mint={view.cur?.mint || p?.mint} now={o.at} /> : null}
      <TeamTrace t={view?.kind === 'case' ? traceOf(o, view.symbol) : null} pos={p} />
      <div className="ofr-rul" data-testid="ofr-rulings"><small>LIVE RULINGS · every desk, newest first</small>{rulingsOf(o, 3).length ? <ul>{rulingsOf(o, 3).map((r, i) => <li key={i} className={r.key === a.key ? 'is-me' : ''} style={{ '--ag': AG[r.key] }} data-tip={r.text}><u>{hhmm(r.at)}</u><b>{r.name}</b> {r.text}</li>)}</ul> : <span className="ofr-nil">none on record yet</span>}</div>
      <p className="ofr-files" data-testid="ofr-files"><small>RUNTIME last {ms(c.latency?.last)} · p95 {ms(c.latency?.p95)}</small>{(a.code || []).map(k => <span key={k.file}><code>{k.file}</code><code className="ofr-fn">{k.fn[0]}()</code></span>)}</p>
    </div>}
    {tab === 'seats' && <SeatsPane o={o} onCoin={sym => onCoin(sym)} focus={coin} />}
    {tab === 'beliefs' && <div className="ofr-pane" data-testid="pane-beliefs"><p className="ofr-job" data-testid="ofr-job"><b>{a.job}</b> {a.question}</p><p className="ofr-ideo">{a.ideology}</p>
      <small>ETHICS</small><ul className="ofr-list">{a.ethics.map(x => <li key={x}>{x}</li>)}</ul><small>IMMUTABLE RULES</small><ul className="ofr-list">{a.hard.map(x => <li key={x}>{x}</li>)}</ul>
      <small>FORBIDDEN</small><ul className="ofr-list is-no">{a.forbidden.map(x => <li key={x}>{x}</li>)}</ul>
      <small>TUNABLE (shadow-tested only)</small>{a.tunable?.length ? <ul className="ofr-list">{a.tunable.map(t => <li key={t.key} data-tip={t.what}>{t.key} = <b>{t.value}</b> · default {t.default} · bounds {t.lo} … {t.hi}</li>)}</ul> : <span className="ofr-nil">none</span>}
      <small>WHY THIS STATE</small><p className="ofr-why">{c.why}</p></div>}
    {tab === 'inputs' && <div className="ofr-pane" data-testid="pane-inputs"><small>TASK</small><p className="ofr-why">{a.task || 'idle'}</p><small>CURRENT INPUTS</small>{dump(a.inputs)}<small>CURRENT OUTPUT</small>{dump(a.output)}
      <small>MISSION CONTRIBUTION · measured only</small>{(() => { const k = o.judge?.contribution; const rows = k?.agents?.[a.key] || [];
        return <ul className="ofr-list" data-testid="ofr-contrib">{rows.length ? rows.map(r => <li key={r[0]} data-tip={r[2]}>{r[0]}: <b>{r[1] == null ? 'not enough records yet' : String(r[1])}</b> <i>{r[2]}</i></li>) : <li>nothing this desk does is counted toward the mission in a number yet</li>}
          {a.key === 'judge' && k ? <>{Object.entries(k.team || {}).map(([n, v]) => <li key={n}>team · {n}: <b>{v == null ? '—' : String(v)}</b></li>)}{(k.notMeasured || []).map(r => <li key={r[0]} className="is-nm">NOT MEASURED — {r[0]}: {r[1]}</li>)}</> : null}</ul>; })()}</div>}
    {tab === 'chart' && <div className="ofr-pane" data-testid="pane-chart">{view?.kind === 'case' ? <ChartBox c={ch} cur={view.cur} />
      : p ? <><small>ENTRY THESIS · ${p.symbol}</small>{p.thesis ? dump({ ...p.thesis, at: ago(p.thesis.at) }) : <span className="ofr-nil">no thesis on file (bought before theses were saved)</span>}<small>CHART NOW</small>{dump({ structure: p.structure, verdict: p.verdict, why: p.why, ...(p.chart || {}) })}</>
        : <span className="ofr-nil">no chart snapshot this pass</span>}</div>}
    {tab === 'code' && <div className="ofr-pane" data-testid="pane-code"><small>SOURCE</small><ul className="ofr-list">{(a.code || []).map(k => <li key={k.file}><code>{k.file}</code>{k.fn.map(fn => <code key={fn} className="ofr-fn">{fn}()</code>)}</li>)}</ul>
      <small>RUNTIME (last {c.latency?.n ?? 0} passes)</small>{dump({ last: ms(c.latency?.last), p50: ms(c.latency?.p50), p95: ms(c.latency?.p95), max: ms(c.latency?.max) })}
      <small>SCORECARD</small>{dump({ samples: c.n, right: c.accuracy, falsePositives: c.fp, falseNegatives: c.fn, missed: c.missed, badApprovals: c.badApprovals, usefulVetoes: c.usefulVetoes, staleReads: c.stale, violations: c.violations, survival: c.survival, chartCalls: c.chartN, chartRight: c.chartRight })}</div>}
  </aside>;
}

export function Roster({ o, sel, onSel }) {
  const alive = (o.agents || []).filter(a => a.card?.status === 'alive').length;
  return <div className="ofr-roster" data-testid="ofr-roster"><small>AGENT ROSTER · {alive} / {(o.agents || []).length} alive</small>
    <div className="ofr-rgrid">{(o.agents || []).map(a => { const c = a.card || {}; const [tag, word] = agentTag(a.key, o); const net = (c.profit ?? 0) + (c.loss ?? 0); const has = c.profit != null || c.loss != null; const avg = has && c.n ? net / c.n : null;   /* 📏 the AVERAGE per sample — a sum of % over 158 exits read as "−468%" */
      return <button key={a.key} type="button" className={`ofr-rcard ${TAG_CLS[tag] || 'is-wait'} ${sel === a.key ? 'is-on' : ''}`} style={{ '--ag': AG[a.key] }} onClick={() => onSel(a.key)} aria-pressed={sel === a.key} data-tip={`${a.role} ${c.why || ''}`} data-testid={`roster-${a.key}`}>
        <span className="ofr-rhead"><i className="ofr-ricon" aria-hidden>{a.icon}</i><span><b>{a.name}</b><u>gen {c.gen ?? 1} · <i className={c.status === 'alive' ? 'ofr-pos' : 'ofr-warn'}>● {c.status || '—'}</i></u></span>
          <em className={net > 0 ? 'ofr-pos' : net < 0 ? 'ofr-neg' : ''} data-tip={has ? `avg per sample (${c.n || 0}) · ${c.unit || ''} · sum ${sgn(net)}` : 'contribution: nothing measured yet'} data-testid={`roster-net-${a.key}`}>{avg != null ? `${sgn(avg)} avg` : has ? sgn(net) : '—'}</em></span>
        <span className="ofr-rmid" data-tip={`runtime per pass, last ${(o.performance?.agents?.[a.key]?.series || []).length} passes (ms)`}><Spark xs={o.performance?.agents?.[a.key]?.series} /><span><b data-tip="right % on its own judged record">{c.accuracy == null ? '—' : `${c.accuracy}%`}</b><u>n {c.n ?? 0} · conf {c.confidence != null ? `${Math.round(c.confidence * 100)}%` : '—'} · {ms(c.latency?.last)}</u></span></span>
        <span className="ofr-rtag" data-tip={word}>{tag}</span></button>; })}</div></div>;
}

// 🖱 what a click on any object in the room does — one pure function (tested without WebGL): a seat → its live position / the empty seat's
// reason · a wall board → the view with its numbers · a case file → its coin at the desk it stands at · the wall monitor → the coin on it ·
// a bot / desk / monitor → that agent. No object in the room is a decorative click.
export function routePick(u, model, seatData, cb) {
  const c = cb || {};
  if (u.kind === 'seat') { const d = seatData ? seatData(u.seat) : null; if (c.seat) c.seat(d?.sb || (d?.symbol ? { symbol: d.symbol } : { empty: true })); else if (d?.symbol) { if (c.coin) c.coin(d.symbol); if (c.sel) c.sel('reaper'); } return 'seat'; }
  if (u.kind === 'board') { if (c.board) c.board(u.board); return 'board'; }
  if (u.kind === 'case') { if (c.coin) c.coin(u.sym); if (c.sel) c.sel(u.at); return 'case'; }
  if (u.kind === 'wall') { const w = model?.wall; if (w?.symbol && c.coin) c.coin(w.symbol); if (c.sel) c.sel(w?.kind === 'position' ? 'reaper' : model?.focus || 'tally'); return 'wall'; }
  if (u.k) { if (c.sel) c.sel(u.k); return u.kind === 'monitor' ? 'monitor' : 'bot'; }
  return null;
}

export const CAMS = [['main', 'Main'], ['card', 'Card'], ['top', 'Top'], ['focus', 'Focus']];
const pref = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };

export function OfficeHQ({ o, roomOn = true, passAt, gl: gl0, card, onEdge }) {
  const [sel, setSel] = useState(null); const [coin, setCoin] = useState(null); const [gl] = useState(() => (gl0 != null ? gl0 : has3D())); const [tabReq, setTabReq] = useState(null);
  // 🪑 a seat (strip / room) → a held seat opens its coin under Reaper's live decision; an empty seat opens the Seats view with its reason
  const onSeat = x => { if (!x) return; if (x.symbol) { setCoin(x.symbol); setSel('reaper'); setTabReq({ tab: 'live', at: Date.now() }); } else setTabReq({ tab: 'seats', at: Date.now() }); };
  // 🧱 a wall board → the view that holds its numbers (pipeline / switch board → Seats · limits → your limits lens)
  const onBoard = k => { if (k === 'limits') { if (onEdge) onEdge('limits'); return; } setTabReq({ tab: 'seats', at: Date.now() }); };
  const [cam, setCam] = useState(() => pref.get('feeless.roomCam', 'main')); const [rot, setRot] = useState(() => pref.get('feeless.roomRot', 'off') === 'on');
  const cur = sel || focusOf(o); const box = useRef(null);
  // the office takes exactly the height the window has left under the mission + status strip, so room · panel · roster share ONE view
  useLayoutEffect(() => { const fit = () => { const el = box.current; const st = el?.querySelector('.ofr-main'); if (!el || !st) return; const top = st.getBoundingClientRect().top + (window.scrollY || 0);
    const rosterH = el.querySelector('.ofr-roster')?.offsetHeight || 96; el.style.setProperty('--ofr-h', `${Math.round(Math.max(390, Math.min(720, window.innerHeight - top - rosterH - 22)))}px`); };
    fit(); window.addEventListener('resize', fit); return () => window.removeEventListener('resize', fit); }, [o?.cold, roomOn]);
  const model0 = useMemo(() => (o && !o.cold ? roomModel(o, cur, coin, card) : null), [o, cur, coin, card]);
  // 👁 the wall screen draws the coin's LIVE chart (the war room's own 1-minute candles, re-read every 10s), never the pass's snapshot
  const wallLive = useLiveCandles(model0?.wall?.pair, model0?.wall?.mint);
  const model = useMemo(() => (model0?.wall && wallLive ? { ...model0, wall: { ...model0.wall, bars: { ...(model0.wall.bars || {}), rows: wallLive.rows, src: 'candles' },
    caption: `LIVE · the FEELESS chart · ${wallLive.rows.length} one-minute candles (${wallLive.provider || 'FEELESS'} + live ticks) · updated every 10s` } } : model0), [model0, wallLive]);
  if (!o || o.cold) return <section className="ofr" data-testid="office-hq"><p className="ofr-nil">waiting for the agents' first pass — the room shows nothing it was not handed</p></section>;
  const a = (o.agents || []).find(x => x.key === cur);
  return <section className={`ofr ${roomOn ? '' : 'is-flat'}`} data-testid="office-hq" ref={box}>
    <header className="ofr-bar"><b>🏢 THE AGENT OFFICE</b><span className="ofr-live"><i />live</span><small className="ofr-pass">last pass {ago(passAt || o.at)}</small><EdgeBand o={o} onOpen={onEdge} />
      {roomOn && gl ? <span className="ofr-cams"><span className="m-seg" role="group" aria-label="Camera">{CAMS.map(([k, l]) => <button key={k} type="button" className={cam === k ? 'active' : ''} onClick={() => { setCam(k); pref.set('feeless.roomCam', k); }} data-testid={`cam-${k}`}>{l}</button>)}</span>
        <button type="button" className={`m-btn ${rot ? 'is-on' : ''}`} aria-pressed={rot} onClick={() => { setRot(!rot); pref.set('feeless.roomRot', rot ? 'off' : 'on'); }} data-tip="Sweep the camera slowly across the room (Main room view)" data-testid="cam-rotate">⟳ {rot ? 'Rotating' : 'Rotate'}</button></span> : null}</header>
    <SeatStrip o={o} sel={coin} onSeat={onSeat} />
    <div className="ofr-main">
      {roomOn ? <div className="ofr-stage" data-testid="ofr-stage">
        {gl ? <Suspense fallback={<div className="ofr-loading">building the room…</div>}><OfficeRoom3D model={model} onSel={setSel} onCoin={setCoin} onSeat={onSeat} onBoard={onBoard} cam={cam} rotate={rot} /></Suspense> : <RoomScene o={o} sel={cur} onSel={setSel} coin={coin} onCoin={setCoin} card={card} onSeat={onSeat} />}
        {gl ? <div className="ofr-foot" data-testid="ofr-foot"><span className="ofr-flowline"><small>FLOW</small>{(o.agents || []).map((x, i) => <React.Fragment key={x.key}>{i ? <i aria-hidden>→</i> : null}<button type="button" className={`${focusOf(o) === x.key ? 'is-focus' : ''} ${cur === x.key ? 'is-on' : ''}`} style={{ '--ag': AG[x.key] }} onClick={() => setSel(x.key)} data-tip={x.job}>{x.name}</button></React.Fragment>)}</span>
          <button type="button" className="ofr-now" onClick={() => { const c = o.currentCase || hotPosition(o.positions); if (c) { setCoin(c.symbol); setSel(o.currentCase ? focusOf(o) : 'reaper'); } }} data-testid="ofr-foot-ticker"><i aria-hidden />{ticker(o)}</button></div> : null}
      </div> : null}
      <AgentPanel key={cur} o={o} a={a} coin={coin} onCoin={setCoin} tabReq={tabReq} /></div>
    <Roster o={o} sel={cur} onSel={setSel} />
  </section>;
}
