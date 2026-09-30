import { RAIL_PRESETS, RAIL_DEFAULTS, railWarnings } from './launchRail';

test('every preset is unruggable and snipe-proof with no warnings', () => {
  RAIL_PRESETS.forEach(pr => {
    const p = { ...RAIL_DEFAULTS, ...pr.params, lockedLpPct: 100, feeClaimerSet: true };
    expect(railWarnings(p)).toEqual([]);
    expect(p.startingFeeBps).toBeGreaterThanOrEqual(9000);
  });
});

test('flags weak anti-snipe, steep fees and withdrawable liquidity', () => {
  const w = railWarnings({ ...RAIL_DEFAULTS, startingFeeBps: 5000, endingFeeBps: 1000, feeDecayMin: 10, lockedLpPct: 80 }).join(' ');
  expect(w).toMatch(/Snipers only pay 50%/);
  expect(w).toMatch(/Normal fee 10% is steep/);
  expect(w).toMatch(/20% of graduated liquidity/);
});

test('house outsider toll must respect Meteora limits', () => {
  expect(railWarnings({ ...RAIL_DEFAULTS, poolCreationFeeSol: 5 }).join(' ')).not.toMatch(/toll/);
  expect(railWarnings({ ...RAIL_DEFAULTS, poolCreationFeeSol: 500 }).join(' ')).toMatch(/Outsider toll must be between/);
});
