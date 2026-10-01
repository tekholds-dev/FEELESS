import { rankSearch } from './SearchBox';

const now = Date.now();
const pair = (sym, addr, liq, extra = {}) => ({ chainId: 'solana', pairAddress: `${addr}-${liq}`, baseToken: { symbol: sym, address: addr }, liquidity: { usd: liq }, marketCap: liq * 10, pairCreatedAt: now - 30 * 864e5, ...extra });

test('search shows the most trusted coin first, not the wash-traded clone', () => {
  const real = pair('WIF', 'RealWif', 4_000_000, { info: { websites: [{}], socials: [{}], imageUrl: 'x' } });
  const clone = pair('WIF', 'CloneWif', 3000, { volume: { h24: 9e9 }, pairCreatedAt: now - 10 * 60e3 });
  const prefix = pair('WIFFY', 'Wiffy', 9_000_000);
  expect(rankSearch([clone, prefix, real], 'wif').map(p => p.baseToken.address)).toEqual(['RealWif', 'CloneWif', 'Wiffy']);
});

test('one row per token (its deepest pool) and a pasted contract wins', () => {
  const shallow = pair('ABC', 'Mint1', 1000); const deep = pair('ABC', 'Mint1', 500_000);
  const other = pair('ABC', 'Mint2', 9_000_000);
  const out = rankSearch([shallow, other, deep], 'mint1');
  expect(out).toHaveLength(2);
  expect(out[0].baseToken.address).toBe('Mint1');
  expect(out[0].liquidity.usd).toBe(500_000);
});
