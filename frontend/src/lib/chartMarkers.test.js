import { snapMarkers, tradeLevels } from './chartMarkers';

test('your trade pins land on a real chart point in line or candle mode (never silently hidden)', () => {
  const times = [1000, 1037, 1090, 1150];   // uneven line-mode points
  const out = snapMarkers([{ time: 1100, text: 'YOU BUY' }, { time: 5000, text: 'YOU SELL' }, { time: 10, text: 'too old' }], times, 60);
  expect(out.map(m => [m.time, m.text])).toEqual([[1090, 'YOU BUY'], [1150, 'YOU SELL']]);
  expect(snapMarkers([{ time: 125 }], [], 60)[0].time).toBe(120);   // no data yet: bucket fallback
});

test('every trade gets its own level at its fill price, numbered per side', () => {
  const lv = tradeLevels([{ side: 'buy', fillPrice: 0.01, usd: 1.15 }, { side: 'buy', fillPrice: 0.012, usd: 2 }, { side: 'sell', fillPrice: 0.015, usd: 1.5 }, { side: 'buy', usd: 1 }]);
  expect(lv).toEqual([{ side: 'buy', price: 0.01, title: 'B1 bought $1.15' }, { side: 'buy', price: 0.012, title: 'B2 bought $2.00' }, { side: 'sell', price: 0.015, title: 'S1 sold $1.50' }]);
});
