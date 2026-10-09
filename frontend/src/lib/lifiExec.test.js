import { checkQuote, executeLifiBatch } from './lifiExec';

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

const TOK = '0x00000000000000000000000000000000000000aa';
const swapQ = (amt = '1000') => ({ transactionRequest: { to: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE', chainId: 25, data: '0xdead', value: '0x0' },
  estimate: { approvalAddress: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE' }, action: { fromAddress: me, toAddress: me, fromAmount: amt, fromChainId: 25, toChainId: 25, fromToken: { address: TOK, symbol: 'HYD', decimals: 18 } } });
const wallet = (caps, status = 200) => { const sent = []; return { sent, request: jest.fn(async ({ method, params }) => {
  if (method === 'eth_chainId') return '0x19';
  if (method === 'wallet_getCapabilities') { if (!caps) throw new Error('unsupported'); return caps; }
  if (method === 'eth_call') return '0x0';                       // no allowance yet
  if (method === 'wallet_sendCalls') { sent.push(params[0]); return { id: 'B1' }; }
  if (method === 'wallet_getCallsStatus') return { status, receipts: [] };
  throw new Error(`unexpected ${method}`); }) }; };

test('a wallet that can batch gets every approve + swap on a chain as ONE request', async () => {
  const w = wallet({ '0x19': { atomic: { status: 'supported' } } });
  const out = await executeLifiBatch({ quotes: [swapQ('1000'), swapQ('2000')], wallet: { address: me }, provider: w, waitMs: 0 });
  expect(out).toMatchObject({ id: 'B1', status: 'DONE' }); expect(w.sent).toHaveLength(1);
  const calls = w.sent[0].calls; expect(calls).toHaveLength(4); expect(w.sent[0].chainId).toBe('0x19');
  expect(calls[0].to).toBe(TOK); expect(calls[0].data.startsWith('0x095ea7b3')).toBe(true); expect(calls[0].data.endsWith((1000).toString(16).padStart(64, '0'))).toBe(true);   // the exact amount, never unlimited
  expect(calls[1]).toMatchObject({ to: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE', data: '0xdead' });
});

test('a plain wallet cannot batch → null (the caller sends one by one); a bad quote or a failed batch throws', async () => {
  expect(await executeLifiBatch({ quotes: [swapQ()], wallet: { address: me }, provider: wallet(null), waitMs: 0 })).toBeNull();
  expect(await executeLifiBatch({ quotes: [swapQ()], wallet: { address: me }, provider: wallet({ '0x19': {} }), waitMs: 0 })).toBeNull();
  const bad = swapQ(); bad.transactionRequest.to = '0x0000000000000000000000000000000000000bad';
  const w = wallet({ '0x19': { atomic: { status: 'ready' } } });
  await expect(executeLifiBatch({ quotes: [swapQ(), bad], wallet: { address: me }, provider: w, waitMs: 0 })).rejects.toThrow(/LI.FI/); expect(w.sent).toHaveLength(0);
  await expect(executeLifiBatch({ quotes: [swapQ()], wallet: { address: me }, provider: wallet({ '0x19': { atomic: { status: 'supported' } } }, 500), waitMs: 0 })).rejects.toThrow(/did not land/);
});
