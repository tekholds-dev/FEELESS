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

import { pickPeople, tagTop, clampTag, DEMO_PEOPLE } from './crowdMath';

test('each fight takes the next walkers\' worth of REAL people; the rest stay anonymous', () => {
  const ppl = [{ n: 1 }, { n: 2 }, { n: 3 }, { n: 4 }];
  expect(pickPeople(ppl, 0, 3)).toEqual([{ n: 1 }, { n: 2 }, { n: 3 }]);
  expect(pickPeople(ppl, 1, 3)).toEqual([{ n: 4 }, null, null]);
  expect(pickPeople([], 0, 3)).toEqual([null, null, null]);      // nobody real → nobody tagged, nothing invented
  expect(pickPeople(undefined, 1, 2)).toEqual([null, null]);
});

test('the line above a name is the last card they bought, else what brought them, else nothing', () => {
  expect(tagTop({ lastCard: 'Prime Diamond', why: 'holder' })).toBe('bought Prime Diamond');
  expect(tagTop({ lastCard: null, why: 'backer' })).toBe('backed a fight');
  expect(tagTop({ lastCard: null, why: 'holder' })).toBe(''); expect(tagTop(null)).toBe('');
  expect(clampTag(5, 300)).toBe(46); expect(clampTag(290, 300)).toBe(254); expect(clampTag(150, 300)).toBe(150);
  expect(DEMO_PEOPLE.every(p => p.demo && /^demo\./.test(p.name))).toBe(true);   // sample people are always marked demo
});

import { spreadTags } from './crowdMath';

test('tags are pushed apart (never overlapping) but stay inside the box and keep their order', () => {
  const o = spreadTags([150, 160, 170], 400, 100, 50);
  expect(o[1] - o[0]).toBeGreaterThanOrEqual(100); expect(o[2] - o[1]).toBeGreaterThanOrEqual(100); expect(o[0]).toBeGreaterThanOrEqual(50); expect(o[2]).toBeLessThanOrEqual(350);
  expect(spreadTags([60, 300], 400)).toEqual([60, 300]);                       // already apart: untouched
  const r = spreadTags([390, 380, 370], 400, 100, 50);                          // crowded at the right edge: shifted left, still ordered by walker
  expect(r[2]).toBeLessThan(r[1]); expect(r[1]).toBeLessThan(r[0]); expect(r[0]).toBeLessThanOrEqual(350);
});
