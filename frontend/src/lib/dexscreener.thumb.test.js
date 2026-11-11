import { thumb } from './dexscreener';

test('🖼 SITE-2: DexScreener coin images are asked for at 2× the shown size (64/128/256 steps), everything else is untouched', () => {
  const u = 'https://cdn.dexscreener.com/cms/images/CN2GXn9xCwxqB6AH?width=800&height=800&quality=95&format=auto';
  expect(thumb(u, 22)).toBe('https://cdn.dexscreener.com/cms/images/CN2GXn9xCwxqB6AH?width=64&height=64&quality=85&format=auto');
  expect(thumb(u, 40)).toContain('width=128&height=128'); expect(thumb(u, 113)).toContain('width=256&height=256'); expect(thumb(u)).toContain('width=64');
  expect(thumb('https://ipfs.io/ipfs/abc.png', 22)).toBe('https://ipfs.io/ipfs/abc.png');
  expect(thumb(undefined)).toBeUndefined(); expect(thumb('/api/reputation/token-logo/x', 22)).toBe('/api/reputation/token-logo/x');
});
