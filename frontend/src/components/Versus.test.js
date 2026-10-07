import { versusLine } from './ArenaPrime';

test('you vs engine: a leader is named only when the server calls one', () => {
  expect(versusLine({ lead: 'engine', gap: 1.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/engine is ahead by 1.7 pts/);
  expect(versusLine({ lead: 'you', gap: 0.7, you: { exits: 9 }, engine: { exits: 9 } })).toMatch(/You are ahead/);
  expect(versusLine({ lead: null, you: { exits: 2 }, engine: { exits: 9 } })).toMatch(/Needs 5 exits/);
  expect(versusLine({ lead: null, you: { exits: 9 }, engine: { exits: 9 } })).toBe('Level');
  expect(versusLine(null)).toBe('');
});

test('a paper card that picks like the owner: which cards and what the tip says', () => {
  const { humanOn, humanTip } = require('./ArenaPrime');
  const h = { tiers: ['next'], picks: 30, need: 8, ready: true, words: ['age 1h–9h (typ. 3h)'] };
  expect(humanOn({ humanStyle: h }, 'next')).toBe(true); expect(humanOn({ humanStyle: h }, 'degen')).toBe(false); expect(humanOn({}, 'next')).toBe(false);
  expect(humanTip(h)).toMatch(/last 30 picks: age 1h–9h/); expect(humanTip(h)).toMatch(/Paper only/);
  expect(humanTip({ ...h, ready: false, picks: 3, words: [] })).toMatch(/3 of 8 noted/);
});

test('buy-bottom lens is in the picker and says its own record honestly', () => {
  const { PICK_LENSES, bottomRecord } = require('./ArenaPrime');
  expect(PICK_LENSES.map(x => x[0])).toContain('bottom'); expect(PICK_LENSES.map(x => x[0])).not.toContain('dip');
  expect(bottomRecord({ n: 12, medPct: -4.2, wonPct: 33 })).toBe('Its own record: 12 coins held 1 hour, typical -4.2%, 33% up.');
  expect(bottomRecord(null)).toMatch(/starts now \(0 of 5 settled\)/);
});

test('seven picker lists, and a row with no recorded prices still gets a line from its own moves', () => {
  const { PICK_LENSES, moveLine } = require('./ArenaPrime');
  expect(PICK_LENSES.length).toBe(7);
  const pts = moveLine({ chg24h: 100, chg6h: 50, chg1h: -20, chg5m: 0 });
  expect(pts.length).toBe(5); expect(pts[0]).toBeCloseTo(0.5); expect(pts[2]).toBeCloseTo(1.25); expect(pts[4]).toBe(1);
  expect(moveLine({ chg1h: 10 })).toBeNull(); expect(moveLine({ chg1h: 10, chg5m: 1, chg24h: -100 }).length).toBe(3);   // a −100% reading is skipped, never divided by zero
});

test('a real card splits into coins, free cash and parked profit that add up to what is in the card', () => {
  const { cardSplit } = require('./ArenaPrime');
  const sp = cardSplit({ valueUsd: 5.32, parkedUsd: 0.06, legs: [{ usd: 1.22 }, { usd: 0.5 }, { usd: 0.49 }, { usd: 0.22 }] });
  expect(sp.coins).toBeCloseTo(2.43); expect(sp.parked).toBe(0.06); expect(sp.cash).toBeCloseTo(2.83);
  expect(cardSplit({ valueUsd: 1, legs: [{ usd: 1.2 }] }).cash).toBe(0); expect(cardSplit(null)).toEqual({ coins: 0, parked: 0, cash: 0 });
});
