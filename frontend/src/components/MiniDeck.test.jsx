import { topTen } from './MiniDeck';

test('top 10 = launch coins under 12h, one row per coin, busiest hour first', () => {
  const now = 1e12; const P = (m, ageH, vol, px = 1) => ({ baseToken: { address: m, symbol: m }, pairCreatedAt: now - ageH * 3.6e6, volume: { h1: vol }, priceUsd: px });
  const rows = topTen([P('a', 1, 10), P('b', 2, 90), P('old', 13, 999), P('b', 2, 50), P('dead', 1, 500, 0), { baseToken: { address: 'noage' }, volume: { h1: 9e9 }, priceUsd: 1 },
    ...Array.from({ length: 12 }, (_, i) => P(`x${i}`, 3, 20 + i))], now);
  expect(rows).toHaveLength(10);
  expect(rows[0].baseToken.address).toBe('b');
  expect(rows.map(r => r.baseToken.address)).not.toEqual(expect.arrayContaining(['old', 'dead', 'noage']));
  expect(rows.filter(r => r.baseToken.address === 'b')).toHaveLength(1);
});
