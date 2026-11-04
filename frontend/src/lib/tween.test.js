import { tweenClose, mergeLiveBar } from './tween';

test('the 30fps candle ease starts where it is drawn and ends EXACTLY on the real tick, never past it', () => {
  expect(tweenClose(1, 2, 0)).toBe(1);
  expect(tweenClose(1, 2, 1)).toBe(2); expect(tweenClose(1, 2, 3)).toBe(2);
  const mid = tweenClose(1, 2, 0.5); expect(mid).toBeGreaterThan(1.5); expect(mid).toBeLessThan(2);   // ease-out: most of the move early
  expect(tweenClose(2, 1, 0.5)).toBeLessThan(1.5);
  expect(tweenClose(NaN, 3, 0.2)).toBe(3);
});

test('a history reload keeps the live forming candle: same bucket merged, a newer bucket appended, another pool / timeframe untouched', () => {
  const bars = [{ time: 60, open: 1, high: 1.2, low: 0.9, close: 1.1 }, { time: 120, open: 1.1, high: 1.15, low: 1.05, close: 1.1 }];
  const lb = { time: 120, open: 1.1, high: 1.3, low: 1.08, close: 1.28, iv: '1m', pool: 'P' };
  expect(mergeLiveBar(bars, lb, '1m', 'P')[1]).toEqual({ time: 120, open: 1.1, high: 1.3, low: 1.05, close: 1.28 });
  expect(mergeLiveBar(bars, { ...lb, time: 180 }, '1m', 'P')).toHaveLength(3);
  expect(mergeLiveBar(bars, lb, '5m', 'P')).toEqual(bars); expect(mergeLiveBar(bars, lb, '1m', 'Q')).toEqual(bars);
  expect(mergeLiveBar(bars, { ...lb, time: 60 }, '1m', 'P')).toEqual(bars);   // an older live bar never rewrites history
});

test('🕯 a new candle starts at the first new price: never a flat bar at the old close, never a filled minute', () => {
  const { liveBar } = require('./tween');
  const last = { time: 1000, open: 1, high: 1, low: 1, close: 1 };
  expect(liveBar(last, 2, 1600)).toEqual({ time: 1600, open: 2, high: 2, low: 2, close: 2 });
  expect(liveBar(last, 1.1, 1060)).toEqual({ time: 1060, open: 1.1, high: 1.1, low: 1.1, close: 1.1 });
  expect(liveBar(last, 1, 1060)).toBeNull();                                  // a quiet minute draws nothing
  expect(liveBar(last, 1.2, 1000)).toEqual({ ...last, high: 1.2, close: 1.2 });
  expect(liveBar(null, 1, 1)).toBeNull();
});

test('🕯 the forming candle is never eased: the chart draws each real tick at once (no in-between prices)', () => {
  const src = require('fs').readFileSync(require('path').join(__dirname, '../components/terminal/PriceChart.jsx'), 'utf8');
  expect(src).not.toMatch(/tweenClose|requestAnimationFrame\(draw\)/);
  expect(src).toMatch(/ref\.series\.update\(bar\); shownRef\.current = value;/);
});
