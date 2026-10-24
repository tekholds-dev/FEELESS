import { perpLines, moveOver, crowd, PERP_POOLS } from './PerpsDash';

jest.mock('./terminal/PriceChart', () => ({ PriceChart: () => null }));

test('📈 the chart draws the ticket\'s ☠ line + every open position on THIS market only', () => {
  const pos = [{ asset: 'SOL', side: 'long', lev: 10, entry: 100, liq: 90.6 }, { asset: 'BTC', side: 'short', lev: 5, entry: 80000, liq: 95000 }];
  const l = perpLines('SOL', { side: 'long', lev: 25, liq: 96.2 }, pos);
  expect(l.map(x => x.px)).toEqual([96.2, 100, 90.6]); expect(l[0].title).toContain('LONG 25× wiped'); expect(l[1].color).toBe('#45e486');
  expect(perpLines('ETH', null, pos)).toEqual([]);
});

test('⏱ the 1-minute move comes from the real ticks in the window — never invented from one tick', () => {
  const now = 1_000_000;
  expect(moveOver([{ t: now - 30000, v: 100 }], 60, now)).toBeNull();
  expect(moveOver([{ t: now - 90000, v: 50 }, { t: now - 50000, v: 100 }, { t: now - 1000, v: 101 }], 60, now)).toBeCloseTo(1);
});

test('⚖ who is crowded = Jupiter\'s long vs short pool utilisation', () => {
  expect(crowd({ longUtilizationPercent: 13.8, shortUtilizationPercent: 68.1 })).toMatchObject({ side: 'SHORTS', long: 13.8, short: 68.1 });
  expect(crowd({ longUtilizationPercent: 30, shortUtilizationPercent: 10 }).share).toBeCloseTo(0.75);
  expect(crowd(null)).toBeNull(); expect(Object.keys(PERP_POOLS)).toEqual(['SOL', 'ETH', 'BTC']);
});
