import { perpPlan, quoteMatches, atPrice, tpOk, slOk, levelAt, rr, liveRow } from './perps';

test('📉 the ticket preview + the quote must match the ticket', () => {
  const p = perpPlan(100, 10, 10, 'long', 0.06);
  expect(p.size).toBe(100); expect(p.per1).toBe(1); expect(p.fee).toBeCloseTo(0.06); expect(p.liq).toBeCloseTo(90.06); expect(p.liqPct).toBeCloseTo(9.94);
  expect(perpPlan(100, 10, 10, 'short').liq).toBeCloseTo(109.94); expect(perpPlan(0, 10, 10, 'long')).toBeNull();
  expect(quoteMatches({ side: 'short', positionSizeUsd: '1250' }, 'short', 1250)).toBe(true);
  expect(quoteMatches({ side: 'long', positionSizeUsd: '1250' }, 'short', 1250)).toBe(false);
  expect(quoteMatches({ side: 'short', positionSizeUsd: '600' }, 'short', 1250)).toBe(false);
});

test('🎯 TP / SL before the trade: the right side, the $ + ROE at each, the % chips, reward : risk', () => {
  expect(atPrice(105, 100, 10, 10, 'long')).toEqual({ move: 5.000000000000004, pnl: 5.000000000000004, roe: 50.00000000000004 });
  expect(atPrice(95, 100, 10, 10, 'short').pnl).toBeCloseTo(5); expect(atPrice(0, 100, 10, 10, 'long')).toBeNull();
  expect(tpOk(105, 100, 'long')).toBe(true); expect(tpOk(95, 100, 'long')).toBe(false); expect(tpOk(95, 100, 'short')).toBe(true); expect(tpOk(null, 100, 'long')).toBe(true);
  expect(slOk(95, 100, 'long', 90)).toBe(true); expect(slOk(89, 100, 'long', 90)).toBe(false); expect(slOk(101, 100, 'long')).toBe(false); expect(slOk(105, 100, 'short', 110)).toBe(true);
  expect(levelAt(100, 5, 'long', 'tp')).toBeCloseTo(105); expect(levelAt(100, 5, 'long', 'sl')).toBeCloseTo(95); expect(levelAt(100, 5, 'short', 'tp')).toBeCloseTo(95);
  expect(rr(110, 95, 100)).toBeCloseTo(2); expect(rr(110, null, 100)).toBeNull();
});

test('📋 a live position marks on the true price: P&L before fees, ROE, distance to ☠', () => {
  const r = liveRow({ side: 'long', entry: 100, size: 100, collateral: 10, liq: 91, mark: 100 }, 102);
  expect(r.pnl).toBeCloseTo(2); expect(r.pnlPct).toBeCloseTo(20); expect(r.toLiq).toBeCloseTo(10.78, 1); expect(r.live).toBe(102);
  expect(liveRow({ side: 'short', entry: 100, size: 100, collateral: 10 }, 98).pnl).toBeCloseTo(2);
});
