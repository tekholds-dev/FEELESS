jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { sparkPath } from './MiniChart';

test('mini chart sparkline spans the box, lowest close at the bottom', () => {
  const d = sparkPath([1, 2, 3], 200, 70);
  expect(d.startsWith('M0.0,67.0')).toBe(true);
  expect(d.endsWith('L200.0,3.0')).toBe(true);
  expect(sparkPath([5])).toBe('');
});
