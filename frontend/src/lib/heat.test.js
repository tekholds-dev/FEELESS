import { heatScore } from './heat';

const p = (o = {}) => ({ txns: { m5: { buys: 40, sells: 20 } }, priceChange: { m5: 5, h1: 20 }, volume: { m5: 4000, h1: 12000 }, liquidity: { usd: 80000 }, ...o });

test('heat: buy pressure, momentum, pace, calls and snipers-out push up; thin pools sink', () => {
  const base = heatScore(p());
  expect(heatScore(p(), { calls: 3, snipersOut: true })).toBe(base + 12 + 15);
  expect(heatScore(p({ liquidity: { usd: 3000 } }))).toBe(base - 25);
  expect(heatScore(p({ txns: { m5: { buys: 10, sells: 50 } } }))).toBeLessThan(base);
  expect(heatScore(p({ priceChange: { m5: 500, h1: 9000 } }))).toBe(heatScore(p({ priceChange: { m5: 15, h1: 40 } })));   // capped
});
