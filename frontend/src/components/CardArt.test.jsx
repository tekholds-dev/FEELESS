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
