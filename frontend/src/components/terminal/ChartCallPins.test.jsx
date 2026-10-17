
test('🧹 at most 2 pins a candle, one per author, models before agents, the rest counted', () => {
  const { thinPins } = require('./ChartCallPins');
  const c = (who, at, kind = 'agent') => ({ id: `${who}${at}`, who, at, kind, cap: 1 });
  const out = thinPins([c('Reaper', 61), c('Reaper', 62), c('Courier', 63), c('G4', 64, 'ai'), c('Trigger', 65), c('Tally', 200)], 60);
  expect(out.filter(x => x.at < 120).map(x => x.who)).toEqual(['G4', 'Trigger']); expect(out.find(x => x.who === 'Trigger').more).toBe(2); expect(out.find(x => x.who === 'Trigger').folded.map(x => x.who)).toEqual(['Courier', 'Reaper']);
  expect(out.find(x => x.who === 'Tally')).toBeTruthy();
});
