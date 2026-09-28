import { Explain } from '../Explain';
import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';

const sym = {};
async function symbolOf(mint) {
  if (mint === 'So11111111111111111111111111111111111111112') return 'SOL';
  if (sym[mint]) return sym[mint];
  sym[mint] = fetch(`https://api.dexscreener.com/latest/dex/tokens/${mint}`).then(r => r.json()).then(d => d.pairs?.find(p => p.baseToken?.address === mint)?.baseToken?.symbol || shortAddress(mint)).catch(() => shortAddress(mint));
  return sym[mint];
}

// Totals from verified receipts: SOL out on buys, in on sells, network fees, and net per coin (SOL basis).
function totalsOf(rows) {
  const t = { spent: 0, received: 0, fees: 0, coins: {} };
  for (const r of rows) {
    t.fees += r.fee || 0;
    const tradeSol = r.sol + (r.fee || 0);  // SOL moved by the trade itself, network fee excluded
    if (tradeSol < 0) t.spent -= tradeSol; else t.received += tradeSol;
    for (const [m] of r.tokens) { const c = t.coins[m] || (t.coins[m] = { spent: 0, received: 0 }); if (tradeSol < 0) c.spent -= tradeSol; else c.received += tradeSol; }
  }
  return t;
}

function csvOf(rows, names) {
  const esc = v => `"${String(v).replaceAll('"', '""')}"`;
  const lines = [['date_utc', 'kind', 'tokens', 'sol_change', 'network_fee_sol', 'transaction'].join(',')];
  for (const r of rows) lines.push([r.t ? new Date(r.t * 1000).toISOString() : '', r.kind, esc(r.tokens.map(([m, d]) => `${d} ${names[m] || m}`).join(' | ')), r.sol, r.fee ?? '', `https://solscan.io/tx/${r.sig}`].join(','));
  return lines.join('\n');
}

export function ReceiptsCard({ address }) {
  const [rows, setRows] = useState(null);
  const [names, setNames] = useState({});
  useEffect(() => {
    fetch(apiUrl(`/api/reputation/receipts/${address}`)).then(r => r.json()).then(d => {
      setRows(d.receipts || []);
      [...new Set((d.receipts || []).flatMap(r => r.tokens.map(t => t[0])))].forEach(async m => { const s = await symbolOf(m); setNames(n => ({ ...n, [m]: s })); });
    }).catch(() => setRows([]));
  }, [address]);
  return <section className="wp-card wp-receipts" data-testid="receipts">
    <h3>Receipts <small>{rows ? `${rows.length} on-chain` : ''}</small></h3>
    <p className="wp-bio">Every FEELESS trade is verified against the chain and kept forever. Tap one to see the transaction.</p>
    {rows?.length > 0 && (() => { const t = totalsOf(rows); const coins = Object.entries(t.coins).filter(([m]) => m !== 'So11111111111111111111111111111111111111112').sort((a, b) => (b[1].spent + b[1].received) - (a[1].spent + a[1].received)); return <div className="wpr-totals" data-testid="receipt-totals">
      <div><small>SOL spent</small><b>{t.spent.toFixed(4)}</b></div><div><small>SOL received</small><b>{t.received.toFixed(4)}</b></div>
      <div><small>Net <Explain>SOL received minus SOL spent across your FEELESS trades. A coin you still hold shows as spent until you sell it, so net only becomes real profit or loss once you exit.</Explain></small><b className={t.received - t.spent >= 0 ? 'positive' : 'negative'}>{(t.received - t.spent >= 0 ? '+' : '') + (t.received - t.spent).toFixed(4)}</b></div><div><small>Network fees</small><b>{t.fees.toFixed(5)}</b></div>
      {coins.length > 0 && <table><thead><tr><th>Coin</th><th>SOL in</th><th>SOL out</th><th>Net</th></tr></thead><tbody>{coins.slice(0, 12).map(([m, c]) => <tr key={m}><td>{names[m] || shortAddress(m)}</td><td>{c.spent.toFixed(4)}</td><td>{c.received.toFixed(4)}</td><td className={c.received - c.spent >= 0 ? 'positive' : 'negative'}>{(c.received - c.spent).toFixed(4)}</td></tr>)}</tbody></table>}
      <button type="button" className="btn-outline" onClick={() => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csvOf(rows, names)], { type: 'text/csv' })); a.download = `feeless-receipts-${address.slice(0, 6)}.csv`; a.click(); URL.revokeObjectURL(a.href); }}>Download CSV for taxes</button>
      <small>Totals come from verified on-chain receipts of trades made through FEELESS, in SOL. A coin's net only counts as realized once you've sold it. Not tax advice; give the CSV to your accountant or tax software.</small>
    </div>; })()}
    {!rows ? <p className="wp-bio">Loading…</p> : !rows.length ? <p className="wp-bio">No receipts yet — trades made through FEELESS land here automatically.</p>
      : <div className="wpr-list">{rows.slice(0, 50).map(r => <a key={r.sig} className="wpr-row" href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">
        <span className={`wpr-kind k-${r.kind}`}>{r.kind}</span>
        <span className="wpr-legs">{r.tokens.map(([m, d]) => <em key={m} className={d >= 0 ? 'positive' : 'negative'}>{d >= 0 ? '+' : ''}{Math.abs(d) >= 1000 ? d.toLocaleString(undefined, { maximumFractionDigits: 0 }) : Number(d.toPrecision(4))} {names[m] || '…'}</em>)}{!r.tokens.length && <em>{r.sol >= 0 ? '+' : ''}{r.sol.toFixed(4)} SOL</em>}</span>
        <time>{r.t ? new Date(r.t * 1000).toLocaleString() : '—'}</time>
        <code>{r.sig.slice(0, 6)}…</code>
      </a>)}</div>}
  </section>;
}
