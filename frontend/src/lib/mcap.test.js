import { mcapOf, isLaunchpadMint } from './mcap';
test('a launchpad coin with no cap yet is charted on price × its fixed 1B supply; a known cap always wins', () => {
  expect(isLaunchpadMint('7xYzpump')).toBe(true); expect(isLaunchpadMint('So11111111111111111111111111111111111111112')).toBe(false);
  expect(mcapOf(0.0000164, null, 'Abcpump')).toBeCloseTo(16400); expect(mcapOf(0.0000164, 15000, 'Abcpump')).toBe(15000);
  expect(mcapOf(1.2, null, 'So11111111111111111111111111111111111111112')).toBeNull();
});
