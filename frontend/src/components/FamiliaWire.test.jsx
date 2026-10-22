import { blipAt } from './Crews';
import { tug } from './FamilyWars';

test('the wire: a newer event sits nearer the middle; a fresh one (< 1h) breathes; every blip stays inside the scope', () => {
  const now = 1_000_000;
  const d = p => Math.hypot(p.x - 100, p.y - 100);
  const fresh = blipAt({ kind: 'crown', id: 1, at: now - 60 }, now); const old = blipAt({ kind: 'crown', id: 1, at: now - 6 * 86400 }, now);
  expect(d(fresh)).toBeLessThan(d(old)); expect(fresh.fresh).toBe(true); expect(old.fresh).toBe(false);
  expect(d(blipAt({ kind: 'launch', id: 9, at: now - 99 * 86400 }, now))).toBeLessThanOrEqual(88.1);
});

test('the war rope leans to the family trading better and never leaves the track', () => {
  expect(tug({ a: { pct: 6.4 }, b: { pct: 2.1 } })).toBeCloseTo(0.6075); expect(tug(null)).toBe(0.5);
  expect(tug({ a: { pct: 90 }, b: { pct: -90 } })).toBe(0.94); expect(tug({ a: { pct: -90 }, b: { pct: 90 } })).toBe(0.06);
});

test('the fuse ladder fills each family toward its next bracket; the top bracket is full', () => {
  const { nextBand } = require('./FamilyFuseBoard');
  const B = [{ from: 0 }, { from: 1100 }, { from: 1250 }, { from: 1400 }];
  expect(nextBand(1000, B)).toBeCloseTo(1000 / 1100); expect(nextBand(1175, B)).toBeCloseTo(0.5); expect(nextBand(1500, B)).toBe(1);
});
