import { apiUrl } from './api';

// Store a verified, compact receipt for an on-chain tx. The server checks the chain
// itself, so this is fire-and-forget; failures never block the user's trade.
export function keepReceipt(sig, wallet, kind = 'swap') {
  if (!sig || !wallet) return Promise.resolve(null);
  return fetch(apiUrl('/api/reputation/receipts'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sig, wallet, kind }) })
    .then(r => (r.ok ? r.json() : null)).catch(() => null);
}
