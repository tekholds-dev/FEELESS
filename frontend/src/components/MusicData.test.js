jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn(), Link: () => null, useLocation: () => ({ pathname: '/' }) }), { virtual: true });
// eslint-disable-next-line import/first
import { firstLoadToday } from './FeeCatWidget';

test('music resumes by itself only on the first load of the day (data saver)', () => {
  localStorage.clear();
  const day = new Date('2026-10-01T09:00:00Z');
  expect(firstLoadToday(day)).toBe(true);
  expect(firstLoadToday(day)).toBe(false);   // refresh: last song shown, waits for play
  expect(firstLoadToday(new Date('2026-10-02T09:00:00Z'))).toBe(true);
});
