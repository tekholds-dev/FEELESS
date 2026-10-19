import { chartTargets, readWords } from './FeeCatLive';

test('her charts show open trades first, then her next picks; her read is said in words', () => {
  const t = chartTargets([{ pairAddress: 'P1', symbol: 'A', currentChange: 4, setups: ['germ'], read: { germ: 3.2, hl: 2, ll: 0 } }],
    [{ pairAddress: 'P1', symbol: 'A' }, { pairAddress: 'P2', symbol: 'B', duo: { who: 'G4', action: 'BUY' } }]);
  expect(t.map(x => [x.kind, x.symbol])).toEqual([['open', 'A'], ['next', 'B']]);
  expect(readWords(t[0])).toEqual(['🦠 on its germ floor', 'germ +3.2%', '2 higher · 0 lower lows']);
  expect(readWords(t[1])).toEqual(['🤝 G4 said BUY']);
});
