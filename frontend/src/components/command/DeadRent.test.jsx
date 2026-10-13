import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { DeadRent } from './FuseWallet';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const q = id => document.querySelector(`[data-testid="${id}"]`);
const PLAN = { ok: true, dry: true, accounts: [{ pubkey: 'A1', mint: 'DUSTMINT', symbol: 'CLAWFUN', usd: 0.0012, rentSol: 0.0015 }, { pubkey: 'A2', mint: 'OFFMINT', symbol: null, usd: null, rentSol: 0.0015 }],
  rentSol: 0.003, rentUsd: 0.32, dustUsd: 0.0012, held: 3, kept: 1, solUsd: 106 };

test('♻ dead coin rent: a dry run first, the burn + close only on the second, explicit click', async () => {
  const call = jest.fn(async (path, opts) => (JSON.parse(opts.body).confirm ? { ...PLAN, dry: false, sig: 'SIG123' } : PLAN));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onDone = jest.fn();
  await act(async () => { root.render(<DeadRent call={call} onDone={onDone} />); });
  expect(q('fw-dead-go')).toBeNull();                                                                  // nothing to confirm before a check
  await act(async () => { q('fw-dead-check').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/fuse-wallet/close-dust', { method: 'POST', body: JSON.stringify({ confirm: false }) });
  expect(q('fw-dead-plan').textContent).toContain('$CLAWFUN'); expect(q('fw-dead-plan').textContent).toContain('written off');
  expect(q('fw-dead-plan').textContent).toContain('0.0030 SOL'); expect(q('fw-dead-go').textContent).toContain('Burn 2');
  await act(async () => { q('fw-dead-go').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/fuse-wallet/close-dust', { method: 'POST', body: JSON.stringify({ confirm: true }) });
  expect(q('fw-dead-tx').getAttribute('href')).toContain('SIG123'); expect(onDone).toHaveBeenCalled();
  await act(async () => { root.unmount(); });
});

test('♻ nothing dead = nothing to burn', async () => {
  const call = jest.fn(async () => ({ ...PLAN, accounts: [], rentSol: 0, rentUsd: 0, kept: 3 }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DeadRent call={call} />); });
  await act(async () => { q('fw-dead-check').click(); });
  expect(q('fw-dead-none').textContent).toContain('No dead coin accounts'); expect(q('fw-dead-go')).toBeNull();
  await act(async () => { root.unmount(); });
});
