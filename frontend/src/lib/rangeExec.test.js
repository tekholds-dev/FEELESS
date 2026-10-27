import { binRange, halves, DLMM_MAX_BINS, venueOf } from './rangeExec';

test('🤖 a ±band → DLMM bins around the active bin, capped to ONE position, with the width it really covers', () => {
  const r = binRange(1 / 1.05, 1.05, 1, 1000, 80);                         // JUP-SOL: 80 bps bins
  expect(r.minBinId).toBe(1000 - 7); expect(r.maxBinId).toBe(1000 + 7); expect(r.bins).toBe(15); expect(r.capped).toBe(false);
  expect(r.loPct).toBeGreaterThan(4.6); expect(r.hiPct).toBeGreaterThan(5);
  const t = binRange(1 / 1.05, 1.05, 1, 0, 4);                             // SOL-USDC: 4 bps bins — ±5 % needs 245 bins, one position holds 69
  expect(t.bins).toBe(DLMM_MAX_BINS); expect(t.capped).toBe(true); expect(t.hiPct).toBeLessThan(1.5);
});

test('💸 a $ deposit splits half in each coin; venue routing', () => {
  expect(halves(10, 0.25, 1)).toEqual({ x: 20, y: 5 });
  expect(venueOf({ venue: 'raydium' })).toBe('raydium'); expect(venueOf({ venue: 'meteora' })).toBe('meteora'); expect(venueOf({ venue: 'orca' })).toBe(null);
});
