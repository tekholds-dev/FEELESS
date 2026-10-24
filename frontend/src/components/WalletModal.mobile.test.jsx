import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import WalletModal from './WalletModal';
import { getChatSession } from '../lib/chatSession';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('./ui/dialog', () => ({
  Dialog: ({ open, children }) => (open ? <div role="dialog">{children}</div> : null),
  DialogContent: ({ children }) => <div>{children}</div>,
  DialogTitle: ({ children }) => <h2>{children}</h2>,
  DialogDescription: ({ children }) => <p>{children}</p>,
}));

jest.mock('../hooks/useWallet', () => ({
  useWallet: () => globalThis.__mobileWalletContext,
  detectWallets: () => globalThis.__detectMobileWallets(),
  EVM_CHAINS: {},
  networkLabel: () => '',
  signWith: jest.fn(),
}));

jest.mock('../lib/chatSession', () => ({ getChatSession: jest.fn() }));

const mount = async props => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  await act(async () => { root.render(<WalletModal {...props} />); });
  return { host, root };
};

afterEach(() => {
  jest.useRealTimers();
  document.body.innerHTML = '';
  window.history.replaceState(null, '', '/');
  delete window.phantom;
  delete globalThis.__mobileWalletContext;
  delete globalThis.__detectMobileWallets;
  if (window.__previousUserAgent) Object.defineProperty(window.navigator, 'userAgent', window.__previousUserAgent);
  delete window.__previousUserAgent;
  getChatSession.mockReset();
});

function setUserAgent(value) {
  const previous = Object.getOwnPropertyDescriptor(window.navigator, 'userAgent');
  window.__previousUserAgent = previous;
  Object.defineProperty(window.navigator, 'userAgent', { configurable: true, value });
}

test('mobile wallet approval uses the wallet session flow and returns without a chat signature', async () => {
  setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)');
  globalThis.__detectMobileWallets = () => [];
  const connect = jest.fn().mockResolvedValue({ wallet: { chain: 'solana', address: 'PublicAddress' }, provider: {} });
  globalThis.__mobileWalletContext = { wallet: null, connect, disconnect: jest.fn(), switchTo: jest.fn(), linkCandidate: null, linkAccounts: jest.fn() };
  const onClose = jest.fn();

  const { host, root } = await mount({ open: true, onClose });
  expect(host.querySelector('[data-testid="wallet-mobile-connect-solana"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="wallet-mobile-connect-evm"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="wallet-install-phantom"]')).toBeNull();
  expect(host.querySelector('[data-testid="wallet-open-phantom"]')).toBeNull();

  await act(async () => {
    host.querySelector('[data-testid="wallet-mobile-connect-solana"]').click();
    await Promise.resolve();
  });
  expect(connect).toHaveBeenCalledWith('solana', 'walletconnect', undefined);
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(getChatSession).not.toHaveBeenCalled();
  await act(async () => { root.unmount(); });
});

test('desktop retains the existing direct install choices', async () => {
  setUserAgent('Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0');
  globalThis.__detectMobileWallets = () => [];
  globalThis.__mobileWalletContext = { wallet: null, connect: jest.fn(), disconnect: jest.fn(), switchTo: jest.fn(), linkCandidate: null, linkAccounts: jest.fn() };

  const { host, root } = await mount({ open: true, onClose: jest.fn() });
  expect(host.querySelector('[data-testid="wallet-install-phantom"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="wallet-mobile-connect-solana"]')).toBeNull();
  await act(async () => { root.unmount(); });
});
