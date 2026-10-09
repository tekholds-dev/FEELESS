import { apiUrl } from './api';

// Secure LI.FI execution, shared by every EVM path (swap card, Bridge, Get Gas, trench / war room EVM trades).
// Quotes come from the FEELESS server (/api/lifi/quote), which already verified the route; the wallet side
// re-checks everything right before signing, because the wallet is the last line of defence:
//   1. the transaction and any approval target LI.FI's own contract (allowlist)
//   2. the wallet is really on the route's network (asks to switch, then confirms eth_chainId)
//   3. the quote was made for this wallet
//   4. approvals are for the exact amount, and only when the current allowance is too low
export const CHAIN_ID = { ethereum: 1, base: 8453, bsc: 56, arbitrum: 42161, avalanche: 43114, polygon: 137, optimism: 10, zksync: 324, zora: 7777777, cronos: 25, unichain: 130, worldchain: 480 };
export const chainKey = id => Object.keys(CHAIN_ID).find(k => CHAIN_ID[k] === Number(id));
export const NATIVE = '0x0000000000000000000000000000000000000000';
const LIFI_CONTRACTS = new Set(['0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae', '0x341e94069f53234fe6dabef707ad424830525715']);

export const toUnits = (amt, dec) => { const [w, f = ''] = String(amt).split('.'); return BigInt(w || 0) * 10n ** BigInt(dec) + BigInt((f + '0'.repeat(dec)).slice(0, dec) || 0); };
export const fromUnits = (v, dec) => Number(BigInt(v || 0)) / 10 ** dec;

export async function lifiServerQuote({ fromChain, toChain, fromToken, toToken, fromAmount, fromAddress, slippage = 0.005 }) {
  const qs = new URLSearchParams({ fromChain, toChain, fromToken, toToken, fromAmount: String(fromAmount), fromAddress, slippage: String(slippage) });
  const res = await fetch(apiUrl(`/api/lifi/quote?${qs}`));
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || 'No route for this trade right now.');
  return body;
}

async function waitReceipt(provider, hash, tries = 90) {
  for (let i = 0; i < tries; i++) {
    const r = await provider.request({ method: 'eth_getTransactionReceipt', params: [hash] }).catch(() => null);
    if (r) { if (r.status === '0x0') throw new Error('Transaction reverted on-chain. Nothing else was sent.'); return r; }
    await new Promise(res => setTimeout(res, 2000));
  }
  throw new Error('Still pending — check your wallet before trying again.');
}

async function allowance(provider, token, owner, spender) {
  const data = `0xdd62ed3e${owner.slice(2).toLowerCase().padStart(64, '0')}${spender.slice(2).toLowerCase().padStart(64, '0')}`;
  const out = await provider.request({ method: 'eth_call', params: [{ to: token, data }, 'latest'] }).catch(() => '0x0');
  return BigInt(out && out !== '0x' ? out : '0x0');
}

export function checkQuote(quote, wallet) {
  const tx = quote?.transactionRequest || {};
  const approval = String(quote?.estimate?.approvalAddress || '').toLowerCase();
  if (!LIFI_CONTRACTS.has(String(tx.to || '').toLowerCase())) throw new Error('Blocked: this route does not go to LI.FI’s contract.');
  if (approval && !LIFI_CONTRACTS.has(approval)) throw new Error('Blocked: unexpected approval target.');
  if (String(quote?.action?.fromAddress || '').toLowerCase() !== String(wallet?.address || '').toLowerCase()) throw new Error('Blocked: this quote was made for a different wallet. Get a fresh quote.');
  const to = String(quote?.action?.toAddress || '').toLowerCase();
  if (to && to !== String(quote?.action?.fromAddress || '').toLowerCase()) throw new Error('Blocked: this route pays out to a different wallet than yours.');
  if (!chainKey(tx.chainId)) throw new Error('Blocked: unsupported network.');
}

// Returns { hash, receipt, status } once the source transaction lands (and, for bridges, the destination).
export async function executeLifi({ quote, wallet, provider, switchTo, onStep = () => {} }) {
  checkQuote(quote, wallet);
  const tx = quote.transactionRequest;
  const net = chainKey(tx.chainId);
  onStep(`Switching your wallet to ${net}…`);
  const switched = await switchTo?.(net);
  const prov = switched?.provider || provider;
  const on = parseInt(await prov.request({ method: 'eth_chainId' }), 16);
  if (on !== Number(tx.chainId)) throw new Error(`Your wallet is on another network. Switch to ${net} and try again.`);
  const from = wallet.address;
  const fromToken = quote.action.fromToken.address;
  const amount = BigInt(quote.action.fromAmount);
  if (fromToken.toLowerCase() !== NATIVE && quote.estimate.approvalAddress) {
    const spender = quote.estimate.approvalAddress;
    if ((await allowance(prov, fromToken, from, spender)) < amount) {
      onStep(`Approve exactly ${fromUnits(amount, quote.action.fromToken.decimals).toLocaleString(undefined, { maximumFractionDigits: 6 })} ${quote.action.fromToken.symbol} in your wallet…`);
      const data = `0x095ea7b3${spender.slice(2).toLowerCase().padStart(64, '0')}${amount.toString(16).padStart(64, '0')}`;
      const ah = await prov.request({ method: 'eth_sendTransaction', params: [{ from, to: fromToken, data }] });
      onStep('Approval sent — waiting for it to confirm…');
      await waitReceipt(prov, ah);
    }
  }
  onStep('Confirm the swap in your wallet…');
  const hash = await prov.request({ method: 'eth_sendTransaction', params: [{ from, to: tx.to, data: tx.data, value: tx.value, gas: tx.gasLimit }] });
  onStep('Submitted — waiting for the network…');
  const receipt = await waitReceipt(prov, hash);
  let status = 'DONE';
  if (quote.action.fromChainId !== quote.action.toChainId) {
    onStep('Bridging — waiting for funds to arrive on the other chain…');
    for (let i = 0; i < 90; i++) {
      const s = await fetch(apiUrl(`/api/lifi/status?txHash=${hash}&fromChain=${quote.action.fromChainId}&toChain=${quote.action.toChainId}`)).then(r => r.json()).catch(() => null);
      if (s?.status === 'DONE' || s?.status === 'FAILED') { status = s.status; break; }
      await new Promise(res => setTimeout(res, 5000));
      status = 'PENDING';
    }
  }
  return { hash, receipt, status };
}

// ⚡ ONE APPROVAL FOR MANY SWAPS (EIP-5792 `wallet_sendCalls`): every approve + swap on ONE chain goes to the wallet as a single request, when the
// wallet can batch (smart-account wallets: MetaMask smart account, Coinbase, Safe…). A plain wallet cannot — it signs one transaction at a time,
// and no site can change that — so this returns null and the caller sends them one by one. Every quote passes the same checks as a single swap.
export const batchCalls = async (prov, quotes, wallet) => {
  const calls = [];
  for (const quote of quotes) {
    checkQuote(quote, wallet);
    const tx = quote.transactionRequest; const fromToken = quote.action.fromToken.address; const amount = BigInt(quote.action.fromAmount);
    if (fromToken.toLowerCase() !== NATIVE && quote.estimate.approvalAddress) {
      const spender = quote.estimate.approvalAddress;
      if ((await allowance(prov, fromToken, wallet.address, spender)) < amount) calls.push({ to: fromToken, value: '0x0', data: `0x095ea7b3${spender.slice(2).toLowerCase().padStart(64, '0')}${amount.toString(16).padStart(64, '0')}` });
    }
    calls.push({ to: tx.to, data: tx.data, value: tx.value || '0x0' });
  }
  return calls;
};
export const canBatch = async (prov, from, chainHex) => {
  try { const caps = await prov.request({ method: 'wallet_getCapabilities', params: [from, [chainHex]] }); const c = (caps || {})[chainHex] || (caps || {})[chainHex.toLowerCase()] || {};
    return ['supported', 'ready'].includes(c.atomic?.status) || c.atomicBatch?.supported === true; } catch { return false; }
};
export async function executeLifiBatch({ quotes, wallet, provider, switchTo, onStep = () => {}, tries = 90, waitMs = 2000 }) {
  if (!quotes?.length) return null;
  const chainId = Number(quotes[0].transactionRequest.chainId);
  if (quotes.some(q => Number(q.transactionRequest.chainId) !== chainId)) throw new Error('A batch is one network at a time.');
  const net = chainKey(chainId); const chainHex = `0x${chainId.toString(16)}`;
  const switched = await switchTo?.(net); const prov = switched?.provider || provider;
  if (parseInt(await prov.request({ method: 'eth_chainId' }), 16) !== chainId) throw new Error(`Your wallet is on another network. Switch to ${net} and try again.`);
  if (!(await canBatch(prov, wallet.address, chainHex))) return null;
  const calls = await batchCalls(prov, quotes, wallet);
  onStep(`Approve ONE request for ${quotes.length} swap${quotes.length === 1 ? '' : 's'} on ${net} in your wallet…`);
  const sent = await prov.request({ method: 'wallet_sendCalls', params: [{ version: '2.0.0', from: wallet.address, chainId: chainHex, atomicRequired: false, calls }] });
  const id = typeof sent === 'string' ? sent : sent?.id;
  onStep('Submitted — waiting for the network…');
  for (let i = 0; i < tries; i++) {
    const st = await prov.request({ method: 'wallet_getCallsStatus', params: [id] }).catch(() => null);
    const code = Number(st?.status);
    if (code >= 200 || st?.status === 'CONFIRMED') { if (code >= 400) throw new Error(code === 600 ? 'Only part of the batch landed — refresh to see what is left.' : 'The batch did not land. Nothing else was sent.'); return { id, status: 'DONE', receipts: st.receipts || [] }; }
    await new Promise(res => setTimeout(res, waitMs));
  }
  throw new Error('Still pending — check your wallet before trying again.');
}
