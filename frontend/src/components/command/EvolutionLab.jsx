import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/evolutionLab.css';

// 🧪 EVOLUTION LAB (COL-11). Reaper's exit settings as generations: the frozen baseline vs a challenger fit on the OLDEST 60% of real exits,
// judged on the NEWEST 40% it never saw. Verdict + reason from the gate, the shadow trades (exits that would have changed) and the history.
// Every number is the server's (backend/evolution_lab.py on the real archive). The lab never changes live trading rules.
const pct = v => `${v > 0 ? '+' : ''}${Number(v || 0).toFixed(2)}%`;
const VERDICT_CLS = { PROMOTE: 'is-up', HOLD: 'is-wait', REJECT: 'is-dn' };
function Duel({ label, side }) {
  const top = Math.max(0.5, Math.abs(side.base.mean), Math.abs(side.chall.mean));
  return <div className="evo-duel"><small>{label} · {side.n} exits</small>
    {[['Baseline', side.base.mean, 'is-base'], ['Challenger', side.chall.mean, 'is-chall']].map(([k, v, c]) => <span key={k} className={c}><em>{k}</em><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.03, Math.abs(v) / top)})` }} className={v < 0 ? 'is-neg' : ''} /></i><b className="m-num">{pct(v)}</b></span>)}
    <strong className={`m-num ${side.edge >= 0 ? 'is-up' : 'is-dn'}`}>{side.edge >= 0 ? '+' : ''}{side.edge.toFixed(2)} pts</strong></div>;
}
export function EvolutionLab({ role = 'reaper' }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { let on = true; fetch(apiUrl(`/api/reputation/evolution/${role}`)).then(r => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`)))).then(j => on && setD(j)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [role]);
  if (err) return <p className="ofb-nil">The lab did not answer ({err}).</p>;
  if (!d) return <p className="ofb-nil">Replaying every real exit…</p>;
  const j = d.judge; const b = d.baseline || {};
  return <div className="evo" data-testid="evo-lab">
    <header className="evo-h"><span><small>GENERATION {b.gen || 1} IN CONTROL · <code>{b.hash}</code></small><b className={`evo-v ${VERDICT_CLS[j.verdict] || ''}`} data-testid="evo-verdict">{j.verdict}</b></span><p data-testid="evo-why">{j.why}</p></header>
    <div className="evo-duels"><Duel label="LEARN · OLDEST 60%" side={j.learn} /><Duel label="HELD-OUT · NEWEST 40%, NEVER SEEN" side={j.held} /></div>
    <p className="evo-gate">Gate: ≥ {d.gate.minHeld} held-out exits · ≥ {d.gate.minChanged} change · held-out edge ≥ +{d.gate.edgePts} pts · not worse on learn. {d.exits} real exits · take line +{d.take}%. {d.note}</p>
    {j.shadow?.length ? <table className="ofb-table evo-shadow" data-testid="evo-shadow"><thead><tr><th>shadow trade</th><th>baseline exit</th><th>challenger exit</th><th>diff</th></tr></thead><tbody>{j.shadow.slice(0, 8).map((r, i) => <tr key={i}><td>${r.sym}</td><td className="m-num">{pct(r.base)}</td><td className="m-num">{pct(r.chall)}</td><td className={`m-num ${r.diff >= 0 ? 'is-up' : 'is-dn'}`}>{pct(r.diff)}</td></tr>)}</tbody></table> : <p className="ofb-nil">No held-out exit would change.</p>}
    <ol className="evo-hist" data-testid="evo-history">{d.history.slice(0, 8).map((h, i) => <li key={i}><small className="m-num">gen {h.gen}</small><em className={h.verdict ? VERDICT_CLS[h.verdict] : ''}>{(h.verdict || h.action).toUpperCase()}</em><span>{h.why || `Frozen: ${Object.entries(h.params || {}).map(([k, v]) => `${k} ${v}`).join(' · ')}`}</span></li>)}</ol>
  </div>;
}
