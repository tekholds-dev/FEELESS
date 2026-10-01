jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { splitSol } from './FusePanel';

test('fuse-in split matches weights and always sums to the amount', () => {
  const s = splitSol('1', [{ pairAddress: 'A', weight: 33.33 }, { pairAddress: 'B', weight: 33.33 }, { pairAddress: 'C', weight: 33.34 }]);
  expect(Math.round(s.reduce((a, p) => a + p.sol, 0) * 1e6) / 1e6).toBe(1);
  expect(splitSol('0', [{ pairAddress: 'A', weight: 100 }])).toEqual([]);
});
