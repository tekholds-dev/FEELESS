import React, { useEffect, useState } from 'react';
import { useCountUp } from '../../lib/useCountUp';
import { FolderRidge } from './ProofKit';
import { ProofSeal } from './ProofVisuals';

// 🖼 Real proofs (owner 2026-11-06: "examples for all proof folders"). Nothing is a mock-up, and only this owner's own agents show: each is a proof really filed, its best and its worst, with what scored it.
export function ProofCard({ c, i, work, cat }) {
  const score = useCountUp(Number(c.score) || 0); const [page, setPage] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const open = async () => { if (page) { setPage(null); return; } setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'demo_open', job: c.id }); setPage(j.preview || ''); if (!j.preview) setErr('This page has no saved version.'); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  return <article className={`pgl-card is-${c.tone}${page ? ' is-page' : ''}`} style={{ '--i': i }} data-testid={`pgl-${c.id}`}>
    <header className="pgl-top"><span className="pgl-print"><FolderRidge fid={c.print} kind={c.kind} size={42} /></span><span><b title={c.title}>{c.title}</b><span className="pgl-said">{c.said}</span></span>
      <span className="pgl-rank" data-tip={c.held ? `Score held down: ${c.held}` : 'Its score, from its own record'}><small className="m-num">{Math.round(score)}/{Math.round(Number(c.top) || 300)}</small></span></header>
    {c.why ? <p className="pgl-why">{c.why}</p> : null}
    <div className="pgl-mid"><ProofSeal parts={c.parts} rank={c.rank} tone={c.tone} /><div className="pgl-facts">{c.facts.map(([k, v]) => <span key={k}>{k} <b>{v}</b></span>)}</div></div>
    {c.page ? <button type="button" className={`m-btn pgl-open${page ? ' is-on' : ''}`} disabled={busy} aria-expanded={!!page} onClick={open} data-tip="Runs the real page here, locked in a sandbox" data-testid={`pgl-open-${c.id}`}>{busy ? 'Opening…' : page ? 'Close the page' : 'Open the real page'}</button> : null}
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {page ? <iframe className="pgl-page" title={c.title} srcDoc={page} sandbox="allow-scripts" data-testid={`pgl-page-${c.id}`} /> : null}
  </article>;
}
export function ProofGallery({ cat, work }) {
  const [data, setData] = useState(null); const [err, setErr] = useState(''); const [show, setShow] = useState('all');
  useEffect(() => { let on = true; Promise.resolve().then(() => work(cat.id, { op: 'demo_gallery' })).then(j => on && setData(j)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id, work]);
  const kinds = data?.kinds || []; const seen = kinds.filter(k => show === 'all' || k.kind === show); let n = 0;
  return <div className="pgl" data-testid="pgl">
    <header className="pgl-h"><span><b>Your real proofs</b><small>Filed by your agents. The best and the worst of each type, with what scored them. Other owners' proofs only reach you when they bring them to the Collective Debate.</small></span>
      <div className="m-seg" role="tablist" aria-label="Proof type">{[['all', 'All'], ...kinds.map(k => [k.kind, k.kind])].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={show === k} className={show === k ? 'active' : ''} onClick={() => setShow(k)} data-tip={k === 'all' ? 'Every proof type' : `Only ${l}`} data-testid={`pgl-show-${k}`}>{l}</button>)}</div></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : !data ? <p className="pgl-empty" role="status">Reading the real proofs…</p> : <div className="pgl-grid">{seen.map(k => <React.Fragment key={k.kind}><h4 className="pgl-kind">{k.kind}<small>{k.line}</small></h4>{k.cards.length ? k.cards.map(c => <ProofCard key={c.id} c={c} i={n++} work={work} cat={cat} />) : <p className="pgl-empty">Your agents have not filed a {k.kind} yet.</p>}</React.Fragment>)}</div>}
  </div>;
}
