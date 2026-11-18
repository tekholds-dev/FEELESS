import React, { useMemo, useState } from 'react';
import '../../styles/trueRecord.css';

// 🧾 THE TRUE RECORD (Slice 0, owner 2026-11-18: "I'm choosing a mind per proof and the backend doesn't even work??"). In every proof window's
// head: the last filed proof of that kind, its four VISION checks as meters, and three facts read from its folder: the minds that REALLY ran
// (from the call log, not the setting), every source it read, and how new its footprint is. A TEST proof Claude ran on Sicario's agent
// ($0, local minds) wears a TEST tag, and the switch shows the last TEST next to the last real one. Nothing here is computed in the browser.
const CODE = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const SHORT = m => String(m || '').split('/').pop();
const atOf = f => Number(f?.closedAt || f?.soldAt || f?.at) || 0;
// `proofChecks` is the record's list; a PoW folder's own `checks` is its live-trade counter (a number), never the record. The first TESTs filed
// on 2026-11-18 carry the list under `checks`, so a list there still reads.
export const checksOf = f => (Array.isArray(f?.proofChecks) ? f.proofChecks : Array.isArray(f?.checks) ? f.checks : null);

export function lastOf(folders, test = null) {
  const rows = (folders || []).filter(f => f && !f.live && (checksOf(f) || Array.isArray(f.ran)) && (test == null || !!f.test === test));
  return rows.reduce((a, f) => (!a || atOf(f) > atOf(a) ? f : a), null);
}

export function TestTag({ f }) {
  if (!f?.test) return null;
  const tip = `A TEST Claude ran on ${f.test.agent || "Sicario's"} with ${(f.test.pair || []).map(SHORT).join(' + ') || 'its free local minds'}: $0, nothing bought, bid or posted.${f.test.bench ? ' Its Test bench row has the full record.' : ''}`;
  return <em className="trec-tag" data-tip={tip} aria-label={tip} data-testid="trc-test">TEST</em>;
}

function Meter({ c, i }) {
  return <li className={`trec-m ${c.ok ? 'is-ok' : 'is-bad'}`} style={{ '--i': i }} data-tip={`${c.label}: ${c.why || ''}`} data-testid={`trc-check-${c.key}`}>
    <small>{c.key}</small><i aria-hidden="true"><b /></i><span className="m-num">{c.ok ? 'PASS' : 'FAIL'}</span></li>;
}

export function TrueRecord({ kind, folders }) {
  const real = useMemo(() => lastOf(folders, false), [folders]); const test = useMemo(() => lastOf(folders, true), [folders]);
  const [lens, setLens] = useState('real'); const f = lens === 'test' ? test || real : real || test;
  if (!f) return null;
  const checks = checksOf(f) || []; const ok = checks.filter(c => c.ok).length; const ran = (f.ran || []).filter(r => r.ok);
  const m = f.mindsCheck || {}; const rd = f.read || {}; const ft = f.foot || {};
  const mindsLine = ran.length ? ran.map(r => `${SHORT(r.asked)} → ${(r.answered || []).map(SHORT).join(', ') || '?'} · ${(r.routes || []).join('/') || '?'} · ${r.calls} call${r.calls === 1 ? '' : 's'}`).join('  ·  ') : (m.why || 'no mind answered');
  const sites = rd.sites || [];
  return <section className={`trec${ok === checks.length && checks.length ? ' is-ok' : ' is-bad'}`} data-testid={`trc-${kind}`} aria-label={`The true record of ${CODE[kind]} #${f.n}`}>
    <div className="trec-top">
      <span className="trec-v"><b className="m-num">{ok}/{checks.length || 4}</b><small>checks pass</small></span>
      <span className="trec-t"><em>LAST {f.test ? 'TEST' : 'FILED'} · {CODE[kind]} #{f.n ?? '?'}</em><TestTag f={f} /></span>
      {real && test ? <span className="m-seg trec-lens" role="tablist" aria-label="Which proof">{[['real', 'Last real'], ['test', 'Last TEST']].map(([k, t]) =>
        <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'is-on' : ''} onClick={() => setLens(k)} data-tip={k === 'test' ? 'The last TEST Claude ran on Sicario\'s agent' : 'The last real proof of this kind'} data-testid={`trc-lens-${k}`}>{t}</button>)}</span> : null}
    </div>
    <ol className="trec-meters">{checks.map((c, i) => <Meter key={c.key} c={c} i={i} />)}</ol>
    <dl className="trec-facts">
      <div data-tip={m.why || ''}><dt>MINDS THAT RAN</dt><dd className={m.ok ? 'is-ok' : 'is-bad'} data-testid="trc-minds">{mindsLine}</dd></div>
      <div data-tip={sites.join(', ')}><dt>SOURCES READ</dt><dd data-testid="trc-sources"><b className="m-num">{sites.length}</b> site{sites.length === 1 ? '' : 's'} · <b className="m-num">{(rd.pages || []).length}</b> page{(rd.pages || []).length === 1 ? '' : 's'}{sites.length ? ` · ${sites.slice(0, 3).join(', ')}${sites.length > 3 ? '…' : ''}` : ''}</dd></div>
      <div data-tip={ft.shared?.length ? `Shared with #${ft.nearest}: ${ft.shared.join(', ')}` : 'Nothing shared with a past proof of its kind'}><dt>FOOTPRINT</dt><dd className={ft.repeat ? 'is-bad' : 'is-ok'} data-testid="trc-foot"><b className="m-num">{ft.pct ?? '—'}%</b> new{ft.nearest ? ` next to #${ft.nearest}` : ''}{ft.sentBack ? ' · sent back once first' : ''}</dd></div>
      {f.studio?.length ? <div data-tip="The pieces sent here from the 3D studio, read back from the page's own code: same file, same turn and spin"><dt>3D STUDIO PIECES</dt><dd className={f.studio.every(r => r.used) ? 'is-ok' : 'is-bad'} data-testid="trc-studio">{f.studio.map(r => `${r.name} · ${r.height ? `${r.height} m` : 'as made'} · ${Math.round((r.turn?.[1] || 0) * 180 / Math.PI)}° · spin ${r.spin || 0} · ${r.used ? 'in the page' : 'MISSING'}`).join('  ·  ')}</dd></div> : null}
    </dl>
  </section>;
}
