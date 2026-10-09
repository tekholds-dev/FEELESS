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

test('nine picker lists (Cooling off first), and a row with no recorded prices still gets a line from its own moves', () => {
  const { PICK_LENSES, moveLine } = require('./ArenaPrime');
  expect(PICK_LENSES.length).toBe(9); expect(PICK_LENSES[0][0]).toBe('exhale');
  const pts = moveLine({ chg24h: 100, chg6h: 50, chg1h: -20, chg5m: 0 });
  expect(pts.length).toBe(5); expect(pts[0]).toBeCloseTo(0.5); expect(pts[2]).toBeCloseTo(1.25); expect(pts[4]).toBe(1);
  expect(moveLine({ chg1h: 10 })).toBeNull(); expect(moveLine({ chg1h: 10, chg5m: 1, chg24h: -100 }).length).toBe(3);   // a −100% reading is skipped, never divided by zero
});

test('a real card splits into coins, free cash and parked profit that add up to what is in the card', () => {
  const { cardSplit } = require('./ArenaPrime');
  const sp = cardSplit({ valueUsd: 5.32, parkedUsd: 0.06, legs: [{ usd: 1.22 }, { usd: 0.5 }, { usd: 0.49 }, { usd: 0.22 }] });
  expect(sp.coins).toBeCloseTo(2.43); expect(sp.parked).toBe(0.06); expect(sp.cash).toBeCloseTo(2.83);
  expect(cardSplit({ valueUsd: 1, legs: [{ usd: 1.2 }] }).cash).toBe(0); expect(cardSplit(null)).toEqual({ coins: 0, parked: 0, cash: 0, total: 0 });
  // real card: cash is the BOOK's confirmed card SOL (not value − coins, where price lag landed); parked comes out of it; the three add up
  const r = cardSplit({ real: true, valueUsd: 4.04, parkedUsd: 0.05, legs: [{ usd: 3.8366 }], realBook: { reconciliation: { cardCashUsd: 0.1748, cardEquityUsd: 4.0402 } } });
  expect(r.cash).toBeCloseTo(0.1248); expect(r.parked).toBe(0.05); expect(r.coins).toBeCloseTo(3.8654); expect(r.coins + r.cash + r.parked).toBeCloseTo(4.0402);
  const h = cardSplit({ real: true, valueUsd: 5, parkedUsd: 0.7, heldUsd: 0.99, legs: [], realBook: { reconciliation: { cardCashUsd: 2.9, cardEquityUsd: 5 } } });
  expect(h.held).toBeCloseTo(0.99); expect(h.parked).toBeCloseTo(0.7); expect(h.cash).toBeCloseTo(1.21); expect(h.coins + h.cash + h.parked + h.held).toBeCloseTo(5);
});

test('the card shows what its confirmed sales came to, never a recycled running total', () => {
  const { soldNet, signedUsd } = require('./ArenaPrime');
  expect(soldNet({ takenUsd: 66.81, realBook: { realized: { netUsd: -6.02 } } })).toBe(-6.02); expect(soldNet({ takenUsd: 66.81 })).toBe(0);
  expect(signedUsd(-6.02)).toBe('−$6.02'); expect(signedUsd(1.5)).toBe('+$1.50');
});

test("the owner's scored moves read as one line", () => {
  const { movesLine } = require('./ArenaPrime');
  expect(movesLine({ pick: { label: '🎯 pick', n: 12, good: 5, bad: 3, medPct: 3.1 }, skim: { label: '💰 profit take', n: 4, good: 2, bad: 0, medPct: -6 } }))
    .toBe('🎯 pick 12 · 5 good · 3 bad · typical +3.1%  |  💰 profit take 4 · 2 good · typical -6%');
  expect(movesLine(null)).toBe('');
});
