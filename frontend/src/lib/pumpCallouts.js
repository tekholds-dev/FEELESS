// Pump's coin-activity wire contract: callout data.createdAt is epoch milliseconds.
export function mergePumpCallouts(previous, items, enteredAt, mint) {
  const incoming = (items || []).filter(item => item?.kind === 'callout' && item.data?.coinMint === mint)
    .map(({ data }) => ({ id: data.calloutId, caller: data.username || data.userId || 'Pump user',
      text: data.thesis || '', at: Number(data.createdAt), marketCap: data.marketCap }))
    .filter(call => call.id && Number.isFinite(call.at) && call.at > 0);
  const merged = [...new Map([...previous, ...incoming].map(call => [call.id, call])).values()]
    .sort((a, b) => a.at - b.at || a.id.localeCompare(b.id));
  return [...merged.filter(call => call.at <= enteredAt).slice(-3),
    ...merged.filter(call => call.at > enteredAt).slice(-97)];
}
