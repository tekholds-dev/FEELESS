import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { PoolWaves, poolFlow, tvlX, apyTone, POOL_LANES } from './PoolWaves';

const rows = [{ id: 'a', sym: 'SOL-USDC', kind: 'v2', proto: 'Raydium', tvl: 1e7, vol: 5e6, apy: 12 }, { id: 'b', sym: 'USDC-BIRB', kind: 'v3', proto: 'Raydium', tvl: 8e5, vol: 4e6, apy: 62 },
  { id: 'c', sym: 'JitoSOL', kind: 'stake', proto: 'Jito', tvl: 2e9, vol: 0, apy: 7 }, { id: 'd', sym: 'X', kind: 'perps', proto: 'P', tvl: 1e6, vol: 0, apy: 1 }];

test('🌊 the pool intake: each pool on its kind\'s water level, across by TVL, coloured by APY, ringed when it trades its TVL; vitals add up', () => {
  const f = poolFlow(rows); const lane = k => POOL_LANES.findIndex(([x]) => x === k);
  expect(f.dots.map(d => d.id).sort()).toEqual(['a', 'b', 'c']);              // perps has no level here
  expect(f.dots.find(d => d.id === 'b')).toMatchObject({ lane: lane('v3'), tone: 'hot', busy: true });
  expect(f.dots.find(d => d.id === 'c')).toMatchObject({ lane: lane('stake'), tone: 'ok', busy: false });
  expect(f.tvl).toBe(1e7 + 8e5 + 2e9 + 1e6); expect(f.flow).toBe(9e6); expect(f.turn).toBeCloseTo(9e6 / 1.08e7); expect(f.hot.id).toBe('b');
  expect(tvlX(1e5)).toBe(0); expect(tvlX(1e10)).toBe(1); expect(apyTone(2)).toBe('q'); expect(apyTone(null)).toBe('q');
  expect(poolFlow([]).dots).toEqual([]);
});

test('🌊 a dot does the room\'s real thing with that pool', async () => {
  const picked = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PoolWaves rows={rows} onPick={r => picked.push(r.id)} />); });
  expect(document.querySelectorAll('.pw-dot')).toHaveLength(3);
  await act(async () => { document.querySelector('[data-testid="pw-b"]').click(); });
  expect(picked).toEqual(['b']);
  act(() => root.unmount());
});
