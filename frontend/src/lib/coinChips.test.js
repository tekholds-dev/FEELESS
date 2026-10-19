import { chipActs } from './coinChips';

test('a coin chip offers sell when it is worth something, burn only for dust, nothing for SOL', () => {
  expect(chipActs({ symbol: 'SOL', usd: 0.8 })).toEqual([]);
  expect(chipActs({ mint: 'm', usd: 0.4 })).toEqual(['sell']);
  expect(chipActs({ mint: 'm', usd: 0.004 })).toEqual(['burn', 'sell']);
  expect(chipActs({ mint: 'm', usd: null })).toEqual(['sell', 'burn']);
});
