import { holderOf, legLive } from './BrainCards';

test('who holds each seat and its live move', () => {
  expect(holderOf({ picked: true })[1]).toBe('YOU');
  expect(holderOf({ aiBy: 'lan' })[1]).toBe('G4');
  expect(holderOf({ aiBy: 'local' })[1]).toBe('OSSY');
  expect(holderOf({})[1]).toBe('AGENTS');
  const v = legLive({ entry: 1, now: 1.1, high: 1.5, usd: 2 }, { price: 1.2 });
  expect(Math.round(v.p)).toBe(20); expect(Math.round(v.pk)).toBe(50);
});
