import { tickGuard } from './tickGuard';

test('a lone spike is dropped, a real move draws on its confirming tick, normal ticks draw at once', () => {
  const g = tickGuard();
  expect(g(1, 1.03, 0)).toBe(1.03);                 // normal
  expect(g(1.03, 2.5, 100)).toBe(null);             // +142% in one print: held
  expect(g(1.03, 1.04, 400)).toBe(1.04);            // next tick back near the old price → the spike was never drawn
  expect(g(1.04, 0.5, 500)).toBe(null);             // a dump: held one tick …
  expect(g(1.04, 0.49, 900)).toBe(0.49);            // … confirmed by the next tick near it
  expect(g(0.49, 0.2, 1000)).toBe(null);
  expect(g(0.49, 0.9, 4000)).toBe(0.9);             // held long enough: the next tick draws whatever is true
  expect(g(0, 5, 0)).toBe(5); expect(g(1, 0, 0)).toBe(null);
});
