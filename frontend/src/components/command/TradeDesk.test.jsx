
test('a gas gauge reads the $ against that chain minimum: empty → 0, the minimum → a quarter, 4× → full', () => {
  const { gasFill } = require('./TradeDesk');
  expect(gasFill({ usd: 0, minUsd: 0.25 })).toBe(0); expect(gasFill({ usd: 0.25, minUsd: 0.25 })).toBe(0.25); expect(gasFill({ usd: 9, minUsd: 0.25 })).toBe(1); expect(gasFill({ usd: null })).toBe(0);
});
