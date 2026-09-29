import { cleanAmount } from './api';

test('amounts typed any way become valid', () => {
  expect(cleanAmount('.01')).toBe('0.01');
  expect(cleanAmount('1,5')).toBe('1.5');
  expect(cleanAmount('1.2.3')).toBe('1.23');
  expect(cleanAmount('007')).toBe('7');
  expect(cleanAmount('0.5')).toBe('0.5');
  expect(cleanAmount('abc')).toBe('');
});
