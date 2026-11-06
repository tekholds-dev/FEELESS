import { KIND_PRINT, kindIdentity, kindOfFolder, ridge } from './proofprint';

test('every folder print is its own, and each kind of proof draws its own way', () => {
  const seen = new Set(); const kinds = Object.keys(KIND_PRINT);
  kinds.forEach(k => { for (let i = 0; i < 300; i += 1) seen.add(ridge(kindIdentity('agent1', k, `f${i}`), 11, 40)); });
  expect(seen.size).toBe(kinds.length * 300);
  expect(new Set(Object.values(KIND_PRINT).map(x => x.family)).size).toBe(kinds.length); expect(new Set(Object.values(KIND_PRINT).map(x => x.ink)).size).toBe(kinds.length);
  expect(ridge(kindIdentity('agent1', 'pow', 'x'), 7, 40)).not.toBe(ridge(kindIdentity('agent2', 'pow', 'x'), 7, 40));
  expect(ridge(kindIdentity('agent1', 'pow', 'x'), 7, 40)).toBe(ridge(kindIdentity('agent1', 'pow', 'x'), 7, 40));   // the same folder always draws the same
  expect(kindOfFolder('ps4d2a')).toBe('pos'); expect(kindOfFolder('pob12')).toBe('pob'); expect(kindOfFolder('f0')).toBe('pow');
});
