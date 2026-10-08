import { crewCost } from './FuseAdminSettings';

test('crew cost: the start price covers 5 seats, every +5 seats adds one pack', () => {
  const c = { createUsd: 25, packUsd: 5 };
  expect([5, 6, 10, 11, 15, 25].map(n => crewCost(n, c))).toEqual([25, 30, 30, 35, 35, 45]);
  expect(crewCost(3, c)).toBe(25); expect(crewCost(10, { createUsd: 40, packUsd: 0 })).toBe(40);
});
