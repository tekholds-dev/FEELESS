
test('🦠 purple germ bubble: a coin within −3…+10% of its germ floor, read from any lens on file; none on file = no purple', () => {
  const { intakeDots, germOf } = require('./intakeBand');
  expect(germOf({ chart: { germDist: 4.2 } })).toBe(4.2); expect(germOf({ germ5Dist: -1 })).toBe(-1); expect(germOf({})).toBe(null);
  const d = intakeDots([{ mint: 'A', symbol: 'A', cap: 50000, status: 'TRACKING', germDist: 3 }, { mint: 'B', symbol: 'B', cap: 50000, status: 'TRACKING', germDist: 40 }, { mint: 'C', symbol: 'C', cap: 50000, status: 'TRACKING' }]);
  const by = Object.fromEntries(d.map(x => [x.mint, x.atGerm]));
  expect(by).toEqual({ A: true, B: false, C: false });
});
