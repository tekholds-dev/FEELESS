import { depositQuote, smallCount } from './depositQuote';
test('10% first and at $50, 5% under, every 3rd under is 10%, half and half, staff free', () => {
  expect(depositQuote(50, true, 0)).toMatchObject({ ratePct: 10, feelessUsd: 2.5, collectiveUsd: 2.5, restUsd: 45 }); expect(depositQuote(40, true, 0).belowFirst).toBe(true);
  expect(depositQuote(20, false, 0).ratePct).toBe(5); expect(depositQuote(20, false, 1)).toMatchObject({ ratePct: 5, nextIsThird: true }); expect(depositQuote(20, false, 2)).toMatchObject({ ratePct: 10, third: true }); expect(depositQuote(50, false, 2).ratePct).toBe(10);
  expect(depositQuote(1, true, 0, true)).toMatchObject({ ratePct: 0, restUsd: 1 }); expect(smallCount([{ usd: 50 }, { usd: 10 }, { usd: 60 }])).toBe(1);
});
