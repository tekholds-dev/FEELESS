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
    {!rows ? <p className="wp-bio">Loading…</p> : !rows.length ? <p className="wp-bio">No receipts yet — trades made through FEELESS land here automatically.</p>
      : <div className="wpr-list">{rows.slice(0, 50).map(r => <a key={r.sig} className="wpr-row" href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">
        <span className={`wpr-kind k-${r.kind}`}>{r.kind}</span>
        <span className="wpr-legs">{r.tokens.map(([m, d]) => <em key={m} className={d >= 0 ? 'positive' : 'negative'}>{d >= 0 ? '+' : ''}{Math.abs(d) >= 1000 ? d.toLocaleString(undefined, { maximumFractionDigits: 0 }) : Number(d.toPrecision(4))} {names[m] || '…'}</em>)}{!r.tokens.length && <em>{r.sol >= 0 ? '+' : ''}{r.sol.toFixed(4)} SOL</em>}</span>
        <time>{r.t ? new Date(r.t * 1000).toLocaleString() : '—'}</time>
        <code>{r.sig.slice(0, 6)}…</code>
      </a>)}</div>}
  </section>;
}
