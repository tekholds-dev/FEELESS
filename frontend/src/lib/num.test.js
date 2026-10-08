import { tiny, price, usd, pct } from './num';

test('tiny prices collapse their zeros into a subscript count', () => {
  expect(tiny(0.0000004123)).toBe('0.0₆4123');
  expect(tiny(0.00001)).toBe('0.0₄1');
  expect(tiny(0.00123)).toBe('0.00123');
  expect(tiny(0.5)).toBe('0.5');
  expect(tiny(1234.567)).toBe('1,234.57');
  expect(price(0.0000004123)).toBe('$0.0₆4123');
  expect(price(0)).toBe('—');
});

test('dollars are compact with commas, % with sign, huge moves as x', () => {
  expect(usd(4_400_000)).toBe('$4.40M');
  expect(usd(12_300)).toBe('$12.3K');
  expect(usd(1234.5)).toBe('$1,234.5');
  expect(pct(12.34)).toBe('+12.3%');
  expect(pct(-3)).toBe('-3.0%');
  expect(pct(1140)).toBe('12.4x');
});
