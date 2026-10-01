import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { VaultDesigner } from './VaultDesigner';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/solPrice', () => ({ useSolPrice: () => 150 }));

test('vault designer: every SOL number has its $, the draft shows who earns what, search adds a REAL Solana pool', async () => {
  const call = jest.fn(async () => ({ vaults: [{ id: 'v1', emoji: '🏦', name: 'FEE Yield', status: 'design', mgmtBps: 100, perfBps: 1000,
    pools: [{ pairAddress: 'P1', symbol: 'SOL/USDC', kind: 'v3', rangePct: 20, venue: 'orca', liquidityUsd: 3e7, aprEst: 40, capPct: 2, liveWeight: 1 }],
    sim: { allocation: { P1: 10 }, bufferSol: 0, capacitySol: 4000, blendedAprPct: 40, yearlyYieldSol: 4, yearlyFeeSol: 0.5 } }], feeWallet: 'FeeWa11et111111111111111111111111111111111' }));
  global.fetch = jest.fn(async () => ({ json: async () => ({ pools: [{ pairAddress: 'P9', symbol: 'cbBTC', quote: 'SOL', kind: 'v2', venue: 'raydium', liquidityUsd: 2e6, volume24h: 9e5, aprEst: 100, real: true }] }) }));
  jest.useFakeTimers();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<VaultDesigner call={call} />); });
  await act(async () => { jest.advanceTimersByTime(350); });
  expect(el.textContent).toContain('NOT DEPLOYED'); expect(el.textContent).toContain('$600');          // 4 SOL/yr yield × $150
  expect(el.textContent).toContain('$75');                                                               // fee 0.5 SOL
  const input = el.querySelector('[data-testid="vault-search"]');
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(input, 'btc'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { jest.advanceTimersByTime(350); }); await act(async () => {});
  expect(el.textContent).toContain('✓ REAL');
  await act(async () => { el.querySelector('.vd-hit').click(); });
  // 10 SOL at 100% APR: yield 10 SOL = $1,500; mgmt 1% = 0.1 SOL ($15); perf 10% = 1 SOL ($150); holder $1,335
  const m = el.querySelector('[data-testid="vd-money"]').textContent;
  expect(m).toContain('100% APR'); expect(m).toContain('holder earns $1.3K/yr'); expect(m).toContain('$165');
  jest.useRealTimers();
});

test('vault ← Arena card: its majors + pools (not runners) load as vault pools in one tap', async () => {
  const card = { id: 'prime-balanced', tpl: 'balanced', label: '🥇 Prime Gold', pnlPct: 2, legs: [{ mint: 'So1', pairAddress: 'PS', symbol: 'SOL', role: 'anchor' }, { mint: 'PumpM', pairAddress: 'PP', symbol: 'PUMP', role: 'pool' }, { mint: 'R', pairAddress: 'PR', symbol: 'RUN', role: 'runner' }] };
  global.fetch = jest.fn(async url => ({ json: async () => (String(url).includes('/fuses/prime') ? { cards: [card] }
    : { pools: [{ pairAddress: String(url).includes('So1') ? 'PS' : 'PP', symbol: String(url).includes('So1') ? 'SOL' : 'PUMP', quote: 'USDC', kind: 'v3', venue: 'orca', liquidityUsd: 3e7, aprEst: 30 }] }) }));
  const call = jest.fn(async () => ({ vaults: [], feeWallet: '' }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<VaultDesigner call={call} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 30)); });
  await act(async () => { el.querySelector('[data-testid="vd-from-balanced"]').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 30)); });
  const legs = [...el.querySelectorAll('.vd-leg b')].map(b => b.textContent);
  expect(legs).toEqual(['SOL/USDC', 'PUMP/USDC']); expect(el.querySelector('[aria-label="Vault name"]').value).toBe('Prime Gold Vault');
});
