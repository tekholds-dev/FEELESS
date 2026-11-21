import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeCatDesk, feeFunnel } from './FeeCatDesk';
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => null }));
jest.mock('./FeeBrain', () => ({ FeeBrain: () => null }));
jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => null }));
jest.mock('./AtomPrint', () => ({ __esModule: true, default: () => null }));
jest.mock('./CollectiveLanding', () => ({ CollectiveLanding: () => <p data-testid="col-landing">landing</p> }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
HTMLCanvasElement.prototype.getContext = () => null;
beforeEach(() => { localStorage.setItem('feeless.deskLook', JSON.stringify({ classic: true })); localStorage.removeItem('feeless.feeDesk.who');
  global.fetch = async () => ({ ok: true, json: async () => ({ agents: 2, pnlSol: 0.4, pow: { trades: 3, won: 2 }, tree: { agents: [{ id: 'a', name: 'Happy', proofs: 4, right: 3, graded: 4, won: 1, pnlSol: 0.5 }, { id: 'b', name: 'Bolt', proofs: 2, right: 0, graded: 1, won: 0, pnlSol: -0.1 }] } }) }); });

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

test('⚡ fast trench dial: the agents\' values, clamped to her bounds, metadata dropped', () => {
  const { fastValues } = require('./FeeCatDesk');
  expect(fastValues({ minLiquidity: 8000, takeProfit1: 30, from: { a: 1 } }, { minLiquidity: [40000, 150000] })).toEqual({ minLiquidity: 40000, takeProfit1: 30 });
});

const D = () => ({ rules: { minLiquidity: 40000, maxPositions: 5 }, bounds: { minLiquidity: [10000, 500000] }, leader: { status: 'running' }, strategyPreset: 'feecat',
  cat: { balanceSol: 24, startingBalanceSol: 25, realizedPnlSol: -0.2, winRate: 50, wins: 1, losses: 1, status: 'running', lastTick: Date.now() / 1000 - 5,
    discipline: { lives: 7, maxLives: 9 }, positions: [{ pairAddress: 'P', symbol: 'ILL', costSol: 0.5, currentChange: 12, openedAt: Date.now() / 1000 - 600 }] },
  scan: { at: Date.now() / 1000, scanned: 44, passed: 1, rejections: { liquidity: 12 } }, duo: { read: Date.now() / 1000, avoid: ['X'], exit: [], split: [], why: 'X: sellers lead' },
  events: [{ id: 1, type: 'BUY', detail: 'Fee is buying $ILL', ts: Date.now() / 1000 - 30 }] });

test("🖥 Slice 34: Fee's desk opens in the Desk look on her real state; Pause/Run hit the same save; The Collective reads /colony/flow; Classic comes back", async () => {
  localStorage.removeItem('feeless.deskLook');
  const call = jest.fn(async () => D());
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => { root.render(<FeeCatDesk call={call} />); });
  expect(box.querySelector('[data-testid="fdl"]')).not.toBeNull(); expect(box.querySelector('[data-testid="feecat-desk"]')).toBeNull();
  expect(box.querySelector('[data-testid="fdl-funnel"]').textContent).toMatch(/44.*coins read.*1.*passed/);
  expect(box.querySelector('[data-testid="fdl-book"]').textContent).toContain('$ILL');
  expect(box.querySelector('[data-testid="dkl-wd-duo"]').textContent).toMatch(/Both say skip\s*1/);
  expect(box.querySelector('[data-testid="fdl-feed"]').textContent).toContain('Fee is buying $ILL');
  await act(async () => { box.querySelector('[data-testid="fch-run"]').click(); });
  const ran = call.mock.calls.find(([u, o]) => u === '/admin/feecat' && o?.method === 'POST'); expect(JSON.parse(ran[1].body)).toMatchObject({ action: 'run' });   // the very save the classic Run button makes
  // every classic folder is one click away on the rail, popped out over the desk
  const lane = box.querySelector('[data-testid="dkl-rail-fee-lane"]'); expect(lane).not.toBeNull();
  await act(async () => { lane.click(); });
  expect(document.querySelector('[data-testid="fdl-pop-lane"]')).not.toBeNull();
  await act(async () => { document.querySelector('[data-testid="fdl-pop-close"]').click(); });
  // The Collective: real agents from the flow
  await act(async () => { box.querySelector('[data-testid="dkl-agent-collective"]').click(); });
  expect(box.querySelector('[data-testid="dkl-wd-top"]').textContent).toMatch(/Happy[\s\S]*0\.500 SOL/);
  expect(box.querySelector('[data-testid="dkl-wd-proofs"]').textContent).toContain('3 of 5 graded right');
  await act(async () => { box.querySelector('[data-testid="fdl-classic"]').click(); });
  expect(box.querySelector('[data-testid="feecat-desk"]')).not.toBeNull();
  await act(async () => { box.querySelector('[data-testid="fch-desk-look"]').click(); });
  expect(box.querySelector('[data-testid="fdl"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); box.remove();
});
