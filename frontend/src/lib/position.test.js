import { applyFill } from './position';

test('a confirmed buy opens / averages the position instantly and a sell books realized P&L', () => {
  const a = applyFill(null, { side: 'buy', tokens: 5000, usd: 15, signature: 's1' });
  expect(a.avgEntry).toBeCloseTo(0.003); expect(a.tokensHeld).toBe(5000); expect(a.pending).toBe(true);
  const b = applyFill(a, { side: 'buy', tokens: 5000, usd: 25, signature: 's2' });
  expect(b.avgEntry).toBeCloseTo(0.004); expect(b.tokensHeld).toBe(10000);
  const c = applyFill(b, { side: 'sell', tokens: 2500, usd: 15, signature: 's3' });
  expect(c.tokensHeld).toBe(7500); expect(c.realizedUsd).toBeCloseTo(5); expect(c.trades.at(-1).pnlUsd).toBeCloseTo(5);
  expect(applyFill(c, { side: 'sell', tokens: 1, usd: 1, signature: 's3' })).toBe(c);   // same tx twice: no double count
  expect(applyFill(c, { side: 'buy', usd: 5, signature: 's4' })).toBe(c);                // unknown size: wait for the server
});
