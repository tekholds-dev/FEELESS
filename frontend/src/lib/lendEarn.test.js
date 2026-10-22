import { okAmount, lendLine } from './lendEarn';

test('an amount is a positive number with ≤ 9 decimals; the review line says exactly what runs', () => {
  expect(['1', '0.5', '12.000000001'].every(okAmount)).toBe(true);
  expect(['', '0', '-1', 'abc', '1.0000000001', '1e3'].some(okAmount)).toBe(false);
  expect(lendLine({ side: 'deposit', sym: 'USDC', apy: 6.1 }, '2.5')).toBe('Deposit 2.5 USDC into Jupiter Lend · 6.1% APY now');
  expect(lendLine({ side: 'withdraw', sym: 'USDC', apy: 6.1 }, '1')).toBe('Withdraw 1 USDC from Jupiter Lend');
});
