import { radarPoint, repVitals } from './RepHero';

test('trust radar: a cleaner record sits nearer the core; every creator keeps one spot; vitals come from the board', () => {
  const d = p => Math.hypot(p.x - 120, p.y - 120);
  const good = radarPoint({ address: 'A1', score: 95, badge: 'trusted' }); const bad = radarPoint({ address: 'A1', score: 10, badge: 'flagged' });
  expect(d(good)).toBeLessThan(d(bad)); expect(good.tone).toBe('#45e486'); expect(bad.tone).toBe('#ff4d6d');
  expect(radarPoint({ address: 'X', score: 50 })).toEqual(radarPoint({ address: 'X', score: 50 }));
  expect(d(radarPoint({ address: 'Z', score: -50 }))).toBeLessThanOrEqual(110.1);
  const v = repVitals([{ badge: 'trusted', ruggedCount: 0 }, { badge: 'risky', ruggedCount: 2, serialDumper: true }, { badge: 'veteran' }, { badge: 'risky', ruggedCount: 1 }]);
  expect(v.trustedPct).toBe(50); expect(v.rugs).toBe(3); expect(v.dumpers).toBe(1); expect(v.mix[0]).toEqual({ k: 'risky', c: 2, w: 0.5 });
});

test('a creator record bar splits its launches by what they became', () => {
  const { recordParts } = require('./ReputationCenter');
  const r = recordParts({ tokenCount: 4, sustainedCount: 1, dumpedCount: 1, ruggedCount: 2 });
  expect(r.parts.map(p => [p.k, p.v])).toEqual([['sustained', 1], ['dumped', 1], ['rugged', 2]]); expect(r.other).toBe(0);
  expect(recordParts({ tokenCount: 1 }).parts).toEqual([]);
});
