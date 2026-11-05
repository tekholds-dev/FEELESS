import { depositQuote } from './depositQuote';
test('every deposit pays the one rate and all of it goes to the Collective', () => {
  expect(depositQuote(50, true)).toMatchObject({ ratePct: 10, collectiveUsd: 5, restUsd: 45 }); expect(depositQuote(20, false)).toMatchObject({ ratePct: 10, collectiveUsd: 2, restUsd: 18 });
  expect(depositQuote(100, false, false, 7).collectiveUsd).toBe(7); expect(depositQuote(40, true).belowFirst).toBe(true); expect(depositQuote(1, true, true)).toMatchObject({ ratePct: 0, restUsd: 1 });
  expect(depositQuote(20, false).feelessUsd).toBeUndefined();
});
