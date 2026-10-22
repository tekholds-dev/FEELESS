
test('real 24h: $1,000 at 7.3 % APY earns $0.20 a day, split fees vs rewards; a DEX pool with no APY gets no guess', () => {
  const { earn24, chartPaths } = require('./PoolHub');
  const e = earn24({ apy: 7.3, base: 3.65, reward: 3.65, tvl: 3_650_000 });
  expect(e.total).toBeCloseTo(0.2); expect(e.base).toBeCloseTo(0.1); expect(e.reward).toBeCloseTo(0.1); expect(e.poolDay).toBeCloseTo(730);
  expect(earn24({ apy: null, tvl: 5 })).toBeNull();
  const pts = Array.from({ length: 40 }, (_, i) => ({ t: i * 86400, tvl: 1000 + i * 10, apy: 5 + (i % 3) }));
  const c = chartPaths(pts, 30); expect(c.n).toBe(31); expect(c.area.startsWith('M0,160')).toBe(true); expect(chartPaths([pts[0]])).toBeNull();
});

test('🎯 range tuner math: v2 IL is the classic curve, a range loses more vs holding but earns ×factor while in range, out of range caps', () => {
  const { ilV2, ilRange, rangeFactor } = require('./PoolHub');
  expect(ilV2(1)).toBeCloseTo(0); expect(ilV2(2) * 100).toBeCloseTo(-5.72, 1); expect(ilV2(0.5) * 100).toBeCloseTo(-5.72, 1);
  expect(ilRange(1, 1.25)).toBeCloseTo(0);
  expect(ilRange(1.1, 1.25)).toBeLessThan(ilV2(1.1));               // concentrated = amplified IL inside the range
  expect(ilRange(2, 1.25)).toBeLessThan(ilV2(2));
  expect(ilRange(100, 1000)).toBeCloseTo(ilV2(100), 1);              // a huge range ≈ v2
  expect(rangeFactor(1.1)).toBeGreaterThan(20); expect(rangeFactor(2)).toBeCloseTo(3.41, 1);
});

test('🐱 FeeCat\'s combo: cash / SOL / fees legs from the live hub, blended APY and honest daily math', () => {
  const { catCombo } = require('./PoolHub');
  const rows = [{ id: 'l', kind: 'lend', stable: true, tvl: 4e8, apy: 6, sym: 'USDC', proto: 'Jupiter Lend' }, { id: 'l2', kind: 'lend', stable: true, tvl: 1e5, apy: 30, sym: 'USDC' },
    { id: 's', kind: 'stake', tvl: 1e9, apy: 7.5, sym: 'JITOSOL' }, { id: 'p', kind: 'v3', tvl: 5e6, apy: 40, base: 32, sym: 'SOL-USDC' }, { id: 'e', kind: 'v3', tvl: 5e6, apy: 150, base: 10, sym: 'FARM' }];
  const c = catCombo(rows, 100);
  expect(c.legs.map(l => l.r.id)).toEqual(['l', 's', 'p']);                      // tiny pool + emission farm skipped
  expect(c.apy).toBeCloseTo(0.5 * 6 + 0.3 * 7.5 + 0.2 * 40, 5);                  // 13.25 %
  expect(c.day).toBeCloseTo(100 * 13.25 / 100 / 365, 6);
  expect(catCombo([], 100).legs).toEqual([]);
});
