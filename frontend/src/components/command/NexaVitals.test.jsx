import { nexaStats } from './NexaDesk';

test('Nexa stats: her calls only, answered %, typical time, the call in flight', () => {
  const s = nexaStats({ log: [{ prov: 'win', ok: true, ms: 40000 }, { prov: 'win', ok: false }, { prov: 'lan', ok: true, ms: 1 }], inflight: [{ prov: 'win', sec: 12 }, { prov: 'lan', sec: 3 }] });
  expect(s.n).toBe(2); expect(s.rate).toBe(50); expect(s.med).toBe(40000); expect(s.flight).toHaveLength(1);
});
