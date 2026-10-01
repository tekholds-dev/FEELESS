import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseLab } from './FuseLab';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./FusePanel', () => ({ FuseLeg: () => null }));
const pool = (pa, sym) => ({ chainId: 'solana', pairAddress: pa, symbol: sym, quote: 'SOL', dex: 'raydium', liquidityUsd: 1e6, volume24h: 2e6, aprEst: 180, change24h: 3 });
const PREVIEW = { sol: 1, usd: 200, solUsd: 200, blendedAprPct: 150, dailyUsd: 0.8, score: { grade: 'B', parts: [{ part: 'depth', points: 25, why: '$2M' }] },
  legs: [{ pairAddress: 'A', symbol: 'AAA', weight: 60, sol: 0.6, usd: 120, dailyUsd: 0.5 }, { pairAddress: 'B', symbol: 'BBB', weight: 40, sol: 0.4, usd: 80, dailyUsd: 0.3 }] };
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('pick two pools → live auto-weighted preview of where the SOL goes', async () => {
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('/preview') ? PREVIEW : { pools: [pool('A', 'AAA'), pool('B', 'BBB')] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseLab />); });
  await tick(0);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('fl-pool-A').click(); });
  expect(el.textContent).toContain('Pick one more pool');
  await act(async () => { q('fl-pool-B').click(); });
  await tick(300);
  expect(el.textContent).toContain('0.6 SOL');
  expect(q('fl-go').textContent).toContain('Fuse in 1 SOL');
  const body = JSON.parse(global.fetch.mock.calls.find(c => String(c[0]).includes('/preview'))[1].body);
  expect(body.pools.map(p => p.pairAddress)).toEqual(['A', 'B']);
});
