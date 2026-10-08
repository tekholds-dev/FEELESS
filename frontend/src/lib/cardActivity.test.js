import { cardActivity, SPARKS } from './cardActivity';

test('a card is as hot as its coins are moving right now, not as its profit', () => {
  expect(cardActivity([{ symbol: 'A', m5: 0.2 }, { symbol: 'B', m5: -0.4 }], 80)).toMatchObject({ heat: 0, word: 'calm', dir: 'flat', sparks: 0, top: null });
  expect(cardActivity([{ symbol: 'A', m5: 3 }, { symbol: 'B', m5: 2 }])).toMatchObject({ heat: 1, dir: 'up', movers: 1 });
  expect(cardActivity([{ symbol: 'A', m5: -6 }, { symbol: 'B', m5: -5 }])).toMatchObject({ heat: 2, dir: 'down', sparks: SPARKS[2] });
  const blaze = cardActivity([{ symbol: 'A', m5: 22 }, { symbol: 'B', m5: 9 }, { symbol: 'C', m5: -2 }]);
  expect(blaze.heat).toBe(3); expect(blaze.top).toEqual({ symbol: 'A', m5: 22 }); expect(blaze.beat).toBe(1);
});

test('one coin ripping lights a sleepy card; sold coins and missing readings never count', () => {
  expect(cardActivity([{ symbol: 'RUN', m5: 18 }, { symbol: 'B', m5: 0 }, { symbol: 'C', m5: 0 }, { symbol: 'D', m5: 0 }]).heat).toBe(2);
  expect(cardActivity([{ symbol: 'OUT', m5: 40, sold: true }, { symbol: 'B', m5: 0.1 }]).heat).toBe(0);
  expect(cardActivity([{ symbol: 'A' }, { symbol: 'B' }], -12)).toMatchObject({ heat: 0, dir: 'down' });   // no live reading: direction from the card's own result
  expect(cardActivity([], 0)).toMatchObject({ heat: 0, dir: 'flat', buying: false, locked: false });
});

test('buying and full-lock states are reported for their own effects', () => {
  expect(cardActivity([{ symbol: 'A', m5: 1, buying: true }, { symbol: 'B', m5: 1 }]).buying).toBe(true);
  expect(cardActivity([{ symbol: 'A', m5: 1, locked: true }, { symbol: 'B', m5: 1, locked: true }]).locked).toBe(true);
  expect(cardActivity([{ symbol: 'A', m5: 1, locked: true }, { symbol: 'B', m5: 1 }]).locked).toBe(false);
});
