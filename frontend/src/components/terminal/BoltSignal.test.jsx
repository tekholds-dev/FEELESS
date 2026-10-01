import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { BoltSignal, PumpPulseBanner } from './BoltSignal';

let mockRep = null;
jest.mock('../../lib/reputation', () => ({ useReputation: () => mockRep }));

const pulse = (overrides = {}) => ({ pulse: true, level: 2, m5Change: 8.4, buys: 70, sells: 30, buyShare: 70, volumeM5: 21000, ...overrides });
const pair = mint => ({ chainId: 'solana', pairAddress: `pool-${mint}`, baseToken: { address: mint, symbol: 'CAT' } });

async function render(ui, coins) {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ edge: Object.fromEntries(Object.entries(coins).map(([m, p]) => [m, { pulse: p }])) }) }));
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  await act(async () => { root.render(ui); });
  await act(async () => { jest.advanceTimersByTime(300); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  return { host, unmount: () => act(() => root.unmount()) };
}

beforeEach(() => { jest.useFakeTimers(); mockRep = null; });
afterEach(() => { jest.useRealTimers(); document.body.innerHTML = ''; });

test('shows the pink bolt and chat banner while a coin is pulsing', async () => {
  const mint = 'Mint1111111111111111111111111111pump';
  const view = await render(<><BoltSignal pair={pair(mint)} /><PumpPulseBanner pair={pair(mint)} /></>, { [mint]: pulse() });
  expect(view.host.querySelector('[data-testid="bolt-signal"]').className).toContain('pulse-2');
  expect(view.host.querySelector('[data-testid="pump-pulse-banner"]').textContent).toContain('+8.4%');
  view.unmount();
});

test('no bolt when the coin is quiet or its creator is flagged', async () => {
  const quiet = 'Quiet111111111111111111111111111pump';
  const flagged = 'Flag1111111111111111111111111111pump';
  mockRep = { badge: 'flagged', score: 10 };
  const view = await render(<><BoltSignal pair={pair(quiet)} /><BoltSignal pair={pair(flagged)} /></>, { [quiet]: pulse({ pulse: false, level: 0 }), [flagged]: pulse() });
  expect(view.host.querySelector('[data-testid="bolt-signal"]')).toBeNull();
  view.unmount();
});
