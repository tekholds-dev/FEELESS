import React, { useState } from 'react';
import { useLivePrices } from '../../lib/livePrices';
import { freshness, useOffice } from '../../lib/agentHub';
import { devilOf } from '../../lib/agentRead';
import { sgn, usd } from './OfficeBoard';
import { OpsLine, CycleLine } from './OfficeEdge';
import '../../styles/seatOps.css';

// 🪑 THE FOUR-SEAT OPERATING MODEL on the Agents tab (`backend/seat_ops.py` → the one office payload: seatBoard · bench · seatSummary ·
// cycleLog · fresh · social). Every number is a field the office already decided with — this file draws, it never decides.

const RES_CLS = { HOLD: 'is-ok', PROTECT: 'is-warn', TAKE: 'is-go', EXIT: 'is-bad', SWAP: 'is-go' };
export const VEL = { ACCELERATING: ['▲', 'is-up', 'accelerating'], STABLE: ['▬', '', 'stable'], STALLING: ['◆', 'is-warn', 'stalling'], REVERSING: ['▼', 'is-bad', 'reversing'], UNKNOWN: ['·', 'is-dim', 'reading…'] };
const secs = (now, at) => (at ? `${Math.max(0, Math.round(now - at))}s` : '—');
const pct = v => (v == null ? '—' : sgn(v));
const pcls = v => (v == null ? '' : v > 0 ? 'is-up' : v < 0 ? 'is-bad' : '');
const short = (s, n = 64) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s || '');

export function Vel({ v, why }) {
  const [g, cls, word] = VEL[v] || VEL.UNKNOWN;
  return <i className={`sop-vel ${cls}`} data-tip={`P/L velocity — ${v || 'UNKNOWN'}${why ? `: ${why}` : ''} (from real valuation reads; no forecast)`}>{g} {word}</i>;
}

// ── the strip above the room: OCCUPANCY x/4 · TARGET · BENCH · BUYS LEFT · CASH + one tile per seat ──────────────────────────────
const HUNT = { trench: 'NEW COINS', mixed: 'NEW + MAJORS', majors: 'MAJORS' };   // seat_ops.universe: recovery → new coins first · ≥ 2× → majors

// ── ⏱ THE ROUND BAR: the desk's 5-minute clock + everything the spec asks to see at a glance (one payload, nothing fetched) ──────────
const AGE_BANDS = ['0–5m', '5–15m', '15–60m', '1–3h', '3–6h'];
const mmss = s => (s == null ? '—' : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`);
export function RoundBar({ o }) {
  const r = o?.rounds; if (!r) return null;
  const b = o?.cycle?.fresh?.buckets || {}; const op = o?.opp || {}; const fr = o?.fresh || {}; const s = o?.seatSummary || {};
  const age = v => (v == null ? '—' : `${Math.round(v)}s`);
  const cell = (k, l, v, tip, cls) => <span key={k} className={`sop-chip ${cls || ''}`} data-tip={tip} data-testid={`rb-${k}`}><small>{l}</small><b>{v}</b></span>;
  return <div className="sop-sum sop-rounds" data-testid="round-bar">
    {cell('round', 'ROUND', `${r.desk?.n ?? '—'} · ${mmss(r.desk?.left)} left`, 'the desk\'s 5-minute clock; every candidate also runs its own round 1 → 2 → 3 from the pass it was first seen')}
    {cell('cands', 'R1 · R2 · R3', `${r.round?.['1'] ?? 0} · ${r.round?.['2'] ?? 0} · ${r.round?.['3'] ?? 0}`, 'candidates in round 1 (discovery) · round 2 (confirm) · round 3 (decide) — none waits past round 3')}
    {cell('dec', 'DECIDED 1H', `${r.decided1h?.ENTER ?? 0} in · ${r.decided1h?.REJECT ?? 0} no · ${r.decided1h?.COOLDOWN ?? 0} cool`, `ENTER · REJECT · COOLDOWN in the last hour — average ${r.avgRounds ?? '—'} rounds before a decision`)}
    {cell('new', 'NEW MINTS', AGE_BANDS.map(k => b[k] ?? 0).join(' · '), `on the desk this cycle by launch age: ${AGE_BANDS.join(' · ')}`)}
    {cell('screen', 'SCREENED → DEEP', `${o?.cycle?.screened ?? '—'} → ${o?.cycle?.reviewed ?? '—'}`, 'cheap Tally screen of the whole feed → coins given the expensive reads (holders · chart · social)')}
    {cell('tiers', 'A · B · C · NO', `${op.A ?? 0} · ${op.B ?? 0} · ${op.C ?? 0} · ${op.hard ?? 0}`, 'opportunity tiers of this pass; NO = a hard safety / universe failure')}
    {cell('bench', 'SEATS · BENCH', `${s.occupancy ?? 0}/${s.target ?? 4} · ${s.bench ?? 0}`, 'seats holding a coin · challengers behind them')}
    {o?.open ? cell('open', '⚡ OPEN · TOP', o.open.top?.length ? o.open.top.slice(0, 2).map(t => `$${t.symbol} ${t.narrative?.toLowerCase()}`).join(' · ') : 'nothing tradeable',
      `volume + newness only: ${o.open.read} read · ${o.open.ranked} tradeable · skipped: ${Object.entries(o.open.skipped || {}).map(([k, v]) => `${k} ${v}`).join(' · ') || 'none'}`, o.open.ranked ? 'is-ok' : 'is-warn') : null}
    {cell('ages', 'PRICE · TAPE · CANDLE · LIQ · DECISION', [fr.price, fr.tape, fr.candle, fr.liquidity, fr.decision].map(age).join(' · '), 'how old each input behind the decisions really is', fr.price > 30 || fr.candle > 90 ? 'is-warn' : '')}
  </div>;
}

// ⏱ ROUND HISTORY (Archivist): each finished candidate — round 1 read · round 2 read · round 3 decision — so patience is judged, not assumed
const DEC_CLS = { ENTER: 'is-ok', REJECT: 'is-bad', COOLDOWN: 'is-wait' };
export function RoundHistory({ r, onCoin }) {
  const h = r?.recent || [];
  if (!h.length) return null;
  return <div data-testid="round-history"><small>ROUND HISTORY · LAST {h.length}</small>
    <ul className="sop-board">{h.map((x, i) => <li key={`${x.sym}-${x.at}-${i}`}>
      <span className="sop-k"><button type="button" className="sop-coin" onClick={() => onCoin && onCoin(x.sym)}>${x.sym}</button></span>
      <span className="sop-v"><i className={`sop-tag ${DEC_CLS[x.decision] || ''}`}>{x.decision}</i> after {x.rounds} round{x.rounds === 1 ? '' : 's'}</span>
      <span className="sop-full">{(x.reads || []).map(rd => `R${rd.round} ${rd.tier || '—'} ${rd.score != null ? Math.round(rd.score) : '—'}${rd.phase ? ` ${rd.phase.toLowerCase()}` : ''}`).join(' → ')} · {x.why}</span></li>)}</ul></div>;
}

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

export function SeatStrip({ o, onSeat, sel }) {
  const sb = o?.seatBoard || []; const s = o?.seatSummary;
  if (!s && !sb.length) return null;
  const posOf = sym => (o?.positions || []).find(p => p.symbol === sym);
  const candOf = sym => (o?.rounds?.live || []).find(c => c.sym === sym);
  const chip = (k, l, v, cls, tip) => <span key={k} className={`sop-chip ${cls || ''}`} data-tip={tip} data-testid={`sop-${k}`}><small>{l}</small><b>{v}</b></span>;
  return <div className="sop-strip" data-testid="sop-strip">
    <RoundBar o={o} />
    <KernelBoard o={o} />
    <div className="sop-sum">
      {chip('occ', 'OCCUPANCY', s ? `${s.occupancy} / ${s.target}` : '—', s && s.occupancy >= s.target ? 'is-ok' : 'is-warn', 'seats holding a coin now / seats the card runs')}
      {chip('target', 'TARGET', s ? `${s.target} / ${s.target}` : '—', '', 'every seat filled — whenever that many defensible coins exist (cash is a valid position)')}
      {chip('bench', 'BENCH', s ? `${s.benchReady} ready · ${o?.benchStats?.near ?? 0} near · ${s.bench}` : '—', s?.benchReady ? 'is-ok' : '', 'ranked challengers behind the seats — ready = cleared every desk AND the newest live check · near = one check still coming')}
      {chip('buys', 'FILLS LEFT', s ? `${s.buysLeft} / ${s.budget}` : '—', s && !s.buysLeft ? 'is-bad' : '', `empty-seat fills this hour (a runaway guard) — ${s ? s.buysUsed : 0} used; switches have their own 6 an hour`)}
      {s?.hunt && chip('hunt', 'HUNTING', HUNT[s.hunt[0]] || s.hunt[0], '', s.hunt[1])}
      {chip('cash', 'CASH', s?.cash != null ? usd(s.cash) : '—', '', 'free card cash the empty seats share')}
      {chip('office', 'OFFICE', o?.ops?.office || '—', o?.ops?.office === 'LIVE' ? 'is-ok' : 'is-warn', 'LIVE = positions read back + the market refilled after a restart; until then no discretionary move')}
      {chip('keeper', 'KEEPER', o?.ops?.keeper || '—', o?.ops?.keeper === '1 active' ? 'is-ok' : 'is-bad', 'exactly one keeper process may send real orders')}
      {chip('exec', 'EXECUTION', o?.ops?.execution || '—', o?.ops?.execution === 'HEALTHY' ? 'is-ok' : o?.ops?.execution === 'BLOCKED' ? 'is-bad' : 'is-warn', 'the Courier\'s read of the keeper\'s own ledger')}
    </div>
    <div className="sop-seats">{sb.map(x => x.empty
      ? <button key={x.seat} type="button" className={`sop-seat is-open ${x.ready ? 'is-ready' : ''}`} onClick={() => onSeat && onSeat(x)} data-testid={`sop-seat-${x.seat}`}
          data-tip={`Seat ${x.seat} is open — ${x.code || ''}: ${x.block || ''}`}>
          <span className="sop-head"><small>SEAT {x.seat}</small><em>OPEN</em></span>
          <b>{x.next ? `next $${x.next.symbol}` : 'no candidate'}</b>
          <span className="sop-line">{x.ready ? <i className="sop-ok">READY</i> : <i className="sop-wait">{x.code || 'NOT READY'}</i>}{x.next && candOf(x.next.symbol) ? <u data-testid={`sop-seat-round-${x.seat}`}>{candOf(x.next.symbol).tier || '—'}-tier · R{candOf(x.next.symbol).round}</u> : null}{x.nextEval != null ? <u>{x.nextEval}s</u> : null}</span>
          <span className="sop-why">{short(x.block, 70)}</span></button>
      : <button key={x.seat} type="button" className={`sop-seat ${RES_CLS[x.result] || ''} ${sel && sel === x.symbol ? 'is-on' : ''}`} onClick={() => onSeat && onSeat(x)} data-testid={`sop-seat-${x.seat}`}
          data-tip={`$${x.symbol} — ${x.result}: ${x.why || ''}`}>
          <span className="sop-head"><small>SEAT {x.seat}</small><em className={`sop-res ${RES_CLS[x.result] || ''}`}>{x.result}</em></span>
          <b>${x.symbol} <span className={pcls(x.pct)}>{pct(x.pct)}</span></b>
          <span className="sop-line"><Vel v={x.vel} why={x.velWhy} />{x.heldMin != null ? <u>{Math.round(x.heldMin)}m</u> : null}{posOf(x.symbol)?.posRound ? <u data-testid={`sop-seat-round-${x.seat}`} data-tip={`round ${posOf(x.symbol).posRound.round} of this position · ${posOf(x.symbol).roundAction} · MFE ${pct(posOf(x.symbol).mfe)} · MAE ${pct(posOf(x.symbol).mae)}`}>R{posOf(x.symbol).posRound.round} {posOf(x.symbol).roundAction}</u> : null}</span>
          <span className="sop-why">{x.score != null ? `score ${Math.round(x.score)}` : 'unscored'}{x.challenger ? ` · vs $${x.challenger.symbol} ${x.margin != null ? `${x.margin >= 0 ? '+' : ''}${Math.round(x.margin)}/${Math.round(x.need)}` : ''}` : ' · no challenger'}</span></button>)}</div>
  </div>;
}

// ── the Seats pane: every seat this cycle, the bench, the input ages, the cycle log ───────────────────────────────────────────────
export function SeatsPane({ o, onCoin, focus }) {
  const now = o?.at || Date.now() / 1000; const sb = o?.seatBoard || []; const bench = o?.bench || []; const f = o?.fresh || {}; const log = (o?.cycleLog || []).slice(-8).reverse();
  const tag = (cls, t) => <i className={`sop-tag ${cls || ''}`}>{t}</i>;
  const coinBtn = (sym, mint) => (sym ? <button type="button" className="sop-coin" onClick={() => onCoin && onCoin(sym, mint)} data-tip="open this coin in the panel">${sym}</button> : '—');
  const fage = v => (v == null ? '—' : `${Math.round(v)}s`);
  return <div className="sop-pane" data-testid="pane-seats">
    <OpsLine o={o?.ops} />
    <CycleLine c={o?.cycle} load={o?.loadPass} />
    <IntakeBlock o={o} />
    <RoundHistory r={o?.rounds} onCoin={onCoin} />
    <small>EVERY SEAT · THIS CYCLE</small>
    <ul className="sop-board">{sb.length ? sb.map(x => <li key={x.seat} className={`${x.empty ? 'is-open' : ''} ${focus && focus === (x.symbol || `seat${x.seat}`) ? 'is-on' : ''}`} data-testid={`sop-row-${x.seat}`}>
      {x.empty ? <>
        <span className="sop-k">SEAT {x.seat}</span><span className="sop-v">{tag(x.ready ? 'is-ok' : 'is-wait', x.ready ? 'READY' : 'NOT READY')} next {x.next ? coinBtn(x.next.symbol, x.next.mint) : 'none'}{x.next?.score != null ? <u> score {Math.round(x.next.score)}</u> : null}</span>
        <span className="sop-full">{x.code ? <b>{x.code}</b> : null} {x.block || ''}{x.nextEval != null ? <u> · next evaluation {x.nextEval}s</u> : null}</span></>
        : <>
        <span className="sop-k">SEAT {x.seat}</span><span className="sop-v">{coinBtn(x.symbol, x.mint)} <b className={pcls(x.pct)}>{pct(x.pct)}</b> <Vel v={x.vel} why={x.velWhy} /> {tag(RES_CLS[x.result], x.result)}</span>
        <span className="sop-grid">
          <span><u>THESIS</u><b>{x.thesis || '—'}{x.structure ? ` · ${x.structure}` : ''}</b></span><span><u>HELD</u><b>{x.heldMin != null ? `${Math.round(x.heldMin)} min` : '—'}</b></span>
          <span><u>PROTECTION</u><b>{x.protection || '—'}</b></span><span><u>SCORE</u><b>{x.score != null ? Math.round(x.score) : '—'}</b></span>
          <span><u>BEST CHALLENGER</u><b>{x.challenger ? `$${x.challenger.symbol} ${x.challenger.score != null ? Math.round(x.challenger.score) : ''}${x.challenger.ready ? ' · ready' : ''}` : 'none'}</b></span>
          <span><u>SWITCH MARGIN</u><b>{x.margin != null ? `${x.margin >= 0 ? '+' : ''}${Math.round(x.margin)} of +${Math.round(x.need)}` : '—'}</b></span>
          <span><u>DECIDED</u><b>{secs(now, x.decidedAt)} ago</b></span><span><u>MARKET INPUT</u><b>{secs(now, x.inputAt)} old</b></span></span>
        <span className="sop-full">{x.rule ? <b>{x.rule}</b> : null} {x.why || ''}{x.switchWhy ? <u> · switch test: {x.switchWhy}</u> : null}</span></>}
    </li>) : <li className="sop-nil">no seat data yet — the tier tick has not run under Agent Control</li>}</ul>
    <small>BENCH · ranked challengers behind the seats{o?.benchStats ? ` · depth ${o.benchStats.depth} · ${o.benchStats.ready} ready · ${o.benchStats.near} near · ${o.benchStats.new ?? '—'} new · ${o.benchStats.dropped} dropped this cycle` : ''}</small>
    <ol className="sop-bench" data-testid="sop-bench">{bench.length ? bench.map(b => <li key={b.mint} className={b.ready ? 'is-ready' : ''}>
      <u>#{b.rank}</u>{coinBtn(b.symbol, b.mint)}<b>{b.score != null ? Math.round(b.score) : '—'}</b><i>{b.quality || '—'}</i><em>{b.ready ? 'READY' : b.near ? `NEAR · ${short(b.block, 70)}` : short(b.block, 80)}</em></li>) : <li className="sop-nil">no challenger has a positive read this cycle — the seats hold, the open ones stay cash</li>}</ol>
    <small>INPUT AGES · how old each input really is</small>
    <div className="sop-ages" data-testid="sop-ages">{[['PRICE', f.price], ['TAPE', f.tape], ['REAL CANDLE', f.candle], ['LIQUIDITY', f.liquidity], ['AGENT INPUT', f.agentInput], ['DECISION', f.decision]].map(([k, v]) =>
      <span key={k} className={v == null ? '' : v > 120 ? 'is-bad' : v > 60 ? 'is-wait' : 'is-ok'}><small>{k}</small><b>{fage(v)}</b></span>)}
      {f.held ? <span className="sop-held" data-tip="the OLDEST input behind a held seat (a decision must not stand on a stale one)"><small>HELD SEATS (oldest)</small><b>px {fage(f.held.price)} · tape {fage(f.held.tape)} · candle {fage(f.held.candle)}</b></span> : null}</div>
    <UtilBlock u={o?.util} />
    <small>CYCLE LOG · one line per ~60s pass</small>
    <div className="sop-logwrap"><table className="sop-log" data-testid="sop-log"><thead><tr><th>pass</th><th>board</th><th>cheap</th><th>unique</th><th>new unique</th><th>new</th><th>deep</th><th>scans</th><th>social</th><th>cleared</th><th>seats</th><th>bench</th><th>best</th><th>seat actions</th><th>px / tape / candle</th></tr></thead>
      <tbody>{log.length ? log.map(l => <tr key={l.at}><td>#{l.n ?? '—'}</td><td>{l.board ?? '—'}</td><td>{l.cheap ?? '—'}</td><td>{l.unique ?? '—'}</td><td data-tip={Object.entries(l.intake?.newBy || {}).map(([k, v]) => `${k} ${v}`).join(' · ')}>{l.intake?.newUnique ?? '—'}</td><td data-tip={(l.newEntering || []).map(s => `$${s}`).join(' ')}>{l.newLaunches ?? '—'}{l.newEntering?.length ? ` (+${l.newEntering.length})` : ''}</td>
        <td data-tip={`${(l.deepCoins || []).filter(Boolean).map(s => `$${s}`).join(' ')} · why due: ${Object.entries(l.deepWhy || {}).map(([k, v]) => `${k} ${v}`).join(' · ') || '—'}`}>{l.deep ?? '—'}</td><td>{l.scans ?? '—'}</td><td data-tip={(l.socialCoins || []).map(s => `$${s}`).join(' ')}>{l.social ?? '—'}</td><td>{l.cleared ?? '—'}</td>
        <td>{l.occupancy != null ? `${l.occupancy}/${l.target}` : '—'}</td><td>{l.bench != null ? `${l.benchReady}/${l.bench}` : '—'}</td><td>{l.best ? `$${l.best.symbol}${l.best.score != null ? ` ${Math.round(l.best.score)}` : ''}` : '—'}</td>
        <td>{(l.seats || []).map((s, i) => <i key={i} className={`sop-tag ${s.empty ? '' : RES_CLS[s.result] || ''}`}>{s.empty ? `open${s.next ? `→$${s.next}` : ''}` : `$${s.symbol} ${s.result}`}</i>)}</td>
        <td>{fage(l.fresh?.price)} / {fage(l.fresh?.tape)} / {fage(l.fresh?.candle)}</td></tr>) : <tr><td colSpan={15} className="sop-nil">no cycle recorded yet</td></tr>}</tbody></table></div>
    {o?.scoreNote ? <p className="sop-note">{o.scoreNote}</p> : null}
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
export function IntakeBlock({ o }) {
  const iv = o?.intakeView; if (!iv) return null;
  const c = iv.cycle || {}; const l = iv.last || {}; const lat = iv.latency || {}; const it = o?.cycle || {}; const bs = o?.benchStats || {}; const sm = o?.seatSummary || {};
  const cell = (k, label, v, tip) => <span key={k} data-tip={tip} data-testid={`sop-in-${k}`}><small>{label}</small><b>{v ?? '—'}</b></span>;
  const nb = c.newBy || {};
  return <div className="sop-intake" data-testid="sop-intake">
    <small>ONE LIVE INTAKE · every existing FEELESS outlet</small>
    <div className="sop-ages">
      {cell('board', 'TOTAL BOARD / FEED', it.board ?? (o?.intakeView?.cycle?.desk), 'every coin the launch board holds + coins other outlets listed (rows built this pass)')}
      {cell('seen', 'UNIQUE SEEN', c.uniqueSeen, 'distinct mints listed by any outlet this pass')}
      {cell('new', 'NEW UNIQUE MINTS', c.newUnique, 'mints no outlet had EVER listed before this pass')}
      {cell('pulse', 'PUMP PULSE NEW', nb.pulse ?? 0, `PumpPortal live launch stream (on-chain creates)${l.pulsePerMin != null ? ` · ${l.pulsePerMin} launches last minute` : ''}`)}
      {cell('migr', 'MIGRATIONS', nb.migr ?? 0, 'PumpPortal live migrations')}
      {cell('board-new', 'BOARD NEW', nb.open ?? 0, 'new to the launch board (Pump biggest + recently traded, Pump trending, Jupiter rankings + newest, launchpad boards)')}
      {cell('outlets', 'OTHER OUTLETS NEW', Object.entries(nb).filter(([k]) => !['pulse', 'migr', 'open'].includes(k)).reduce((a, [, v]) => a + v, 0), Object.entries(nb).map(([k, v]) => `${iv.labels?.[k] || k} ${v}`).join(' · '))}
      {cell('cheap', 'CHEAP SCREENED', it.screened, 'Tally read every one of these this pass')}
      {cell('deep', 'DEEP REVIEWED', (o?.cycleLog || []).slice(-1)[0]?.deep ?? it.reviewed, 'read on real 1-minute candles this pass')}
      {cell('bench', 'READY BENCH', bs.ready != null ? `${bs.ready} + ${bs.near} near` : '—', 'ready = cleared every desk + the newest live check · near = one check (entry moment / data / holder scan) still coming')}
      {cell('cleared', 'CLEARED', it.cleared)}
      {cell('seats', 'SEATS', sm.target ? `${sm.occupancy} held · ${sm.open} open` : '—')}
      {cell('desknew', 'DESK TURNOVER', c.deskNew != null ? `${c.deskNew} new / ${c.desk}` : '—', 'coins on the desk this pass that were not on it last pass')}
    </div>
    <FreshBlock f={it.fresh} />
    <RpcLanes r={o?.rpc} />
    <ActiveIndex rows={o?.index} />
    <div className="sop-ages" data-testid="sop-latency">{[['sourceToIntake', 'SOURCE → INTAKE'], ['intakeToDeep', 'INTAKE → DEEP REVIEW'], ['deepToClear', 'DEEP → CLEAR'], ['clearToSeat', 'CLEAR → SEAT'], ['birthToSeen', 'LAUNCH → FIRST SEEN']].map(([k, label]) =>
      <span key={k} data-tip={`median over the last 6h · ${lat[k]?.n ?? 0} coins`}><small>{label}</small><b>{secTxt(lat[k]?.med)}</b><u>n {lat[k]?.n ?? 0}</u></span>)}</div>
    <div className="sop-logwrap"><table className="sop-log" data-testid="sop-sources"><thead><tr><th>outlet (6h)</th><th>seen</th><th>found first</th><th>promoted</th><th>deep</th><th>cleared</th><th>bought</th><th>won / lost</th><th>median P/L</th><th>rugged</th><th>median hold</th><th>age at entry</th><th>MC at entry</th><th>age first seen</th></tr></thead>
      <tbody>{Object.entries(iv.sources || {}).slice(0, 14).map(([k, v]) => <tr key={k}><td>{iv.labels?.[k] || k}</td><td>{v.seen}</td><td>{v.firstFinder}</td><td>{v.promoted}</td><td>{v.deep}</td><td>{v.cleared}</td><td>{v.bought}</td><td>{v.won} / {v.lost}</td>
        <td>{v.medPct == null ? '—' : `${v.medPct > 0 ? '+' : ''}${v.medPct}%`}</td><td>{v.rugRate == null ? '—' : `${v.rugRate}%`}</td><td>{v.medHoldMin == null ? '—' : `${Math.round(v.medHoldMin)}m`}</td>
        <td>{hm(v.medAgeEntryH == null ? null : v.medAgeEntryH * 60)}</td><td>{v.medMcEntry == null ? '—' : `$${Math.round(v.medMcEntry / 1000)}K`}</td><td>{hm(v.medAgeSeenMin)}</td></tr>)}</tbody></table></div>
    <p className="sop-note">{iv.note}</p>
  </div>;
}

export function UtilBlock({ u }) {
  if (!u?.all) return null;
  const t = s => (s == null ? '—' : s >= 3600 ? `${(s / 3600).toFixed(1)}h` : `${Math.round(s / 60)}m`);
  return <div className="sop-util" data-testid="sop-util"><small>SEAT UTILIZATION · last {u.windowH}h</small>
    <div className="sop-ages"><span className={u.all.pct == null ? '' : u.all.pct >= 75 ? 'is-ok' : u.all.pct >= 40 ? 'is-wait' : 'is-bad'}><small>ALL SEATS</small><b>{u.all.pct == null ? '—' : `${u.all.pct}%`}</b></span>
      {Object.entries(u.seats || {}).map(([k, b]) => <span key={k} data-tip={`occupied ${t(b.occ)} · empty ${t(b.empty)} (waiting on a valid candidate ${t(b.waiting)} · safety ${t(b.safety)} · buy budget ${t(b.budget)} · cash ${t(b.cash)})`}>
        <small>SEAT {k}</small><b>{b.pct == null ? '—' : `${b.pct}%`}</b></span>)}
      <span className="sop-held"><small>EMPTY TIME · WHY</small><b>waiting {t(u.all.waiting)} · safety {t(u.all.safety)} · budget {t(u.all.budget)} · cash {t(u.all.cash)}</b></span></div></div>;
}

// ── 🧾 PROOF / SOURCES: what Sherlock saw, clickable, with the exact mints compared ───────────────────────────────────────────────
const ST_CLS = { FOUND: 'is-ok', 'NOT FOUND': 'is-wait', UNKNOWN: '' };
const MM_CLS = { YES: 'is-ok', NO: 'is-bad', UNKNOWN: '' };
const safeUrl = u => (typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null);

export function CopyMint({ mint }) {
  const [ok, setOk] = useState(false);
  if (!mint) return null;
  const copy = () => { try { navigator.clipboard.writeText(mint).then(() => { setOk(true); setTimeout(() => setOk(false), 1400); }, () => {}); } catch (e) { /* no clipboard (http / old browser) */ } };
  return <button type="button" className="sop-copy" onClick={copy} data-tip={`copy the mint ${mint}`} data-testid="sop-copy-mint">{ok ? '✓ copied' : `⧉ ${mint.slice(0, 4)}…${mint.slice(-4)}`}</button>;
}

export function ProofSources({ p, mint, now }) {
  const t = now || Date.now() / 1000;
  if (!p) return <div className="sop-proof" data-testid="sop-proof"><small>PROOF / SOURCES</small><span className="sop-nil">not researched yet — only the strongest candidates are read (no paid API, no X API)</span><CopyMint mint={mint} /></div>;
  const ev = p.evidence || []; const lg = p.legal || {}; const nar = p.narrative || {}; const cc = p.cross || {};
  const ageOf = s => (s ? `${Math.max(0, Math.round((t - s) / 60))}m ago` : 'not opened');
  return <div className="sop-proof" data-testid="sop-proof">
    <header><small>PROOF / SOURCES · researched {Math.max(0, Math.round((t - (p.at || t)) / 60))}m ago</small><CopyMint mint={mint || p.mint} /></header>
    <ul className="sop-ev">{ev.map(e => { const u = safeUrl(e.url); return <li key={e.kind} className={ST_CLS[e.status] || ''} data-testid={`sop-ev-${e.kind}`}>
      <span className="sop-evh">{u ? <a href={u} target="_blank" rel="noopener noreferrer" data-tip={u}>{e.label}</a> : <span>{e.label}</span>}<i className={`sop-tag ${ST_CLS[e.status] || ''}`}>{e.status}</i></span>
      <span className="sop-evd">{e.title ? <b>{short(e.title, 60)}</b> : null}{e.mintMatch && e.mintMatch !== 'UNKNOWN' ? <i className={`sop-tag ${MM_CLS[e.mintMatch]}`} data-tip={`launch mint ${e.launchMint || '—'} · this source showed ${e.sourceMint || 'no address'}`}>MINT {e.mintMatch}</i> : null}
        <u>{e.fetchedAt ? ageOf(e.fetchedAt) : ''}{e.note ? `${e.fetchedAt ? ' · ' : ''}${e.note}` : ''}</u>{e.postUrl && safeUrl(e.postUrl) ? <a href={e.postUrl} target="_blank" rel="noopener noreferrer">latest post ↗</a> : null}
        {e.excerpt ? <q>{short(e.excerpt, 140)}</q> : null}</span></li>; })}</ul>
    <p className="sop-evl"><small>NARRATIVE</small><b>{nar.class || 'UNKNOWN'}</b>{(nar.sources || []).length ? <span> — from {(nar.sources || []).map((s, i) => <React.Fragment key={i}>{i ? ', ' : ''}{safeUrl(s.url) ? <a href={s.url} target="_blank" rel="noopener noreferrer">{s.source}</a> : s.source} ({(s.keywords || []).join(' ')})</React.Fragment>)}</span> : <span> — no source supports a class: UNKNOWN</span>}</p>
    <p className="sop-evl"><small>IDENTITY</small><b>{cc.confidence == null ? 'UNKNOWN' : `${cc.confidence}/100`}</b>{cc.conflict ? <span className="sop-bad"> — the site {cc.sourceUrl ? <a href={safeUrl(cc.sourceUrl) || undefined} target="_blank" rel="noopener noreferrer">{cc.sourceUrl}</a> : ''} shows {cc.sourceMint}, launch mint {cc.launchMint}</span> : (cc.flags || []).length ? <span> — {(cc.flags || []).join(' · ')}</span> : null}</p>
    <p className="sop-evl" data-testid="sop-legal"><small>LEGAL / ENTITY</small><b>{lg.level || 'NONE'}</b><span> — {(lg.labels || ['NO PUBLIC LEGAL EVIDENCE FOUND']).join(' · ')}{lg.entity ? ` · ${lg.entity}` : ''}{lg.jurisdiction ? ` · ${lg.jurisdiction}` : ''}{lg.regRef ? ` · reg. ${lg.regRef}` : ''}</span>{lg.note ? <u> ({lg.note})</u> : null}</p>
  </div>;
}
