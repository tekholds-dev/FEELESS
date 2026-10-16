
test('pulse adds net flow, average sizes, trades / min, whales and the price move of the minute', () => {
  const { pulse } = require('./TrenchPulse');
  const now = Date.parse('2026-10-16T00:01:00Z');
  const t = (s, kind, usd, price) => ({ ts: new Date(now - s * 1000).toISOString(), kind, usd, price, wallet: `${kind}${s}` });
  const p = pulse([t(50, 'buy', 600, 1), t(30, 'sell', 100, 1.05), t(10, 'buy', 50, 1.1)], now);
  expect(p.net).toBe(550); expect(p.tpm).toBe(3); expect(p.whalesB).toBe(1); expect(p.avgB).toBe(325);
  expect(p.pxMove).toBeCloseTo(10);
});
