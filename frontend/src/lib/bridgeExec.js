import { apiUrl } from './api';
import { relayConnection } from './launchRail';
import { CHAIN_ID, NATIVE, fromUnits, samePayout } from './lifiExec';

// 🌉 THE BRIDGE ENGINE (Trade › Bridge + ⛽ Get gas): SOL / USDC out to every EVM chain LI.FI routes, and back. One path per side:
//   EVM source  → lifiExec.executeLifi (LI.FI's contract only, exact approvals, eth_call dry run, your wallet signs)
//   Solana source → executeSolRoute: the server built + opened LI.FI's transaction (backend/lifi.py `verify_svm`), here it is checked against
//   the ticket, given a fresh blockhash, SIMULATED (and refused if it would spend more SOL than the quote), signed by your wallet, then the
//   server checks it again and broadcasts it ONCE. trackBridge follows LI.FI's status until the funds land on the other chain.
export const SOLANA_ID = 1151111081099710;
export const SOL_NATIVE = '11111111111111111111111111111111';
export const SOL_USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
export const RENT_SLACK = 10_000_000;   // lamports a route may move beside the amount (account rent, relayer tips) — the server's RENT_SLACK
// Every chain the bridge + gas station list: Solana + each EVM chain LI.FI still routes (Zora left LI.FI on 2026-10-23 → off the list).
export const BRIDGE_CHAINS = ['solana', 'ethereum', 'base', 'arbitrum', 'bsc', 'polygon', 'avalanche', 'optimism', 'zksync', 'unichain', 'worldchain', 'cronos'];
export const CHAIN = {
  solana: { name: 'Solana', tick: 'SOL', native: 'SOL', c1: '#9945ff', c2: '#14f195' }, ethereum: { name: 'Ethereum', tick: 'ETH', native: 'ETH', c1: '#627eea', c2: '#a8b8ff' },
  base: { name: 'Base', tick: 'BASE', native: 'ETH', c1: '#0052ff', c2: '#5d8bff' }, arbitrum: { name: 'Arbitrum', tick: 'ARB', native: 'ETH', c1: '#28a0f0', c2: '#9bd6ff' },
  bsc: { name: 'BNB Chain', tick: 'BNB', native: 'BNB', c1: '#f0b90b', c2: '#ffe08a' }, polygon: { name: 'Polygon', tick: 'POL', native: 'POL', c1: '#8247e5', c2: '#c3a4ff' },
  avalanche: { name: 'Avalanche', tick: 'AVAX', native: 'AVAX', c1: '#e84142', c2: '#ff9b9b' }, optimism: { name: 'Optimism', tick: 'OP', native: 'ETH', c1: '#ff0420', c2: '#ff8a96' },
  zksync: { name: 'zkSync', tick: 'ZK', native: 'ETH', c1: '#8c8dfc', c2: '#d0d0ff' }, unichain: { name: 'Unichain', tick: 'UNI', native: 'ETH', c1: '#f50db4', c2: '#ff8ad8' },
  worldchain: { name: 'World Chain', tick: 'WLD', native: 'ETH', c1: '#c9d1cc', c2: '#ffffff' }, cronos: { name: 'Cronos', tick: 'CRO', native: 'CRO', c1: '#1199fa', c2: '#8fd0ff' },
};
export const chainIdOf = k => (k === 'solana' ? SOLANA_ID : CHAIN_ID[k]);
export const keyOf = id => (Number(id) === SOLANA_ID ? 'solana' : Object.keys(CHAIN_ID).find(k => CHAIN_ID[k] === Number(id)));
export const isSol = k => k === 'solana';
// the token LI.FI wants on each side: the chain's native coin, or USDC (a plain symbol LI.FI resolves on EVM, the mint on Solana)
export const tokenOf = (k, asset) => (asset === 'usdc' ? (isSol(k) ? SOL_USDC : 'USDC') : isSol(k) ? SOL_NATIVE : NATIVE);
export const decimalsOf = (k, asset) => (asset === 'usdc' ? (k === 'bsc' ? 18 : 6) : isSol(k) ? 9 : 18);

const b64ToBytes = b => Uint8Array.from(atob(b), c => c.charCodeAt(0));
const bytesToB64 = u => { let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000)); return btoa(s); };
const sum = rows => (rows || []).reduce((a, r) => a + Number(r.amountUSD || 0), 0);

// pure: what the quote means in plain numbers — the four vitals on the desk
export function routeVitals(q) {
  if (!q?.estimate || !q?.action) return null;
  const ft = q.action.fromToken || {}; const tt = q.action.toToken || {};
  const send = fromUnits(q.action.fromAmount, ft.decimals ?? 18); const get = fromUnits(q.estimate.toAmount, tt.decimals ?? 18);
  const sendUsd = Number(q.estimate.fromAmountUSD) || send * Number(ft.priceUSD || 0); const getUsd = Number(q.estimate.toAmountUSD) || get * Number(tt.priceUSD || 0);
  const feeUsd = sum(q.estimate.feeCosts); const gasUsd = sum(q.estimate.gasCosts); const costUsd = Math.max(0, sendUsd - getUsd);
  return { send, sendSym: ft.symbol, sendUsd, get, getSym: tt.symbol, getUsd, feeUsd, gasUsd, costUsd, costPct: sendUsd ? (costUsd / sendUsd) * 100 : 0,
    secs: Math.max(1, Math.round(Number(q.estimate.executionDuration) || 30)), tool: q.toolDetails?.name || q.tool, logo: q.toolDetails?.logoURI };
}
export const fmtSecs = s => (s < 90 ? `${s}s` : `${Math.round(s / 60)} min`);

// pure: a Solana quote must match the ticket on screen before the wallet sees it — FEELESS-verified, your wallet pays, your OWN wallet on the
// other side gets paid, the coin + amount are the ones you typed.
export function checkSolQuote(q, { address, payTo, fromToken, fromAmount }) {
  if (!q?.feeless?.safety?.verified || Number(q?.action?.fromChainId) !== SOLANA_ID) throw new Error('Blocked: FEELESS did not verify this route. Get a fresh quote.');
  if (q.action.fromAddress !== address) throw new Error('Blocked: this quote was made for a different wallet. Get a fresh quote.');
  if (!samePayout(q.action.toAddress, payTo)) throw new Error('Blocked: this route pays out to a different wallet than yours.');
  if (fromToken && q.action.fromToken?.address !== fromToken) throw new Error('Blocked: this quote spends a different coin than the ticket.');
  if (fromAmount != null && String(q.action.fromAmount) !== String(fromAmount)) throw new Error('Blocked: this quote spends a different amount than the ticket.');
  if (!q.transactionRequest?.data) throw new Error('Blocked: no transaction in this quote.');
}
// pure: the simulation may not take more SOL out of the wallet than the quote (+ rent / tips slack)
export const spendOk = ({ pre, post, fromToken, fromAmount }) => pre == null || post == null || pre - post <= (fromToken === SOL_NATIVE ? Number(fromAmount) : 0) + RENT_SLACK;

export async function bridgeQuote({ from, to, asset, amountUnits, fromAddress, toAddress, slippage = 0.01 }) {
  const qs = new URLSearchParams({ fromChain: chainIdOf(from), toChain: chainIdOf(to), fromToken: tokenOf(from, asset), toToken: tokenOf(to, asset), fromAmount: String(amountUnits),
    fromAddress, toAddress, slippage: String(slippage) });
  const res = await fetch(apiUrl(`/api/lifi/quote?${qs}`)); const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || 'No route for this bridge right now.');
  return body;
}

export async function executeSolRoute({ quote, provider, address, payTo, onStep = () => {}, sleep = ms => new Promise(r => setTimeout(r, ms)) }) {
  checkSolQuote(quote, { address, payTo });
  const { web3, connection } = await relayConnection();
  const tx = web3.VersionedTransaction.deserialize(b64ToBytes(quote.transactionRequest.data));
  if (tx.message.staticAccountKeys[0].toBase58() !== address) throw new Error('Blocked: this transaction is not for your wallet.');
  onStep('Simulating it on Solana…', 'sim');
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
  tx.message.recentBlockhash = blockhash;   // the only thing that may change — the server's fingerprint ignores it, nothing else
  const pre = await connection.getBalance(new web3.PublicKey(address), 'confirmed').catch(() => null);
  const sim = await connection.simulateTransaction(tx, { sigVerify: false, accounts: { encoding: 'base64', addresses: [address] } });
  if (sim.value.err) throw new Error(`Simulation failed — nothing was signed: ${JSON.stringify(sim.value.err)} ${(sim.value.logs || []).slice(-1).join(' ')}`.trim());
  const post = sim.value.accounts?.[0]?.lamports;
  if (!spendOk({ pre, post, fromToken: quote.action.fromToken?.address, fromAmount: quote.action.fromAmount })) throw new Error('Refused: the simulation spends more SOL than the quote.');
  onStep('Approve in your wallet…', 'sign');
  const signed = await provider.signTransaction(tx);
  const res = await fetch(apiUrl('/api/lifi/solana/send'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ signed: bytesToB64(signed.serialize()) }) });
  const out = await res.json().catch(() => ({}));
  if (!res.ok || !out.signature) throw new Error(out.detail || 'FEELESS could not send it — nothing left your wallet.');
  onStep('Sent — confirming on Solana…', 'source');
  for (let i = 0; i < 60; i++) {
    const st = (await connection.getSignatureStatuses([out.signature])).value[0];
    if (st?.err) throw new Error(`It failed on Solana: ${JSON.stringify(st.err)} — nothing was bridged.`);
    if (st?.confirmationStatus === 'confirmed' || st?.confirmationStatus === 'finalized') return { hash: out.signature };
    if ((await connection.getBlockHeight('confirmed')) > lastValidBlockHeight) throw new Error('It expired before it landed. Nothing was spent; get a fresh quote.');
    await sleep(1500);
  }
  throw new Error(`Still confirming — check ${out.signature} on Solscan before trying again.`);
}

// Follows LI.FI's status until the funds land on the other chain (or it fails). Never resends anything.
export async function trackBridge({ hash, fromChainId, toChainId, onStep = () => {}, tries = 120, every = 5000, fetchImpl = fetch, sleep = ms => new Promise(r => setTimeout(r, ms)) }) {
  onStep('Bridging — waiting for it to land on the other chain…', 'bridge');
  for (let i = 0; i < tries; i++) {
    const s = await fetchImpl(apiUrl(`/api/lifi/status?txHash=${hash}&fromChain=${fromChainId}&toChain=${toChainId}`)).then(r => r.json()).catch(() => null);
    if (s?.status === 'DONE' || s?.status === 'FAILED') return s;
    await sleep(every);
  }
  return { status: 'PENDING' };
}
