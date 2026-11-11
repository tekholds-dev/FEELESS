import React, { useEffect } from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { WalletProvider, useWallet, insecureWalletPage } from './useWallet';

afterEach(() => { delete window.isSecureContext; });

test('insecure page (LAN http) maps to the same path on localhost', () => {
  Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false });
  window.history.replaceState(null, '', '/terminal/feecat/agents?x=1#top');
  const r = insecureWalletPage();
  expect(r.localUrl).toMatch(/^http:\/\/localhost(:\d+)?\/terminal\/feecat\/agents\?x=1#top$/);
});

test('secure page (localhost / https) is left alone', () => {
  Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true });
  expect(insecureWalletPage()).toBeNull();
});


globalThis.IS_REACT_ACT_ENVIRONMENT = true;
function Capture() { const c = useWallet(); useEffect(() => { window.__w = c; }, [c]); return null; }
const mountProvider = async () => { const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); await act(async () => root.render(<WalletProvider><Capture /></WalletProvider>)); return root; };

test('a bare connect() from a door connects Phantom on Solana, never the EVM wallet', async () => {
  localStorage.clear();
  const pk = { toString: () => 'SolAddr111' };
  window.phantom = { solana: { isPhantom: true, connect: jest.fn().mockResolvedValue({ publicKey: pk }), on() {}, off() {} } };
  window.ethereum = { isMetaMask: true, request: jest.fn() };
  const root = await mountProvider();
  let r; await act(async () => { r = await window.__w.connect(); });
  expect(r.wallet).toMatchObject({ chain: 'solana', address: 'SolAddr111' });
  expect(window.ethereum.request).not.toHaveBeenCalled();
  await act(async () => root.unmount()); delete window.phantom; delete window.ethereum;
});

test('connect on an insecure LAN page refuses at once with the localhost hint instead of hanging', async () => {
  Object.defineProperty(window, 'isSecureContext', { configurable: true, value: false });
  window.phantom = { solana: { isPhantom: true, connect: jest.fn(() => new Promise(() => {})), on() {}, off() {} } };
  const root = await mountProvider();
  await expect(window.__w.connect('solana', 'phantom')).rejects.toMatchObject({ code: 'INSECURE' });
  expect(window.phantom.solana.connect).not.toHaveBeenCalled();
  await act(async () => root.unmount()); delete window.phantom;
});
