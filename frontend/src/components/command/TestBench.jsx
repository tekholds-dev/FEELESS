import React, { useCallback, useEffect, useState } from 'react';
import { pageOf } from './Code3D';
import '../../styles/testBench.css';

// 🧪 Proofs › Test bench (owner 2026-11-12: "if u testing on sicarios then any tests etc should show in folder etc so i can see"). Every test run
// on this desk, from the append-only ledger: what was tested, the models, what came back, the real cost and time, pass or fail and why, and its
// raw outputs. A 3D module can be run right here, in the same locked page the playground uses.
const ago = at => { const s = Math.max(0, Date.now() / 1000 - at); return s < 90 ? 'just now' : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 129600 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; };
const usd = v => (v > 0 ? `$${v < 0.01 ? v.toFixed(4) : v.toFixed(2)}` : '$0');
const secs = v => (v == null ? '—' : v >= 90 ? `${Math.round(v / 60)} min` : `${Math.round(v)} s`);

function Run({ r, i, catId, work }) {
  const [open, setOpen] = useState(false); const [file, setFile] = useState(null); const [run3d, setRun3d] = useState(false);
  const show = async name => { setRun3d(false); setFile({ name, text: null }); try { const j = await work(catId, { op: 'test_run_file', job: r.id, text: name }); setFile({ name, text: j.text }); } catch (e) { setFile({ name, text: null, err: e.message || 'Could not read it.' }); } };
  const is3d = r.kind === '3d' && file?.text && /\.(m?js)$/.test(file.name) && /THREE/.test(file.text);
  return <li className={`tbn-run ${r.ok ? 'is-ok' : 'is-bad'}${open ? ' is-open' : ''}`} style={{ '--i': i }} data-testid={`tbn-run-${r.id}`}>
    <button type="button" className="tbn-head" onClick={() => setOpen(o => !o)} aria-expanded={open} data-tip="Shows its steps and the outputs it kept">
      <span className="tbn-badge">{r.ok ? 'PASS' : 'FAIL'}</span><span className="tbn-kind">{String(r.kind).toUpperCase()}</span><b>{r.title}</b>
      <span className="tbn-meta m-num">{usd(r.costUsd)} · {secs(r.secs)} · {ago(r.at)}</span></button>
    <p className="tbn-why">{r.why}</p>
    {r.models?.length ? <span className="tbn-models">{r.models.map(m => <em key={m}>{m}</em>)}</span> : null}
    {open ? <div className="tbn-more">
      {r.steps?.length ? <ol className="tbn-steps">{r.steps.map((s, n) => <li key={n}>{s}</li>)}</ol> : null}
      {r.files?.length ? <div className="m-seg tbn-files" role="tablist" aria-label="Kept outputs">{r.files.map(f => <button key={f.name} type="button" role="tab" aria-selected={file?.name === f.name} className={file?.name === f.name ? 'active' : ''} onClick={() => show(f.name)} data-tip={`${f.bytes.toLocaleString()} bytes`}>{f.name}</button>)}</div> : <small className="tbn-none">No outputs kept.</small>}
      {file ? <div className="tbn-file">{file.err ? <p className="tbn-none">{file.err}</p> : file.text == null ? <p className="tbn-none">Reading…</p> : <>
        {is3d ? <button type="button" className={`m-btn tbn-go${run3d ? ' is-on' : ''}`} onClick={() => setRun3d(x => !x)} data-tip="Runs this module in the playground's locked page">{run3d ? 'Show the code' : '▶ Run it'}</button> : null}
        {run3d ? <iframe title={`${r.title} running`} sandbox="allow-scripts" srcDoc={pageOf(file.text)} /> : <pre>{file.text}</pre>}</>}</div> : null}
    </div> : null}
    <small className="tbn-by">filed by {r.by}</small>
  </li>;
}

export function TestBench({ catId, work }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [lens, setLens] = useState('all');
  const load = useCallback(() => work(catId, { op: 'test_runs' }).then(j => { setD(j); setErr(''); }).catch(e => setErr(e.message || 'Could not read the bench.')), [catId, work]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => clearInterval(t); }, [load]);
  if (err && !d) return <p className="tbn-none" data-testid="tbn-err">{err}</p>;
  if (!d) return <p className="tbn-none">Reading the test bench…</p>;
  const st = d.stats || {}; const rows = (d.runs || []).filter(r => lens === 'all' || (lens === 'pass' ? r.ok : !r.ok));
  const pct = st.runs ? st.passed / st.runs : 0; const C = 2 * Math.PI * 22;
  return <section className="tbn m-card m-live" data-testid="tbn">
    <header className="tbn-top"><svg className="tbn-ring" viewBox="0 0 56 56" aria-hidden="true"><circle cx="28" cy="28" r="22" /><circle cx="28" cy="28" r="22" className="is-fg" strokeDasharray={`${C * pct} ${C}`} transform="rotate(-90 28 28)" /><text x="28" y="32" textAnchor="middle">{Math.round(pct * 100)}%</text></svg>
      <div className="tbn-sum"><span className="m-label">TEST BENCH · EVERY TEST RUN ON THIS DESK</span>
        <div className="tbn-stats">{[['Runs', st.runs || 0], ['Passed', st.passed || 0, 'up'], ['Failed', st.failed || 0, 'dn'], ['Spent', usd(st.costUsd || 0)], ['Time', secs(st.secs || 0)]].map(([k, v, t]) => <span key={k} className={t ? `is-${t}` : ''}><small>{k}</small><b className="m-num">{v}</b></span>)}</div></div>
      <div className="m-seg tbn-lens" role="tablist" aria-label="Show">{[['all', 'All'], ['pass', 'Passed'], ['fail', 'Failed']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)}>{l}</button>)}</div></header>
    {rows.length ? <ol className="tbn-list">{rows.map((r, i) => <Run key={r.id} r={r} i={i} catId={catId} work={work} />)}</ol>
      : <p className="tbn-none">{d.runs?.length ? 'Nothing in this view.' : 'No tests run on this desk yet. Every test run here is filed with its result, cost and outputs.'}</p>}
  </section>;
}
