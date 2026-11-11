import { useEffect, useState } from 'react';

// 💲 What one proof of a kind should cost this agent BEFORE it starts (owner 2026-11-10: "show price for stuff so users aren't blind or find
// out later"). The server prices it from its own real bills, or every agent's real token use at its own minds' rates; its own machines are free.
// One fetch per agent every 5 minutes, shared by every button that shows it.
const CACHE = new Map();
export function useProofPrices(catId, work) {
  const [p, setP] = useState(() => CACHE.get(catId)?.prices || null);
  useEffect(() => {
    if (!catId || !work) return undefined; let live = true; const hit = CACHE.get(catId);
    if (hit && Date.now() - hit.at < 300000) { setP(hit.prices); return undefined; }
    Promise.resolve().then(() => work(catId, { op: 'proof_prices' })).then(j => { if (!j?.prices) return; CACHE.set(catId, { at: Date.now(), prices: j.prices }); if (live) setP(j.prices); }).catch(() => {});
    return () => { live = false; };
  }, [catId, work]);
  return p;
}
// '≈$0.0042 a proof' · 'free on your machines' · '' (no price known yet: never a made-up number)
export function priceWord(row) {
  if (!row || row.usd == null) return '';
  if (row.usd === 0) return row.from === 'local' ? 'free on your machines' : 'free';
  return `≈$${row.usd < 0.01 ? row.usd.toFixed(4) : row.usd.toFixed(2)} a proof`;
}
export const priceTip = row => (!row || row.usd == null ? 'Its price shows once any agent has filed one of these' : row.from === 'local' ? `Both minds run on your own machines (${(row.minds || []).join(' + ')}): no model bill`
  : row.from === 'its proofs' ? `The middle of its own ${row.n} real bill${row.n === 1 ? '' : 's'} for this proof` : `Real token use of every agent's proofs of this kind, at ${(row.minds || []).join(' + ')} rates`);
