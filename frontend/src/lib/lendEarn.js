import { apiUrl } from './api';
import { relayConnection, signSend } from './launchRail';

// 🏦 Jupiter Lend Earn, in FEELESS: the server asks Jupiter for the UNSIGNED transaction and only returns it after checking it (you pay, you
// sign alone, only Jupiter Lend + Solana's own programs — backend/lend_earn.py). Here: simulate first (nothing is signed if the chain would
// reject it), your wallet signs, we wait for it to land. FEELESS never holds funds.
export const LEND_SIDES = [['deposit', '＋ Deposit'], ['withdraw', '− Withdraw']];
// pure: a typed amount is a positive number with ≤ 9 decimals
export const okAmount = v => /^\d*(\.\d{0,9})?$/.test(String(v || '').trim()) && Number(v) > 0;
// pure: the review line the user reads before the wallet opens
export const lendLine = (q, amount) => `${q.side === 'withdraw' ? 'Withdraw' : 'Deposit'} ${amount} ${q.sym || ''} ${q.side === 'withdraw' ? 'from' : 'into'} Jupiter Lend${q.apy != null && q.side !== 'withdraw' ? ` · ${q.apy}% APY now` : ''}`.replace(/\s+/g, ' ').trim();

export async function lendQuote({ address, asset, side, amount }) {
  const r = await fetch(apiUrl('/api/reputation/familia-pools/earn'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, asset, side, amount: String(amount) }) });
  const b = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(b.detail || 'Could not build it.');
  return b;
}

export async function lendSign({ provider, address, quote, onStatus }) {
  const { web3, connection } = await relayConnection();
  const tx = web3.VersionedTransaction.deserialize(Uint8Array.from(atob(quote.transaction), c => c.charCodeAt(0)));
  if (tx.message.staticAccountKeys[0].toBase58() !== address) throw new Error('This transaction is not for your wallet — refused.');
  onStatus?.('Checking it on Solana…');
  return signSend(web3, connection, provider, tx, new web3.PublicKey(address), [], onStatus);
}
