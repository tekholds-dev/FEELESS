import { legPair } from './FuseCard';
import { tokenImageUrls } from './terminal/MarketPrimitives';

const SOL = 'So11111111111111111111111111111111111111112';
test('card coin art: every leg shape resolves to a real coin logo chain (never empty)', () => {
  // My cards / Prime legs carry `mint` only
  expect(tokenImageUrls(legPair({ pairAddress: 'P', mint: 'MintA', symbol: 'A' }))[0]).toBe('/api/reputation/token-logo/MintA');
  // a SOL anchor (SOL is the base) still shows SOL
  expect(tokenImageUrls(legPair({ pairAddress: 'P', mint: SOL, baseAddress: SOL, quoteAddress: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', symbol: 'SOL' }))).toContain(`/api/reputation/token-logo/${SOL}`);
  // a pool leg with its own logo uses it first
  expect(tokenImageUrls(legPair({ baseAddress: 'MintB', quoteAddress: SOL, symbol: 'B', logo: 'https://x.test/b.png' }))[0]).toBe('https://x.test/b.png');
});

test('top-tier cards: real-time % is measured from what the card STARTED with (+ cash/parked), not re-based leg costs', () => {
  const { revalue } = require('./FuseCard');
  const r = { baseUsd: 100, extraUsd: 10, pnlPct: 5, legs: [{ pairAddress: 'P', tokens: 2, usd: 80, valueUsd: 80 }] };   // leg cost re-based at 80
  const live = new Map([['P', { price: 50 }]]);
  const out = revalue(r, live);
  expect(out.valueUsd).toBe(110); expect(out.pnlPct).toBeCloseTo(10); expect(out.costUsd).toBe(100);
  expect(revalue(r, new Map()).pnlPct).toBe(5);                                       // no live price yet → server number
});
