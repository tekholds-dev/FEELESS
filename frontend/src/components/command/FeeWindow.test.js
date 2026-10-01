import { feeWindow } from './TreasuryPulse';

test('fee header never claims 7 days of history it does not have', () => {
  const now = 1_700_000_000;
  expect(feeWindow(now - 9.1 * 3600, now)).toBe('all since 9h ago');
  expect(feeWindow(now - 3 * 86400, now)).toBe('all since 3d ago');
  expect(feeWindow(now - 30 * 86400, now)).toBe('7d');
  expect(feeWindow(null, now)).toBe('7d');
});
