import { rowVitals } from './RowVitals';

test('shows only what the row really has, and the radar when the edge has it', () => {
  const t = rowVitals({ pad: 'Bags', ageH: 0.5, mcap: 250000, vol1h: 42000, buyShare: 61, top10: 18, dev: 0, site: true, x: false, tg: false }, null).map(i => i.t);
  expect(t).toEqual(['🚀 Bags', '30m', '$250K cap', '$42K/h', '61% buys', 'top-10 18%', 'dev 0.0%', '🌐']);
  expect(rowVitals({}, null)).toEqual([]);                                       // nothing known → nothing shown, never a fake 0
  const e = rowVitals({ top10: 40 }, { pulse: { m5Change: 3.2, buyShare: 70 }, snipersOut: { text: 'x' }, runner: { passing: false, gates: ['dev holds 12%'] } });
  expect(e.find(i => i.k === 't10').tone).toBe('bad');
  expect(e.map(i => i.k)).toEqual(expect.arrayContaining(['radar', 'snp', 'gate', 'buy']));
});
