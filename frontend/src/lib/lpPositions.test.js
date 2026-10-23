import { positionView, floorOut } from './lpPositions';
import { blockPlan, spotOf, centerOf } from './cityPlan';
import { impactOf, engineQuote, MAX_IMPACT_PCT } from './swapEngine';

const Q = 2 ** 64;
test('🏗 a position\'s numbers: the SOL side + the coin side at the pool\'s own price, unclaimed fees, in range', () => {
  // A = the coin (6 decimals), B = SOL (9): sqrtPrice² × 10^(6−9) = the coin's price in SOL → 0.001 SOL a coin
  const sqrt = Math.sqrt(0.001 / 10 ** (6 - 9)) * Q;
  const v = positionView({ aIsSol: false, amountA: String(2000e6), amountB: String(2e9), feeA: '0', feeB: String(0.05e9), decA: 6, decB: 9, sqrtPrice: sqrt, sqrtMin: 1, sqrtMax: 2 ** 120, solUsd: 100 });
  expect(v.coinInSol).toBeCloseTo(0.001, 8); expect(v.solAmt).toBe(2); expect(v.coinAmt).toBe(2000);
  expect(v.valueSol).toBeCloseTo(4, 6); expect(v.valueUsd).toBeCloseTo(400, 4); expect(v.feeUsd).toBeCloseTo(5, 6); expect(v.inRange).toBe(true);
  const out = positionView({ aIsSol: true, amountA: '0', amountB: '0', feeA: '0', feeB: '0', decA: 9, decB: 6, sqrtPrice: 10, sqrtMin: 50, sqrtMax: 90, solUsd: 100 });
  expect(out.inRange).toBe(false); expect(out.valueUsd).toBe(0);
});

test('↩ removing keeps a 2 % floor on both sides (never 0 — a moved price can\'t empty the withdrawal)', () => {
  expect(floorOut('1000000')).toBe(980000n); expect(floorOut('0')).toBe(0n); expect(floorOut(10000, 50)).toBe(9950n);
});

test('🏙 your LP positions stand on the family block: a tower each, green in range / grey out, before the town; empty ones never stand', () => {
  const bl = { tag: 'FRT', name: 'Sicario', buildings: [{ key: 'orca', name: 'Orca', kind: 'dex', state: 'construction' }], town: ['tt'], open: 1 };
  const lp = [{ id: 'P1', sym: 'PANGEA-SOL', valueUsd: 12.5, feeUsd: 0.31, feeDay: 0.06, inRange: true }, { id: 'P2', sym: 'BORDR-SOL', valueUsd: 4, feeUsd: 0, inRange: false }, { id: 'P3', sym: 'X-SOL', empty: true }];
  const p = blockPlan(bl, { lp });
  const towers = p.markets.filter(m => m.key.startsWith('lp-')); expect(towers.map(m => m.key)).toEqual(['lp-P1', 'lp-P2']);
  expect(towers[0]).toMatchObject({ tone: '#45e486', pick: { lp: 'P1' } }); expect(towers[1].tone).toBe('#6b6f78');
  expect(towers[0].lines.join(' ')).toContain('$12.50 · fees +$0.310'); expect(towers[0].lines.join(' ')).toContain('IN RANGE · 6.0%/day'); expect(towers[1].lines.join(' ')).toContain('OUT OF RANGE');
  expect(spotOf(p, { lp: 'P1' })).toEqual(centerOf(towers[0].rect));
  const rects = [...p.markets, ...p.places, ...p.lots].map(x => `${x.rect.x},${x.rect.z}`); expect(new Set(rects).size).toBe(rects.length);   // nothing stacked
});

test('⚡ the zap\'s swap leg: refuses a thin route, reads impact either way the engine answers it', async () => {
  expect(impactOf({ priceImpactPct: '0.012' })).toBeCloseTo(1.2, 6); expect(impactOf({ priceImpact: 4 })).toBe(4); expect(impactOf({})).toBeNull();
  const was = global.fetch;
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ order_id: 'o'.repeat(40), quote: { transaction: 'AA', priceImpactPct: String((MAX_IMPACT_PCT + 1) / 100) } }) }));
  await expect(engineQuote({ inputMint: 'S', outputMint: 'C', amount: '0.05', wallet: 'W' })).rejects.toThrow(/too thin/);
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ order_id: 'o'.repeat(40), quote: { transaction: 'AA', priceImpactPct: '0.002' } }) }));
  const o = await engineQuote({ inputMint: 'S', outputMint: 'C', amount: '0.05', wallet: 'W' }); expect(o.order_id).toHaveLength(40);
  expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toMatchObject({ input_mint: 'S', output_mint: 'C', amount: '0.05', wallet: 'W' });
  global.fetch = was;
});
