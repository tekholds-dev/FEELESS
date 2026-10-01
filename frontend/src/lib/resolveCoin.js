import { apiUrl } from './api';

// Find a coin's market from a pool address OR a mint. Order: DexScreener pool → DexScreener token (deepest
// pool) → FEELESS pair lookup (Pump stream fallback) → FEELESS ecosystem assets ($FEE, rFEE,
// FEECAT, priced via Jupiter even without a DEX listing). Returns null when nothing knows the address.
export async function resolveCoin(chain, address) {
  const tryJson = async url => { try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch { return null; } };
  const pools = await tryJson(`https://api.dexscreener.com/latest/dex/pairs/${chain}/${address}`);
  if (pools?.pairs?.[0]) return pools.pairs[0];
  const tokens = await tryJson(`https://api.dexscreener.com/tokens/v1/${chain}/${address}`);
  const deepest = (Array.isArray(tokens) ? tokens : []).filter(x => x.baseToken?.address === address).sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0))[0];
  if (deepest) return deepest;
  const ours = await tryJson(apiUrl(`/api/market/pair/${chain}/${address}`));
  if (ours?.pairs?.[0]) return ours.pairs[0];
  const assets = await tryJson(apiUrl('/api/market/assets'));
  const asset = (assets?.assets || []).find(a => a.mint === address || a.pair?.pairAddress === address);
  if (asset?.pair) return { ...asset.pair, info: { ...(asset.pair.info || {}), imageUrl: asset.pair.info?.imageUrl || asset.imageUrl } };
  // FEELESS coin with no market yet (or prices still loading): still a coin — show its profile pre-market.
  if (asset) return { chainId: chain, pairAddress: asset.mint, dexId: 'pre-market', preMarket: true, url: `https://pump.fun/coin/${asset.mint}`,
    baseToken: { address: asset.mint, symbol: asset.label || asset.id?.toUpperCase(), name: asset.name || asset.label || asset.id },
    info: { imageUrl: asset.imageUrl || `/api/reputation/token-logo/${asset.mint}` }, priceChange: {}, txns: {}, volume: {}, liquidity: {} };
  return null;
}

export async function isCoinAddress(chain, address) {
  return Boolean(await resolveCoin(chain, address));
}
