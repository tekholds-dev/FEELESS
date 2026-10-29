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

test('a stale history never makes one fake candle from an old close to the live price: the candle opens at the first real tick', () => {
  const { liveBar } = require('./tween');
  const last = { time: 1000, open: 1, high: 1, low: 1, close: 1 };
  const stale = liveBar(last, 2, 1000 + 60 * 10, 60);                      // 10 minutes behind, price doubled
  expect(stale.fill).toEqual([]); expect(stale.bar).toEqual({ time: 1600, open: 2, high: 2, low: 2, close: 2 });
  const fresh = liveBar(last, 1.1, 1120, 60);                                // 2 buckets behind: a real continuation
  expect(fresh.fill).toHaveLength(1); expect(fresh.bar.open).toBe(1); expect(fresh.bar.close).toBe(1.1);
  expect(liveBar(last, 1.2, 1000, 60).bar).toEqual({ ...last, high: 1.2, close: 1.2 });
});

test('🕯 the forming candle is never eased: the chart draws each real tick at once (no in-between prices)', () => {
  const src = require('fs').readFileSync(require('path').join(__dirname, '../components/terminal/PriceChart.jsx'), 'utf8');
  expect(src).not.toMatch(/tweenClose|requestAnimationFrame\(draw\)/);
  expect(src).toMatch(/ref\.series\.update\(bar\); shownRef\.current = value;/);
});

test('🕯 the candle clock opens the next candle ON TIME at the previous close; nothing to roll in the same bucket or over a stale history', () => {
  const { rollBar, msToNextBucket } = require('./tween');
  const last = { time: 1000 * 60, open: 1, high: 1.3, low: 0.9, close: 1.2 };
  expect(rollBar(last, 1001 * 60, 60).bar).toEqual({ time: 1001 * 60, open: 1.2, high: 1.2, low: 1.2, close: 1.2 });   // flat at the last close, then real ticks shape it
  expect(rollBar(last, 1000 * 60, 60)).toBeNull();                                  // same bucket: the forming candle stays
  expect(rollBar(last, 1002 * 60, 60).fill).toHaveLength(1);                        // one missed boundary is filled (every bucket exists)
  expect(rollBar(last, 1010 * 60, 60)).toBeNull();                                  // a stale history: the first REAL tick opens it
  expect(rollBar({ time: 60, value: 2 }, 120, 60).bar).toEqual({ time: 120, value: 2 });   // line series
  expect(rollBar(null, 120, 60)).toBeNull();
  expect(msToNextBucket(60, 59_990)).toBe(30); expect(msToNextBucket(60, 60_000)).toBe(20); expect(msToNextBucket(60, 60_500)).toBe(59_520);
});
