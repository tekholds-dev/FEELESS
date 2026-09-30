import React from 'react';

// Every live trade, step by step: quoted + simulated → signed in YOUR wallet → broadcast → confirmed on-chain,
// with the time of each step, who signed, the tx link and what it cost (FEELESS fee + network). Nothing hidden.
const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '');
const secs = (a, b) => (a && b ? `+${((b - a) / 1000).toFixed(1)}s` : '');

export function timelineSteps(t) {
  if (!t) return [];
  const failed = t.state === 'failed';
  return [
    { key: 'quoted', label: 'Quoted + simulated', done: Boolean(t.quotedAt), at: t.quotedAt, note: t.route || 'Jupiter route' },
    { key: 'signed', label: 'Signed in your wallet', done: Boolean(t.signedAt), at: t.signedAt, note: t.signer ? `✓ ${t.wallet || 'wallet'} ${short(t.signer)}` : 'waiting for your approval' },
    { key: 'sent', label: 'Broadcast to Solana', done: Boolean(t.sentAt), at: t.sentAt, note: t.signature ? `tx ${short(t.signature)}` : '' },
    { key: 'confirmed', label: failed ? 'Failed on-chain — nothing moved' : 'Confirmed on-chain', done: t.state === 'confirmed', bad: failed, at: t.doneAt,
      note: t.state === 'confirmed' || failed ? '' : t.sentAt ? 'confirming…' : '' },
  ];
}

export function TradeTimeline({ t }) {
  if (!t) return null;
  const steps = timelineSteps(t);
  const current = steps.findIndex(s => !s.done && !s.bad);
  return <div className="m-card trade-timeline" data-testid="trade-timeline" role="status" aria-live="polite">
    <span className="m-label">LIVE TRADE <em>{t.side === 'sell' ? 'SELL' : 'BUY'} {t.symbol ? `$${t.symbol}` : ''}</em></span>
    <ol>{steps.map((s, i) => <li key={s.key} className={`${s.done ? 'is-done' : ''} ${s.bad ? 'is-bad' : ''} ${i === current ? 'is-now' : ''}`}>
      <i aria-hidden="true">{s.bad ? '✕' : s.done ? '✓' : i === current ? '' : '·'}</i>
      <b>{s.label}</b><small>{s.note}{s.done && i > 0 ? ` ${secs(steps[i - 1].at, s.at)}` : ''}</small></li>)}</ol>
    {(t.feeUsd != null || t.networkSol != null) && <div className="m-kv trade-costs">
      <span>FEELESS fee</span><b className="m-num sm">{t.feeUsd ? `$${t.feeUsd.toFixed(t.feeUsd < 1 ? 3 : 2)} (${t.feePct}%)` : 'free'}</b>
      <span>Network</span><b className="m-num sm">{t.networkSol != null ? `${t.networkSol.toFixed(6)} SOL${t.solUsd ? ` · $${(t.networkSol * t.solUsd).toFixed(3)}` : ''}` : '—'}</b></div>}
    {t.signature && <a className="m-btn trade-tx" href={`https://solscan.io/tx/${t.signature}`} target="_blank" rel="noopener noreferrer">View on Solscan ↗</a>}
  </div>;
}
