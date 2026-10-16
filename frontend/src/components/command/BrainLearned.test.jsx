import { germBars } from './BrainLearned';
import { sideBySide } from './AiPlayground';
import { vitalTiles } from '../../lib/vitalBoard';

test('germ record bars rank the best bucket first', () => {
  const b = germBars({ 'off the germ': { n: 4, med: -6, won: 25 }, 'at the germ': { n: 5, med: 8.2, won: 80 } });
  expect(b[0].k).toBe('at the germ'); expect(b[1].won).toBe(25);
});

test('side by side pairs removed and added lines', () => {
  const r = sideBySide('--- a\n+++ b\n@@ -1 +1 @@\n x = 1\n-y = 2\n+y = 3\n+z = 4');
  expect(r.find(x => x[2] === 'chg')).toEqual(['y = 2', 'y = 3', 'chg']);
  expect(r.find(x => x[2] === 'add')).toEqual([null, 'z = 4', 'add']);
});

test('the vital board reads the germ floor and the gun line', () => {
  const t = vitalTiles({ vit: { germ: 'floor', germD: 6, germ5: 'near', hiD: 2 } });
  expect(t.find(x => x.key === 'germ').tone).toBe('good');
  expect(t.find(x => x.key === 'gun').tone).toBe('bad');
});
