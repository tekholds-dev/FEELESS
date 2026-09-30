import { apiUrl } from './api';

// Store a verified, compact receipt for an on-chain tx. The server checks the chain
// itself, so this is fire-and-forget; failures never block the user's trade.
export function keepReceipt(sig, wallet, kind = 'swap') {
  if (!sig || !wallet) return Promise.resolve(null);
  // A fresh tx can take a few seconds to be readable by the RPC: retry (server dedupes by signature).
  const once = () => fetch(apiUrl('/api/reputation/receipts'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sig, wallet, kind }) })
    .then(r => (r.ok ? r.json() : r.status === 404 || r.status >= 500 ? 'retry' : null)).catch(() => 'retry');
  return (async () => { for (let i = 0; i < 4; i++) { const r = await once(); if (r !== 'retry') return r; await new Promise(ok => setTimeout(ok, 5000)); } return null; })();
}
