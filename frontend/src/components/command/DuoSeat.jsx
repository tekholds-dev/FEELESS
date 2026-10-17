// 🔁 OSSY ⚔ G4 — the tag-team seat (owner, 2026-10-16): the two models take turns deciding ONE seat, a call a minute; when neither
// answers, the agents decide (🤝 backup). Drawn from the Agents payload's `duo` block (no fetch of its own). Every number on the board is
// from their real calls: answered vs missed, buys, latency, confidence, the open seat, each one's own closed-trade record.
import React, { useEffect, useState } from 'react';
import '../../styles/duoSeat.css';

const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - (Number(at) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
const sgn = v => `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`;
const secs = ms => (ms == null ? '—' : `${(ms / 1000).toFixed(1)}s`);
const ACT = ['talk', 'buy', 'sell', 'hold', 'wait', 'noanswer'];
const actKey = a => { const k = String(a || '').toLowerCase().replace(/\s/g, ''); return ACT.includes(k) ? k : 'wait'; };

// pure: one pod's record numbers (n · won · typical) and how full its record bar is (won %, 0–1)
export function podOf(name, rec) {
  const r = (rec || {})[name] || {};
  return { name, n: r.n || 0, won: r.n ? r.won : null, med: r.n ? r.med : null, fill: r.n ? Math.max(0.04, Math.min(1, r.won / 100)) : 0 };
}

// pure: one fighter's live activity from the call log — calls it owned, how many it answered, its buys, typical latency, and the
// signal trace (newest last): one bar per call, height = latency against the slowest call on the board, tone = the action.
export function sideOf(name, log) {
  const all = log || [];
  const mine = all.filter(r => r.model === name);
  const ok = mine.filter(r => r.action && r.action !== 'NO ANSWER');
  const ms = ok.map(r => Number(r.ms)).filter(x => x > 0).sort((a, b) => a - b);
  const top = Math.max(1, ...all.map(r => Number(r.ms) || 0));
  return {
    name, calls: mine.length, answered: ok.length, missed: mine.length - ok.length,
    rate: mine.length ? Math.round((100 * ok.length) / mine.length) : null,
    buys: ok.filter(r => r.action === 'BUY').length, sells: ok.filter(r => r.action === 'SELL').length,
    medMs: ms.length ? ms[Math.floor(ms.length / 2)] : null,
    conf: ok.length ? Math.round(ok.reduce((a, r) => a + (Number(r.conf) || 0), 0) / ok.length) : null,
    last: mine[0] || null,
    bars: mine.slice(0, 16).reverse().map(r => ({ act: actKey(r.action), h: Math.max(0.12, Math.min(1, (Number(r.ms) || top * 0.3) / top)), at: r.at, why: r.why, symbol: r.symbol })),
  };
}

function Side({ s, pod, turn, busy, side }) {
  return <section className={`dso-side ${side} ${turn ? 'is-turn' : ''} ${turn && busy ? 'is-busy' : ''}`} data-testid={`duo-pod-${s.name}`}>
    <i className="dso-scan" aria-hidden="true" />
    <header><b>{s.name}</b><em className="dso-state">{turn ? (busy ? 'THINKING' : 'ON TURN') : 'STANDBY'}<i /></em></header>
    <div className="dso-stats">
      <span><small>CALLS</small><b>{s.calls}</b></span>
      <span className={s.rate != null && s.rate < 50 ? 'bad' : ''}><small>ANSWERED</small><b>{s.rate == null ? '—' : `${s.rate}%`}</b></span>
      <span><small>BUYS</small><b>{s.buys}</b></span>
      <span><small>THINK</small><b>{secs(s.medMs)}</b></span>
      <span><small>CONF</small><b>{s.conf == null ? '—' : s.conf}</b></span>
      <span className={s.missed ? 'bad' : ''}><small>MISSED</small><b>{s.missed}</b></span>
    </div>
    <div className="dso-trace" aria-label={`${s.name} recent calls`}>
      {s.bars.length ? s.bars.map((b, i) => <i key={`${b.at}-${i}`} className={`t-${b.act}`} style={{ '--h': b.h, '--i': i }} title={`${b.act.toUpperCase()}${b.symbol ? ` $${b.symbol}` : ''} · ${b.why || ''}`} />)
        : <small className="dso-none">no calls yet</small>}
    </div>
    <span className="dso-rec"><i style={{ transform: `scaleX(${pod.fill})` }} /></span>
    <small className="dso-recw">{pod.n ? `${pod.n} closed · ${pod.won}% won · ${sgn(pod.med)}` : 'no closed trades yet'}</small>
    <p className="dso-last">{s.last ? <><b className={`a-${actKey(s.last.action)}`}>{s.last.action}{s.last.symbol ? ` $${s.last.symbol}` : ''}</b> {s.last.why} <small>· {ago(s.last.at)}</small></> : '—'}</p>
  </section>;
}

// pure: the live "thinking" read — how far into its typical think time the deciding model is, which step that is, and the coins it reads
export const THINK_STEPS = ['reading the packet', 'weighing the coins', 'checking the agents', 'deciding'];
export function thinkOf(live, typicalMs, nowS) {
  if (!live) return null;
  const el = Math.max(0, nowS - Number(live.at || nowS));
  const typ = Math.max(5, (Number(typicalMs) || 25000) / 1000);
  const frac = Math.min(1, el / typ);
  return { el, typ, frac, step: Math.min(THINK_STEPS.length - 1, Math.floor(frac * THINK_STEPS.length)), over: el > typ * 1.5 };
}

const bar = (v, lo, hi) => Math.max(0.06, Math.min(1, ((Number(v) || 0) - lo) / (hi - lo)));

function Think({ duo, sides }) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { if (!duo.busy) return undefined; const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, [duo.busy]);
  const live = duo.live;
  if (!live) return null;
  const side = sides.find(x => x.name === live.by) || {};
  const t = duo.busy ? thinkOf(live, side.medMs, now) : null;
  return <div className={`dso-think ${duo.busy ? 'is-on' : ''} ${live.by === 'OSSY' ? 'by-ossy' : 'by-g4'}`} data-testid="duo-think">
    <header><b>{duo.busy ? `🧠 ${live.by} is thinking` : `🧠 ${live.by}'s last read`}</b>
      {t ? <small>{Math.round(t.el)}s · typical {Math.round(t.typ)}s{t.over ? ' · slow — the agents decide if it misses' : ''}</small> : <small>{live.held ? `holding $${live.held.symbol} ${live.held.pct != null ? sgn(live.held.pct) : ''}` : `${(live.cands || []).length} coins on the table`}</small>}</header>
    {t ? <><span className="dso-tbar"><i style={{ transform: `scaleX(${t.frac})` }} /></span>
      <ol className="dso-steps">{THINK_STEPS.map((w, i) => <li key={w} className={i < t.step ? 'done' : i === t.step ? 'now' : ''}>{w}</li>)}</ol></> : null}
    <div className="dso-cands">{(live.cands || []).map((c, i) => <span key={`${c.symbol}-${i}`} className={`dso-cand ${c.symbol === live.pick ? 'is-pick' : ''} st-${String(c.status || '').toLowerCase()}`} style={{ '--i': i }}
      title={`${c.status || ''} · Trigger ${c.trigger || '—'}${c.rank != null ? ` · rank ${c.rank}` : ''}`}>
      <b>${c.symbol}{c.symbol === live.pick ? ' 🤖' : ''}</b>
      <em><i className="v5" style={{ transform: `scaleX(${bar(Math.abs(c.move5m), 0, 25)})` }} data-neg={c.move5m < 0 ? 1 : 0} /><small>5m {c.move5m != null ? sgn(c.move5m) : '—'}</small></em>
      <em><i className="vb" style={{ transform: `scaleX(${bar(c.buyers, 30, 80)})` }} /><small>buy {c.buyers != null ? `${c.buyers}%` : '—'}</small></em>
      <em><i className="vg" style={{ transform: `scaleX(${bar(25 - Math.abs(c.germ ?? 25), 0, 25)})` }} /><small>germ {c.germ != null ? `${c.germ}%` : '—'}</small></em>
    </span>)}</div>
    {live.pick ? <small className="dso-pickw">🤖 the agents' own pick: ${live.pick}</small> : null}
  </div>;
}

// 🔁 one turn, step by step (owner, 2026-10-16: "one decides, it gets bought, they discuss until it's sold, then the other chooses; no seat open → they wait")
export const TURN_STEPS = [['HUNTING', '🔎 picks a coin'], ['BOUGHT', '🛒 bought'], ['HOLDING', '💬 trading + talking'], ['SOLD', '🏁 sold → other\'s turn']];
export function turnStep(duo) {
  const ph = String(duo?.phase || '').toUpperCase();
  if (ph === 'SEATS FULL') return { i: -1, word: '🪑 every seat full — waiting for one to open' };
  if (ph === 'HOLDING') return { i: 2, word: `${duo.holder || duo.next} is running $${duo.holding?.symbol || '?'} — the partner advises every 2 min` };
  if (/seated/.test(duo?.fate?.why || '')) return { i: 1, word: `$${duo.fate.symbol} took the seat — the keeper buys it` };
  return { i: 0, word: `${duo?.next || '—'}'s turn to pick a coin` };
}
function TurnBar({ duo }) {
  const t = turnStep(duo);
  return <div className={`dso-turn ${t.i < 0 ? 'is-wait' : ''}`} data-testid="duo-turn" data-step={t.i}>
    <ol>{TURN_STEPS.map(([k, w], i) => <li key={k} className={i === t.i ? 'is-now' : i < t.i ? 'is-done' : ''}><i aria-hidden="true" /><span>{w}</span></li>)}</ol>
    <p key={t.word}>{t.word}</p></div>;
}

export function DuoSeat({ duo }) {
  if (!duo || duo.mode === 'off') return <div className="dso is-off" data-testid="duo-seat"><b>🔁 OSSY ⚔ G4</b><small>seat off — turn it on in 🎛 Limits › 🧠 G4 SEAT</small></div>;
  const log = duo.log || [];
  const g4 = sideOf('G4', log), os = sideOf('OSSY', log);
  const last = log[0];
  const from = last?.model === 'OSSY' ? 'r' : last?.model === 'AGENTS' ? 'c' : 'l';
  const agentsN = log.filter(r => r.model === 'AGENTS').length;
  return <div className={`dso is-${duo.mode}`} data-testid="duo-seat">
    <header className="dso-head"><b>🔁 OSSY ⚔ G4 · {String(duo.mode).toUpperCase()}</b>
      <small>{duo.busy ? `${duo.next} is thinking…` : last ? `last call ${ago(last.at)} ago · ${duo.next} next` : 'first call within a minute'}</small></header>
    <TurnBar duo={duo} />
    <div className="dso-arena">
      <Side s={g4} pod={podOf('G4', duo.rec)} turn={duo.next === 'G4'} busy={duo.busy} side="l" />
      <div className="dso-core" data-testid="duo-open">
        {last ? <i key={`${last.at}-${from}`} className={`dso-beam from-${from} a-${actKey(last.action)}`} aria-hidden="true" /> : null}
        <div className="dso-hex"><i className="dso-ring" aria-hidden="true" />
          <small>SEAT</small><b>{duo.open ? `$${duo.open.symbol}` : 'EMPTY'}</b>
          <small>{duo.open ? `${duo.open.by === 'local' ? 'OSSY' : duo.open.by === 'agents' ? 'agents' : 'G4'} · peak ${sgn(duo.open.peak || 0)}` : `${duo.next} calls next`}</small>
        </div>
        {duo.fate ? <small className={`dso-fate ${/^seated/.test(duo.fate.why) ? 'ok' : /sent/.test(duo.fate.why) ? 'go' : 'no'}`} data-testid="duo-fate" title="What happened to the newest model BUY">
          🧾 {duo.fate.symbol ? `$${duo.fate.symbol}` : 'buy'}: {duo.fate.why} · {ago(duo.fate.at)}</small> : null}
        <small className="dso-agents" title="Minutes neither model answered, so the agents decided the seat">🤝 agents backed up {agentsN}{duo.agents?.n ? ` · ${duo.agents.n} closed, ${duo.agents.won}% won` : ''}</small>
      </div>
      <Side s={os} pod={podOf('OSSY', duo.rec)} turn={duo.next === 'OSSY'} busy={duo.busy} side="r" />
    </div>
    <Think duo={duo} sides={[g4, os]} />
    <ol className="dso-log">{log.slice(0, 8).map((r, i) => <li key={`${r.at}-${i}`} className={`a-${actKey(r.action)} ${r.model === 'OSSY' ? 'by-ossy' : r.model === 'AGENTS' ? 'by-agents' : 'by-g4'}`} style={{ '--i': i }}>
      <em>{r.model || '—'}</em><b>{r.action}{r.symbol ? ` $${r.symbol}` : ''}{r.pct != null ? ` ${sgn(r.pct)}` : ''}</b><span title={r.miss ? `models missed: ${r.miss}` : undefined}>{r.why}</span><small>{ago(r.at)}{r.ms ? ` · ${secs(r.ms)}` : ''}</small></li>)}</ol>
  </div>;
}
