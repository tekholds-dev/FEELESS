import { apiUrl } from './api';
import { keepReceipt } from './receipts';

// ⚡ THE FEELESS SWAP ENGINE as two calls (the same /api/trading path the Trade tab's SwapWorkspace walks): quote → the server simulates →
// the wallet signs exactly the quoted transaction (fee payer checked here) → the server checks the signed message equals the quote and sends
// it once — no resubmits. Used where a flow needs a swap leg without opening the swap card (the LP zap). The FEELESS fee rides on the route
// like every swap (HQ › Core). Amounts are UI units ("0.025" SOL).
const API = apiUrl('/api/trading');
async function request(path, body) {
  const res = await fetch(`${API}${path}`, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.detail?.message || data?.detail || data?.message || `Swap service answered ${res.status}`);
  return data;
}
export const MAX_IMPACT_PCT = 3;   // a zap never signs into a thin route: above this the user opens the swap card and decides
// pure: the order's price impact in % (the engine answers it either as a fraction or as a percent)
export const impactOf = q => (q?.priceImpactPct != null ? Math.abs(Number(q.priceImpactPct) * 100) : q?.priceImpact != null ? Math.abs(Number(q.priceImpact)) : null);

export async function engineQuote({ inputMint, outputMint, amount, wallet, slippageBps = 150 }) {
  const order = await request('/quote', { input_mint: inputMint, output_mint: outputMint, amount: String(amount), slippage_bps: slippageBps, wallet });
  if (!order?.quote?.transaction || !order.order_id) throw new Error('The swap engine returned no transaction to sign.');
  const imp = impactOf(order.quote); if (imp != null && imp > MAX_IMPACT_PCT) throw new Error(`Price impact ${imp.toFixed(1)}% — too thin for a one-tap zap. Use the swap to decide.`);
  return order;
}

export async function engineSwap({ provider, wallet, order, onStatus }) {
  if (!order.simulated) { onStatus?.('Simulating the swap…'); await request('/simulate', { order_id: order.order_id }); }
  const { VersionedTransaction } = await import('@solana/web3.js');
  if (!provider?.signTransaction || provider.publicKey?.toString() !== wallet) throw new Error('Connected wallet changed — reconnect and zap again.');
  const tx = VersionedTransaction.deserialize(Uint8Array.from(atob(order.quote.transaction), c => c.charCodeAt(0)));
  if (tx.message.staticAccountKeys[0].toBase58() !== wallet) throw new Error('Wallet does not match the quoted fee payer.');
  onStatus?.('Approve the swap in your wallet…');
  const signed = await Promise.race([provider.signTransaction(tx), new Promise((_, rej) => setTimeout(() => rej(new Error('Wallet did not respond — open it and zap again.')), 60000))]);
  let res = await request('/execute', { order_id: order.order_id, signed_transaction: btoa(String.fromCharCode(...signed.serialize())) });
  for (let i = 0; i < 30 && res.signature && !['confirmed', 'failed'].includes(res.state); i++) {   // poll, never resend
    onStatus?.('Swap submitted — confirming…'); await new Promise(r => setTimeout(r, 2000));
    try { res = await request(`/order/${encodeURIComponent(order.order_id)}`); } catch { /* keep polling */ }
  }
  if (res.state !== 'confirmed') throw new Error(res.state === 'failed' ? 'The swap failed on-chain — nothing was joined.' : 'The swap is still confirming — check it before joining.');
  keepReceipt(res.signature, wallet, 'swap');
  return res;
}
