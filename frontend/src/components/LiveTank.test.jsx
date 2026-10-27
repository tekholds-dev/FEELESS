import { place, bubbles } from './LiveTank';

test('🫧 a launch floats by its real numbers: across = age (newest right), up = market cap (log $2K…$100K), colour = curve progress', () => {
  const now = 1_800_000_000_000;
  const a = place({ marketCapUsd: 2000, at: now, devBuySol: 0, curveProgress: 0 }, now);
  expect(a.x).toBe(1); expect(a.y).toBe(0); expect(a.r).toBe(6); expect(a.p).toBe(0);
  const b = place({ marketCapUsd: 100000, at: now - 5 * 60000, devBuySol: 1, curveProgress: 80 }, now);
  expect(b.x).toBeCloseTo(0.5); expect(b.y).toBeCloseTo(1); expect(b.r).toBe(15); expect(b.p).toBe(0.8);
  expect(place({ marketCapUsd: 1e9, at: now - 1e9, curveProgress: 500 }, now)).toMatchObject({ x: 0, y: 1, p: 1 });
});

test('🛰 the other levels draw only what the read has: GERM keeps −3…+10 % of the floor, DESK every intake coin, TRENDING by the 1h move', () => {
  const intake = { coins: [{ mint: 'A', sym: 'A', mc: 5e4, ch: 5, status: 'READY', germ: 4 }, { mint: 'B', sym: 'B', mc: 5e5, ch: -5, status: 'CONTENDING', germ: 40 }, { mint: 'C', sym: 'C', mc: 1e5, ch: 0 }] };
  expect(bubbles('germ', intake).rows.map(r => r.id)).toEqual(['A']);
  expect(bubbles('desk', intake).rows).toHaveLength(3); expect(bubbles('desk', intake).rows[0].p).toBe(1);   // READY glows
  const t = bubbles('trend', { pairs: [{ pairAddress: 'P', baseToken: { address: 'M', symbol: 'X' }, priceChange: { h1: 100 }, marketCap: 1e7 }] }).rows[0];
  expect(t.x).toBe(1); expect(t.y).toBe(1); expect(t.p).toBe(1);
  expect(bubbles('top', null).rows).toEqual([]);
});
