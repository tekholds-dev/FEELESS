import { decide, replay, targetWidth, realizedVol, marketState, inRangeOdds, moveCost, projection, ilRange, closes } from './autoRange';

const T0 = 1_800_000_000;
const bars = (fn, n = 120) => Array.from({ length: n }, (_, i) => { const c = fn(i); return [T0 + i * 900, c, c * 1.001, c * 0.999, c, 0]; });
const calm = bars(i => 1 + 0.004 * Math.sin(i / 3));
const wild = bars(i => (i % 2 ? 1.25 : 0.8));
const rising = bars(i => 1 + i * 0.004 + 0.002 * Math.sin(i));

test('📏 volatility + state come from the candles themselves; widths stay inside each strategy', () => {
  expect(realizedVol(closes(calm))).toBeLessThan(0.2); expect(marketState(closes(wild)).state).toBe('WILD');
  expect(marketState(closes(rising)).state).toBe('RISING'); expect(marketState(closes(calm.slice(0, 5))).state).toBe('READING');
  expect(targetWidth(0.01, 'tight')).toBe(2); expect(targetWidth(5, 'balanced')).toBe(15); expect(targetWidth(0.4, 'aggressive')).toBe(88);
  expect(inRangeOdds(50, 0.05)).toBeGreaterThan(0.99); expect(inRangeOdds(1, 1)).toBeLessThan(0.05);
});

test('🤖 the engine only moves when 24h of fees beat the move — waits out a wick, pauses when no band survives', () => {
  const base = { amt: 100, rate: 0.01, candles: calm, strat: 'balanced', now: 1e12 };
  expect(decide({ ...base, price: 1, band: null }).action).toBe('OPEN');
  expect(decide({ ...base, price: 1.0, band: { lo: 0.95, hi: 1.05 } }).action).toBe('HOLD');
  const out = { ...base, price: 1.2, band: { lo: 0.95, hi: 1.05 } };
  expect(decide({ ...out, outSince: 1e12 - 60000 }).action).toBe('HOLD');                  // 1 min out < 15 min wait
  expect(decide({ ...out, outSince: 1e12 - 20 * 60000 }).action).toBe('RECENTER');
  expect(decide({ ...out, amt: 1, rate: 0.0001, outSince: 1e12 - 20 * 60000 }).action).toBe('HOLD');   // $1 at a dead pool: the move costs more
  expect(decide({ ...base, candles: wild, price: 1, band: { lo: 0.9, hi: 1.1 } }).action).toBe('PAUSE');
  expect(decide({ ...base, price: 1, band: { lo: 0.5, hi: 2 } }).action).toBe('TIGHTEN');
  expect(moveCost(100)).toBeCloseTo(0.16);
});

test('🔁 replay runs the same rules on real-shaped candles: fees only in range, moves cost money, the books add up', () => {
  const r = replay(rising, { amt: 5, rate: 0.01, strat: 'balanced' });
  expect(r.bars).toBe(104); expect(r.moves).toBeGreaterThan(0); expect(r.fees).toBeGreaterThan(0); expect(r.costs).toBeGreaterThan(0);
  expect(r.end).toBeCloseTo(r.start + r.fees - r.costs + r.il + r.drift, 6);
  expect(replay(calm.slice(0, 10), {})).toBe(null);
});

test('📐 projection: a 50/50 band at 0 move keeps its $ + a day of fees; −20% loses more than IL alone', () => {
  const p = projection(1, 0.1, 10, 5, 0.01);
  expect(p.base.value).toBeGreaterThan(5); expect(p.dn.value).toBeLessThan(5 * 0.9 * (1 + ilRange(0.8, 1.1)) + 0.0001 + 5 * 0.9);
  expect(p.pts[0].up).toBe(1); expect(p.pts[5].up).toBeGreaterThan(p.pts[1].up);
});
