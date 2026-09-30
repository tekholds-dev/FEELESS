import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('./FeeInputs', () => ({ useSolUsd: () => 150, money: v => `$${Number(v).toFixed(2)}` }));
const { TreasuryPulse } = require('./TreasuryPulse');
const { _resetPulse } = require('../../lib/moneyPulse');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const PULSE = { feesTodayUsd: 4.2, fees7dUsd: 31, feeAccounts: [{ asset: 'wSOL', amount: 0.12 }, { asset: 'USDC', amount: 3 }],
  checks: [{ key: 'rpc', label: 'Solana RPC key set', ok: true }, { key: 'jup', label: 'Jupiter API key set', ok: false, fix: 'Add JUPITER_API_KEY' }, { key: 'ledger', label: 'Last fee recorded', ok: true, info: true, detail: '4m ago' }],
  alerts: [{ tone: 'ok', text: 'S1: 0.5 SOL ready for 3 holders', tab: 'badges' }, { tone: 'warn', text: 'S2: reserve wallet is empty', tab: 'badges' }] };

test('header strip reads the one pulse: fees, readiness, nudges', async () => {
  _resetPulse();
  const call = jest.fn(async () => PULSE); const onOpen = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TreasuryPulse call={call} onOpen={onOpen} />); });
  expect(call).toHaveBeenCalledWith('/admin/money-pulse');
  expect(el.textContent).toContain('$4.20');
  expect(el.querySelector('[data-testid="pulse-ready"]').textContent).toContain('1/2');
  await act(async () => { el.querySelector('[data-testid="pulse-ready"]').click(); });
  expect(el.textContent).toContain('Add JUPITER_API_KEY');
  if (process.env.DUMP_PANEL) require('fs').writeFileSync('/tmp/claude-0/panels.html', `<div style="display:flex;justify-content:flex-end;height:560px">${el.innerHTML}</div>`);
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent.includes('S1:')).click(); });
  expect(onOpen).toHaveBeenCalledWith('badges');
  act(() => root.unmount());
});
