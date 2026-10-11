import React, { useState } from 'react';
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
export function SeatStrip({ o, onSeat, sel }) {
  const sb = o?.seatBoard || []; const s = o?.seatSummary;
  if (!s && !sb.length) return null;
  const chip = (k, l, v, cls, tip) => <span key={k} className={`sop-chip ${cls || ''}`} data-tip={tip} data-testid={`sop-${k}`}><small>{l}</small><b>{v}</b></span>;
  return <div className="sop-strip" data-testid="sop-strip">
    <div className="sop-sum">
      {chip('occ', 'OCCUPANCY', s ? `${s.occupancy} / ${s.target}` : '—', s && s.occupancy >= s.target ? 'is-ok' : 'is-warn', 'seats holding a coin now / seats the card runs')}
      {chip('target', 'TARGET', s ? `${s.target} / ${s.target}` : '—', '', 'every seat filled — whenever that many defensible coins exist (cash is a valid position)')}
      {chip('bench', 'BENCH', s ? `${s.benchReady} ready · ${o?.benchStats?.near ?? 0} near · ${s.bench}` : '—', s?.benchReady ? 'is-ok' : '', 'ranked challengers behind the seats — ready = cleared every desk AND the newest live check · near = one check still coming')}
      {chip('buys', 'BUYS LEFT', s ? `${s.buysLeft} / ${s.budget}` : '—', s && !s.buysLeft ? 'is-bad' : '', `the hourly hard buy budget (fills + switches) — ${s ? s.buysUsed : 0} used this hour`)}
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
          <span className="sop-line">{x.ready ? <i className="sop-ok">READY</i> : <i className="sop-wait">{x.code || 'NOT READY'}</i>}{x.nextEval != null ? <u>{x.nextEval}s</u> : null}</span>
          <span className="sop-why">{short(x.block, 70)}</span></button>
      : <button key={x.seat} type="button" className={`sop-seat ${RES_CLS[x.result] || ''} ${sel && sel === x.symbol ? 'is-on' : ''}`} onClick={() => onSeat && onSeat(x)} data-testid={`sop-seat-${x.seat}`}
          data-tip={`$${x.symbol} — ${x.result}: ${x.why || ''}`}>
          <span className="sop-head"><small>SEAT {x.seat}</small><em className={`sop-res ${RES_CLS[x.result] || ''}`}>{x.result}</em></span>
          <b>${x.symbol} <span className={pcls(x.pct)}>{pct(x.pct)}</span></b>
          <span className="sop-line"><Vel v={x.vel} why={x.velWhy} />{x.heldMin != null ? <u>{Math.round(x.heldMin)}m</u> : null}</span>
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
    <div className="sop-ages" data-testid="sop-latency">{[['sourceToIntake', 'SOURCE → INTAKE'], ['intakeToDeep', 'INTAKE → DEEP REVIEW'], ['deepToClear', 'DEEP → CLEAR'], ['clearToSeat', 'CLEAR → SEAT'], ['birthToSeen', 'LAUNCH → FIRST SEEN']].map(([k, label]) =>
      <span key={k} data-tip={`median over the last 6h · ${lat[k]?.n ?? 0} coins`}><small>{label}</small><b>{secTxt(lat[k]?.med)}</b><u>n {lat[k]?.n ?? 0}</u></span>)}</div>
    <div className="sop-logwrap"><table className="sop-log" data-testid="sop-sources"><thead><tr><th>outlet (6h)</th><th>seen</th><th>found first</th><th>promoted</th><th>deep</th><th>cleared</th><th>bought</th><th>won / lost</th></tr></thead>
      <tbody>{Object.entries(iv.sources || {}).slice(0, 14).map(([k, v]) => <tr key={k}><td>{iv.labels?.[k] || k}</td><td>{v.seen}</td><td>{v.firstFinder}</td><td>{v.promoted}</td><td>{v.deep}</td><td>{v.cleared}</td><td>{v.bought}</td><td>{v.won} / {v.lost}</td></tr>)}</tbody></table></div>
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
