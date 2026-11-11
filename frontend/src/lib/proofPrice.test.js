import { priceTip, priceWord } from './proofPrice';

test('a proof price reads plainly and never makes one up', () => {
  expect(priceWord({ usd: 0.0042, from: 'estimate' })).toBe('≈$0.0042 a proof');
  expect(priceWord({ usd: 0.31, from: 'its proofs', n: 3 })).toBe('≈$0.31 a proof');
  expect(priceWord({ usd: 0, from: 'local', minds: ['ossy', 'g4'] })).toBe('free on your machines');
  expect(priceWord({ usd: null })).toBe(''); expect(priceWord(undefined)).toBe('');
  expect(priceTip({ usd: 0.3, from: 'its proofs', n: 3 })).toContain('3 real bills');
});
