import { impactPercent, impactGate, impactBlocks } from './impactGuard';

test('reads Jupiter fractions and legacy percents', () => {
  expect(impactPercent({ priceImpactPct: '-0.12' })).toBeCloseTo(12);
  expect(impactPercent({ priceImpact: 3.5 })).toBeCloseTo(3.5);
  expect(impactPercent({})).toBeNull();
  expect(impactPercent(null)).toBeNull();
});

test('15% needs a tick, 50% is refused', () => {
  expect(impactGate(2)).toBe('ok');
  expect(impactGate(15)).toBe('ack');
  expect(impactGate(50)).toBe('block');
  expect(impactBlocks(20, false)).toBe(true);
  expect(impactBlocks(20, true)).toBe(false);
  expect(impactBlocks(60, true)).toBe(true);
  expect(impactBlocks(null, false)).toBe(false);
});
