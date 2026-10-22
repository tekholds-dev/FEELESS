
test('real 24h: $1,000 at 7.3 % APY earns $0.20 a day, split fees vs rewards; a DEX pool with no APY gets no guess', () => {
  const { earn24, chartPaths } = require('./PoolHub');
  const e = earn24({ apy: 7.3, base: 3.65, reward: 3.65, tvl: 3_650_000 });
  expect(e.total).toBeCloseTo(0.2); expect(e.base).toBeCloseTo(0.1); expect(e.reward).toBeCloseTo(0.1); expect(e.poolDay).toBeCloseTo(730);
  expect(earn24({ apy: null, tvl: 5 })).toBeNull();
  const pts = Array.from({ length: 40 }, (_, i) => ({ t: i * 86400, tvl: 1000 + i * 10, apy: 5 + (i % 3) }));
  const c = chartPaths(pts, 30); expect(c.n).toBe(31); expect(c.area.startsWith('M0,160')).toBe(true); expect(chartPaths([pts[0]])).toBeNull();
});
