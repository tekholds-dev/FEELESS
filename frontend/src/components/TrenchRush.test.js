import { rushScore, rushTop, leanOf } from './ArenaPrime';

test('rush board: failed scans and busted / wash reads never show, the cleanest three lead', () => {
  const row = (sym, k = {}) => ({ mint: sym, symbol: sym, safe: true, chg5m: 4, buyShare: 60, site: 's', x: 'x', tv: { heat: 60, rug: 20, call: ['🔥', 'SEND IT'] }, ...k });
  expect(rushScore(row('F', { safe: false }))).toBeNull();
  expect(rushScore(row('W', { tv: { heat: 90, rug: 10, call: ['🧪', 'WASH TRADED'] } }))).toBeNull();
  expect(rushScore(row('R', { rug: 60 }))).toBeNull();
  expect(rushScore(row('K', { chg5m: -28 }))).toBeNull();   // falling right now = never rushed
  const top = rushTop([row('A'), row('U', { safe: null }), row('B', { brain: { est: 20 } }), row('C', { chg5m: 40 }), row('F', { safe: false })]);
  expect(top.map(r => r.symbol)).toEqual(['B', 'A', 'U']);   // the brain's learned play lifts B · a +40% 5m candle is a top (never rushed) · F never
  expect(top[0].rush).toBeGreaterThan(top[1].rush);
});

test('lean line: momentum + buyers + pace + vitals point up or down, bounded', () => {
  expect(leanOf({ chg5m: 10, chg1h: 40, buyShare: 65, vol5m: 20000, vol1h: 100000, tv: { heat: 80, rug: 10 } })).toBeGreaterThan(0.5);
  expect(leanOf({ chg5m: -12, chg1h: -30, buyShare: 38, vol5m: 20000, vol1h: 100000, tv: { heat: 10, rug: 70 } })).toBeLessThan(-0.5);
  expect(Math.abs(leanOf({}))).toBeLessThanOrEqual(0.15);
  expect(leanOf({ chg5m: 999, chg1h: 999, buyShare: 100, vol5m: 1e9, vol1h: 1, tv: { heat: 100 } })).toBeLessThanOrEqual(1);
});
