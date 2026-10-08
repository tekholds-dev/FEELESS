import { chartPulse, pulseCall, TF_WINDOW } from './chartPulse';

const run = (from, step, n, vol = () => 100) => Array.from({ length: n }, (_, i) => { const o = from + step * i; const c = o + step; return [i * 60, o, Math.max(o, c) * 1.001, Math.min(o, c) * 0.999, c, vol(i)]; });

test('a steady climb reads as pushing highs, at the top of its range', () => {
  const p = chartPulse(run(100, 1, 30));
  expect(p.pos).toBeGreaterThanOrEqual(95); expect(p.greens).toBe(10); expect(p.streak).toBe(30); expect(p.offHigh).toBeLessThan(1);
  expect(p.call).toEqual(['🚀', 'PUSHING HIGHS', 'good']); expect(p.move).toBeGreaterThan(25);
});

test('the same climb on drying volume says so', () => {
  const p = chartPulse(run(100, 1, 30, i => (i >= 25 ? 10 : 100)));
  expect(p.volX).toBe(0.1); expect(p.call[1]).toBe('HIGHS ON FADING VOLUME');
});

test('a long slide off the high reads as sliding', () => {
  const p = chartPulse([...run(100, 2, 10), ...run(120, -2, 20)]);
  expect(p.offHigh).toBeGreaterThanOrEqual(20); expect(p.streak).toBe(-20); expect(p.call).toEqual(['🔪', 'SLIDING', 'bad']);
});

test('too few or broken candles give no read, and the call copes with nothing', () => {
  expect(chartPulse(run(100, 1, 5))).toBeNull(); expect(chartPulse(null)).toBeNull(); expect(chartPulse([[1, 0, 0, 0, 0, 0], 'x'])).toBeNull();
  expect(pulseCall(null)[1]).toBe('NO CHART');
  expect(pulseCall({ pos: 50, greens: 5, streak: 1, offHigh: 2, offLow: 2, volX: 1, swing: 3 })[1]).toBe('FLAT');
  expect(pulseCall({ pos: 25, greens: 5, streak: 3, offHigh: 30, offLow: 6, volX: 1, swing: 40 })[1]).toBe('TURNING UP');
});

test('each chart timeframe has the flow window that fits it', () => { expect(TF_WINDOW).toEqual({ '1m': '5m', '5m': '1h', '15m': '6h', '1h': '24h' }); });
