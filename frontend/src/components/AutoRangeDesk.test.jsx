import { bandChart } from './AutoRangeDesk';
import { replay } from '../lib/autoRange';

const bars = Array.from({ length: 140 }, (_, i) => { const c = 1 + i * 0.003 + 0.01 * Math.sin(i / 4); return [1_800_000_000 + i * 900, c, c * 1.002, c * 0.998, c, 0]; });

test('🤖 the band chart draws real candles + the replayed bands, with a marker on every re-center', () => {
  const r = replay(bars, { amt: 5, rate: 0.01, strat: 'tight' });
  const c = bandChart(bars, r.path, 600, 220, 1.5);
  expect(c.candles).toHaveLength(120); expect(c.upper.startsWith('M')).toBe(true); expect(c.fill.endsWith('Z')).toBe(true);
  expect(c.moves.length).toBeGreaterThan(0); expect(c.last).toBe(1.5); expect(c.ticks).toHaveLength(5);
  expect(bandChart(bars.slice(0, 1), [], 600, 220)).toBe(null);
});
