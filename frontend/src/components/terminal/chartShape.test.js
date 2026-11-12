import fs from 'fs';
import path from 'path';

jest.mock('lightweight-charts', () => ({}));
const { chartShape } = require('./PriceChart');

const row = (t, c) => [t, c, c, c, c, 1];
const key = { pair: 'P', interval: '1m', ratio: 1 };

test('⚡ a candle refresh keeps the chart: only another coin, timeframe, scale, series type or price decade rebuilds it', () => {
  const a = [row(1, 0.0012), row(2, 0.0013), row(3, 0.0014)]; const base = chartShape(a, [], key);
  expect(chartShape([...a, row(4, 0.0015)], [], key)).toBe(base);                  // one new bar
  expect(chartShape(a.map(r => [...r]), [], key)).toBe(base);                      // a fresh array of the same rows
  expect(chartShape(a, [], { ...key, pair: 'Q' })).not.toBe(base);
  expect(chartShape(a, [], { ...key, interval: '5m' })).not.toBe(base);
  expect(chartShape(a, [], { ...key, ratio: 2 })).not.toBe(base);
  expect(chartShape([row(1, 0.0012)], [], key)).not.toBe(base);                     // sparse line ↔ candles
  expect(chartShape([], [{ time: 1, value: 0.0012 }], key)).not.toBe(base);         // trail → candles
  expect(chartShape([...a, row(4, 0.012)], [], key)).not.toBe(base);                // axis precision moved
  expect(chartShape([], [], key)).toContain('trail');                               // nothing yet: no crash
});

test('⚡ the build effect never hangs on candle identity again', () => {
  const src = fs.readFileSync(path.join(__dirname, 'PriceChart.jsx'), 'utf8');
  expect(src).toContain('}, [shape, hasChart, dayMode, showVolume, chartStyle, bgOn, chartTheme]);');
  expect(src).not.toContain('}, [displayCandles, trail, hasChart,');
});

test('🕯 a quote is not a trade: only a real fill (k) shapes the forming candle; 1m/5m keep reloading the source bar every 15s', () => {
  const src = fs.readFileSync(path.join(__dirname, 'PriceChart.jsx'), 'utf8');
  expect(src).toMatch(/if \(ref\.kind === 'candle'\) \{\s*if \(!fill\) return;/);   // aggregate price ticks never draw a wick
  expect(src).toContain("apply(Number(m.p), { source: m.k ? 'live trades' : 'live stream' }, !!m.k)");
  expect(src).not.toMatch(/apply\(Number\(live\?\.usd\), live, true\)/);           // the backup poll is quotes: header price only
  expect(src).toMatch(/<= 300 \? null/);                                             // short timeframes never settle to a 60s reload
});
