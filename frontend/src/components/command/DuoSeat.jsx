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
    <p className="dso-seat" data-testid="duo-open">{duo.open ? <>🪑 ${duo.open.symbol} · opened by {duo.open.by === 'local' ? 'OSSY' : 'G4'} · peak {sgn(duo.open.peak || 0)}</> : <>🪑 seat empty — {duo.next} calls next</>}</p>
    <ol className="dso-log">{(duo.log || []).map((r, i) => <li key={`${r.at}-${i}`} className={`a-${String(r.action || '').toLowerCase().replace(/\s/g, '')} ${r.model === 'OSSY' ? 'by-ossy' : 'by-g4'}`} style={{ '--i': i }}>
      <em>{r.model || '—'}</em><b>{r.action}{r.symbol ? ` $${r.symbol}` : ''}{r.pct != null ? ` ${sgn(r.pct)}` : ''}</b><span>{r.why}</span><small>{ago(r.at)}{r.ms ? ` · ${(r.ms / 1000).toFixed(1)}s` : ''}</small></li>)}</ol>
  </div>;
}
