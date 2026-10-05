import { cardChoice, keepChoice } from './cardChoice';

const pricing = { prepay: { on: true, perSwapUsd: 0.05, swapsPerRound: 2, rounds: 5, swaps: 10, usd: 0.5 }, rounds: { per5Usd: 0.25 } };

test('buyer choice price mirrors the server: packs beyond the free 5 + swaps, or $0 on the free rounds', () => {
  expect(cardChoice({}, pricing)).toMatchObject({ chosen: false, usd: 0.5, swaps: 10 });           // no pick → HQ default, as before
  expect(cardChoice({ rounds: 20, swapsPerRound: 3, payUpfront: true }, pricing)).toMatchObject({ chosen: true, packs: 3, roundsUsd: 0.75, swaps: 60, swapsUsd: 3, usd: 3.75 });
  expect(cardChoice({ rounds: 20, swapsPerRound: 3, payUpfront: false }, pricing)).toMatchObject({ usd: 0, swapsPerRound: 3 });
  expect(cardChoice({ rounds: 7, swapsPerRound: 9, payUpfront: true }, pricing)).toMatchObject({ rounds: 5, swapsPerRound: 1, usd: 0.25 });
  expect(cardChoice({ rounds: 10 }, { ...pricing, prepay: { ...pricing.prepay, on: false } }).usd).toBe(0.25);
});

test('a risk dial change keeps what the buyer picked', () => {
  expect(keepChoice({ risk: 'safe', rounds: 20, payUpfront: false, legs: {} })).toEqual({ rounds: 20, payUpfront: false });
  expect(keepChoice({ risk: 'safe' })).toEqual({});
});
