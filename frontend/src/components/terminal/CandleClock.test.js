import { clockWord } from './CandleClock';

test('counts down to the candle close', () => {
  expect(clockWord(1000 * 60 + 18, 60)).toEqual({ left: 42, word: '0:42' });
  expect(clockWord(0, 300).word).toBe('5:00');
  expect(clockWord(3600 * 3 + 12, 3600 * 4)).toEqual({ left: 3588, word: '59:48' });
  expect(clockWord(10, 3600 * 4).word).toBe('3:59:50');
});
