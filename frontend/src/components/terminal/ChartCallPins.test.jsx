
test('🧹 at most 2 pins a candle, one per author, models before agents, the rest counted', () => {
  const { thinPins } = require('./ChartCallPins');
  const c = (who, at, kind = 'agent') => ({ id: `${who}${at}`, who, at, kind, cap: 1 });
  const out = thinPins([c('Reaper', 61), c('Reaper', 62), c('Courier', 63), c('G4', 64, 'ai'), c('Trigger', 65), c('Tally', 200)], 60);
  expect(out.filter(x => x.at < 120).map(x => x.who)).toEqual(['G4', 'Trigger']); expect(out.find(x => x.who === 'Trigger').more).toBe(2); expect(out.find(x => x.who === 'Trigger').folded.map(x => x.who)).toEqual(['Courier', 'Reaper']);
  expect(out.find(x => x.who === 'Tally')).toBeTruthy();
});

test('🫧 pins within the stack gap merge into ONE stack led by a model, and split again when zoomed apart', () => {
  const { clusterPins, STACK_GAP } = require('./ChartCallPins');
  const p = (id, x, kind, at = 1) => ({ id, x, kind, at, top: 100 - x });
  const g = clusterPins([p('w', 10, 'wallet'), p('a', 20, 'agent'), p('o', 30, 'ai'), p('far', 200, 'agent')]);
  expect(g).toHaveLength(2); expect(g[0].lead).toBe('o'); expect(g[0].ids.sort()).toEqual(['a', 'o', 'w']); expect(g[0].top).toBe(70);
  expect(clusterPins([p('w', 10, 'wallet'), p('a', 10 + STACK_GAP * 3, 'agent')])).toHaveLength(2);
});

test('🎛 each pin kind belongs to one lens', () => {
  const { lensOf } = require('./ChartCallPins');
  expect([lensOf('ai'), lensOf('talk'), lensOf('agent'), lensOf('wallet'), lensOf('user'), lensOf(undefined)]).toEqual(['models', 'models', 'agents', 'wallets', 'you', 'you']);
});
