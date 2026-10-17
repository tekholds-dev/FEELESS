// 🔁 G4 × OSSY — the tag-team seat (owner, 2026-10-16): the two models take turns deciding ONE seat, a call a minute. Drawn from the
// Agents payload's `duo` block (no fetch of its own): whose turn it is, each model's own record, the open paper seat and the last calls.
import React from 'react';
import '../../styles/duoSeat.css';

const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - (Number(at) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
const sgn = v => `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`;

// pure: one pod's numbers (n · won · typical) and how full its record bar is (won %, 0–1)
export function podOf(name, rec) {
  const r = (rec || {})[name] || {};
  return { name, n: r.n || 0, won: r.n ? r.won : null, med: r.n ? r.med : null, fill: r.n ? Math.max(0.04, Math.min(1, r.won / 100)) : 0 };
}

// pure: the 🌊 tank — water level = share of the summed result that WON (50 = break-even), tone, and one drop per closed trade
// (won = a bubble floating up, lost = a red bead sinking; size = how big the move was). Display only; the record is the proof.
export function tankOf(w) {
  const level = Math.max(4, Math.min(96, Number(w?.level ?? 50)));
  const drops = (w?.drops || []).map((d, i, a) => ({ ...d, good: d.pct > 0, x: a.length > 1 ? 6 + (88 * i) / (a.length - 1) : 50,
    r: Math.max(3, Math.min(9, 3 + Math.sqrt(Math.abs(d.pct)) * 1.4)) }));
  return { level, tone: !w?.n ? 'flat' : level >= 55 ? 'good' : level <= 45 ? 'bad' : 'flat', drops, n: w?.n || 0, net: w?.net };
}

// pure: 🐋 one whale per model = its vital. Depth = its won % (high = winning, belly-down = losing, mid = no trades yet), size = trades,
// mood = typical result after costs. The model whose turn it is glows and blows a spout.
export function whaleOf(pod, turn) {
  const top = pod.n ? Math.max(8, Math.min(78, 86 - pod.won * 0.8)) : 44;
  return { ...pod, top, scale: Math.min(1.5, 0.8 + Math.sqrt(pod.n || 0) * 0.12), mood: pod.n == null || !pod.n ? 'new' : pod.med > 0 ? 'happy' : 'sad', turn };
}

const WhaleSvg = () => <svg viewBox="0 0 64 30" aria-hidden="true"><path className="wb" d="M4 17c0-7 9-12 22-12 11 0 19 4 24 9l9-7c1-1 3 0 2 2l-4 8 4 8c1 2-1 3-2 2l-9-7c-5 5-13 9-24 9C13 29 4 24 4 17z" />
  <path className="wl" d="M8 20c6 4 18 5 30 1" /><circle className="we" cx="15" cy="14" r="1.8" /></svg>;

function Tank({ water, pods = [], next }) {
  const t = tankOf(water);
  const whales = pods.map(p => whaleOf(p, next === p.name));
  return <div className={`dso-tank t-${t.tone}`} data-testid="duo-tank" title="Water rises with winning trades, drains with losing ones (last 16 closed, after costs)">
    <div className="dso-water" style={{ transform: `translateY(${100 - t.level}%)` }}><i className="w1" /><i className="w2" /></div>
    {t.drops.map((d, i) => <span key={i} className={`dso-drop ${d.good ? 'up' : 'dn'}`} style={{ left: `${d.x}%`, width: d.r * 2, height: d.r * 2, '--i': i }} title={`${d.sym ? `$${d.sym} ` : ''}${sgn(d.pct)}`} />)}
    {whales.map((w, i) => <div key={w.name} className={`dso-whale ${['w-g4', 'w-os'][i]} m-${w.mood} ${w.turn ? 'is-turn' : ''}`} data-testid={`duo-whale-${w.name}`}
      style={{ top: `${w.top}%`, '--s': w.scale, '--i': i }} title={`${w.name}: ${w.n ? `${w.n} trades · ${w.won}% won · typical ${sgn(w.med)}` : 'no closed trades yet'}`}>
      <i className="dso-spout" /><WhaleSvg /><em>{w.name}</em></div>)}
    <b className="dso-tank-n">{t.n ? `${t.level}% won water · net ${sgn(t.net || 0)}` : 'tank fills as trades close'}</b>
  </div>;
}

export function DuoSeat({ duo }) {
  if (!duo || duo.mode === 'off') return <div className="dso is-off" data-testid="duo-seat"><b>🔁 G4 × OSSY</b><small>seat off — turn it on in 🎛 Limits › 🧠 G4 SEAT</small></div>;
  const pods = ['G4', 'OSSY'].map(n => podOf(n, duo.rec));
  const last = (duo.log || [])[0];
  return <div className={`dso is-${duo.mode} ${duo.next === 'OSSY' ? 'turn-ossy' : 'turn-g4'}`} data-testid="duo-seat">
    <header><b>🔁 G4 × OSSY · {String(duo.mode).toUpperCase()}</b><small>{duo.busy ? 'thinking…' : last ? `last call ${ago(last.at)} ago` : 'first call within a minute'}</small></header>
    <div className="dso-ring">
      {pods.map((p, i) => <div key={p.name} className={`dso-pod ${['p0', 'p1'][i]} ${duo.next === p.name ? 'is-turn' : ''}`} data-testid={`duo-pod-${p.name}`}>
        <i className="dso-core" aria-hidden="true" /><b>{p.name}</b>
        <span className="dso-rec"><i style={{ transform: `scaleX(${p.fill})` }} /></span>
        <small>{p.n ? `${p.n} · ${p.won}% won · ${sgn(p.med)}` : 'no closed trades yet'}</small></div>)}
      <div className="dso-baton" aria-label={`${duo.next}'s call next`}><i /></div>
    </div>
    <Tank water={duo.water} pods={pods} next={duo.next} />
    <p className="dso-seat" data-testid="duo-open">{duo.open ? <>🪑 ${duo.open.symbol} · opened by {duo.open.by === 'local' ? 'OSSY' : duo.open.by === 'agents' ? 'the agents' : 'G4'} · peak {sgn(duo.open.peak || 0)}</> : <>🪑 seat empty — {duo.next} calls next</>}{duo.agents?.n ? <small> · 🤝 agents backed up {duo.agents.n} trades ({duo.agents.won}% won)</small> : null}</p>
    <ol className="dso-log">{(duo.log || []).map((r, i) => <li key={`${r.at}-${i}`} className={`a-${String(r.action || '').toLowerCase().replace(/\s/g, '')} ${r.model === 'OSSY' ? 'by-ossy' : r.model === 'AGENTS' ? 'by-agents' : 'by-g4'}`} style={{ '--i': i }}>
      <em>{r.model || '—'}</em><b>{r.action}{r.symbol ? ` $${r.symbol}` : ''}{r.pct != null ? ` ${sgn(r.pct)}` : ''}</b><span title={r.miss ? `models missed: ${r.miss}` : undefined}>{r.why}</span><small>{ago(r.at)}{r.ms ? ` · ${(r.ms / 1000).toFixed(1)}s` : ''}</small></li>)}</ol>
  </div>;
}
