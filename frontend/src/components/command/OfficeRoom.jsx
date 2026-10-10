import React, { Suspense, lazy, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { ChartBox, dump, sgn, usd, ago, clock, ms, STRUCT_CLS } from './OfficeBoard';
import { tiny } from '../../lib/num';
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
  return { w, h, hi, lo, last: rs[rs.length - 1][4], y,
    bars: rs.map((r, i) => ({ x: i * step + step / 2, o: y(r[1]), h: y(r[2]), l: y(r[3]), c: y(r[4]), up: r[4] >= r[1], bw })),
    lines: lv.filter(l => l.px <= hi && l.px >= lo).map(l => ({ ...l, y: y(l.px) })),
    off: lv.filter(l => l.px > hi || l.px < lo).map(l => ({ ...l, up: l.px > hi })) };   // too far to draw to scale: named at the edge it lies beyond, never squashed in
}
// SVG labels go through createElement: the dev server's babel plugin wraps a JSX {expr} child in a <span>, which SVG cannot draw
const T = (props, text) => React.createElement('text', props, text);

export function CandleChart({ bars, levels, note, big }) {
  const g = useMemo(() => candleGeom(bars?.rows, levels, big ? 520 : 420, big ? 112 : 150), [bars, levels, big]);
  if (!g) return <div className="ofr-nochart" data-testid="ofr-nochart">no candles for this coin this pass — the agents are not shown a chart they did not read</div>;
  return <figure className="ofr-chart" data-testid="ofr-chart" data-tip={bars.src === 'candles' ? 'The same one-minute candles the agents read this pass, with their levels.' : "Tally's own tape (closes only): drawn as a line, never as candles."}>
    <svg viewBox={`0 0 ${g.w} ${g.h}`} preserveAspectRatio="none" role="img" aria-label="The candles the agents read this pass, with their levels">
      {g.lines.map(l => <g key={l.label} className={`ofr-lv ${l.cls || ''}`}><line x1="0" x2={g.w - 54} y1={l.y} y2={l.y} />{T({ x: g.w - 52, y: l.y + 3 }, l.label)}</g>)}
      {bars.src === 'tape' ? <polyline className="ofr-line" points={g.bars.map(b => `${b.x},${b.c}`).join(' ')} /> : g.bars.map((b, i) => <g key={i} className={b.up ? 'ofr-up' : 'ofr-dn'}><line x1={b.x} x2={b.x} y1={b.h} y2={b.l} /><rect x={b.x - b.bw / 2} y={Math.min(b.o, b.c)} width={b.bw} height={Math.max(0.8, Math.abs(b.c - b.o))} /></g>)}
      {g.off.map((l, i) => <g key={l.label} className={`ofr-lv ${l.cls || ''}`}>{T({ x: 4 + g.off.filter((x, j) => j < i && x.up === l.up).length * 92, y: l.up ? 9 : g.h - 3 }, `${l.up ? '↑' : '↓'} ${l.label}`)}</g>)}
      <g className="ofr-lv is-last"><line x1="0" x2={g.w - 54} y1={g.y(g.last)} y2={g.y(g.last)} />{T({ x: g.w - 52, y: g.y(g.last) + 3 }, tiny(g.last))}</g>
    </svg>
    <figcaption>{bars.src === 'candles' ? `${bars.rows.length} one-minute candles — the same rows the agents read` : `${bars.rows.length} tape readings (closes only)`}{note ? ` · ${note}` : ''}</figcaption>
  </figure>;
}

// the coin on screen: the current candidate, or an open position (then its entry / take / stop / invalidation are drawn)
export function coinView(o, sym) {
  const p = (o?.positions || []).find(x => x.symbol === sym);
  if (p) { const e = p.entry; const th = p.thesis;
    return { kind: 'position', symbol: p.symbol, bars: p.bars, pos: p, structure: p.structure, note: `REAPER: ${p.decision}`,
      levels: [e && { px: e, label: 'entry', cls: 'is-entry' }, e && p.take && { px: e * (1 + p.take / 100), label: `take +${p.take}%`, cls: 'is-take' }, e && p.stop && { px: e * (1 + p.stop / 100), label: `stop ${p.stop}%`, cls: 'is-stop' },
        th?.invalidation && { px: th.invalidation, label: 'invalid', cls: 'is-stop' }, th?.support && { px: th.support, label: 'support', cls: 'is-sup' }].filter(Boolean) }; }
  const c = o?.currentCase; if (!c || (sym && c.symbol !== sym)) return null; const f = c.chart?.f || {};
  return { kind: 'case', symbol: c.symbol, bars: c.bars, cur: c, structure: c.chart?.state, note: c.chart ? `TRIGGER: ${c.chart.entry?.[0]}` : null,
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
// everything the 3D room draws, as plain data: ten stations (action word · state · monitor line · focus · selected), the wall monitor
// (coin · stage · structure · decision · Warden · Devil · review clock · the candles + levels) and the pipeline counts
export function roomModel(o, sel, coin) {
  const focus = focusOf(o); const names = Object.fromEntries((o?.agents || []).map(a => [a.key, a.name])); const hot = hotPosition(o?.positions);
  const view = coinView(o, coin) || coinView(o, o?.currentCase?.symbol) || (hot ? coinView(o, hot.symbol) : null); const c = view?.cur; const p = view?.pos;
  const wall = !view ? null : { kind: view.kind, symbol: view.symbol, bars: view.bars, levels: view.levels, structure: view.structure || 'NO CHART', move: p ? p.pct : c?.chart?.f?.r5 ?? null,
    stage: p ? 'Reaper' : names[focus] || focus, decision: p ? p.decision : c?.chart?.entry?.[0] || String(c?.trigger?.call?.[0] || '—').toUpperCase(),
    warden: p ? (p.warden != null ? `${p.warden}×` : 'not sized') : c?.warden ? `${c.warden.eff}×${c.warden.veto ? ' VETO' : ''}` : c?.chart ? `${c.chart.risk?.[0]}× chart risk` : '—',
    devil: p ? (p.devil === 'object' ? 'OBJECT' : p.devil === 'agree' ? 'NO OBJECTION' : '—') : c?.devil?.verdict === 'agree' ? 'NO OBJECTION' : c?.devil ? 'OBJECT' : '—',
    reviewAt: p?.nextReview != null ? Math.max(0, p.nextReview - (Date.now() / 1000 - (o?.at || Date.now() / 1000))) : null,
    caption: view.bars ? (view.bars.src === 'candles' ? `${view.bars.rows.length} one-minute candles the agents read` : `${view.bars.rows.length} tape readings (closes only)`) : 'no candles this pass' };
  return { wall, focus,
    stations: (o?.agents || []).map(a => { const [tag] = agentTag(a.key, o); return { key: a.key, name: a.name, tag, cls: TAG_CLS[tag] || 'is-wait', line: deskLine(a.key, o), focus: focus === a.key, selected: sel === a.key }; }),
    status: [[o?.office?.cleared ?? 0, 'cleared', '#45e486'], [(o?.office?.cases ?? 0) - (o?.office?.cleared ?? 0), 'blocked', '#f5c451'], [(o?.positions || []).length, 'open positions', '#6cc7ff'], [o?.office?.coins ?? 0, 'coins read', '#7d998b'], [o?.execution?.health || '—', 'execution', o?.execution?.health === 'HEALTHY' ? '#45e486' : '#ff6b86']] };
}
// the office's latest rulings, newest first, every desk in one list (each line is that desk's own recorded decision)
export function rulingsOf(o, n = 8) {
  const now = (o?.agents || []).filter(a => a.decision && a.decisionAt).map(a => ({ at: a.decisionAt, key: a.key, name: a.name, text: a.decision })).sort((x, y) => y.at - x.at);
  const seen = new Set(now.map(r => `${r.key}|${r.text}`));
  const past = (o?.agents || []).flatMap(a => (a.recent || []).filter(r => r.at && !seen.has(`${a.key}|${r.text}`)).map(r => ({ at: r.at, key: a.key, name: a.name, text: r.text }))).sort((x, y) => y.at - x.at);
  return [...now, ...past].slice(0, n);
}
export const hhmm = at => { const d = new Date(at * 1000); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const Tag = ({ cls, children, tip }) => <i className={`ofr-tag ${cls || ''}`} data-tip={tip}>{children}</i>;
const Bot = () => <span className="ofr-bot" aria-hidden><i className="ofr-ant" /><i className="ofr-head"><u /><u /></i><i className="ofr-body" /></span>;
const Spark = ({ xs, cls }) => { const v = (xs || []).filter(x => x != null); if (v.length < 2) return <svg className="ofr-spark" viewBox="0 0 60 18" aria-hidden />;
  const hi = Math.max(...v); const lo = Math.min(...v); const sp = (hi - lo) || 1;
  return <svg className={`ofr-spark ${cls || ''}`} viewBox="0 0 60 18" preserveAspectRatio="none" aria-hidden><polyline points={v.map((x, i) => `${(i / (v.length - 1)) * 60},${16 - ((x - lo) / sp) * 14}`).join(' ')} /></svg>; };

export function RoomScene({ o, sel, onSel, coin, onCoin }) {
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
          <CandleChart bars={view.bars} levels={view.levels} note={view.note} />
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
    <p className="ofr-flow"><span>Flow: {(o.office?.chain || []).join(' → ')}</span><b data-testid="ofr-ticker">{ticker(o)}</b></p>
  </div>;
}

export const PANEL_TABS = [['live', 'Live decision'], ['beliefs', 'Beliefs & ethics'], ['inputs', 'Current inputs'], ['chart', 'Chart intel'], ['code', 'Source code']];

export function AgentPanel({ o, a, coin, onCoin }) {
  const [tab, setTab] = useState('live'); const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(t); }, []);
  if (!a) return null;
  const c = a.card || {}; const [tag, word] = agentTag(a.key, o); const hot = hotPosition(o.positions);
  const view = (a.key === 'reaper' && !coin && hot ? coinView(o, hot.symbol) : coinView(o, coin)) || coinView(o, o.currentCase?.symbol) || (hot ? coinView(o, hot.symbol) : null);
  const p = view?.pos; const ch = view?.cur?.chart; const wd = view?.cur?.warden; const tk = o.take || {};
  const review = p?.nextReview != null ? Math.max(0, p.nextReview - (Date.now() / 1000 - (o.at || 0))) : null;
  const coins = [...new Set([o.currentCase?.symbol, ...(o.positions || []).map(x => x.symbol)].filter(Boolean))];
  return <aside className="ofr-panel" style={{ '--ag': AG[a.key] }} data-testid="ofr-panel">
    <header className="ofr-phead"><span className="ofr-pname" data-tip={a.role}><b>{a.icon} {a.name.toUpperCase()}</b><small>gen {c.gen ?? 1} · {a.role}</small></span>
      <Tag cls={c.status === 'alive' ? 'is-pass' : 'is-obj'} tip={c.why}>● {c.status === 'alive' ? 'LIVE' : (c.status || '—').toUpperCase()}</Tag></header>
    <div className="m-seg ofr-tabs" role="tablist" aria-label={`${a.name} views`}>{PANEL_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`ptab-${k}`}>{l}</button>)}</div>
    {tab === 'live' && <div className="ofr-pane" data-testid="pane-live">
      <div className="ofr-decision" data-tip={`${a.decision || word}${a.rule ? ` · rule: ${a.rule}` : ''}`}><small>CURRENT DECISION · {ago(a.decisionAt)}{a.rule ? ` · rule: ${a.rule}` : ''}</small><b><Tag cls={TAG_CLS[tag]}>{tag}</Tag>{a.decision || word}</b></div>
      <div className="ofr-tiles">
        <span data-tip="How much judged record stands behind this desk (samples ÷ (samples + 30)) and how often it was right."><small>RECORD</small><em>{c.accuracy == null ? '—' : `${c.accuracy}%`}</em><u>{c.n ?? 0} samples · conf {c.confidence != null ? `${Math.round(c.confidence * 100)}%` : '—'}</u></span>
        <span data-tip="The lines this coin trades inside: the active take line and the stop for this entry. Not a forecast."><small>TAKE / STOP</small><em>{p ? `+${p.take}% / ${p.stop}%` : ch ? `+${tk.active ?? '—'}% / −${ch.stop}%` : '—'}</em><u>{p ? `${p.takeSource} take` : `${tk.source || '—'} take`}</u></span>
        <span><small>RISK</small><em>{ch ? `${ch.risk?.[0]}×` : p?.warden != null ? `${p.warden}×` : '—'}</em><u>{ch ? ch.risk?.[1] : p ? `sized by the Warden` : 'no chart risk read'}</u></span>
        <span><small>POSITION SIZE</small><em>{p ? usd(p.usd) : wd ? usd(wd.allowed) : '—'}</em><u>{p ? 'on the card now' : wd ? `asked ${usd(wd.requested)} · ${wd.decided}` : 'sized when a seat opens'}</u></span></div>
      <div className="ofr-csel"><small>CHART</small>{coins.map(s => <button key={s} type="button" className={view?.symbol === s ? 'is-on' : ''} onClick={() => onCoin(s)} data-testid={`coin-${s}`}>${s}</button>)}
        {review != null ? <em data-testid="ofr-review">⏱ next review {clock(review)}</em> : null}</div>
      {view ? <CandleChart bars={view.bars} levels={view.levels} note={view.note} big /> : <div className="ofr-nochart">no candidate and no open position this pass</div>}
      <div className="ofr-intel" data-testid="ofr-intel"><small>CHART INTELLIGENCE{view ? ` · $${view.symbol}` : ''}</small>
        {(() => { const s = ch || p?.chart; const st = view?.structure; return <div className="ofr-igrid">
          <span><u>Structure</u><b>{st ? <Tag cls={STRUCT_CLS[st]}>{st}</Tag> : '—'}</b></span><span><u>Trend</u><b>{s?.trend ?? '—'}<i>/100</i></b></span><span><u>Chop</u><b>{s?.chop ?? '—'}<i>/100</i></b></span>
          <span><u>Momentum</u><b>{s?.mom ?? '—'}<i>/100</i></b></span><span><u>Extension</u><b>{s?.ext ?? '—'}<i>/100</i></b></span>
          <span><u>Flow</u><b>{ch?.f?.buy != null ? `${Math.round(ch.f.buy)}% buy` : '—'}</b></span><span><u>Liquidity</u><b>{ch?.f?.liq != null ? `$${(ch.f.liq / 1000).toFixed(0)}K` : p?.liq != null ? `$${(p.liq / 1000).toFixed(0)}K` : '—'}</b></span>
          <span><u>Warden size</u><b>{wd ? `${wd.eff}×` : p?.warden != null ? `${p.warden}×` : ch ? `${ch.risk?.[0]}× chart` : '—'}</b></span>
          <span><u>Reaper next review</u><b>{review != null ? clock(review) : '—'}</b></span><span><u>Active take source</u><b>{p?.takeSource || tk.source || '—'} +{p?.take ?? tk.active ?? '—'}%</b></span>
          <span className="is-wide"><u>{p ? 'Thesis' : 'Entry call'}</u><b>{p ? (p.thesis ? `${p.thesis.structure} · ${p.thesis.triggerRule} → now ${p.verdict || 'unchecked'}` : 'no thesis on file') : ch ? `${ch.entry?.[0]} — ${ch.entry?.[2]}` : '—'}</b></span></div>; })()}</div>
      <div className="ofr-rul" data-testid="ofr-rulings"><small>LIVE RULINGS · every desk, newest first</small>{rulingsOf(o, 4).length ? <ul>{rulingsOf(o, 4).map((r, i) => <li key={i} className={r.key === a.key ? 'is-me' : ''} style={{ '--ag': AG[r.key] }} data-tip={r.text}><u>{hhmm(r.at)}</u><b>{r.name}</b> {r.text}</li>)}</ul> : <span className="ofr-nil">none on record yet</span>}</div>
      <p className="ofr-files" data-testid="ofr-files"><small>RUNTIME last {ms(c.latency?.last)} · p95 {ms(c.latency?.p95)}</small>{(a.code || []).map(k => <span key={k.file}><code>{k.file}</code><code className="ofr-fn">{k.fn[0]}()</code></span>)}</p>
    </div>}
    {tab === 'beliefs' && <div className="ofr-pane" data-testid="pane-beliefs"><p className="ofr-ideo">{a.ideology}</p>
      <small>ETHICS</small><ul className="ofr-list">{a.ethics.map(x => <li key={x}>{x}</li>)}</ul><small>IMMUTABLE RULES</small><ul className="ofr-list">{a.hard.map(x => <li key={x}>{x}</li>)}</ul>
      <small>FORBIDDEN</small><ul className="ofr-list is-no">{a.forbidden.map(x => <li key={x}>{x}</li>)}</ul>
      <small>TUNABLE (shadow-tested only)</small>{a.tunable?.length ? <ul className="ofr-list">{a.tunable.map(t => <li key={t.key} data-tip={t.what}>{t.key} = <b>{t.value}</b> · default {t.default} · bounds {t.lo} … {t.hi}</li>)}</ul> : <span className="ofr-nil">none</span>}
      <small>WHY THIS STATE</small><p className="ofr-why">{c.why}</p></div>}
    {tab === 'inputs' && <div className="ofr-pane" data-testid="pane-inputs"><small>TASK</small><p className="ofr-why">{a.task || 'idle'}</p><small>CURRENT INPUTS</small>{dump(a.inputs)}<small>CURRENT OUTPUT</small>{dump(a.output)}</div>}
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
    <div className="ofr-rgrid">{(o.agents || []).map(a => { const c = a.card || {}; const [tag, word] = agentTag(a.key, o); const net = (c.profit ?? 0) + (c.loss ?? 0); const has = c.profit != null || c.loss != null;
      return <button key={a.key} type="button" className={`ofr-rcard ${TAG_CLS[tag] || 'is-wait'} ${sel === a.key ? 'is-on' : ''}`} style={{ '--ag': AG[a.key] }} onClick={() => onSel(a.key)} aria-pressed={sel === a.key} data-tip={`${a.role} ${c.why || ''}`} data-testid={`roster-${a.key}`}>
        <span className="ofr-rhead"><i className="ofr-ricon" aria-hidden>{a.icon}</i><span><b>{a.name}</b><u>gen {c.gen ?? 1} · <i className={c.status === 'alive' ? 'ofr-pos' : 'ofr-warn'}>● {c.status || '—'}</i></u></span>
          <em className={net > 0 ? 'ofr-pos' : net < 0 ? 'ofr-neg' : ''} data-tip={c.unit || 'contribution: nothing measured yet'}>{has ? sgn(net) : '—'}</em></span>
        <span className="ofr-rmid" data-tip={`runtime per pass, last ${(o.performance?.agents?.[a.key]?.series || []).length} passes (ms)`}><Spark xs={o.performance?.agents?.[a.key]?.series} /><span><b data-tip="right % on its own judged record">{c.accuracy == null ? '—' : `${c.accuracy}%`}</b><u>n {c.n ?? 0} · conf {c.confidence != null ? `${Math.round(c.confidence * 100)}%` : '—'} · {ms(c.latency?.last)}</u></span></span>
        <span className="ofr-rtag" data-tip={word}>{tag}</span></button>; })}</div></div>;
}

export const CAMS = [['main', 'Main room'], ['top', 'Top'], ['focus', 'Focus desk']];
const pref = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };

export function OfficeHQ({ o, roomOn = true, passAt, gl: gl0 }) {
  const [sel, setSel] = useState(null); const [coin, setCoin] = useState(null); const [gl] = useState(() => (gl0 != null ? gl0 : has3D()));
  const [cam, setCam] = useState(() => pref.get('feeless.roomCam', 'main')); const [rot, setRot] = useState(() => pref.get('feeless.roomRot', 'off') === 'on');
  const cur = sel || focusOf(o); const box = useRef(null);
  // the office takes exactly the height the window has left under the mission + status strip, so room · panel · roster share ONE view
  useLayoutEffect(() => { const fit = () => { const el = box.current; const st = el?.querySelector('.ofr-main'); if (!el || !st) return; const top = st.getBoundingClientRect().top + (window.scrollY || 0);
    const rosterH = el.querySelector('.ofr-roster')?.offsetHeight || 96; el.style.setProperty('--ofr-h', `${Math.round(Math.max(390, Math.min(720, window.innerHeight - top - rosterH - 22)))}px`); };
    fit(); window.addEventListener('resize', fit); return () => window.removeEventListener('resize', fit); }, [o?.cold, roomOn]);
  const model = useMemo(() => (o && !o.cold ? roomModel(o, cur, coin) : null), [o, cur, coin]);
  if (!o || o.cold) return <section className="ofr" data-testid="office-hq"><p className="ofr-nil">waiting for the agents' first pass — the room shows nothing it was not handed</p></section>;
  const a = (o.agents || []).find(x => x.key === cur); const q = o.queue || [];
  return <section className={`ofr ${roomOn ? '' : 'is-flat'}`} data-testid="office-hq" ref={box}>
    <header className="ofr-bar"><b>🏢 THE AGENT OFFICE</b><span className="ofr-live"><i />live</span><small data-testid="ofr-ticker">last pass {ago(passAt || o.at)} · {ticker(o)}</small>
      {roomOn && gl ? <span className="ofr-cams"><span className="m-seg" role="group" aria-label="Camera">{CAMS.map(([k, l]) => <button key={k} type="button" className={cam === k ? 'active' : ''} onClick={() => { setCam(k); pref.set('feeless.roomCam', k); }} data-testid={`cam-${k}`}>{l}</button>)}</span>
        <button type="button" className={`m-btn ${rot ? 'is-on' : ''}`} aria-pressed={rot} onClick={() => { setRot(!rot); pref.set('feeless.roomRot', rot ? 'off' : 'on'); }} data-tip="Sweep the camera slowly across the room (Main room view)" data-testid="cam-rotate">⟳ Auto rotate {rot ? 'on' : 'off'}</button></span> : null}</header>
    <div className="ofr-main">
      {roomOn ? <div className="ofr-stage" data-testid="ofr-stage">
        {gl ? <Suspense fallback={<div className="ofr-loading">building the room…</div>}><OfficeRoom3D model={model} onSel={setSel} cam={cam} rotate={rot} /></Suspense> : <RoomScene o={o} sel={cur} onSel={setSel} coin={coin} onCoin={setCoin} />}
        {gl ? <div className="ofr-over" data-testid="ofr-queue"><small>CASE FILES</small>{q.length ? q.map(x => <button key={x.mint} type="button" className={`ofr-case ${coin === x.symbol ? 'is-on' : ''} ${x.cleared ? 'is-pass' : 'is-obj'}`} style={{ '--ag': AG[x.at] }}
          onClick={() => { setCoin(x.symbol); setSel(x.at); }} data-tip={x.word} data-testid={`case-${x.symbol}`}><b>${x.symbol}</b><u>{x.structure || 'no chart'} · at {x.at} · {TAG_WORD[x.state] || x.state}</u></button>) : <span className="ofr-nil">no case file this pass</span>}
          {(o.positions || []).map(p => <button key={p.mint} type="button" className={`ofr-case is-posn ${coin === p.symbol ? 'is-on' : ''}`} style={{ '--ag': AG.reaper }} onClick={() => { setCoin(p.symbol); setSel('reaper'); }} data-tip={`${p.rule} — ${p.evidence}`} data-testid={`posn-${p.symbol}`}><b>${p.symbol}</b><u>{sgn(p.pct)} · {p.decision}</u></button>)}</div> : null}
      </div> : null}
      <AgentPanel key={cur} o={o} a={a} coin={coin} onCoin={setCoin} /></div>
    <Roster o={o} sel={cur} onSel={setSel} />
  </section>;
}
