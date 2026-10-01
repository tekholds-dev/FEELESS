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

test('position panel: total P&L = realized + unrealized from your entry', () => {
  const { pnlSummary } = require('./position');
  // owner's PAID buy: $1.15125 all-in for 103.9455, worth $1.18 now → up about 2.5%, never down because SOL moved
  const s = pnlSummary({ tokensHeld: 103.9455, avgEntry: 1.15125 / 103.9455, investedUsd: 1.15125 }, 1.18 / 103.9455);
  expect(s.value).toBeCloseTo(1.18); expect(s.pnl).toBeCloseTo(0.02875); expect(s.pct).toBeCloseTo(2.497, 2);
  // bought $10 of 1000, sold 500 for $8 (+$3 realized), 500 left now worth $4 (−$1 unrealized) → +$2 = +20%
  const t = pnlSummary({ tokensHeld: 500, avgEntry: 0.01, investedUsd: 10, soldUsd: 8, realizedUsd: 3 }, 0.008);
  expect(t.pnl).toBeCloseTo(2); expect(t.pct).toBeCloseTo(20); expect(t.sold).toBe(8); expect(t.value).toBeCloseTo(4);
});

test('a fresh buy starts at $0 P&L on its fill price (fees paid in the background, no break-even)', () => {
  const { pnlSummary } = require('./position');
  // paid $10.25 all-in (incl. $0.25 fees) for 1000 tokens that filled at $0.01
  const s = pnlSummary({ tokensHeld: 1000, avgEntry: 0.01025, fillPrice: 0.01, investedUsd: 10 }, 0.01);
  expect(s.entry).toBe(0.01); expect(s.pnl).toBeCloseTo(0); expect(s.pct).toBeCloseTo(0);
  const up = pnlSummary({ tokensHeld: 1000, avgEntry: 0.01025, fillPrice: 0.01, investedUsd: 10 }, 0.011);
  expect(up.pnl).toBeCloseTo(1); expect(up.pct).toBeCloseTo(10);   // real time: +10% the moment price is 10% over entry
});
