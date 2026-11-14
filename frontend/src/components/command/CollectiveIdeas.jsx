import React from 'react';
import '../../styles/collectiveIdeas.css';

// 🧠 THE COLLECTIVE'S BIG IDEAS (owner 2026-11-14: "do all of the big ideas"). From the proofs it already shows — no model call, no money moves:
//  · FORM: each agent's record on its settled proofs, and every agent backs the best record but its own (free chips only)
//  · THE COLLECTIVE'S PICK: the open proof whose agent has the best record — a vote, shown only; the Pool never moves on it
//  · RIVALS: two agents on opposite sides of the same Kalshi market, and who won once Kalshi settled it
const SETTLED = { proved: 1, not: 0 };

export function formOf(proofs) {
  const by = {};
  (proofs || []).forEach(p => {
    const v = SETTLED[p?.stamp?.state]; if (v == null || !p.agent) return;
    const a = by[p.agent] || (by[p.agent] = { agent: p.agent, proved: 0, settled: 0 });
    a.proved += v; a.settled += 1;
  });
  const rows = Object.values(by).map(a => ({ ...a, rate: a.proved / a.settled })).sort((a, b) => b.rate - a.rate || b.settled - a.settled);
  return rows.map(a => ({ ...a, backers: rows.filter(o => o.agent !== a.agent && rows.find(t => t.agent !== o.agent)?.agent === a.agent).map(o => o.agent) }));
}

export function collectivePick(proofs, form) {
  const rank = Object.fromEntries((form || []).map((a, i) => [a.agent, i]));
  const open = (proofs || []).filter(p => p?.agent && SETTLED[p?.stamp?.state] == null && rank[p.agent] != null);
  return open.sort((a, b) => rank[a.agent] - rank[b.agent] || (b.at || 0) - (a.at || 0))[0] || null;
}

export function CollectiveIdeas({ d }) {
  const form = formOf(d?.proofs); const pick = collectivePick(d?.proofs, form); const rivals = d?.rivals || [];
  if (!form.length && !rivals.length) return null;
  return <section className="cix" data-testid="clx-ideas">
    {form.length ? <div className="cix-card m-glass" data-testid="cix-form"><header><b>🏆 FORM</b><small>Settled proofs, best record first. Each agent backs the best record but its own, with free chips.</small></header>
      <ol>{form.slice(0, 6).map((a, i) => <li key={a.agent} style={{ '--i': i }}><em className="m-num">#{i + 1}</em><b>{a.agent}</b>
        <span className="cix-bar" aria-hidden="true"><s style={{ transform: `scaleX(${a.rate})` }} /></span><small className="m-num">{a.proved}/{a.settled} proved</small>
        <small className="cix-back">{a.backers.length ? `backed by ${a.backers.join(', ')}` : 'no backers yet'}</small></li>)}</ol></div> : null}
    {pick ? <div className="cix-card m-glass is-pick" data-testid="cix-pick"><header><b>🗳 THE COLLECTIVE'S PICK</b><small>The open proof from the best record. A vote, shown only: the Pool never moves on it.</small></header>
      <p><em>{pick.kind}</em><b>{pick.label || 'its proof'}</b><small>by {pick.agent}</small></p></div> : null}
    {rivals.length ? <div className="cix-card m-glass" data-testid="cix-rivals"><header><b>🥊 RIVALS ON KALSHI</b><small>Two agents on opposite sides of the same market.</small></header>
      <ol>{rivals.slice(0, 5).map((r, i) => <li key={`${r.ticker}-${i}`} className="cix-rival" style={{ '--i': i }}><b>{r.title}</b>
        <small><span className={r.winner === r.yes ? 'is-won' : r.loser === r.yes ? 'is-lost' : ''}>{r.yes} YES</span> vs <span className={r.winner === r.no ? 'is-won' : r.loser === r.no ? 'is-lost' : ''}>{r.no} NO</span></small>
        <small className="cix-back">{r.result ? `Kalshi settled ${String(r.result).toUpperCase()}: ${r.loser} lost` : 'waiting on Kalshi'}</small></li>)}</ol></div> : null}
  </section>;
}
