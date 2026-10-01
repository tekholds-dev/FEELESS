import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseEvolve } from './FuseEvolve';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: () => {} } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const CH = (n, f) => ({ pools: [`a${n}`, `b${n}`], fitness: f, bornGen: 2, parts: { grade: 'B', points: 60, aprScore: 40, momentum24h: 3, calm: 80, impactLegs: 0, dupes: 0, feeDragPct: 12 },
  legs: [{ pairAddress: `a${n}`, symbol: 'AAA', quote: 'SOL', weight: 60, chainId: 'solana' }, { pairAddress: `b${n}`, symbol: 'BBB', quote: 'SOL', weight: 40, chainId: 'solana' }] });

test('evolve: sends strategy + budget, replays generations, loads a champion into the Lab', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ So11111111111111111111111111111111111111112: { usdPrice: 200 } }) }));
  const call = jest.fn(async () => ({ history: [{ gen: 0, best: 40, avg: 20 }, { gen: 1, best: 55, avg: 30 }], champions: [CH(1, 55), CH(2, 50)], pool: 20, evaluated: 64 }));
  const onLoad = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FuseEvolve call={call} onLoad={onLoad} />); }); await tick(0);
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent.includes('Degen')).click(); });
  await act(async () => { el.querySelector('[data-testid="fe-run"]').click(); }); await tick(1200);
  const body = JSON.parse(call.mock.calls[0][1].body);
  expect(body).toMatchObject({ style: 'degen', legs: 3, generations: 16 }); expect(body.sol).toBeCloseTo(0.025);
  expect(el.textContent).toContain('FEE DRAG');
  await act(async () => { el.querySelector('[data-testid="fe-load-0"]').click(); });
  expect(onLoad.mock.calls[0][0].map(l => l.symbol)).toEqual(['AAA', 'BBB']);
});
