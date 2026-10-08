import { payRows } from './PayMap';

test('rows follow the hold order, skip empty buckets and size bars by $', () => {
  const m = { byHold: { '<5m': { n: 10, usd: -4, wonPct: 20, avgRet: -3 }, '30-60m': { n: 5, usd: 2, wonPct: 60, avgRet: 12 } }, byKind: { trim: { n: 4, usd: 3, wonPct: 75 }, whole: { n: 9, usd: -6, wonPct: 20 } } };
  const r = payRows(m);
  expect(r.hold.map(x => x.k)).toEqual(['<5m', '30-60m']);
  expect(r.hold[0].w).toBe(1); expect(r.hold[1].w).toBeCloseTo(0.5);
  expect(r.kind.map(x => x.k)).toEqual(['trim', 'whole']);
  expect(payRows(null)).toEqual({ hold: [], kind: [] });
});
