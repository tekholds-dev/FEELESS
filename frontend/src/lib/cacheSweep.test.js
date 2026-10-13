import { sweepable, sweepNow, cacheSizes } from './cacheSweep';

test('🧹 old entries go, a cache is trimmed oldest-first, and what is on screen is kept', () => {
  const aged = sweepable('t-aged', new Map(), { ttl: 1000, max: 100 });
  aged.set('old', { at: 1000 }); aged.set('new', { at: 9500 }); aged.set('noStamp', { v: 1 });
  const sized = sweepable('t-sized', new Map(), { max: 3, keep: k => k === 'live' });
  ['live', 'a', 'b', 'c', 'd'].forEach(k => sized.set(k, 1));
  expect(sweepNow(10000)).toBe(3);
  expect([...aged.keys()]).toEqual(['new', 'noStamp']);            // no time stamp = judged by size only
  expect([...sized.keys()]).toEqual(['live', 'c', 'd']);           // 'live' is in use: kept although it is the oldest
  expect(sweepNow(10000)).toBe(0);
  expect(cacheSizes()).toMatchObject({ 't-aged': 2, 't-sized': 3 });
});
