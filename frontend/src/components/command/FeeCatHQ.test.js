jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { livesRow } from './FeeCatHQ';

test('nine paws, lit for each life left', () => {
  expect(livesRow(7)).toEqual([true, true, true, true, true, true, true, false, false]);
  expect(livesRow(0).every(x => !x)).toBe(true);
});
