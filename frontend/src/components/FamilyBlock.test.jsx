import { heightOf, liveStash, LOOK } from './FamilyBlock';

test('store heights grow with level; a park is flat', () => {
  expect(heightOf('tower', 5)).toBeGreaterThan(heightOf('tower', 1));
  expect(heightOf('park', 3)).toBe(0);
  expect(Object.keys(LOOK)).toContain('casino');
});

test('the stash ticks up at the store rate between reads, capped', () => {
  expect(liveStash({ stash: 10, rate: 3600, stashCap: 100, _at: 0 }, 5)).toBe(15);
  expect(liveStash({ stash: 10, rate: 3600, stashCap: 100, _at: 0 }, 500)).toBe(100);
});
