import { mergePumpCallouts, visiblePumpCallouts, isPumpCoin } from './pumpCallouts';
const row = (id, at, mint = 'mint') => ({ kind: 'callout', data: { calloutId: id, createdAt: at, coinMint: mint, thesis: 'Actual user message' } });
test('merges without duplicates and ignores other coins', () => {
  const initial = mergePumpCallouts([], [row('a', 1), row('b', 2), row('wrong', 3, 'other')], 'mint');
  expect(initial.map(c => c.id)).toEqual(['a', 'b']);
  const next = mergePumpCallouts(initial, [row('b', 2), row('c', 3)], 'mint');
  expect(next.map(c => c.id)).toEqual(['a', 'b', 'c']);
  expect(next[2].text).toBe('Actual user message');
});
test('shows three prior calls at entry, then every third new call', () => {
  const all = mergePumpCallouts([], ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k'].map((id, i) => row(id, i + 1)), 'mint');
  // Entered at t=4: prior a..d -> last three b,c,d. New e..k -> 3rd (g) and 6th (j).
  expect(visiblePumpCallouts(all, 4).map(c => c.id)).toEqual(['b', 'c', 'd', 'g', 'j']);
});
test('rejects malformed timestamps and non-callout activity', () => {
  expect(mergePumpCallouts([], [row('a', 'bad'), { kind: 'trade', data: {} }], 'mint')).toEqual([]);
});
test('detects Pump coins by launchpad, dex, or mint suffix', () => {
  expect(isPumpCoin({ chainId: 'solana', baseToken: { address: 'abcpump' } })).toBe(true);
  expect(isPumpCoin({ chainId: 'solana', dexId: 'raydium', baseToken: { address: 'abc' } })).toBe(false);
  expect(isPumpCoin({ chainId: 'base', launchpadId: 'pump', baseToken: { address: 'abcpump' } })).toBe(false);
});
