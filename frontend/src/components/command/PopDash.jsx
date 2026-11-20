import React, { Suspense, lazy, useMemo, useState } from 'react';
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, YAxis } from 'recharts';
import { boxRef } from '../../lib/boxRef';
import { TestTag } from './TrueRecord';
import { ProposalCard, ProposalScore } from './PopDesk';
import '../../styles/popDash.css';

// 📉 THE PoP DESK DASHBOARD (Slice 26 · the desk bar, RULINGS 2026-11-20: "each proof type will have a user in it for hours"). The PoP folder opens on
// its paper perps, its own look (a perps terminal: violet longs, pink shorts, and a liquidation ruler under every position — where the price sits
// between ☠ liquidation, the stop, the entry and the take profit), never a copy of PoW / PoB / PoC: the open paper position (entry / mark / liquidation,
// P&L on the paper stake, NO fees: §1), the true chart (Lightweight Charts, the engine's own mark feed), its win rate, and every time the minds sat
// out with each mind's own reason. Every number is read from its PoP folders or the live folder; nothing is made up here.
const TAB_KEY = 'feeless.popDashTab';
const TABS = [['desk', 'Desk'], ['sit', 'Sat out'], ['filed', 'All filed'], ['tools', 'Tools']];
const MARKETS = ['SOL', 'ETH', 'BTC'];   // the engine's markets (backend/pop.py MARKETS) — the chart's feed carries exactly these
export const STAKE_USD = 10;            // backend/pop.py COLLATERAL_USD: the paper stake every PoP is measured on
const box = boxRef([640, 900]);
const PerpsChartLazy = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));
const readTab = () => { try { return localStorage.getItem(TAB_KEY) || 'desk'; } catch { return 'desk'; } };
const usd = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(2)}`);
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`);
const px = v => { const n = Number(v); if (!n) return '—'; return `$${n.toLocaleString(undefined, { maximumFractionDigits: n >= 1000 ? 1 : n >= 10 ? 2 : 4 })}`; };
const ago = s => { const m = Math.max(0, (Date.now() / 1000 - Number(s || 0)) / 60); return m < 1 ? 'now' : m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const pn = f => (f.n != null ? `PoP #${f.n}` : 'PoP');   // the first PoPs were filed before numbering
const tok = n => { try { return getComputedStyle(document.body).getPropertyValue(n).trim() || 'gray'; } catch { return 'gray'; } };

/** A mind's reason, readable: a reply cut off mid-JSON keeps its "why" (the raw text the engine filed is `{"market":…,"why":"…`). */
export function mindWhy(s) {
  const t = String(s || '').trim(); if (!t) return 'gave no reason';
  if (!t.startsWith('{')) return t;
  try { const j = JSON.parse(t); if (j?.why) return String(j.why); } catch { /* cut off: read what survived */ }
  const m = t.match(/"why"\s*:\s*"((?:[^"\\]|\\.)*)("?)/);
  if (m && m[1]) return `${m[1].replace(/\\(["\\/])/g, '$1')}${m[2] ? '' : '…'}`;
  const side = t.match(/"side"\s*:\s*"(\w+)"/)?.[1];
  return side === 'none' ? 'called no trade (its reason was cut off)' : 'its reply was cut off before its reason';
}
/** Why a folder sat out: the minds split, a mind passed, or nobody called. */
export const sitKind = f => (/ vs /.test(String(f.why || '')) ? 'split' : (f.calls || []).length ? 'passed' : 'nocall');
const SIT = { split: ['SPLIT', 'The minds called different trades, so nothing ran'], passed: ['PASSED', 'A mind looked and called no trade'], nocall: ['NO CALL', 'No mind gave a usable call'] };

/** Pure: where ☠ liquidation sits (backend/pop.py liq_move_pct: the move that wipes the stake). */
export function liqPrice(t) {
  const e = Number(t?.entry) || 0; const l = Number(t?.liqPct) || (t?.lev ? Math.round(100 / Math.max(Number(t.lev), 1) * 0.9 * 100) / 100 : 0);
  if (!e || !l) return null; return e * (1 - (t.side === 'short' ? -1 : 1) * l / 100);
}

/** Pure: every number on the PoP dashboard, from its folders and the live folder / proposal card. */
export function popNumbers(folders, live = null, card = null) {
  const rows = (folders || []).filter(Boolean).slice().sort((a, b) => (b.at || 0) - (a.at || 0));
  const trades = rows.filter(f => f.status === 'closed' && !f.noTrade && !f.ghost && !f.proposal && f.roePct != null).sort((a, b) => (a.closedAt || a.at || 0) - (b.closedAt || b.at || 0));
  const pnlOf = f => (f.pnlUsd != null ? Number(f.pnlUsd) : STAKE_USD * Number(f.roePct || 0) / 100);   // paper: the stake × ROE, no fee ever counts
  let run = 0; const curve = trades.map(f => { run += pnlOf(f); return { n: f.n, v: Number(run.toFixed(4)) }; });
  const won = trades.filter(f => Number(f.roePct) > 0).length;
  const ghosts = rows.filter(f => f.ghost && f.roePct != null); const sits = rows.filter(f => f.noTrade);
  const open = [...(live && live.status !== 'closed' ? [{ ...live, live: true }] : []), ...(card ? [{ ...card, live: true, card: true }] : [])];
  const openPnl = open.filter(t => !t.card).reduce((a, t) => a + STAKE_USD * Number(t.roePct || 0) / 100, 0);
  const bySit = sits.reduce((a, f) => { const k = sitKind(f); return { ...a, [k]: (a[k] || 0) + 1 }; }, {});
  const lastRead = rows.find(f => (f.reads || []).length)?.reads || [];
  return { rows, trades, curve, pnl: run, won, winPct: trades.length ? Math.round(100 * won / trades.length) : null, ghosts, ghostWon: ghosts.filter(g => g.won).length,
    sits, bySit, open, openPnl, lastRead, cost: rows.reduce((a, f) => a + (Number(f.cost) || 0), 0), proofs: rows.filter(f => !f.proposal || f.noTrade).length };
}

function Curve({ data }) {
  if (data.length < 2) return <span className="ppx-curve is-empty" aria-hidden="true" />;
  const up = data[data.length - 1].v >= 0;
  return <span className={`ppx-curve ${up ? 'is-up' : 'is-dn'}`} data-testid="ppx-curve"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 3, right: 0, bottom: 0, left: 0 }}>
    <defs><linearGradient id="ppxFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity={0.4} /><stop offset="100%" stopColor="currentColor" stopOpacity={0} /></linearGradient></defs>
    <YAxis hide domain={['dataMin', 'dataMax']} /><ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.3} strokeDasharray="2 3" />
    <Area type="stepAfter" dataKey="v" stroke="currentColor" strokeWidth={1.5} fill="url(#ppxFill)" isAnimationActive={false} /></AreaChart></ResponsiveContainer></span>;
}

function Hero({ n, onTab }) {
  const live = n.open.find(t => !t.card);
  return <div className="ppx-hero" data-testid="ppx-hero">
    <div className={`ppx-kpi is-pnl ${n.pnl >= 0 ? 'is-up' : 'is-dn'}`} style={{ '--i': 0 }} data-tip={`Paper P&L without fees (§1): each closed PoP's ROE on its $${STAKE_USD} paper stake, summed. Ghosts of passed proposals never count.`}>
      <small>PAPER P&L · NO FEES</small><b className="m-num" data-testid="ppx-pnl">{n.trades.length ? usd(n.pnl) : '$0.00'}</b><Curve data={n.curve} /><em>{n.trades.length} trade{n.trades.length === 1 ? '' : 's'} · ${STAKE_USD} stake each</em></div>
    <div className="ppx-kpi" style={{ '--i': 1 }} data-tip="Closed paper PoPs that made money. Its proposals' ghosts are tracked apart">
      <small>WIN RATE</small><b className="m-num" data-testid="ppx-win">{n.winPct == null ? '—' : `${n.winPct}%`}</b><span className="ppx-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(n.winPct || 0) / 100})` }} /></span>
      <em>{n.trades.length ? `${n.won}/${n.trades.length} won · best ${pct(Math.max(...n.trades.map(f => Number(f.roePct) || 0)))}` : 'no trade closed yet'}{n.ghosts.length ? ` · ghosts ${n.ghostWon}/${n.ghosts.length}` : ''}</em></div>
    <button type="button" className={`ppx-kpi is-go${live ? ' is-live' : ''}`} style={{ '--i': 2 }} onClick={() => onTab('desk')} data-tip="The paper position open now, or a proposal waiting for your Run" data-testid="ppx-kpi-open">
      <small>{live ? <i className="ppx-lamp" aria-hidden="true" /> : null}OPEN</small><b className="m-num" data-testid="ppx-open-n">{n.open.length}</b>
      <em>{live ? `${live.side} ${live.market} · ${usd(n.openPnl)}` : n.open.length ? 'a proposal waits' : 'flat · nothing open'}</em></button>
    <button type="button" className="ppx-kpi is-go" style={{ '--i': 3 }} onClick={() => onTab('sit')} data-tip="Proofs where the minds read the market and chose not to trade: a split, a pass, or no usable call" data-testid="ppx-kpi-sit">
      <small>SAT OUT</small><b className="m-num" data-testid="ppx-sit-n">{n.sits.length}<small>/{n.rows.length}</small></b>
      <span className="ppx-split" aria-hidden="true">{['passed', 'split', 'nocall'].map(k => <i key={k} className={`is-${k}`} style={{ flexGrow: n.bySit[k] || 0 }} />)}</span>
      <em>pass {n.bySit.passed || 0} · split {n.bySit.split || 0} · none {n.bySit.nocall || 0}</em></button>
  </div>;
}

// ☠ the liquidation ruler: liq · stop · entry · take on one line (danger always on the left), the mark riding it. Liquidation sits far from the
// rest, so the line is piecewise: each stretch gets a fixed share of the ruler and the mark is placed inside its stretch by price.
const RULE = [['liq', 0, '☠ LIQ'], ['sl', 0.38, 'STOP'], ['entry', 0.62, 'ENTRY'], ['tp', 1, 'TAKE']];
export function rulerAt(t) {
  const e = Number(t?.entry) || 0; const dir = t?.side === 'short' ? -1 : 1; const liq = liqPrice(t); if (!e || !liq) return null;
  const mv = v => (v / e - 1) * 100 * dir;   // the move, in % of price, in the trade's favour
  const stops = [[mv(liq), 0], [-(Number(t.sl) || 0), 0.38], [0, 0.62], [Number(t.tp) || 0, 1]].filter(([m], i, a) => !i || m > a[i - 1][0]);
  const m = mv(Number(t.mark) || e); let mark = m <= stops[0][0] ? 0 : 1;
  for (let i = 1; i < stops.length; i += 1) if (m <= stops[i][0]) { const [a, pa] = stops[i - 1]; const [b, pb] = stops[i]; mark = pa + (pb - pa) * (m - a) / (b - a); break; }
  return { liq, sl: t.sl ? e * (1 - dir * t.sl / 100) : null, tp: t.tp ? e * (1 + dir * t.tp / 100) : null, e, mark: Math.max(0, Math.min(1, mark)) };
}
export function Ruler({ t }) {
  const r = rulerAt(t); if (!r) return null; const price = { liq: r.liq, sl: r.sl, entry: r.e, tp: r.tp };
  return <div className={`ppx-ruler is-${t.side}`} data-testid="ppx-ruler" data-tip={`☠ ${px(r.liq)} · stop ${px(r.sl)} · entry ${px(r.e)} · take ${px(r.tp)} · mark ${px(t.mark)}`}>
    <u aria-hidden="true"><s style={{ left: 0, width: '38%' }} /></u>
    {RULE.filter(([k]) => price[k]).map(([k, at, l]) => <span key={k} className={`ppx-tick is-${k}`} style={{ left: `${at * 100}%` }}><i aria-hidden="true" /><small>{l}</small><small className="m-num">{px(price[k])}</small></span>)}
    <b className="ppx-mark" style={{ left: `${r.mark * 100}%` }} aria-label={`mark ${px(t.mark)}`} data-testid="ppx-mark" /></div>;
}

function Position({ t, send, busy }) {
  if (t.card) return <div className="ppx-cardwrap"><ProposalCard c={t} send={send} busy={busy} /></div>;
  const liq = liqPrice(t); const mins = Math.max(0, Math.floor((Date.now() / 1000 - Number(t.openedAt || t.at || 0)) / 60)); const pnl = STAKE_USD * Number(t.roePct || 0) / 100;
  return <article className={`ppx-pos is-${t.side} ${pnl >= 0 ? 'is-up' : 'is-dn'}`} data-testid="ppx-pos">
    <header><em className={`ppx-side is-${t.side}`}>{t.side}</em><b>{t.market}-PERP</b><small className="m-num">{t.lev}× · paper · {mins} min</small><TestTag f={t} /></header>
    <div className="ppx-pnl"><b className="m-num" key={t.mark} data-testid="ppx-pos-pnl">{usd(pnl)}</b><small className="m-num">{pct(t.roePct)} ROE · no fees</small></div>
    <dl className="ppx-nums"><div><dt>ENTRY</dt><dd className="m-num">{px(t.entry)}</dd></div><div><dt>MARK</dt><dd className="m-num" data-testid="ppx-pos-mark">{px(t.mark)}</dd></div>
      <div className="is-liq"><dt>☠ LIQ</dt><dd className="m-num" data-testid="ppx-pos-liq">{px(liq)}</dd></div><div><dt>TP / SL</dt><dd className="m-num">+{t.tp}/−{t.sl}%</dd></div></dl>
    <Ruler t={t} />
    {(t.calls || []).length ? <ul className="ppx-minds">{t.calls.map(c => <li key={c.mind}><b>{c.name}</b><small>{mindWhy(c.why)}</small></li>)}</ul> : null}
    <button type="button" className="m-btn" disabled={busy} onClick={() => send('stop')} data-tip="Ends this PoP at the live price" data-testid="pop-stop">■ Stop</button>
  </article>;
}

function Desk({ n, send, busy, onTab }) {
  const pos = n.open.find(t => t.market); const [mk, setMk] = useState(null); const m = mk || pos?.market || n.lastRead[0]?.market || 'SOL';
  const t = n.open.find(x => x.market === m && x.entry); const dir = t?.side === 'short' ? -1 : 1; const e = Number(t?.entry) || 0;
  const lines = useMemo(() => (e ? [{ id: 'entry', price: e, color: tok('--m-text'), title: 'ENTRY' }, { id: 'tp', price: e * (1 + dir * t.tp / 100), color: tok('--ppd-ac2'), title: 'TAKE', dash: true },
    { id: 'sl', price: e * (1 - dir * t.sl / 100), color: tok('--ppd-dg1'), title: 'STOP', dash: true }, ...(liqPrice(t) ? [{ id: 'liq', price: liqPrice(t), color: tok('--m-danger'), title: '☠ LIQ' }] : [])] : []), [e, dir, t]);   // eslint-disable-line react-hooks/exhaustive-deps
  const read = n.lastRead.find(r => r.market === m); const last = n.sits[0];
  return <div className="ppx-desk">
    <section className="ppx-chart" data-testid="ppx-chart">
      <header><span className="m-seg ppx-mks" role="group" aria-label="Market">{MARKETS.map(k => <button key={k} type="button" className={m === k ? 'active' : ''} aria-pressed={m === k} onClick={() => setMk(k)} data-testid={`ppx-mk-${k}`}>{k}{n.open.some(x => x.market === k) ? <i className="ppx-lamp" aria-hidden="true" /> : null}</button>)}</span>
        {read ? <small className="m-num" data-tip="What the minds read on their last PoP">last read {px(read.px)} · <span className={read.chgPct >= 0 ? 'is-up' : 'is-dn'}>{pct(read.chgPct)} 24h</span></small> : null}</header>
      <div className="ppx-chart-in"><Suspense fallback={<p className="ppx-none">Loading true candles…</p>}><PerpsChartLazy key={m} asset={m} iv="1m" lines={lines} /></Suspense></div>
      <small className="ppx-src">True candles from the engine's own mark feed (Coinbase Exchange), the same prices its paper fills use</small>
    </section>
    <section className="ppx-side-col" data-testid="ppx-open">
      {n.open.length ? n.open.map(x => <Position key={x.id || x.market} t={x} send={send} busy={busy} />)
        : <div className="ppx-flat"><b>FLAT</b><small>No paper position open. A PoP opens only when both minds agree on the same market and side.</small>
          {last ? <button type="button" className="ppx-lastsit" onClick={() => onTab('sit')} data-tip="Every time they sat out" data-testid="ppx-lastsit"><em>{SIT[sitKind(last)][0]} · {pn(last)} · {ago(last.at)} ago</em><span>{mindWhy((last.calls || [])[1]?.why || (last.calls || [])[0]?.why || last.why)}</span></button> : null}</div>}
    </section>
  </div>;
}

function SatOut({ n, onOpen }) {
  if (!n.sits.length) return <p className="ppx-none">They have not sat out yet. Every PoP where the minds choose not to trade lands here with each mind's reason.</p>;
  const max = Math.max(1, ...Object.values(n.bySit));
  return <><ol className="ppx-sbars" data-testid="ppx-sbars">{['passed', 'split', 'nocall'].map((k, i) => <li key={k} className={`is-${k}`} style={{ '--i': i }} data-tip={SIT[k][1]}><small>{SIT[k][0]}</small><span className="ppx-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(n.bySit[k] || 0) / max})` }} /></span><b className="m-num">{n.bySit[k] || 0}</b></li>)}</ol>
    <ol className="ppx-rows" data-testid="ppx-sits">{n.sits.map((f, i) => { const k = sitKind(f);
      return <li key={f.id} className="ppx-row is-sit" style={{ '--i': Math.min(i, 14) }}><button type="button" className="ppx-open-b" onClick={() => onOpen(f.id)} data-tip="Open its folder: the reads, each mind's sources, the discussion" data-testid={`ppx-sit-${f.id}`}>
        <span className="ppx-sit-h"><em className={`ppx-tag is-${k}`}>{SIT[k][0]}</em><b>{pn(f)}</b><small>{ago(f.at)} ago{f.proposal ? ' · proposal' : ''}</small><TestTag f={f} />
          {(f.reads || []).length ? <span className="ppx-reads">{f.reads.map(r => <small key={r.market} className="m-num">{r.market} {px(r.px)} <i className={r.chgPct >= 0 ? 'is-up' : 'is-dn'}>{pct(r.chgPct)}</i></small>)}</span> : null}</span>
        <span className="ppx-why">{(f.calls || []).length ? f.calls.map(c => <span key={c.mind} className={`ppx-mind is-m${c.mind}`}><em>{c.side && c.side !== 'none' ? `${c.side} ${c.market}` : 'pass'}</em><b>{c.name || `mind ${c.mind === 0 ? 'A' : 'B'}`}</b><small>{mindWhy(c.why)}</small></span>)
          : <span className="ppx-mind"><small>{f.why || 'no reason filed'}</small></span>}</span></button></li>; })}</ol></>;
}

function Filed({ n, onOpen }) {
  return <><ProposalScore rows={n.rows} /><ol className="ppx-rows is-dense" data-testid="ppx-filed">{n.rows.map((f, i) => { const g = f.noTrade || f.roePct == null ? '' : f.roePct > 0 ? 'is-up' : 'is-dn';
    return <li key={f.id} className="ppx-row" style={{ '--i': Math.min(i, 14) }}><button type="button" className="ppx-open-b is-line" onClick={() => onOpen(f.id)} data-tip={f.why || ''} data-testid={`pop-x-${f.id}`}>
      <em className="m-num ppx-num">{f.n != null ? `#${f.n}` : '·'}</em><span className="ppx-t"><b>{f.kept ? '📌 ' : ''}{pn(f)} · {f.noTrade ? 'no trade' : `${f.side} ${f.market} ${f.lev}×`}</b><small>{f.ghost ? 'ghost of a proposal · not counted' : f.noTrade ? SIT[sitKind(f)][0].toLowerCase() : f.why || f.status} · {ago(f.at)} ago</small></span>
      <span className="ppx-n"><b className={`m-num ${g}`}>{f.noTrade ? '—' : pct(f.roePct)}</b><small>{f.noTrade || f.ghost ? 'ROE' : usd(f.pnlUsd ?? STAKE_USD * Number(f.roePct || 0) / 100)}</small></span>
      <span className="ppx-n"><b className="m-num">{f.cost != null ? `$${Number(f.cost).toFixed(4)}` : '—'}</b><small>minds</small></span><TestTag f={f} /></button></li>; })}</ol></>;
}

export function PopDash({ d, send, busy = false, asking = false, err = '', price = '', onOpen, tools = null }) {
  const [tab, setTab] = useState(readTab);
  const n = useMemo(() => popNumbers(d?.popFolders, d?.popFolder, d?.popCard), [d?.popFolders, d?.popFolder, d?.popCard]);
  const go = k => { setTab(k); try { localStorage.setItem(TAB_KEY, k); } catch { /* private window */ } };
  const live = n.open.find(t => !t.card); const counts = { desk: n.open.length, sit: n.sits.length, filed: n.rows.length };
  return <section ref={box} className="ppx" data-testid="ppx">
    <Hero n={n} onTab={go} />
    <div className="ppx-bar-row">
      <div className="m-seg ppx-tabs" role="tablist" aria-label="PoP dashboard">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={e => { go(k); e.currentTarget.scrollIntoView?.({ block: 'nearest', inline: 'nearest' }); }} data-testid={`ppx-tab-${k}`}>
        {k === 'desk' && live ? <i className="ppx-lamp" aria-hidden="true" /> : null}{l}{counts[k] ? <em className="m-num"> {counts[k]}</em> : null}</button>)}</div>
      <span className="ppx-acts">{!d?.popCard && !live ? <button type="button" className="m-btn" disabled={busy} onClick={() => send('propose')} data-tip="The same paid call, filed as a card. Nothing opens until you press Run. Or type propose a perp" data-testid="pop-propose">💡 Propose</button> : null}
        {!live ? <button type="button" className="m-btn m-go" disabled={busy} onClick={() => send('start')} data-tip="Each mind reads its own sources against the chart and makes one small paid model call. A paper trade runs only if they agree. Or type file a perp" data-testid="pop-start">File a PoP{price ? ` · ${price}` : ''}</button> : null}</span>
    </div>
    {asking ? <p className="ppx-asking" role="status" data-testid="pop-asking"><i aria-hidden="true" />{d?.popRead ? 'Each mind is reading sites in its own window. Watch its monitors…' : 'Each mind is reading its own sources against the chart…'}</p> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <div key={tab} className="ppx-pane" role="tabpanel">
      {tab === 'desk' ? <Desk n={n} send={send} busy={busy} onTab={go} /> : tab === 'sit' ? <SatOut n={n} onOpen={onOpen} /> : tab === 'filed' ? <Filed n={n} onOpen={onOpen} /> : <div className="ppx-tools">{tools}</div>}
    </div>
  </section>;
}
