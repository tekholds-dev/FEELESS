import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';

// Every account's lifetime FEELESS fees: the book any future FeeBack / payback is paid from.
const usd = v => `$${Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: Number(v) >= 100 ? 0 : 2 })}`;
const day = t => (t ? new Date(t * 1000).toLocaleDateString() : '—');

export function FeeBook({ call }) {
  const [d, setD] = useState(null);
  const [q, setQ] = useState('');
  useEffect(() => { call('/admin/fee-book').then(setD).catch(e => toast.error(errorText(e))); }, [call]);
  const csv = () => {
    const cols = ['address', 'trades', 'volumeUsd', 'feeUsd', 'feeSol', 'feeUsdc', 'feeBackUsd', 'paidUsd', 'owedUsd', 'first', 'last'];
    const body = [cols.join(','), ...d.rows.map(r => cols.map(c => (c === 'first' || c === 'last' ? new Date(r[c] * 1000).toISOString() : r[c] ?? '')).join(','))].join('\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([body], { type: 'text/csv' })); a.download = 'feeless-fee-book.csv'; a.click();
  };
  if (!d) return <p className="cc-empty">Opening the fee book…</p>;
  const rows = d.rows.filter(r => !q || r.address.toLowerCase().includes(q.toLowerCase()));
  return <section className="m-card m-stack" data-testid="fee-book">
    <div className="m-row cs-bar"><span className="m-label">FEE BOOK <em>lifetime FEELESS fees per account · the payback base</em></span>
      <button type="button" className="m-btn" onClick={csv} disabled={!d.rows.length}>⬇ Export CSV</button></div>
    <div className="m-grid"><div className="m-stat"><small>Accounts</small><b className="m-num">{d.accounts}</b></div><div className="m-stat"><small>Fees collected</small><b className="m-num m-pos">{usd(d.totalFeesUsd)}</b></div>
      <div className="m-stat"><small>FeeBack owed ({d.feeBackPct}%)</small><b className="m-num">{usd(d.owedUsd)}</b></div></div>
    <input className="m-input" placeholder="Find a wallet…" value={q} onChange={e => setQ(e.target.value)} aria-label="Find a wallet" />
    {!rows.length ? <p className="m-dim">No fees recorded yet. Every confirmed FEELESS trade adds a line here.</p>
      : <div className="fb-table m-scroll"><div className="fb-row fb-head"><span>Wallet</span><span>Trades</span><span>Volume</span><span>Fees paid</span><span>FeeBack owed</span><span>Since</span></div>
        {rows.map(r => <a key={r.address} className="fb-row" href={`/terminal/profile/${r.address}`} target="_blank" rel="noopener noreferrer">
          <code>{r.address.slice(0, 4)}…{r.address.slice(-4)}</code><span>{r.trades}</span><span>{usd(r.volumeUsd)}</span>
          <b className="m-pos">{usd(r.feeUsd)}{r.feeSol ? <small> · {r.feeSol.toFixed(4)} SOL</small> : null}</b><span>{usd(r.owedUsd)}</span><em>{day(r.first)}</em></a>)}</div>}
  </section>;
}
