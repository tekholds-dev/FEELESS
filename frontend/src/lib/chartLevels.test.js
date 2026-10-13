import { distWord, feeLevels, levelRead, ownLevels, spreadTags, toolLevels } from './chartLevels';

test('a Fuse card coin gets entry, stop, lock and trail as key rows in the chart unit, plus the agents named lines', () => {
  const rows = ownLevels({ userEntry: 2, ratio: 10, fuse: { entry: 1, stop: 0.8, slPct: 20, lock: 1.3, lockPct: 30, trail: 0, lines: [{ px: 1.5, title: '🎯 take +50%', color: '#15d16a' }, { px: 0.9, title: 'support' }, { px: 0 }] } });
  expect(rows.map(r => r.id)).toEqual(['you', 'entry', 'stop', 'lock', 'x0', 'x1']);
  expect(rows.find(r => r.id === 'stop')).toMatchObject({ px: 8, tone: 'dn', key: true, title: '🛑 stop −20%' });
  expect(rows.find(r => r.id === 'x0')).toMatchObject({ px: 15, tone: 'up', key: true });
  expect(rows.find(r => r.id === 'x1')).toMatchObject({ tone: 'mute', key: false });
  expect(ownLevels({})).toEqual([]);
});

test('Fee levels far outside the candles on screen are left out', () => {
  const rows = feeLevels({ resistance: 12, support: 9, vwap: 10, entry: 100 }, { lo: 8, hi: 13 }, { hi: 13, lo: 8 });
  expect(rows.map(r => r.id)).toEqual(['f-res', 'f-sup', 'f-fair', 'f-fib0.382', 'f-fib0.5', 'f-fib0.618']);   // the entry at 100 is 7× off the screen
  expect(feeLevels(null)).toEqual([]);
});

test('chart tools become rows; the gun line and the germ are key', () => {
  const rows = toolLevels({ fvg: [{ mid: 5, dir: 'up' }], magnets: [{ price: 7, hits: 3, side: 'above' }], gun: { price: 8, fired: false }, germ: { bot: 4, lost: true } });
  expect(rows.map(r => [r.id, r.title, r.key])).toEqual([['g0', '🪜 gap', false], ['m0', '🧲 ×3 highs', false], ['gun', '🔫 gun line', true], ['germ', '🦠 germ lost', true]]);
});

test('the read against the live price: distance, near inside 2.5%, side', () => {
  expect(levelRead(110, 100)).toMatchObject({ near: false, above: true });
  expect(levelRead(110, 100).dist).toBeCloseTo(10);
  expect(levelRead(98, 100)).toMatchObject({ near: true, above: false });
  expect(levelRead(0, 100)).toBeNull();
  expect(distWord(10.2)).toBe('▲ 10%'); expect(distWord(-1.24)).toBe('▼ 1.2%'); expect(distWord(0.01)).toBe('AT IT'); expect(distWord(2400)).toBe('▲ 25.0x');
});

test('tags that would overlap are pushed apart and stay inside the plot', () => {
  expect(spreadTags([100, 104, 50, null], 300)).toEqual([100, 115, 50, null]);
  const out = spreadTags([290, 292, 294], 300);
  expect(Math.max(...out)).toBeLessThanOrEqual(296);
  expect(out[1] - out[0]).toBeGreaterThanOrEqual(15); expect(out[2] - out[1]).toBeGreaterThanOrEqual(15);
});

test('🧹 level tags stay off the live price row (the P&L tag + the axis price label) and still never overlap each other', () => {
  const { spreadAround, LIVE_ROOM, TAG_GAP } = require('./chartLevels');
  const live = 100;
  const out = spreadAround([95, 104, 140, null], 300, [live]);
  out.filter(y => y != null).forEach(y => expect(Math.abs(y - live)).toBeGreaterThanOrEqual(LIVE_ROOM));
  const ys = out.filter(y => y != null).sort((a, b) => a - b);
  ys.slice(1).forEach((y, i) => expect(y - ys[i]).toBeGreaterThanOrEqual(TAG_GAP));
  expect(out[3]).toBeNull();
  expect(spreadAround([40, 200], 300, [null])).toEqual([40, 200]);   // no live row → plain spread
});
