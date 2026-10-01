import { useCoinEdge, dropEdge } from './coinEdge';

// Verified check for a coin's logo: read from the shared coin edge poller (lib/coinEdge.js — one batched request for every
// coin on screen; the server verifies unknown coins in the background and the next edge refresh carries the result).
export function useVerified(mint) {
  return useCoinEdge(mint)?.verify || null;
}
export const clearVerified = mint => { dropEdge(mint); };
