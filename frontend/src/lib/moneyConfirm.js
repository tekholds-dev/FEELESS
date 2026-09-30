import { toast } from 'sonner';
import { apiUrl } from './api';

// One confirmation for every live-money action (launch, EVM swap, bridge): a toast with the explorer link,
// and a refresh signal for holdings / portfolio / positions. Solana swaps also get a server-side ✅ notification.
const EXPLORER = { solana: 'https://solscan.io/tx/', ethereum: 'https://etherscan.io/tx/', base: 'https://basescan.org/tx/', bsc: 'https://bscscan.com/tx/',
  arbitrum: 'https://arbiscan.io/tx/', polygon: 'https://polygonscan.com/tx/', optimism: 'https://optimistic.etherscan.io/tx/', avalanche: 'https://snowtrace.io/tx/', cronos: 'https://cronoscan.com/tx/' };
const CHAIN_BY_ID = { 1: 'ethereum', 8453: 'base', 56: 'bsc', 42161: 'arbitrum', 137: 'polygon', 10: 'optimism', 43114: 'avalanche', 25: 'cronos' };

export const explorerTx = (chain, hash) => (hash ? `${EXPLORER[CHAIN_BY_ID[chain] || chain] || 'https://blockscan.com/tx/'}${hash}` : '');

export function moneyConfirmed({ title, chain = 'solana', hash, mint, side = 'buy', usd, wallet, detail }) {
  const url = explorerTx(chain, hash);
  toast.success(`✅ ${title}`, { description: detail || (hash ? `Confirmed on-chain · ${hash.slice(0, 6)}…${hash.slice(-4)}` : 'Confirmed on-chain'),
    duration: 9000, ...(url ? { action: { label: 'View tx', onClick: () => window.open(url, '_blank', 'noopener') } } : {}) });
  const d = { mint, side, signature: hash, usd, wallet, chain };
  window.dispatchEvent(new CustomEvent('feeless:money-confirmed', { detail: d }));
  // Coin-specific listeners (tape, chart pins, position) only when we know the coin.
  if (mint && hash) window.dispatchEvent(new CustomEvent('feeless:trade-confirmed', { detail: d }));
}

// A cross-chain route that was still in flight: keep watching LI.FI in the background and confirm when it lands.
export function watchBridge({ hash, fromChainId, toChainId, title = 'Bridge delivered', every = 15000, tries = 40, fetchImpl = fetch }) {
  let n = 0; let stop = false;
  const tick = async () => {
    if (stop || n++ >= tries) { if (!stop) toast.warning('Bridge still pending', { description: 'Check the transaction on the explorer — nothing was resent.' }); return; }
    const s = await fetchImpl(apiUrl(`/api/lifi/status?txHash=${hash}&fromChain=${fromChainId}&toChain=${toChainId}`)).then(r => r.json()).catch(() => null);
    if (s?.status === 'DONE') { moneyConfirmed({ title, chain: toChainId, hash: s.receiving?.txHash || hash, detail: 'Funds arrived on the destination chain.' }); return; }
    if (s?.status === 'FAILED') { toast.error('Bridge failed', { description: s.substatusMessage || 'LI.FI reported the route failed. Check the explorer.' }); return; }
    setTimeout(tick, every);
  };
  setTimeout(tick, every);
  return () => { stop = true; };
}
