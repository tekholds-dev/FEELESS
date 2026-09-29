// Pump's coin-activity wire contract: callout data.createdAt is epoch milliseconds.
// Keeps every callout seen for the coin (deduplicated, oldest first) so the every-3rd cadence stays stable.
export function mergePumpCallouts(previous, items, mint) {
  const incoming = (items || []).filter(item => item?.kind === 'callout' && item.data?.coinMint === mint)
    .map(({ data }) => ({ id: String(data.calloutId || ''), caller: data.username || data.userId || 'Pump user',
      text: data.thesis || '', at: Number(data.createdAt), marketCap: data.marketCap }))
    .filter(call => call.id && Number.isFinite(call.at) && call.at > 0);
  return [...new Map([...previous, ...incoming].map(call => [call.id, call])).values()]
    .sort((a, b) => a.at - b.at || a.id.localeCompare(b.id))
    .slice(-300);
}

// FEELESS coin chat stays FEELESS-first: on entry show the 3 callouts made just before the user arrived,
// then only every 3rd Pump callout posted after entry.
export function visiblePumpCallouts(all, enteredAt) {
  const before = all.filter(call => call.at <= enteredAt).slice(-3);
  const after = all.filter(call => call.at > enteredAt).filter((_, index) => (index + 1) % 3 === 0);
  return [...before, ...after];
}

export const isPumpCoin = pair => {
  const mint = pair?.baseToken?.address;
  return pair?.chainId === 'solana' && Boolean(mint)
    && (pair?.launchpadId === 'pump' || String(pair?.dexId || '').toLowerCase().includes('pump') || mint.endsWith('pump'));
};
