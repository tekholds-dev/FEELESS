import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// The verification report for a coin: verdict, hard gates, scored checks — every line cited.
export function VerifyReport({ mint, report: given, fresh = 0 }) {
  const [r, setR] = useState(given || null);
  useEffect(() => {
    if (given) { setR(given); return undefined; }
    let alive = true; setR(null);
    fetch(apiUrl(`/api/reputation/verify/${mint}${fresh ? '?fresh=1' : ''}`)).then(x => (x.ok ? x.json() : null)).then(d => alive && setR(d)).catch(() => {});
    return () => { alive = false; };
  }, [mint, given, fresh]);
  if (!r) return <p className="cc-empty">Running verification checks…</p>;
  if (!Array.isArray(r.gates) || !Array.isArray(r.checks)) return <p className="cc-empty">Verification unavailable for this coin right now.</p>;
  const verdict = { gold: ['vr-gold', '✦ FEELESS verified'], verified: ['vr-ok', '✓ Verified'], revoked: ['vr-bad', '✕ Verification revoked'] }[r.level] || ['vr-none', 'Not verified yet'];
  return <div className="verify-report" data-testid="verify-report">
    <div className={`vr-head ${verdict[0]}`}><b>{verdict[1]}</b><span className="vr-score"><i style={{ width: `${r.score}%` }} /><em>{r.score}/100 · needs {r.min}</em></span><small>{r.reason}</small></div>
    <div className="vr-cols">
      <div><small>SAFETY GATES · all must pass</small>{r.gates.map(g => <div key={g.key} className={`vr-line ${g.pass ? 'pass' : 'fail'}`}><i>{g.pass ? '✓' : '✕'}</i><span>{g.label}</span><em>{g.source}</em></div>)}</div>
      <div><small>SCORED CHECKS</small>{r.checks.map(c => <div key={c.key} className={`vr-line ${c.pass ? 'pass' : 'miss'}`}><i>{c.pass ? '✓' : '·'}</i><span>{c.label}</span><em>+{c.weight} · {c.source}</em></div>)}</div>
    </div>
  </div>;
}
