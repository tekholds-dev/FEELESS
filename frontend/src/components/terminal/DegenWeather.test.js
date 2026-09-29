import { forecast } from './DegenWeather';
const p = h1 => ({ priceChange: { h1 } });
test('forecast reads the live board honestly', () => {
  expect(forecast([p(1), p(2)])).toBeNull();
  expect(forecast([p(40), p(60), p(30), p(25), p(-5)]).icon).toBe('☀️');
  expect(forecast([p(5), p(-5), p(3), p(-2), p(-1)]).icon).toBe('⛅');
  expect(forecast([p(-40), p(-35), p(-50), p(5), p(2)]).icon).toBe('⛈️');
  expect(forecast([p(-5), p(-8), p(-3), p(-2), p(4)]).icon).toBe('🌧️');
});
