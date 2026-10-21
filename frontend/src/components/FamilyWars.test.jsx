import { clockWord, tug } from './FamilyWars';

test('clockWord reads a countdown', () => {
  expect(clockWord(3 * 86400 + 3600)).toBe('3d 1h');
  expect(clockWord(3725)).toBe('1h 2m');
  expect(clockWord(42)).toBe('42s');
});

test('tug leans to the side winning, even when one side has not traded', () => {
  expect(tug({ a: { pct: 10 }, b: { pct: -10 } })).toBeGreaterThan(0.9);
  expect(tug({ a: { pct: null }, b: { pct: null } })).toBe(0.5);
  expect(tug({ a: { pct: 2 }, b: { pct: null } })).toBeGreaterThan(0.5);
});
