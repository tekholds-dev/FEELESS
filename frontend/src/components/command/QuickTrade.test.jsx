import { stageOf } from './QuickTrade';

test('quick trade steps follow the real leg — never a fake done', () => {
  expect(stageOf({ kind: 'sell', units0: 100, saved: false }, 100).i).toBe(0);
  expect(stageOf({ kind: 'sell', units0: 100, saved: true }, 100)).toEqual({ i: 2, word: 'saved — the keeper sells next pass' });
  expect(stageOf({ kind: 'sell', units0: 100, saved: true }, 50).i).toBe(3);
  expect(stageOf({ kind: 'buy', units0: 100, saved: true }, 120).i).toBe(3);
  expect(stageOf({ kind: 'line', saved: true, word: 'stop −15%' }, 100).i).toBe(3);
  expect(stageOf({ err: 'refused' }, 1)).toEqual({ i: -1, word: 'refused' });
});
