import { snapMarkers } from './chartMarkers';

test('your trade pins land on a real chart point in line or candle mode (never silently hidden)', () => {
  const times = [1000, 1037, 1090, 1150];   // uneven line-mode points
  const out = snapMarkers([{ time: 1100, text: 'YOU BUY' }, { time: 5000, text: 'YOU SELL' }, { time: 10, text: 'too old' }], times, 60);
  expect(out.map(m => [m.time, m.text])).toEqual([[1090, 'YOU BUY'], [1150, 'YOU SELL']]);
  expect(snapMarkers([{ time: 125 }], [], 60)[0].time).toBe(120);   // no data yet: bucket fallback
});
