import { perpLines, crowd, inRange } from './PerpsDash';
import { kalshiRead } from './perps/KalshiDesk';

jest.mock('lightweight-charts', () => ({}));

test('📈 the chart\'s levels: the ticket (☠ liq, draggable TP / SL) + every open position on THIS market only', () => {
  const t = { side: 'long', lev: 10, tp: 110, sl: 98 }; const plan = { liq: 92.5 };
  const pos = [{ asset: 'SOL', side: 'long', lev: 5, entry: 100, liq: 80.2, tpsl: [{ id: 'R1', kind: 'tp', price: 120 }] }, { asset: 'BTC', side: 'short', lev: 5, entry: 80000, liq: 95000 }];
  const l = perpLines('SOL', t, plan, 102, pos);
  expect(l.map(x => [x.id, x.price, !!x.drag])).toEqual([['liq', 92.5, false], ['tp', 110, true], ['sl', 98, true], ['e0', 100, false], ['l0', 80.2, false], ['oR1', 120, false]]);
  expect(perpLines('ETH', { side: 'long', lev: 2 }, null, null, pos)).toEqual([]);                      // no price yet → no ticket lines
});

test('⚖ who is crowded + where the price sits in its 24 h range', () => {
  expect(crowd({ longUtilizationPercent: 13.8, shortUtilizationPercent: 68.1 })).toMatchObject({ side: 'SHORTS', long: 13.8, short: 68.1 });
  expect(crowd({ longUtilizationPercent: 30, shortUtilizationPercent: 10 }).share).toBeCloseTo(0.75); expect(crowd(null)).toBeNull();
  expect(inRange(103, 101, 105)).toBeCloseTo(0.5); expect(inRange(99, 101, 105)).toBe(0); expect(inRange(103, 105, 101)).toBeNull();
});

test('⏱ the Kalshi read: the odds, the countdown, the live price vs the target, what $1 pays — nothing without a live ask', () => {
  const now = Date.parse('2026-10-24T03:10:00Z');
  const r = kalshiRead({ m15: { yes: 0.8, no: 0.21, target: 80875.28, closes: '2026-10-24T03:15:00Z' }, day: { strike: 81000, yes: 0.44 } }, 80900, now);
  expect(r.up).toBe(0.8); expect(r.left).toBe(300); expect(r.frac).toBeCloseTo(1 / 3); expect(r.above).toBeCloseTo(24.72); expect(r.payUp).toBeCloseTo(1.25); expect(r.payDn).toBeCloseTo(4.7619);
  expect(kalshiRead({ m15: { yes: null, no: 0.3, closes: 'x' } }, 1, now).up).toBeCloseTo(0.7);
  expect(kalshiRead({}, 1, now)).toBeNull(); expect(kalshiRead({ m15: { yes: null, no: null } }, 1, now)).toBeNull();
});
