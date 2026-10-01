import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'MeWa11et' } }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess' }));
jest.mock('./FuseLab', () => ({ FuseLab: p => <div data-testid="lab">picks:{p.runnerPicks.length}</div> }));
jest.mock('./FuseSide', () => ({ FuseSide: () => null }));
jest.mock('./FuseCard', () => ({ LiveFuseCard: ({ r }) => <div data-testid={`live-${r.id}`} /> }));
jest.mock('./FuseGo', () => ({ FuseGo: p => <div data-testid="fusego" data-side={p.side} data-n={(p.orders || []).length} /> }));
// eslint-disable-next-line import/first
import { FusePage, togglePick, collectSplit } from './FusePage';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const ROW = { id: 'c1', name: 'Core', closed: false, legs: [{ pairAddress: 'P1', symbol: 'AAA', mint: 'M1', tokens: 10, usd: 50, heldUsd: 75, priceNow: 7.5 }, { pairAddress: 'P2', symbol: 'BBB', mint: 'M2', tokens: 5, usd: 50, heldUsd: 75, priceNow: 15 }], drift: 0 };
const RUNNERS = { round: { picks: [1, 2, 3, 4].map(i => ({ mint: `R${i}`, symbol: `RUN${i}`, lane: 'runner', score: 80, mcap: 50000, chg1h: 12, buyShare: 60 })) }, live: [] };

beforeEach(() => {
  window.history.replaceState(null, '', '/terminal/fuse');
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => (String(url).includes('/runners') ? RUNNERS : String(url).includes('/fuses/pnl') ? { pnlUsd: 50, pnlPct: 50, valueUsd: 150, rows: [ROW] }
    : String(url).includes('/balance/') ? { raw: '10000000000', decimals: 9 } : String(url).includes('/limits/') ? { open: 1, max: 2, canOpen: true } : { fuses: [] }) }));
});

test('runner picks cap at 3 and toggle off', () => {
  const r = i => ({ mint: `R${i}` });
  let p = []; [1, 2, 3, 4].forEach(i => { p = togglePick(p, r(i)); });
  expect(p.map(x => x.mint)).toEqual(['R1', 'R2', 'R3']);
  expect(togglePick(p, r(2)).map(x => x.mint)).toEqual(['R1', 'R3']);
  expect(collectSplit(33.3, ROW.legs).every(l => l.pct === 33.3)).toBe(true);
});

test('Fuse 🧬: tabs, runners carry into the Lab, My cards shows every action', async () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick();
  expect(host.querySelector('[data-testid="lab"]').textContent).toBe('picks:0');
  act(() => host.querySelector('[data-testid="fuse-tab-runners"]').click()); await tick();
  ['R1', 'R2', 'R3'].forEach(m => act(() => host.querySelector(`[data-testid="runner-add-${m}"]`).click()));
  expect(host.querySelector('[data-testid="runner-add-R4"]').disabled).toBe(true);           // card full
  act(() => host.querySelector('[data-testid="runners-to-lab"]').click()); await tick();
  expect(host.querySelector('[data-testid="lab"]').textContent).toBe('picks:3');
  act(() => host.querySelector('[data-testid="fuse-tab-cards"]').click()); await tick(); await tick();
  ['take', 'yield', 'rebalance', 'switch', 'limits', 'withdraw'].forEach(k => expect(host.querySelector(`[data-testid="act-${k}-c1"]`)).not.toBeNull());
  await act(async () => host.querySelector('[data-testid="act-yield-c1"]').click());
  expect(host.querySelector('[data-testid="act-panel-yield"]').textContent).toContain('33.3% of each leg');   // +50% → sell only the gain
  await act(async () => host.querySelector('[data-testid="act-withdraw-c1"]').click()); await tick();
  expect(host.querySelector('[data-testid="fusego"]').dataset.side).toBe('sell');
});

test('alert link ?collect=<id>&pct= opens a pre-filled Collect profit', async () => {
  window.history.replaceState(null, '', '/terminal/fuse?tab=cards&collect=c1&pct=33.3');
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FusePage />); }); await tick(); await tick(); await tick();
  const panel = host.querySelector('[data-testid="act-panel-take"]');
  expect(panel).not.toBeNull();
  expect(panel.textContent).toContain('33.3%');
  expect(host.querySelector('[data-testid="fusego"]').dataset.n).toBe('2');                    // both legs, sell 33.3% each
});
