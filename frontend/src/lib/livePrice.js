// Fastest trustworthy price per chain. Solana: Jupiter price API (full precision, updates on
// every routed trade). Other chains: DexScreener pair snapshot.
export async function fetchLivePrice(pair) {
  const chain = pair?.chainId;
  const mint = pair?.baseToken?.address;
  if (chain === 'solana' && mint) {
    try {
      const res = await fetch(`https://lite-api.jup.ag/price/v3?ids=${mint}`);
      if (res.ok) {
        const body = await res.json();
        const row = body?.[mint];
        const usd = Number(row?.usdPrice);
        if (usd > 0) return { usd, change24h: Number(row.priceChange24h), source: 'Jupiter' };
      }
    } catch {
      // fall through to DexScreener
    }
  }
  if (!chain || !pair?.pairAddress) return null;
  try {
    const res = await fetch(`https://api.dexscreener.com/latest/dex/pairs/${chain}/${pair.pairAddress}`);
    if (!res.ok) return null;
    const body = await res.json();
    const p = (body?.pairs || [])[0] || body?.pair;
    const usd = Number(p?.priceUsd);
    return usd > 0 ? { usd, change24h: Number(p?.priceChange?.h24), source: 'DexScreener', pair: p } : null;
  } catch {
    return null;
  }
}

// Price with enough significant digits that real sub-cent moves are visible live.
export function formatLivePrice(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  if (n >= 1000) return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  if (n >= 1) return `$${n.toFixed(4)}`;
  const digits = Math.min(12, Math.max(6, -Math.floor(Math.log10(n)) + 5));
  return `$${n.toFixed(digits)}`;
}
