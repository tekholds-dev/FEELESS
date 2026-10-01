jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { nextReserveStep } from './ReserveProgress';

const b = (id, hold, extraDone = true) => ({ id, set: 'frsv', earned: false, tasks: [{ metric: 'fee_usd', target: hold, done: false }, { metric: 'trades', target: 1, done: extraDone }] });

test('next Fee Reserve unlock: holding-only badges first, then the cheapest', () => {
  const s = nextReserveStep([b('frsv-elite', 10000), b('frsv-vip', 1000), b('frsv-recruit', 100, false)], 40);
  expect(s.b.id).toBe('frsv-vip'); expect(s.need).toBe(960); expect(s.onlyHold).toBe(true);
  expect(nextReserveStep([b('frsv-recruit', 100, false)], 40).onlyHold).toBe(false);
  expect(nextReserveStep([{ ...b('frsv-vip', 1000), earned: true }], 40)).toBeNull();
});
