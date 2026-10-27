import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { PoolWaves, poolFlow, wavePath } from './PoolWaves';

const rows = [{ id: 'a', sym: 'SOL-USDC', kind: 'v2', proto: 'Raydium', tvl: 1e7, vol: 5e6, apy: 12 }, { id: 'b', sym: 'USDC-BIRB', kind: 'v3', proto: 'Raydium', tvl: 8e5, vol: 4e6, apy: 22 },
  { id: 'c', sym: 'JitoSOL', kind: 'stake', proto: 'Jito', tvl: 2e9, vol: 0, apy: 7 }];

test('🌊 the busiest pools become waves: taller = more turnover, faster = more volume; the sea sums every pool', () => {
  const f = poolFlow(rows);
  expect(f.waves.map(w => w.id)).toEqual(['a', 'b']);                       // no flow → no wave (JitoSOL still counts in the TVL)
  expect(f.tvl).toBe(1e7 + 8e5 + 2e9); expect(f.flow).toBe(9e6); expect(f.turn).toBeCloseTo(9e6 / 1.08e7);   // turnover only over pools that trade
  const [a, b] = f.waves; expect(b.amp).toBeGreaterThan(a.amp);             // BIRB turns over 5× its pool — rougher water
  expect(a.dur).toBeLessThan(16); expect(a.dur).toBeGreaterThanOrEqual(5); expect(f.hot.id).toBe('b');
  expect(wavePath(10, 100)).toMatch(/^M0 100 Q75 80 150 100 Q225 120 300 100/);
  expect(poolFlow([]).waves).toEqual([]);
});

test('🌊 a wave chip does the room\'s real thing with that pool', async () => {
  const picked = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PoolWaves rows={rows} onPick={r => picked.push(r.id)} />); });
  expect(document.querySelectorAll('.pw-wave')).toHaveLength(2);
  await act(async () => { document.querySelector('[data-testid="pw-b"]').click(); });
  expect(picked).toEqual(['b']);
  act(() => root.unmount());
});
