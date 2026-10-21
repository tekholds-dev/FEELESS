import { territories, strength, DISTRICTS } from './FamilyMap';
import { landingNumbers } from './FamilyLanding';

test('the city: board order holds districts, the rest unclaimed, my turf + wars marked', () => {
  const rows = [{ id: 'a', tag: 'A', members: 5, active: 3, pct: 20, badge: { c1: '#111111' } }, { id: 'b', tag: 'B', members: 2, active: 0, pct: -5 }];
  const t = territories(rows, 'b', [{ state: 'live', a: { id: 'a' }, b: { id: 'b' } }]);
  expect(t).toHaveLength(DISTRICTS.length);
  expect(t[0].owner.id).toBe('a'); expect(t[0].color).toBe('#111111'); expect(t[0].h).toBe(1);
  expect(t[1].mine).toBe(true); expect(t[0].war && t[1].war).toBe(true); expect(t[2].owner).toBeNull();
  expect(strength({ members: 1 })).toBe(4);
});

test('landing numbers read the board, the live feed and the war room', () => {
  const n = landingNumbers({ board: [{ members: 3 }, { members: 2 }] }, { vitals: { members: 5 } }, { wars: [{ state: 'live', pot: 300 }, { state: 'done', pot: 50 }, { state: 'set', pot: 100 }] });
  expect(n).toEqual([['FAMILIES', 2], ['MEMBERS', 5], ['WARS LIVE', 1], ['POINTS AT STAKE', 400]]);
});
