import { catchLine, shortMint } from './RugBounty';

test('a catch reads in plain words and mints are shortened', () => {
  expect(catchLine({ wallets: 3, bundlers: 2, snipers: 1 })).toBe('3 wallets flagged · 2 bundled · 1 sniped');
  expect(catchLine({ wallets: 1, bundlers: 0, snipers: 0 })).toBe('1 wallet flagged');
  expect(shortMint('Abcd1234567890Wxyz')).toBe('Abcd…Wxyz'); expect(shortMint('')).toBe('');
});
