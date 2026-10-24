import React, { useEffect } from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { WalletProvider, useWallet } from './useWallet';
import { connectWalletConnect, disconnectWalletConnect, subscribeWalletConnectSession } from '../lib/reownWalletConnect';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../lib/reownWalletConnect', () => ({
  __esModule: true,
  connectWalletConnect: jest.fn(),
  disconnectWalletConnect: jest.fn(),
  subscribeWalletConnectSession: jest.fn().mockResolvedValue(() => {}),
  getWalletConnectSession: jest.fn(),
}));

function CaptureWallet() {
  const walletContext = useWallet();
  useEffect(() => { window.__capturedWalletContext = walletContext; }, [walletContext]);
  return null;
}

test('WalletConnect sessions populate the existing wallet context and disconnect cleanly', async () => {
  localStorage.clear();
  const provider = {
    request: jest.fn().mockResolvedValue('0x1'),
    on: jest.fn(() => { throw new Error("undefined is not an object (evaluating 'this.listeners[event].push')"); }),
  };
  connectWalletConnect.mockResolvedValue({
    address: 'SolanaPublicAddress',
    provider,
    name: 'Phantom',
  });
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);

  await act(async () => {
    root.render(<WalletProvider><CaptureWallet /></WalletProvider>);
  });
  await act(async () => {
    await window.__capturedWalletContext.connect('solana', 'walletconnect');
    await Promise.resolve();
    await Promise.resolve();
  });

  expect(connectWalletConnect).toHaveBeenCalledWith('solana');
  expect(subscribeWalletConnectSession).toHaveBeenCalledWith('solana', expect.any(Function));
  expect(provider.on).not.toHaveBeenCalled();
  expect(window.__capturedWalletContext.wallet).toMatchObject({
    name: 'Phantom',
    chain: 'solana',
    address: 'SolanaPublicAddress',
    connection: 'walletconnect',
  });
  expect(localStorage.getItem('feeless:last-wallet')).toBe(JSON.stringify({ type: 'solana', brand: 'walletconnect' }));

  await act(async () => {
    await window.__capturedWalletContext.disconnect();
  });
  expect(disconnectWalletConnect).toHaveBeenCalledWith('solana');
  expect(window.__capturedWalletContext.wallet).toBeNull();
  expect(localStorage.getItem('feeless:last-wallet')).toBeNull();

  await act(async () => { root.unmount(); });
  document.body.removeChild(host);
  delete window.__capturedWalletContext;
  localStorage.clear();
});

test('restored WalletConnect sessions work without environment configuration and skip the crashing provider event API', async () => {
  const previousProjectId = process.env.REACT_APP_REOWN_PROJECT_ID;
  delete process.env.REACT_APP_REOWN_PROJECT_ID;
  localStorage.setItem('feeless:last-wallet', JSON.stringify({ type: 'solana', brand: 'walletconnect' }));
  const provider = {
    request: jest.fn().mockResolvedValue('0x1'),
    on: jest.fn(() => { throw new Error("undefined is not an object (evaluating 'this.listeners[event].push')"); }),
  };
  subscribeWalletConnectSession.mockImplementation(async (type, onSession) => {
    onSession({ address: 'SolanaPublicAddress', provider, name: 'Phantom' });
    return jest.fn();
  });
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);

  await act(async () => {
    root.render(<WalletProvider><CaptureWallet /></WalletProvider>);
    await new Promise(resolve => setTimeout(resolve, 0));
  });

  expect(subscribeWalletConnectSession).toHaveBeenCalledWith('solana', expect.any(Function));
  expect(provider.on).not.toHaveBeenCalled();
  expect(window.__capturedWalletContext.wallet).toMatchObject({
    name: 'Phantom',
    chain: 'solana',
    address: 'SolanaPublicAddress',
    connection: 'walletconnect',
  });

  await act(async () => { root.unmount(); });
  document.body.removeChild(host);
  delete window.__capturedWalletContext;
  localStorage.clear();
  if (previousProjectId === undefined) delete process.env.REACT_APP_REOWN_PROJECT_ID;
  else process.env.REACT_APP_REOWN_PROJECT_ID = previousProjectId;
});
