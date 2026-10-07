jest.mock('./FuseCard', () => ({ LiveFuseCard: () => null, revalue: r => r }));

test('prime league shows the real card + the one best paper card; the rest fold; no real card = all show', () => {
  const { primeGroups } = require('./ArenaPrime');
  const cards = [{ tpl: 'a', pnlPct: -5 }, { tpl: 'real', real: true, pnlPct: -60 }, { tpl: 'b', pnlPct: 28 }, { tpl: 'c', pnlPct: 3 }];
  const [shown, rest] = primeGroups(cards);
  expect(shown.map(c => c.tpl)).toEqual(['real', 'b']); expect(rest.map(c => c.tpl)).toEqual(['a', 'c']);
  expect(primeGroups(cards.filter(c => !c.real))).toEqual([cards.filter(c => !c.real)]);
  expect(primeGroups([{ tpl: 'real', real: true }, { tpl: 'b' }]).length).toBe(1); expect(primeGroups(null)).toEqual([[]]);
});
