import { ema, vwap, bollinger, rsi } from './indicators';

const B = Array.from({ length: 30 }, (_, i) => ({ time: i, open: 100 + i, high: 101 + i, low: 99 + i, close: 100 + i, volume: 10 }));

test('📐 EMA starts at the SMA once the window is full, then weights the newest close', () => {
  const e = ema(B, 9);
  expect(e[0]).toEqual({ time: 8, value: 104 }); expect(e).toHaveLength(22); expect(e[1].value).toBeCloseTo(105, 6); expect(ema(B.slice(0, 5), 9)).toEqual([]);
});

test('📐 VWAP, Bollinger and RSI on true candles', () => {
  const v = vwap(B); expect(v[0].value).toBeCloseTo(100); expect(v[29].value).toBeCloseTo(114.5);
  const bb = bollinger(B, 20, 2); expect(bb.mid[0]).toEqual({ time: 19, value: 109.5 }); expect(bb.upper[0].value - bb.mid[0].value).toBeCloseTo(2 * Math.sqrt(33.25), 6);
  expect(rsi(B, 14).every(x => x.value === 100)).toBe(true);                                             // only up-closes
  const zig = Array.from({ length: 40 }, (_, i) => ({ time: i, close: 100 + (i % 2 ? 1 : -1), high: 0, low: 0 }));
  const r = rsi(zig, 14); expect(r[r.length - 1].value).toBeGreaterThan(40); expect(r[r.length - 1].value).toBeLessThan(60); expect(rsi(B.slice(0, 10), 14)).toEqual([]);
});
