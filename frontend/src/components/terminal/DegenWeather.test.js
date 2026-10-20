import { forecast } from './DegenWeather';
const p = h1 => ({ priceChange: { h1 } });
test('forecast reads the live board honestly', () => {
  expect(forecast([p(1), p(2)])).toBeNull();
  expect(forecast([p(40), p(60), p(30), p(25), p(-5)]).icon).toBe('☀️');
  expect(forecast([p(5), p(-5), p(3), p(-2), p(-1)]).icon).toBe('⛅');
  expect(forecast([p(-40), p(-35), p(-50), p(5), p(2)]).icon).toBe('⛈️');
  expect(forecast([p(-5), p(-8), p(-3), p(-2), p(4)]).icon).toBe('🌧️');
});

test('coin weather reads the coin: storm on a rug read, heat on a clean send, every vital toned', () => {
  const { coinForecast } = require('./DegenWeather');
  const pair = { baseToken: { symbol: 'PKMN', address: 'M' }, priceChange: { m5: 3 }, txns: { h1: { buys: 70, sells: 30 } }, liquidity: { usd: 40000 } };
  const storm = coinForecast({ row: { top10: 60 }, vital: { grade: 'D' }, tv: { rug: 72, heat: 80 } }, pair, null);
  expect(storm.tone).toBe('storm');
  expect(storm.tiles.find(t => t.k === 'top10').t).toBe('bad');
  const hot = coinForecast({ row: { top10: 12, dev: 1, bundledN: 0, snipersN: 2 }, vital: { grade: 'B', score: 78, organicPct: 30, crew: { kind: 'popular', icon: '🔥', label: 'popular crew' } }, tv: { rug: 20, heat: 82, call: ['🔥', 'SEND IT', 'good'] } }, pair, { runner: { creatorRep: 'clean' } });
  expect(hot.tone).toBe('hot'); expect(hot.rep.tone).toBe('good'); expect(hot.crew.label).toBe('popular crew');
  expect(hot.tiles.find(t => t.k === 'buys').val).toBe('70%');
  const empty = coinForecast(null, { baseToken: { symbol: 'X' } }, null);
  expect(empty.tiles.find(t => t.k === 'rug').val).toBe('—');   // a missing reading is never a fake 0
});
