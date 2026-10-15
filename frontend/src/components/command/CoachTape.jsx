import { CopyCa } from './CopyCa';
import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { tradeCard, tapeLine, gradeRows, coachRows, pullable, speedMeters, lineWord } from '../../lib/coachTape';
import { STANCE_TONE } from '../../lib/aiRead';
import '../../styles/coachTape.css';

// 🎬 THE REAL TRADE TAPE — every real agent trade as ONE story: the fill → why the agents took it → what the model said → the exit → the
// result → the Judge's ruling. Built server-side from the ledger, the archive, the Judge's reviews and the model's log (coach.trade_tape).
// 👑 THE COACH — the directives that weigh the ranking right now (yours · the model's · the Judge's), ✅ back / ✕ kill, teach a new one,
// and PULL + TEACH: sell a seat with a cause the agents then rank against. Same one payload as the rest of the tab; no request of its own.
const tx = sig => `https://solscan.io/tx/${sig}`;

function Trade({ r, now, on, onPick }) {
  const c = tradeCard(r, now);
  return <li className={`ctp-trade ${c.tone} ${on ? 'is-on' : ''}`} data-testid={`ctp-trade-${c.sym}`}>
    <button type="button" className="ctp-head" onClick={() => c.mint && onPick?.(c.mint)} data-tip="Put this coin on the chart">
      <b>${c.sym}<CopyCa mint={c.mint} sym={c.sym} testid={`ctp-ca-${c.sym}`} /></b>{c.yours ? <i className="ctp-yours" data-tip="your own pick — the agents only suggest on it">👤 YOURS</i> : null}<small>{c.ago} ago</small><em className="ctp-res" data-testid={`ctp-res-${c.sym}`}>{c.head}{c.usd ? <i>{c.usd}</i> : null}</em></button>
    <ol className="ctp-steps">
      <li className="is-buy"><span>⬇ FILL</span><p>{c.buy.join(' · ') || '—'}{c.slipBad ? <i className="ctp-warn" data-tip="This fill landed more than 2.5% above the market price of the decision"> ⚠</i> : null}{c.slow ? <i className="ctp-warn" data-tip="More than a minute passed between the call and the fill"> ⏱</i> : null}
        {c.buySig ? <a href={tx(c.buySig)} target="_blank" rel="noreferrer" aria-label="Buy transaction">tx ↗</a> : null}</p></li>
      <li className="is-why"><span>🤖 WHY</span><p>{c.why.join(' · ') || 'no entry record kept'}{c.src.length ? <small> · from {c.src.join(', ')}</small> : null}</p></li>
      {c.ai ? <li className="is-ai"><span>🧠 {c.ai.label}</span><p><em className={`cai-stance ${STANCE_TONE[c.ai.stance] || 'is-hold'}`}>{c.ai.stance}</em> {c.ai.text}{c.ai.flags.length ? <small> · {c.ai.flags.join(' · ')}</small> : null}</p></li> : null}
      {c.sells.map(s => <li key={s.sig} className="is-sell"><span>⬆ EXIT</span><p>{s.text || '—'} <a href={tx(s.sig)} target="_blank" rel="noreferrer" aria-label="Sell transaction">tx ↗</a></p></li>)}
      {c.exit.length ? <li className="is-end"><span>☠ REAPER</span><p>{c.exit.join(' · ')}</p></li> : null}
      {c.judge ? <li className="is-judge"><span>👨‍⚖️ JUDGE</span><p>{c.judge}</p></li> : null}
    </ol></li>;
}

function Graded({ title, rec, tip, testid }) {
  const rows = gradeRows(rec, 2);
  if (!rows.length) return null;
  return <div className="ctp-grade" data-testid={testid} data-tip={tip}><small>{title}</small>
    <ul>{rows.slice(0, 8).map(r => <li key={r.k} className={r.tone}><b>{r.k}</b><span className="ctp-bar"><i style={{ transform: `scaleX(${r.fill.toFixed(3)})` }} /></span>
      <em>{r.med == null ? '—' : `${r.med > 0 ? '+' : ''}${r.med.toFixed(0)}%`}</em><small>{r.won}/{r.n} won</small></li>)}</ul></div>;
}

// ⏱ how fast a call becomes a fill — three meters from the tape's own medians (transform-only bars)
function Speed({ st }) {
  const ms = speedMeters(st);
  if (!ms.length) return null;
  return <div className="ctp-speed" data-testid="ctp-speed">{ms.map(m => <span key={m.k} className={`ctp-meter ${m.tone}`} data-tip={m.tip} data-testid={`ctp-speed-${m.k}`}>
    <small>{m.label}</small><b>{m.word}</b><i className="ctp-bar"><i style={{ transform: `scaleX(${m.fill.toFixed(3)})` }} /></i></span>)}</div>;
}

function LineReplay({ line }) {
  const l = lineWord(line);
  if (!l) return null;
  return <p className={`ctp-replay ${l.tone}`} data-testid="ctp-replay" data-tip="Every real trade's recorded path replayed with a tighter cut, against what really happened. It ships only when it clearly pays."><b>🧪 {l.head}</b> {l.text}</p>;
}

export function TradeTape({ tape, mint, onPick }) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => !document.hidden && setNow(Date.now() / 1000), 15000); return () => clearInterval(t); }, []);
  const [show, setShow] = useState('all');
  const rows = useMemo(() => (tape?.rows || []).filter(r => show === 'all' || (show === 'open' ? r.open : show === 'won' ? (r.result?.pct ?? 0) > 0 : r.result && r.result.pct <= 0)), [tape, show]);
  return <section className="m-card ctp" data-testid="ctp-tape">
    <header className="ctp-top"><span className="m-label">🎬 REAL TRADE TAPE</span><small className="ctp-line" data-testid="ctp-stats">{tapeLine(tape?.stats)}</small>
      <span className="m-seg ctp-filter" role="group" aria-label="Trades">{[['all', 'ALL'], ['open', 'OPEN'], ['won', 'WON'], ['lost', 'LOST']].map(([k, l]) =>
        <button key={k} type="button" className={show === k ? 'active' : ''} onClick={() => setShow(k)} data-testid={`ctp-show-${k}`}>{l}</button>)}</span></header>
    <Speed st={tape?.stats} />
    {rows.length ? <ul className="ctp-list">{rows.map(r => <Trade key={`${r.mint}-${r.at}`} r={r} now={now} on={r.mint === mint} onPick={onPick} />)}</ul>
      : <p className="ctp-nil">{(tape?.rows || []).length ? 'Nothing in this view.' : 'No confirmed agent buy on the ledger yet — a trade shows here the moment its fill is signed.'}</p>}
    <div className="ctp-grades"><Graded title="📏 SOURCES · REAL FILLS" rec={tape?.sources} testid="ctp-sources" tip="Each list a coin came from, graded only on confirmed real exits (typical result, capped at ±100%). A coin whose every source is a proven loser ranks down 10%." />
      <Graded title="☠ EXIT RULES · REAL FILLS" rec={tape?.rules} testid="ctp-rules" tip="How the trades each exit rule closed really ended. R4f = sellers took over, R4c = buying climax — read these before trusting either." /></div>
    <LineReplay line={tape?.line} />
  </section>;
}

export function CoachBox({ coach, seats, tpl, call, isOwner }) {
  const [key, setKey] = useState(''); const [why, setWhy] = useState(''); const [seat, setSeat] = useState('');
  const rows = coachRows(coach); const causes = (coach || {}).causes || []; const held = pullable(seats);
  const post = (body, ok) => call('/admin/agents', { method: 'POST', body: JSON.stringify({ coach: body }) }).then(() => { toast.success(ok); setWhy(''); }).catch(e => toast.error(e.message));
  const teach = () => { if (!key) { toast.error('Pick what went wrong first'); return; } post({ key, why }, `👑 Taught: ${key} — the agents rank it down from their next pass`); };
  const pull = () => {
    const s = held.find(x => x.mint === seat);
    if (!s || !key) { toast.error('Pick the seat and the reason'); return; }
    if (!tpl) { toast.error('No real card to pull from'); return; }
    if (!window.confirm(`Pull $${s.symbol} off its seat now (sell it all to card cash) and teach the agents "${key}"? It stays off their buy list for 6 hours.`)) return;
    call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ manualSell: { tpl, pairAddress: s.pair, pct: 100, ack: true } }) })
      .then(() => post({ key, why, mint: s.mint, sym: s.symbol }, `✋ $${s.symbol} pulled — "${key}" is now a rule the agents rank against`)).then(() => setSeat(''))
      .catch(e => toast.error(e.message));
  };
  return <section className="m-card ctp-coach" data-testid="ctp-coach">
    <header className="ctp-top"><span className="m-label">👑 COACH · WHAT THE AGENTS RANK AGAINST</span>
      <small className="ctp-line">a weight on the ranking — never an order, a size or a sell{coach?.watching ? ` · grading ${coach.watching} coin${coach.watching === 1 ? '' : 's'}` : ''}{coach?.blocked ? ` · ${coach.blocked} pulled coin${coach.blocked === 1 ? '' : 's'} off their list` : ''}</small></header>
    {rows.length ? <ul className="ctp-rules">{rows.map(r => <li key={`${r.by}-${r.key}`} className={`is-${r.by}`} data-testid={`ctp-rule-${r.key.replace(/\s+/g, '-')}`}>
      <i className="ctp-who">{r.icon} {r.who}</i><b>{r.key}</b><em>{r.points == null ? '' : `${r.points.toFixed(0)}%`}</em>
      <p>{r.why || r.words}{r.sym ? ` · from $${r.sym}` : ''}{r.left ? <small> · {r.left}</small> : null}</p>
      {r.grade ? <span className={`ctp-rgrade ${r.grade.tone}`} data-tip={r.grade.tip} data-testid={`ctp-grade-${r.key.replace(/\s+/g, '-')}`}>{r.grade.icon} {r.grade.word}</span> : null}
      {isOwner && r.canBack ? <button type="button" className="m-btn ctp-yes" onClick={() => post({ strengthen: r.id }, `✅ Backed: ${r.key} is your rule now`)} data-testid={`ctp-back-${r.id}`} data-tip="Make the model's suggestion YOUR rule: full strength for 24h">✅ Back it</button> : null}
      {isOwner && r.canKill ? <button type="button" className="m-btn ctp-no" onClick={() => post({ kill: r.id }, `✕ ${r.key} dropped`)} data-testid={`ctp-kill-${r.id}`} aria-label={`Drop ${r.key}`}>✕</button> : null}</li>)}</ul>
      : <p className="ctp-nil">Nothing is weighing the ranking beyond the agents' own read. Teach them below — or pull a seat with a reason.</p>}
    {coach?.ai?.summary ? <p className="ctp-aisaid" data-testid="ctp-ai-said">🧠 {coach.ai.source || 'model'} coach: {coach.ai.summary}</p> : null}
    {isOwner ? <div className="ctp-teach" data-testid="ctp-teach">
      <div className="ctp-causes" role="group" aria-label="What went wrong">{causes.map(c => <button key={c.key} type="button" className={key === c.key ? 'active' : ''} onClick={() => setKey(k => (k === c.key ? '' : c.key))} data-tip={c.words} data-testid={`ctp-cause-${c.key.replace(/\s+/g, '-')}`}>{c.key}</button>)}</div>
      <input className="m-input" value={why} onChange={e => setWhy(e.target.value.slice(0, 120))} placeholder="why — in your words (the agents see it)" aria-label="Why" data-testid="ctp-why" />
      <div className="ctp-acts"><button type="button" className="m-btn primary" onClick={teach} disabled={!key} data-testid="ctp-teach-go" data-tip="Adds this as YOUR rule: coins it matches rank down 8% for 24h">👑 Teach the agents</button>
        <select className="m-input" value={seat} onChange={e => setSeat(e.target.value)} aria-label="Seat to pull" data-testid="ctp-seat">
          <option value="">✋ pull a seat…</option>{held.map(s => <option key={s.mint} value={s.mint}>${s.symbol}{s.pct != null ? ` ${s.pct >= 0 ? '+' : ''}${Number(s.pct).toFixed(1)}%` : ''}</option>)}</select>
        <button type="button" className="m-btn danger" onClick={pull} disabled={!seat || !key} data-testid="ctp-pull-go" data-tip="Sells this seat to card cash now AND teaches the reason; the coin stays off the agents' list for 6h">✋ Pull + teach</button></div>
    </div> : null}
  </section>;
}
