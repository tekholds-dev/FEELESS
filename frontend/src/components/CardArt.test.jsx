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

test('card pricing math reads per coin: flat $/coin, capped % on small coins, normal % on big ones', () => {
  const { legFee, cardFee } = require('./FuseLab');
  const pr = { swapBps: 100, bundle: { on: true, perLegUsd: 0.5, maxPct: 20, maxLegUsd: 50 } };
  expect(legFee(0.39, pr)).toEqual({ fee: 0.39 * 0.2, why: '20% cap (small coin)' });     // $0.50 would be 128% of it
  expect(legFee(10, pr).fee).toBe(0.5); expect(legFee(100, pr).fee).toBe(1);               // flat · 1% over $50
  expect(cardFee([{ usd: 0.39 }, { usd: 0.39 }, { usd: 0.39 }], pr)).toBeCloseTo(0.234);   // the screenshot: 3 × $0.078
});
