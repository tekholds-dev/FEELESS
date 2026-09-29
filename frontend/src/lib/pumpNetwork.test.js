import { launchToPair, ageLabel, buyPressure } from './pumpNetwork';

test('shapes a streamed launch as a pump pair keyed by its bonding curve', () => {
  const pair = launchToPair({ mint: 'Mint111pump', curve: 'Curve111', name: 'Cat', symbol: 'CAT', at: 1000.4, marketCapUsd: 5000 });
  expect(pair.pairAddress).toBe('Curve111');
  expect(pair.baseToken).toEqual({ address: 'Mint111pump', name: 'Cat', symbol: 'CAT' });
  expect(pair.launchpadId).toBe('pump');
  expect(pair.marketCap).toBe(5000);
});

test('formats ages compactly', () => {
  expect(ageLabel(0, 42_000)).toBe('42s');
  expect(ageLabel(0, 5 * 60_000)).toBe('5m');
  expect(ageLabel(0, 2 * 3_600_000)).toBe('2h');
});

test('buy pressure prefers live SOL flow, then DexScreener counts', () => {
  expect(buyPressure({ buySol: 3, sellSol: 1 }, null)).toEqual({ pct: 75, basis: 'SOL volume · live' });
  expect(buyPressure({ buySol: 0, sellSol: 0 }, { txns: { m5: { buys: 1, sells: 3 } } })).toEqual({ pct: 25, basis: 'trade count · DexScreener' });
  expect(buyPressure(null, {})).toBeNull();
});
