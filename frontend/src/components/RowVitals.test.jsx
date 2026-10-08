import { rowVitals } from './RowVitals';

test('shows only what the row really has, and the radar when the edge has it', () => {
  const t = rowVitals({ pad: 'Bags', ageH: 0.5, mcap: 250000, vol1h: 42000, buyShare: 61, top10: 18, dev: 0, site: true, x: false, tg: false }, null).map(i => i.t);
  expect(t).toEqual(['🚀 Bags', '30m', '$250K cap', '$42K/h', '61% buys', 'top-10 18%', 'dev 0.0%', '🌐']);
  expect(rowVitals({}, null)).toEqual([]);                                       // nothing known → nothing shown, never a fake 0
  const e = rowVitals({ top10: 40 }, { pulse: { m5Change: 3.2, buyShare: 70 }, snipersOut: { text: 'x' }, runner: { passing: false, gates: ['dev holds 12%'] } });
  expect(e.find(i => i.k === 't10').tone).toBe('bad');
  expect(e.map(i => i.k)).toEqual(expect.arrayContaining(['radar', 'snp', 'gate', 'buy']));
});

test('your-entry chips: dip with volume is your setup, a 5m pump is chasing, thin volume is thin — each quotes your record', () => {
  const rules = { chase: { n: 42, wonPct: 26, pct: -8 }, setup: { n: 18, wonPct: 55, pct: 6 }, thin: { n: 3, wonPct: 0, pct: -9 } };
  const a = rowVitals({ chg5m: -5, vol1h: 90000 }, null, { rules }); expect(a.find(i => i.k === 'mine-setup').tip).toContain('55% won');
  const b = rowVitals({ chg5m: 9, vol1h: 90000 }, null, { rules }); expect(b.find(i => i.k === 'mine-chase').tip).toContain('42 picks');
  const c = rowVitals({ chg5m: 0, vol1h: 5000 }, null, { rules }); expect(c.find(i => i.k === 'mine-thin').tip).not.toContain('picks');   // under 8 picks: no record quoted
  expect(rowVitals({ chg5m: 1, vol1h: 90000 }, null, { rules }).some(i => i.k.startsWith('mine-'))).toBe(false);
});

test('a pool under $40K reads as thin (never for a trench ticket) and quotes your record once it has 8 picks', () => {
  const rules = { thinpool: { n: 12, wonPct: 25, pct: -9 } };
  const a = rowVitals({ liq: 25000, vol1h: 90000, chg5m: 0 }, null, { rules });
  expect(a.find(i => i.k === 'mine-thinpool').tip).toContain('12 picks');
  expect(rowVitals({ liq: 25000, vol1h: 90000 }, null, { rules: {} }).find(i => i.k === 'mine-thinpool').tip).not.toContain('picks');
  expect(rowVitals({ liq: 25000, trench: true, vol1h: 90000 }, null, { rules }).some(i => i.k === 'mine-thinpool')).toBe(false);
  expect(rowVitals({ liq: 120000, vol1h: 90000 }, null, { rules }).some(i => i.k === 'mine-thinpool')).toBe(false);
});
