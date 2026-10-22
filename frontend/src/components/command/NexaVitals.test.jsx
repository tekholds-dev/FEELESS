import { nexaStats } from './NexaDesk';

test('Nexa stats: her calls only, answered %, typical time, the call in flight', () => {
  const s = nexaStats({ log: [{ prov: 'win', ok: true, ms: 40000 }, { prov: 'win', ok: false }, { prov: 'lan', ok: true, ms: 1 }], inflight: [{ prov: 'win', sec: 12 }, { prov: 'lan', sec: 3 }] });
  expect(s.n).toBe(2); expect(s.rate).toBe(50); expect(s.med).toBe(40000); expect(s.flight).toHaveLength(1);
});

test('her reads strip: fast vs full, failed reads marked, taller = slower, last 16', () => {
  const { readBars } = require('./NexaDesk');
  const b = readBars([{ at: 1, ms: 2000, mode: 'fast', ok: true }, { at: 2, ms: 240000, mode: 'full', ok: true }, { at: 3, ms: 60000, ok: false }]);
  expect(b.map(x => [x.mode, x.ok, x.sec])).toEqual([['fast', true, 2], ['full', true, 240], ['fast', false, 60]]);
  expect(b[1].h).toBe(1); expect(b[0].h).toBeGreaterThan(0.06); expect(b[0].h).toBeLessThan(b[2].h);
  expect(readBars(Array.from({ length: 30 }, (_, i) => ({ at: i, ms: 1000 })))).toHaveLength(16);
});
