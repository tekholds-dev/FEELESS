import { detectWallets } from './useWallet';

test('EIP-6963 wallets are detected by name, Crypto.com gets its own row', () => {
  const mm = { request: jest.fn() }; const cdc = { request: jest.fn() }; const rabby = { request: jest.fn() };
  const announce = (rdns, name, provider) => window.dispatchEvent(Object.assign(new Event('eip6963:announceProvider'), { detail: { info: { rdns, name, icon: '' }, provider } }));
  announce('io.metamask', 'MetaMask', mm);
  announce('com.crypto.wallet', 'Crypto.com Onchain', cdc);
  announce('io.rabby', 'Rabby Wallet', rabby);
  const found = detectWallets();
  expect(found.find(w => w.brand === 'cryptocom')).toBeTruthy();
  expect(found.find(w => w.label === 'MetaMask').brand).toBe('eip6963:io.metamask');
  expect(found.find(w => w.label === 'Rabby Wallet')).toBeTruthy();
  expect(found.filter(w => w.label === 'Crypto.com Onchain')).toHaveLength(1);
});
