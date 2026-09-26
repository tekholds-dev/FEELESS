// Quiet background reputation scanning: whenever a market list/feed renders, kick off
// FEELESS's own on-chain forensics (snipers, bundlers, holder concentration) for the coins
// on screen, so evidence exists by the time anyone opens one — not only when they ask for it.
// Fire-and-forget, deduped, capped, Solana-only (the only chain FEELESS forensics cover).
const scanned = new Set();
let inflight = 0;
const MAX_CONCURRENT = 3;
const PER_TICK = 8;

export function scanBackground(pairs) {
  if (!Array.isArray(pairs) || !pairs.length) return;
  const todo = pairs.filter(p => p?.chainId === 'solana' && p.baseToken?.address && !scanned.has(p.baseToken.address)).slice(0, PER_TICK);
  todo.forEach(p => {
    const mint = p.baseToken.address;
    scanned.add(mint);
    if (inflight >= MAX_CONCURRENT) return;
    inflight++;
    fetch(`/api/reputation/intel/solana/${mint}`).catch(() => {}).finally(() => { inflight--; });
  });
}
