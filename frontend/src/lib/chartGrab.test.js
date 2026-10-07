import { snapLevel, grabLevels, withGrab, grabOrder, GRAB } from './chartGrab';

const f = { tpl: 'degen', pairAddress: 'PA', symbol: 'SK', entry: 1, slPct: 15, lockPct: 15, trailPct: 15, tpPct: 0, peak: 0, riding: false };

test('a dragged level moves in 1% steps and stays inside its range', () => {
  expect(snapLevel('stop', 0.79, 1)).toMatchObject({ pct: 21 });
  expect(snapLevel('stop', 0.834, 1).pct).toBe(17);
  expect(snapLevel('stop', 0.2, 1).pct).toBe(50); expect(snapLevel('stop', 1.4, 1).pct).toBe(5);   // can't leave the range (or cross the entry)
  expect(snapLevel('lock', 1.63, 1).pct).toBe(63); expect(snapLevel('tp', 9, 1).pct).toBe(500);
  expect(snapLevel('trail', 1.78, 2).pct).toBe(11);                           // trail counts from the PEAK
  expect(snapLevel('stop', 0, 1)).toBeNull(); expect(snapLevel('nope', 1, 1)).toBeNull();
  expect([GRAB.stop.min, GRAB.stop.max, GRAB.trail.min, GRAB.trail.max]).toEqual([5, 50, 3, 50]);
});

test('what can be grabbed: stop + lock while proving, only the trail once riding, take-profit when the card has no lock; nothing without a card', () => {
  expect(grabLevels(f).map(x => [x.kind, x.price])).toEqual([['stop', 0.85], ['lock', 1.15]]);
  expect(grabLevels({ ...f, riding: true, peak: 2 }).map(x => [x.kind, x.price])).toEqual([['trail', 1.7]]);
  expect(grabLevels({ ...f, lockPct: 0, tpPct: 100 }).map(x => x.kind)).toEqual(['stop', 'tp']);
  expect(grabLevels({ ...f, tpl: '' })).toEqual([]); expect(grabLevels(null)).toEqual([]);
});

test('a confirmed drag moves the line; the order says whether it is this coin or the whole card', () => {
  expect(withGrab(f, { stop: 20 }).stop).toBeCloseTo(0.8); expect(withGrab(f, { lock: 50 }).lock).toBeCloseTo(1.5); expect(withGrab(f, null)).toBe(f);
  expect(withGrab({ ...f, riding: true, peak: 2 }, { trail: 10 }).trail).toBeCloseTo(1.8);
  const s = grabOrder({ ...f, kind: 'stop', pct: 20 }); expect(s.body).toEqual({ leg: { tpl: 'degen', pairAddress: 'PA', sl: 20 } }); expect(s.ask).toContain('Only this coin');
  const l = grabOrder({ ...f, kind: 'lock', pct: 25 }); expect(l.body).toEqual({ realCfg: { rideAt: 25 } }); expect(l.ask).toContain('every coin');
  expect(grabOrder({ ...f, kind: 'trail', pct: 8 }).body).toEqual({ realCfg: { rideTrail: 8 } });
  expect(grabOrder({ ...f, kind: 'stop', pct: 17 }).body.leg.sl).toBe(17);    // any whole % in range
  expect(grabOrder({ ...f, kind: 'stop', pct: 4 })).toBeNull(); expect(grabOrder({ ...f, kind: 'stop', pct: 17.5 })).toBeNull();
});
