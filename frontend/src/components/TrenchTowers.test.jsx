import { sparkPath } from './TrenchTowers';

test('🗼 a tower line is drawn only from real points: 2+ reads, ends up / down from where it started', () => {
  expect(sparkPath([1])).toBe(null); expect(sparkPath([])).toBe(null); expect(sparkPath([0, 0])).toBe(null);
  const up = sparkPath([1, 1.2, 1.1, 1.5]); expect(up.up).toBe(true); expect(up.move).toBeCloseTo(50); expect(up.line.startsWith('M0.0,')).toBe(true);
  const dn = sparkPath([2, 1.5, 1]); expect(dn.up).toBe(false); expect(dn.last[0]).toBe(160);
});
