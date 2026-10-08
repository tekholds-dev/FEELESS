import { crowdTargets, garmentPick, boneClass } from './crowdMath';

test('the crowd gathers under the leading card and spreads along the foot when level', () => {
  const a = crowdTargets('a', 8, 3), b = crowdTargets('b', 8, 3), lvl = crowdTargets('', 8, 3);
  expect(a.every(x => x < 0)).toBe(true);                       // a = the left card
  expect(b.every(x => x > 0)).toBe(true);                       // b = the right card
  expect(lvl[0]).toBeLessThan(0); expect(lvl[2]).toBeGreaterThan(0); expect(lvl).toEqual([...lvl].sort((p, q) => p - q));
});

test('garments are picked from the real body by bone class and height', () => {
  expect(boneClass('thigh_l')).toBe('leg'); expect(boneClass('upperarm_r')).toBe('arm'); expect(boneClass('ball_l')).toBe('foot'); expect(boneClass('index_02_l')).toBe('hand');
  expect(garmentPick('top', { arm: 0.21 }, 'spine', 0.7, 0)).toBe(true);
  expect(garmentPick('top', { arm: 0.21 }, 'spine', 0.4, 0)).toBe(false);          // below the hem
  expect(garmentPick('top', { arm: 0.21 }, 'arm', 0.75, 0.15)).toBe(true);          // a short sleeve …
  expect(garmentPick('top', { arm: 0.21 }, 'arm', 0.75, 0.3)).toBe(false);          // … ends before the forearm
  expect(garmentPick('pants', { minH: 0.065 }, 'leg', 0.3, 0.05)).toBe(true);
  expect(garmentPick('pants', { minH: 0.065 }, 'leg', 0.03, 0.05)).toBe(false);     // not over the ankle
  expect(garmentPick('shoes', {}, 'foot', 0.02, 0.05)).toBe(true);
});
