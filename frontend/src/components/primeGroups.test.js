jest.mock('./FuseCard', () => ({ LiveFuseCard: () => null, revalue: r => r }));

test('prime league shows the real card + the one best paper card; the rest fold; no real card = all show', () => {
  const { primeGroups } = require('./ArenaPrime');
  const cards = [{ tpl: 'a', pnlPct: -5 }, { tpl: 'real', real: true, pnlPct: -60 }, { tpl: 'b', pnlPct: 28 }, { tpl: 'c', pnlPct: 3 }];
  const [shown, rest] = primeGroups(cards);
  expect(shown.map(c => c.tpl)).toEqual(['real', 'b']); expect(rest.map(c => c.tpl)).toEqual(['a', 'c']);
  expect(primeGroups(cards.filter(c => !c.real))).toEqual([cards.filter(c => !c.real)]);
  expect(primeGroups([{ tpl: 'real', real: true }, { tpl: 'b' }]).length).toBe(1); expect(primeGroups(null)).toEqual([[]]);
});

test('league table ranks every tier card best first and keeps the real flag', () => {
  const { standings } = require('./ArenaPrime');
  const mk = (tpl, tier, pct, real) => ({ id: tpl, tpl, tier, label: tpl, real, startUsd: 20, valueUsd: 20 * (1 + pct / 100), legs: [], math: real ? { pnlUsd: 20 * pct / 100 } : undefined, cardFeesUsd: real ? 0 : undefined, realBook: real ? { fundedUsd: 20 } : undefined });
  const rows = standings([mk('degen', 'blaze', -60, true), mk('safe', 'diamond', 12, false), mk('next', 'next', 30, false)], new Map());
  expect(rows.map(r => [r.rank, r.tpl, r.real, Math.round(r.pct)])).toEqual([[1, 'next', false, 30], [2, 'safe', false, 12], [3, 'degen', true, -60]]);
  expect(standings(null)).toEqual([]);
});
