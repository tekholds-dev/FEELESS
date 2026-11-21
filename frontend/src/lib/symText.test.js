import { symText, normSyms } from './symText';
test('🔤 a block-character symbol reads as a marked look-alike, a normal one is untouched', () => {
  expect(symText('███WIF')).toBe('≈WIF'); expect(symText('WIF')).toBe('WIF'); expect(symText('▇▇▇')).toBe('≈?'); expect(symText('BO​NK')).toBe('≈BONK');
  expect(symText('$MEW 🐱')).toBe('$MEW 🐱');   // emoji in a name stay (they are real letters to the coin)
  const d = normSyms({ cards: [{ legs: [{ symbol: '███WIF', mint: 'm1' }], parked: [{ symbol: 'OTC' }] }] });
  expect(d.cards[0].legs[0]).toEqual({ symbol: '≈WIF', mint: 'm1' }); expect(d.cards[0].parked[0].symbol).toBe('OTC');
});
