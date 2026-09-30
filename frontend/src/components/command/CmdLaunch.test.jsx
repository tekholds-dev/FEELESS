import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'Own1111111111111111111111111111111111111111' } }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const { CmdLaunch, LaunchReceipt } = require('./CmdLaunch');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const rail = { ready: true, config: 'Cfg11111111111111111111111111111111111111111', params: {}, house: [{ config: 'Hse11111111111111111111111111111111111111111', label: 'Reserve coins', params: { initialMarketCap: 40, migrationMarketCap: 600, poolCreationFeeSol: 5 } }] };
const REC = { at: Date.now(), kind: 'pump', mint: 'Mint1111111111111111111111111111111111pump', signature: '5sig'.padEnd(88, 'x'), uri: 'https://ipfs.io/ipfs/Qm', wallet: 'Own1111111111111111111111111111111111111111', name: 'Fee Cat', symbol: 'FEECAT', devBuy: 0.5, unit: 'SOL', terms: [['Curve', 'Pump.fun bonding curve']] };

test('house launch shows that config’s terms + toll, and waits for a complete coin', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<CmdLaunch rail={rail} />); });
  expect(el.textContent).toContain('Reserve coins');
  expect(el.textContent).toContain('40 → 600 SOL');
  expect(el.textContent).toContain('Launch toll');
  expect(el.querySelector('[data-testid="cmd-launch-review"]').disabled).toBe(true);
  const pump = [...el.querySelectorAll('[role="radio"]')].find(b => b.textContent.includes('Pump'));
  await act(async () => { pump.click(); });
  expect(el.textContent).toContain('PUMP.FUN TERMS');
  act(() => root.unmount());
});

test('receipt shows the CA and the pump.fun link', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchReceipt r={REC} />); });
  expect(el.querySelector('[data-testid="cmd-launch-ca"]').textContent).toBe(REC.mint);
  expect([...el.querySelectorAll('a')].some(a => a.href === `https://pump.fun/coin/${REC.mint}`)).toBe(true);
  act(() => root.unmount());
});

if (process.env.DUMP_PANEL) test('dump', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<><CmdLaunch rail={rail} /><div style={{ height: 20 }} /><LaunchReceipt r={REC} /></>); });
  require('fs').writeFileSync('/tmp/claude-0/panels.html', el.innerHTML);
});
