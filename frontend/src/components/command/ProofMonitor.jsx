import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/proofMonitor.css';

// 🖥 owner 2026-11-12: "all proofs can be seen in desk monitors, in dynamic ways regardless of proof type — like static we can see a code window and a
// static window". Each kind draws its OWN folder's real data on the monitor: nothing here is sample data, and a missing piece says so.
const DOCS = new Map();   // ws → { code, preview } — one read per page per 2 minutes, shared by every monitor
async function readDoc(work, catId, ws) {
  const hit = DOCS.get(ws); if (hit && Date.now() - hit.at < 120000) return hit;
  const j = await work(catId, { op: 'ws_open', text: ws }); const d = { code: String(j?.doc?.code || ''), preview: j?.doc?.preview || '', at: Date.now() }; DOCS.set(ws, d); return d;
}
export function codeLines(code, n = 90) {
  const body = String(code || '').replace(/\r/g, ''); const at = body.search(/<script[^>]*>/i);   // the page's own script reads better than its <head>
  return (at > 0 ? body.slice(at) : body).split('\n').map(l => l.replace(/\t/g, '  ')).filter(l => l.trim()).slice(0, n);
}

function PsMon({ f, catId, work }) {
  const [doc, setDoc] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { let on = true; if (!f?.ws || !work) return undefined; readDoc(work, catId, f.ws).then(d => on && setDoc(d)).catch(() => on && setErr('Its page could not be read right now.')); return () => { on = false; }; }, [f?.ws, catId, work]);
  const lines = codeLines(doc?.code);
  return <div className="pmn-ps">
    <div className="pmn-code" aria-label="Its code"><span className="pmn-bar"><i /><i /><i /><b>index.html</b></span>
      {lines.length ? <ol style={{ '--n': lines.length }}>{[...lines, ...lines].map((l, i) => <li key={i}>{l}</li>)}</ol> : <p className="pmn-none">{err || (doc ? 'No code filed yet.' : 'Reading its code…')}</p>}</div>
    <div className="pmn-page" aria-label="Its page"><span className="pmn-bar"><i /><i /><i /><b>{String(f?.topic || 'page').slice(0, 28)}</b></span>
      {doc?.preview ? <iframe title="Its page" sandbox="allow-scripts" srcDoc={doc.preview} tabIndex={-1} /> : <p className="pmn-none">{err || (doc ? 'No page built yet.' : 'Opening its page…')}</p>}</div>
  </div>;
}
function PowMon({ f }) {
  const pct = Number(f?.pnlPct); const has = Number.isFinite(pct); const shown = useCountUp(has ? Math.round(pct * 100) : 0) / 100;
  const coins = (f?.coins || []).slice(0, 4);
  return <div className="pmn-pow"><b className="pmn-sym">${String(f?.sym || coins[0]?.sym || '…').slice(0, 12)}</b>
    <span className={`pmn-pnl m-num ${!has ? '' : pct >= 0 ? 'is-up' : 'is-dn'}`}>{has ? `${shown >= 0 ? '+' : ''}${shown.toFixed(2)}%` : 'no trade yet'}</span>
    {has ? <span className="pmn-meter" aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, Math.abs(pct) / 50)})` }} className={pct >= 0 ? 'is-up' : 'is-dn'} /></span> : null}
    <small>{f?.minds || 1} mind{(f?.minds || 1) > 1 ? 's' : ''} · {String(f?.phase || 'filed')}{Number.isFinite(Number(f?.pnlSol)) ? ` · ${Number(f.pnlSol) >= 0 ? '+' : ''}${Number(f.pnlSol).toFixed(4)} SOL` : ''}</small>
    {coins.length > 1 ? <ul className="pmn-coins">{coins.map(c => <li key={c.mint || c.sym} className={Number(c.ch) >= 0 ? 'is-up' : 'is-dn'}>${String(c.sym || '').slice(0, 10)}<em>{Number.isFinite(Number(c.ch)) ? `${Number(c.ch) >= 0 ? '+' : ''}${Number(c.ch).toFixed(0)}%` : ''}</em></li>)}</ul> : null}</div>;
}
function PobMon({ f }) {
  const sites = (f?.sites || []).slice(0, 6); const calls = f?.calls || [];
  return <div className="pmn-pob"><b className="pmn-topic">{String(f?.topic || 'Bids').slice(0, 60)}</b>
    <ul className="pmn-sites">{sites.map((s, i) => <li key={s} style={{ '--i': i }} className={f?.browsed?.[s] ? 'is-read' : ''}>{s}</li>)}</ul>
    <small className={calls.length ? 'is-up' : 'is-dn'}>{calls.length ? `${calls.length} call${calls.length > 1 ? 's' : ''} made` : f?.noTrade ? 'No call: nothing was read, so nothing staked' : 'Reading the games'}</small></div>;
}
function PocMon({ f, catId }) {
  const shot = (f?.shots || []).find(x => x.file); const found = (shot?.found || []).slice(0, 5);
  return <div className="pmn-poc">{shot ? <img src={apiUrl(`/api/cats/${catId}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${shot.file}?${agentAuthQuery()}`)} alt={`What it read on ${shot.site}`} loading="lazy" /> : <p className="pmn-none">No snapshot filed.</p>}
    <span className="pmn-poc-say"><b>{String(f?.topic || 'PoC').slice(0, 50)}</b>{found.length ? <span className="pmn-words">{found.map(w => <em key={w}>{w}</em>)}</span> : null}</span></div>;
}
function PoeMon({ f }) {
  const months = (f?.months || []).slice(-6); const top = Math.max(1, ...months.flatMap(m => [Number(m.income) || 0, Number(m.costs) || 0]));
  const usd = v => `$${Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}K` : Math.round(v)}`;
  return <div className="pmn-poe"><b className="pmn-topic">{String(f?.topic || 'Its books').slice(0, 40)}</b>
    <div className="pmn-bars">{months.map((m, i) => <span key={m.month} style={{ '--i': i }} data-tip={`${m.month}: in ${usd(m.income)}, out ${usd(m.costs)}`}><u className="is-in" style={{ transform: `scaleY(${(Number(m.income) || 0) / top})` }} /><u className="is-out" style={{ transform: `scaleY(${(Number(m.costs) || 0) / top})` }} /><small>{String(m.month).slice(5)}</small></span>)}</div>
    <small>Net <b className={Number(f?.net) >= 0 ? 'is-up' : 'is-dn'}>{usd(Number(f?.net) || 0)}</b> · margin {Number.isFinite(Number(f?.margin)) ? `${Number(f.margin).toFixed(1)}%` : '—'}</small></div>;
}
const BODY = { ps: PsMon, pow: PowMon, pob: PobMon, poc: PocMon, poe: PoeMon };
export function ProofMonitorBody({ p, catId, work }) {
  const B = BODY[p?.k]; return B && p?.f ? <B f={p.f} catId={catId} work={work} /> : null;
}
