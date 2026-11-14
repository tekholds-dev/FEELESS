import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/approveInbox.css';

// ✅ AGX-10 · THE APPROVE INBOX (owner 2026-11-14): the one place where anything an agent wants to do that SPENDS MODEL USAGE waits for you —
// what runs, on which models, about what it costs — and runs only when you tap Approve. First user: the pot alert's redo (a proof that went in
// under 1x: "Fix first: …", then rebuild it with both minds). Decline = nothing runs. A trade or a bid is never offered here (money).
const POLL_MS = 15000;
const STATE = { waiting: ['WAITING', 'warn'], approved: ['APPROVED', 'go'], ran: ['RAN', 'go'], declined: ['DECLINED', 'mute'], failed: ['DID NOT START', 'bad'] };
const ago = t => { const s = Math.max(0, Date.now() / 1000 - (Number(t) || 0)); return s < 90 ? 'just now' : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 129600 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; };
export const costLine = usd => (usd == null ? 'Cost not known yet: about what a fresh one costs' : `≈ $${Number(usd).toFixed(4)} in model usage (what this proof cost to make)`);

/** Its inbox, read through the work route (owner only) every 15 s while the page is visible. → [rows, decide(id, yes), err] */
export function useApprovals(catId, work) {
  const [rows, setRows] = useState([]); const [err, setErr] = useState('');
  const load = useCallback(() => { if (!catId || document.hidden) return; work(catId, { op: 'approvals' }).then(x => setRows(x?.approvals || [])).catch(() => {}); }, [catId, work]);
  useEffect(() => { load(); const t = setInterval(load, POLL_MS); return () => clearInterval(t); }, [load]);
  const decide = useCallback(async (id, yes) => { setErr(''); try { const x = await work(catId, { op: 'approve', text: id, job: yes ? 'yes' : 'no' }); setRows(x?.approvals || []); return x?.row; } catch (e) { setErr(e.message); load(); return null; } }, [catId, work, load]);
  return [rows, decide, err];
}

export function ApproveButton({ rows, onOpen }) {
  const n = (rows || []).filter(r => r.state === 'waiting').length;
  return <button type="button" className={`m-btn dsk-pick apx-btn${n ? ' has-wait' : ''}`} onClick={onOpen} data-tip="Anything that spends model usage waits here for your tap" data-testid="dsk-approve">✅ Approve{n ? <b className="m-num">{n}</b> : null}</button>;
}

function Row({ r, onDecide, busy, focus }) {
  const [label, tone] = STATE[r.state] || [String(r.state || '').toUpperCase(), 'mute'];
  return <li className={`apx-row is-${r.state}${focus ? ' is-focus' : ''}`} data-testid={`apx-${r.id}`}>
    <header><em className={`apx-chip is-${tone}`}>{label}</em><b>{r.what}</b><time>{ago(r.decidedAt || r.at)}</time></header>
    <dl>
      <div><dt>RUNS</dt><dd>{r.op?.op === 'ws_build' ? `Both minds rebuild the page: “${String(r.op.text || '').slice(0, 140)}”` : r.op?.op === 'poc' ? `Both minds file a new PoC${r.op.text ? ` on “${r.op.text}”` : ''}` : r.op?.op || '—'}</dd></div>
      <div><dt>MODELS</dt><dd>{(r.models || []).length ? r.models.map(m => <span key={m} className="apx-model">{m}</span>) : 'its minds'}</dd></div>
      <div><dt>COST</dt><dd className="m-num">{costLine(r.estUsd)}</dd></div>
    </dl>
    {r.state === 'waiting' ? <span className="apx-act"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onDecide(r.id, true)} data-testid={`apx-yes-${r.id}`}>{busy === r.id ? 'Starting…' : 'Approve and run'}</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => onDecide(r.id, false)} data-testid={`apx-no-${r.id}`}>Decline</button><small>Nothing runs until you tap Approve.</small></span>
      : r.say ? <p className="apx-say">{r.say}</p> : null}
  </li>;
}

/** The inbox panel over the desk. Waiting rows first; what you decided below. Esc closes. */
export default function ApproveInbox({ rows, onDecide, onClose, focus = null, err = '' }) {
  const [busy, setBusy] = useState(''); const [said, setSaid] = useState('');
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose?.(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  const decide = async (id, yes) => { setBusy(id); setSaid(''); const r = await onDecide(id, yes); setBusy(''); if (r) setSaid(r.state === 'declined' ? 'Declined: nothing ran.' : r.state === 'ran' ? 'Approved: it is running. It lands in its folder.' : r.say || 'Approved.'); };
  const wait = (rows || []).filter(r => r.state === 'waiting'); const done = (rows || []).filter(r => r.state !== 'waiting');
  return <div className="apx-veil" role="dialog" aria-modal="true" aria-label="Approve inbox" onClick={e => { if (e.target === e.currentTarget) onClose?.(); }} data-testid="apx">
    <section className="apx">
      <header className="apx-h"><div><small>APPROVE · {wait.length} WAITING</small><h3>Nothing that spends model usage runs until you tap Approve.</h3></div><button type="button" className="apx-x" onClick={onClose} aria-label="Close the inbox">✕</button></header>
      {said ? <p className="apx-said" role="status">{said}</p> : null}{err ? <p className="apx-err" role="alert">⚠ {err}</p> : null}
      {wait.length ? <ul className="apx-list">{wait.map(r => <Row key={r.id} r={r} onDecide={decide} busy={busy} focus={focus === r.id} />)}</ul>
        : <p className="apx-none">Nothing is waiting. When a proof goes into the pot under 1x, its agent says what to fix first, and a redo lands here.</p>}
      {done.length ? <><p className="apx-sub">DECIDED</p><ul className="apx-list is-done">{done.slice(0, 12).map(r => <Row key={r.id} r={r} onDecide={decide} busy={busy} />)}</ul></> : null}
    </section>
  </div>;
}
