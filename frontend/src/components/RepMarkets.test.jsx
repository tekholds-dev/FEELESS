import { clock, sparkPath, KIND_WORD } from './RepMarkets';

test('clock words and the spark path', () => {
  expect(clock(0)).toBe('closed');
  expect(clock(125)).toBe('2:05');
  expect(clock(3 * 3600 + 120)).toBe('3h 2m');
  expect(sparkPath([1])).toBe('');
  expect(sparkPath([1, 1.2, 0.9]).startsWith('M0.0,')).toBe(true);
  expect(Object.keys(KIND_WORD)).toEqual(['up', 'double', 'rug']);
});
