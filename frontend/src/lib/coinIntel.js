import { useEffect, useState } from 'react';
import { fetchEdgeIntel } from './coinEdge';

// Launch forensics for a coin (creator, snipers, bundled wallets, top holders): one request per coin per minute,
// shared by every tape row / card that asks.
// Forensics come through the coin edge (one record per coin, cached server-side); `intel=1` runs the scan if needed.
export function fetchIntel(chain, mint) {
  return chain === 'solana' && mint ? fetchEdgeIntel(mint) : Promise.resolve(null);
}

// wallet -> [{ id, label, tone, why }] for the tape: who this trader is on this coin.
export function walletTags(intel) {
  const tags = new Map();
  const add = (w, t) => { if (w) tags.set(w, [...(tags.get(w) || []), t]); };
  if (!intel) return tags;
  add(intel.creator, { id: 'dev', label: 'DEV', tone: 'bad', why: 'Created this coin' });
  (intel.sniperWallets || []).forEach(w => add(w, { id: 'sniper', label: 'SNIPER', tone: 'bad', why: 'Bought in the launch block(s)' }));
  (intel.bundledWallets || []).forEach(w => add(w, { id: 'bundle', label: 'BUNDLE', tone: 'warn', why: 'Bundled with the launch' }));
  (intel.topHolders || []).filter(h => h.kind !== 'program' && h.pct >= 1).forEach(h => add(h.owner, { id: 'top', label: `TOP ${h.pct.toFixed(1)}%`, tone: 'warn', why: `Holds ${h.pct.toFixed(1)}% of supply` }));
  return tags;
}

export function useWalletTags(pair) {
  const [tags, setTags] = useState(() => new Map());
  const mint = pair?.baseToken?.address; const chain = pair?.chainId;
  useEffect(() => {
    let alive = true;
    if (chain !== 'solana' || !mint) { setTags(new Map()); return undefined; }
    fetchIntel(chain, mint).then(d => alive && setTags(walletTags(d)));
    return () => { alive = false; };
  }, [chain, mint]);
  return tags;
}
