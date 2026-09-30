import { checkQuote } from './lifiExec';

const me = '0xAbC0000000000000000000000000000000000001';
const base = () => ({ transactionRequest: { to: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE', chainId: 8453 }, estimate: {}, action: { fromAddress: me, toAddress: me } });

test('a clean LI.FI route to your own wallet passes', () => {
  expect(() => checkQuote(base(), { address: me.toLowerCase() })).not.toThrow();
});

test('payout to someone else is refused', () => {
  const q = base(); q.action.toAddress = '0x0000000000000000000000000000000000000bad';
  expect(() => checkQuote(q, { address: me })).toThrow(/different wallet/);
});

test('non-LI.FI contract, other wallet or odd approval are refused', () => {
  const a = base(); a.transactionRequest.to = '0x0000000000000000000000000000000000000bad';
  expect(() => checkQuote(a, { address: me })).toThrow(/LI.FI/);
  expect(() => checkQuote(base(), { address: '0x0000000000000000000000000000000000000002' })).toThrow(/different wallet/);
  const c = base(); c.estimate.approvalAddress = '0x0000000000000000000000000000000000000bad';
  expect(() => checkQuote(c, { address: me })).toThrow(/approval/);
});
