import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeCatDesk, feeFunnel } from './FeeCatDesk';
jest.mock('./FeeBrain', () => ({ FeeBrain: () => null }));

test('the scan reads as a funnel with the stopping rules ranked', () => {
  const f = feeFunnel({ scanned: 44, passed: 1, rejections: { 'too new': 9, liquidity: 12 }, top: [{ symbol: 'illusion', reason: '🎓 learning lane' }] });
  expect(f.reasons.map(r => r.k)).toEqual(['liquidity', 'too new']); expect(f.reasons[0].w).toBe(1); expect(f.top[0].symbol).toBe('illusion');
});

test("🐱 Fee's HQ desk: why she trades, the duo read, open trades — from one request", async () => {
  const d = { rules: { minLiquidity: 40000 }, bounds: { minLiquidity: [10000, 500000] }, leader: { status: 'running' }, strategyPreset: 'feecat',
    cat: { balanceSol: 24, startingBalanceSol: 25, realizedPnlSol: -0.2, winRate: 50, wins: 1, losses: 1, status: 'running', lastTick: Date.now() / 1000 - 5,
      positions: [{ pairAddress: 'P', symbol: 'ILL', costSol: 0.5, currentChange: 12, openedAt: Date.now() / 1000 - 600 }] },
    scan: { at: Date.now() / 1000, scanned: 44, passed: 1, rejections: { liquidity: 12 } }, duo: { read: Date.now() / 1000, avoid: ['X'], exit: [], split: [], why: 'X: sellers lead', models: ['DESKTOP AI', 'LOCAL AI'] },
    events: [{ id: 1, type: 'BUY', detail: 'Fee is buying $ILL' }] };
  const call = jest.fn(async () => d);
  const box = document.createElement('div'); const root = createRoot(box);
  await act(async () => { root.render(<FeeCatDesk call={call} />); });
  expect(box.querySelector('[data-testid="fch-status"]').textContent).toContain('LIVE');
  expect(box.querySelector('[data-testid="fch-funnel"]').textContent).toContain('liquidity');
  expect(box.querySelector('[data-testid="fch-duo"]').textContent).toContain('both say skip');
  expect(box.querySelector('[data-testid="fch-open"]').textContent).toContain('$ILL');
  act(() => root.unmount());
});
