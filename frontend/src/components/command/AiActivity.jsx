// 📜 THE BRAIN'S ACTIVITY (owner, 2026-10-14: "show log for all activity"): one live timeline of everything the models did — every read
// (role · coin · stance · which model · how long), every fix they proposed and what you decided, every playground creation, the
// background lane. Filter chips by kind, a pulse bar for the last hour, each line slides in. Reads `/admin/ai/activity` every 10s while open.
import React, { useEffect, useMemo, useState } from 'react';
import { openCoin } from '../CoinDrawer';
import '../../styles/aiActivity.css';

const KINDS = [['all', 'All'], ['g4', '🧠 G4 seat'], ['read', '🔍 Reads'], ['proposal', '🛠 Fixes'], ['decision', '✅ Your calls'], ['play', '🧪 Made'], ['lane', '🖥 Lane']];
const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
// pure: how many things happened in each 5-minute slot of the last hour (the pulse bar)
export function pulse(items, now = Date.now() / 1000) {
  const b = Array(12).fill(0);
  (items || []).forEach(x => { const k = Math.floor((now - Number(x.at)) / 300); if (k >= 0 && k < 12) b[11 - k] += 1; });
  return b;
}

const recWord = r => (!r || !r.n ? 'no closed trades yet' : `${r.n} closed · ${r.won}% won · typical ${r.med >= 0 ? '+' : ''}${r.med}%`);
// 🧠 G4's own seat (owner, 2026-10-16): mode, its paper + real record, the coin it holds and its newest minute thought
export function G4Card({ g }) {
  if (!g || g.mode === 'off') return null;
  const last = (g.log || [])[0];
  return <div className={`cac-g4 is-${g.mode}`} data-testid="g4-seat">
    <div className="cac-g4h"><b><i className="cac-g4dot" aria-hidden="true" />🧠 G4 SEAT · {String(g.mode).toUpperCase()}</b>
      <span data-tip="paper = at live prices, after a 1.5% swap cost both ways">📄 {recWord(g.paper)}</span><span data-tip="real closed trades from the card's archive">💵 {recWord(g.real)}</span></div>
    {g.open ? <p className="cac-g4o">holding ${g.open.symbol} (paper) since {ago(g.open.at)} ago · peak {Number(g.open.peak || 0).toFixed(1)}%</p> : null}
    {last ? <p className="cac-g4l"><em className={`is-${String(last.action).toLowerCase()}`}>{last.action}</em>{last.symbol ? ` $${last.symbol}` : ''} — {last.why}
      {last.watch ? <small> · sells if: {last.watch}</small> : null}</p> : <p className="cac-g4l"><small>G4 thinks once a minute — the first thought lands here</small></p>}
  </div>;
}

export function AiActivity({ call }) {
  const [items, setItems] = useState([]); const [g4, setG4] = useState(null); const [kind, setKind] = useState('all'); const [err, setErr] = useState(null);
  useEffect(() => { let on = true;
    const load = () => { if (typeof document !== 'undefined' && document.hidden) return; Promise.resolve().then(() => call('/admin/ai/activity')).then(r => { if (on) { setItems(r.items || []); setG4(r.g4 || null); setErr(null); } }).catch(x => { if (on) setErr(x.message); }); };
    load(); const t = setInterval(load, 10000); return () => { on = false; clearInterval(t); }; }, [call]);
  const shown = useMemo(() => items.filter(x => kind === 'all' || x.kind === kind), [items, kind]);
  const bars = useMemo(() => pulse(items), [items]); const top = Math.max(1, ...bars);
  return <div className="cac" data-testid="ai-activity">
    <div className="cac-head"><span className="cac-pulse" data-tip="Model activity in the last hour, 5 minutes a bar" aria-label="last hour">{bars.map((v, i) => <i key={i} style={{ transform: `scaleY(${Math.max(0.06, v / top)})` }} />)}</span>
      <span className="cac-kinds" role="tablist">{KINDS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={kind === k} className={kind === k ? 'active' : ''} onClick={() => setKind(k)} data-testid={`cac-k-${k}`}>{l}</button>)}</span></div>
    <G4Card g={g4} />
    {err ? <p className="cac-err">{err}</p> : null}
    <ol className="cac-list">{shown.map((x, i) => <li key={`${x.kind}-${x.at}-${i}`} className={`is-${x.tone || 'mute'}`} style={{ '--i': Math.min(i, 12) }}>
      <span className="cac-ico" aria-hidden="true">{x.icon}</span>
      <span className="cac-txt"><b>{x.mint ? <button type="button" onClick={() => openCoin({ mint: x.mint })}>{x.title}</button> : x.title}</b>{x.sub ? <small>{x.sub}</small> : null}
        {x.kind === 'g4' && (x.vitals || x.qwen || (x.pressure || []).length) ? <span className="cac-g4v">{x.vitals ? <i>🫀 {x.vitals}</i> : null}
          {(x.pressure || []).map((p, j) => <i key={j} className="is-push">☠ agents: {p}</i>)}{x.qwen ? <i className="is-qwen">💻 Qwen: {x.qwen}</i> : null}</span> : null}</span>
      <span className="cac-meta"><em>{x.who || ''}</em><small>{ago(x.at)}{x.ms ? ` · ${(x.ms / 1000).toFixed(1)}s` : ''}</small></span></li>)}
      {!shown.length ? <li className="is-empty"><small>nothing yet — the models' reads, fixes and creations show up here as they happen</small></li> : null}</ol>
  </div>;
}
