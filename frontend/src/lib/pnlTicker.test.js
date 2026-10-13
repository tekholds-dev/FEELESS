import { tickHeat } from './pnlTicker';

test('a real tick is classified by how far it moved; nothing known = calm', () => {
  expect(tickHeat(1, 1.001)).toMatchObject({ heat: 0, dir: 1 });
  expect(tickHeat(1, 1.005).heat).toBe(1); expect(tickHeat(1, 0.985)).toMatchObject({ heat: 2, dir: -1 }); expect(tickHeat(1, 1.05).heat).toBe(3);
  expect(tickHeat(null, 1)).toEqual({ heat: 0, dir: 0, pct: 0 }); expect(tickHeat(2, 2)).toEqual({ heat: 0, dir: 0, pct: 0 });
});
