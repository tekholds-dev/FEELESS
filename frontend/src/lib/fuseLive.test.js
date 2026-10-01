import { liveRowPnl, liveBook, liveStagePct } from './fuseLive';

const live = new Map([['P1', { price: 3 }], ['P2', { price: 0.5 }]]);

test('a card revalues live: held × live price + taken out, vs cost', () => {
  const r = { costUsd: 150, legs: [{ pairAddress: 'P1', tokens: 50, usd: 100, heldUsd: 100 }, { pairAddress: 'P2', tokens: 0, usd: 50, soldUsd: 70 }] };
  expect(liveRowPnl(r, live)).toMatchObject({ value: 220, pnlUsd: 70 });
  expect(liveRowPnl(r, new Map()).value).toBe(170);                                   // no live price → server value
  expect(liveBook([r, r], live).pnlPct).toBeCloseTo(46.67, 1);
});

test('stage cards: lit = avg move from entry, mega = weighted index vs base, missing prices → null', () => {
  expect(liveStagePct({ kind: 'lit', legs: [{ pairAddress: 'P1', entry: 2 }, { pairAddress: 'P2', entry: 1 }] }, live)).toBeCloseTo(0);   // +50% and −50%
  expect(liveStagePct({ kind: 'mega', legs: [{ pairAddress: 'P1', base: 2, weight: 75 }, { pairAddress: 'P2', base: 1, weight: 25 }] }, live)).toBeCloseTo(25);
  expect(liveStagePct({ kind: 'round', legs: [{ pairAddress: 'X', entry: 1 }] }, live)).toBeNull();
});
