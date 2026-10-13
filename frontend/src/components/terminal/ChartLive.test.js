import { liveRead, pctWord, usdWord } from './ChartLive';

test('the live tag reads the trade from the entry and the price the candle shows', () => {
  expect(liveRead(2, 3, 10)).toEqual({ pct: 50, usd: 5, up: true });
  const dn = liveRead(2, 1.5, 10); expect(dn.pct).toBe(-25); expect(dn.usd).toBe(-2.5); expect(dn.up).toBe(false);
  expect(liveRead(2, 3, null).usd).toBeNull();                 // no stake known (a card's coin seen by a visitor): the % only
  expect(liveRead(0, 3, 10)).toBeNull(); expect(liveRead(2, 0, 10)).toBeNull();
  expect(pctWord(12.345)).toBe('+12.3%'); expect(pctWord(-3.456)).toBe('−3.46%'); expect(pctWord(1240)).toBe('13.4x');
  expect(usdWord(0.034)).toBe('+$0.034'); expect(usdWord(-12.5)).toBe('−$12.50'); expect(usdWord(null)).toBe('');
});
