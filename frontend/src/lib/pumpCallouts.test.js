import { mergePumpCallouts } from './pumpCallouts';
const row = (id, at, mint = 'mint') => ({ kind: 'callout', data: { calloutId: id, createdAt: at, coinMint: mint, thesis: 'Actual user message' } });
test('retains three prior calls at entry, then appends new calls without duplicates', () => {
  const initial = mergePumpCallouts([], [row('a', 1), row('b', 2), row('c', 3), row('d', 4), row('wrong', 4, 'other')], 4, 'mint');
  expect(initial.map(c => c.id)).toEqual(['b', 'c', 'd']);
  const live = mergePumpCallouts(initial, [row('d', 4), row('e', 5)], 4, 'mint');
  expect(live.map(c => c.id)).toEqual(['b', 'c', 'd', 'e']);
  expect(live[3].text).toBe('Actual user message');
});
test('rejects malformed timestamps and non-callout activity', () => {
  expect(mergePumpCallouts([], [row('a', 'bad'), { kind: 'trade', data: {} }], 4, 'mint')).toEqual([]);
});
