import { genRisk, tug, dedupeAutopsies, readAs, missedWord, dropFrac } from './lifeLens';

test('life left = how close a generation is to replacement', () => {
  expect(genRisk({ net: -27, replaceAt: 3, probationAt: 2 })).toMatchObject({ frac: 0, word: 'SAFE', tone: 'is-good' });
  expect(genRisk({ net: 2, replaceAt: 3, probationAt: 2 })).toMatchObject({ word: 'ON THE EDGE', tone: 'is-bad' });
  expect(genRisk({ net: 3, replaceAt: 3 }).frac).toBe(1);
  expect(genRisk({}).word).toBe('NO RECORD');
  expect(tug({ winsAttributed: 27, lossesAttributed: 8 }).share).toBeCloseTo(27 / 35);
  expect(tug({})).toBeNull();
});

test('one rug = one card, the one that knows the 60-min result, newest first', () => {
  const rows = dedupeAutopsies([{ sym: 'Hugo', calledAt: 100, p5: -53, p60: null }, { sym: 'Hugo', calledAt: 100, p5: -53, p60: -68 }, { sym: 'Cul', calledAt: 50, p5: -59 }]);
  expect(rows.map(r => [r.sym, r.p60])).toEqual([['Hugo', -68], ['Cul', undefined]]);
  expect(readAs('$X rugged (-53% in 5 min) — we read it as: a, b, c, d')).toEqual(['a', 'b', 'c']);
  expect(missedWord('pad:pump:migrated')).toBe('launchpad pump:migrated');
  expect(missedWord('crowd_real')).toBe('crowd real');
  expect(dropFrac(-68)).toBeCloseTo(0.68); expect(dropFrac(null)).toBe(0);
});
