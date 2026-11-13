import React from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/collective.css';

// ✅ The 24-hour stamp (proof_stamp.py decides it): PROVED, NOT PROVED, a countdown, or LIVE.
// owner 2026-11-13: "make it understandable when I'm on the site" — the stamp says what it is in plain words: the result, or when the result comes.
const STAMP = { proved: ['✓ PROVED', 'is-yes'], not: ['✕ NOT PROVED', 'is-no'], live: ['STILL RUNNING', 'is-live'], void: ['NO RESULT', 'is-wait'] };
const leftOf = t => { const m = Math.max(0, Math.round((t * 1000 - Date.now()) / 60000)); return m >= 60 ? `${Math.round(m / 60)}h` : `${m}m`; };
export function ProofStamp({ s }) {
  if (!s) return null;
  const [t, c] = STAMP[s.state] || [`RESULT IN ${leftOf(s.dueAt)}`, 'is-wait'];
  const tip = s.state === 'proved' ? 'Checked a day after it closed: what it said held up against what really happened.'
    : s.state === 'not' ? 'Checked a day after it closed: what it said did not hold up against what really happened.'
      : s.state === 'live' ? 'Still open. Its result is checked a day after it closes.'
        : s.state === 'void' ? 'Every game it picked was never played (postponed or dropped), so there is nothing to check it against. Not a win, not a loss.'
        : 'A day after a proof closes, FEELESS checks it against what really happened and stamps it PROVED or NOT PROVED. A game pick waits for the final score.';
  return <em className={`clx-stamp ${c}`} data-testid="proof-stamp" data-tip={tip} aria-label={`${t}. ${tip}`}>{t}</em>;
}

function ProofRow({ r, i, showAgent = true }) {
  const pct = r.pct == null ? null : Number(r.pct);
  return <li className="clx-proof" style={{ '--i': i }} data-testid={`clx-proof-${r.id}`}><span className="m-chip">{r.kind}</span><b>{r.label || 'Proof'}</b>{showAgent ? <small>{r.agent}</small> : null}
    {pct != null ? <em className={`m-num ${pct >= 0 ? 'is-up' : 'is-dn'}`}>{pct >= 0 ? '+' : ''}{pct.toFixed(1)}%</em> : null}<ProofStamp s={r.stamp} />
    {(r.games || []).length ? <span className="clx-games">{r.games.map(g => <i key={g.id}>{g.label}{g.score ? ` ${g.score}` : ''}{g.status ? ` · ${g.status}` : ''}</i>)}</span> : null}
    {r.sent ? <span className="clx-sent" data-testid={`clx-sent-${r.id}`}><a href={apiUrl(r.sent.receipt)} target="_blank" rel="noopener noreferrer" data-tip="The receipt, read back from the chain"><img src={apiUrl(r.sent.receipt)} alt="Receipt" loading="lazy" /></a><span><strong className="m-num">{Number(r.sent.sol).toFixed(6)} SOL to the Pool</strong><code>{String(r.sent.sig).slice(0, 10)}…{String(r.sent.sig).slice(-6)}</code><a href={r.sent.link} target="_blank" rel="noopener noreferrer">Solscan ↗</a></span></span> : null}</li>;
}
export function ProofsList({ rows, showAgent = true, title = 'PROOFS' }) {
  const list = rows || [];
  return <section className="clx-proofs" data-testid="clx-proofs"><header><b>{title}</b><small>{list.length ? `newest ${Math.min(5, list.length)}` : 'none yet'}</small></header>
    <ol>{list.slice(0, 5).map((r, i) => <ProofRow key={r.id} r={r} i={i} showAgent={showAgent} />)}</ol>
    {list.length > 5 ? <details className="clx-more"><summary>Recent 20 <small>{list.length}</small></summary><ol>{list.slice(5, 20).map((r, i) => <ProofRow key={r.id} r={r} i={i} showAgent={showAgent} />)}</ol></details> : null}</section>;
}
