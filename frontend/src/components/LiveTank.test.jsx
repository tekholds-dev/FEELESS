import { place } from './LiveTank';

test('🫧 a launch floats by its real numbers: across = age (newest right), up = market cap (log $2K…$100K), colour = curve progress', () => {
  const now = 1_800_000_000_000;
  const a = place({ marketCapUsd: 2000, at: now, devBuySol: 0, curveProgress: 0 }, now);
  expect(a.x).toBe(1); expect(a.y).toBe(0); expect(a.r).toBe(6); expect(a.p).toBe(0);
  const b = place({ marketCapUsd: 100000, at: now - 5 * 60000, devBuySol: 1, curveProgress: 80 }, now);
  expect(b.x).toBeCloseTo(0.5); expect(b.y).toBeCloseTo(1); expect(b.r).toBe(15); expect(b.p).toBe(0.8);
  expect(place({ marketCapUsd: 1e9, at: now - 1e9, curveProgress: 500 }, now)).toMatchObject({ x: 0, y: 1, p: 1 });
});
