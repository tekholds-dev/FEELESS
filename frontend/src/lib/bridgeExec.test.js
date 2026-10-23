import { checkSolQuote, routeVitals, spendOk, trackBridge, executeSolRoute, SOLANA_ID, SOL_NATIVE, SOL_USDC, RENT_SLACK, BRIDGE_CHAINS, tokenOf } from './bridgeExec';

const mockConn = { getLatestBlockhash: jest.fn(), getBalance: jest.fn(), simulateTransaction: jest.fn(), getSignatureStatuses: jest.fn(), getBlockHeight: jest.fn() };
const mockTx = { message: { staticAccountKeys: [{ toBase58: () => 'ME' }], recentBlockhash: 'OLD' } };
jest.mock('./launchRail', () => ({ relayConnection: async () => ({ connection: mockConn, web3: { VersionedTransaction: { deserialize: () => mockTx }, PublicKey: function P(a) { this.a = a; } } }) }));

const EVM = '0xAbC0000000000000000000000000000000000001';
const quote = (over = {}) => ({ feeless: { safety: { verified: true } }, transactionRequest: { data: 'AQID' }, tool: 'relaydepository', toolDetails: { name: 'Relay' },
  action: { fromChainId: SOLANA_ID, toChainId: 8453, fromAddress: 'ME', toAddress: EVM.toLowerCase(), fromAmount: '20000000', fromToken: { address: SOL_NATIVE, symbol: 'SOL', decimals: 9 }, toToken: { symbol: 'ETH', decimals: 18 } },
  estimate: { toAmount: '850000000000000', fromAmountUSD: '3.0', toAmountUSD: '2.9', executionDuration: 3, feeCosts: [{ amountUSD: '0.01' }], gasCosts: [{ amountUSD: '0.02' }] }, ...over });

test('the quote reads as four vitals: send, get, cost (with %), time', () => {
  const v = routeVitals(quote());
  expect(v).toMatchObject({ send: 0.02, sendSym: 'SOL', get: 0.00085, getSym: 'ETH', sendUsd: 3, getUsd: 2.9, feeUsd: 0.01, gasUsd: 0.02, secs: 3, tool: 'Relay' });
  expect(v.costUsd).toBeCloseTo(0.1); expect(v.costPct).toBeCloseTo(3.33, 1);
  expect(routeVitals(null)).toBeNull();
});

test('only a FEELESS-verified Solana quote for YOUR wallet, paying YOUR wallet, for the ticket on screen passes', () => {
  const t = { address: 'ME', payTo: EVM, fromToken: SOL_NATIVE, fromAmount: '20000000' };
  expect(() => checkSolQuote(quote(), t)).not.toThrow();
  expect(() => checkSolQuote(quote({ feeless: {} }), t)).toThrow(/verify/);
  expect(() => checkSolQuote(quote(), { ...t, address: 'SOMEONE' })).toThrow(/different wallet/);
  expect(() => checkSolQuote(quote(), { ...t, payTo: '0x0000000000000000000000000000000000000002' })).toThrow(/pays out/);
  expect(() => checkSolQuote(quote(), { ...t, fromAmount: '30000000' })).toThrow(/amount/);
  expect(() => checkSolQuote(quote(), { ...t, fromToken: SOL_USDC })).toThrow(/coin/);
});

test('the simulation may not spend more SOL than the quote (+ rent slack); token routes only rent', () => {
  expect(spendOk({ pre: 1e9, post: 1e9 - 20_000_000 - 5000, fromToken: SOL_NATIVE, fromAmount: '20000000' })).toBe(true);
  expect(spendOk({ pre: 1e9, post: 1e9 - 20_000_000 - RENT_SLACK - 1, fromToken: SOL_NATIVE, fromAmount: '20000000' })).toBe(false);
  expect(spendOk({ pre: 1e9, post: 1e9 - 2_100_000, fromToken: SOL_USDC, fromAmount: '5000000' })).toBe(true);
  expect(spendOk({ pre: 1e9, post: 1e9 - 0.5e9, fromToken: SOL_USDC, fromAmount: '5000000' })).toBe(false);
  expect(spendOk({ pre: null, post: 1 })).toBe(true);   // no reading → the server's checks stand
});

test('Zora is off the list; USDC is the mint on Solana and the symbol on EVM', () => {
  expect(BRIDGE_CHAINS).not.toContain('zora'); expect(BRIDGE_CHAINS[0]).toBe('solana');
  expect(tokenOf('solana', 'usdc')).toBe(SOL_USDC); expect(tokenOf('base', 'usdc')).toBe('USDC'); expect(tokenOf('solana', 'native')).toBe(SOL_NATIVE);
});

test('tracking follows LI.FI until it lands, never resending', async () => {
  const seen = []; let n = 0;
  const fetchImpl = async url => { seen.push(url); n += 1; return { json: async () => (n < 3 ? { status: 'PENDING' } : { status: 'DONE', receiving: '0xabc', got: 0.00085 }) }; };
  const s = await trackBridge({ hash: 'SIG', fromChainId: SOLANA_ID, toChainId: 8453, fetchImpl, sleep: async () => {} });
  expect(s).toMatchObject({ status: 'DONE', receiving: '0xabc' }); expect(seen).toHaveLength(3); expect(seen[0]).toMatch(/txHash=SIG&fromChain=1151111081099710&toChain=8453/);
  expect((await trackBridge({ hash: 'S', fromChainId: 1, toChainId: 2, tries: 2, fetchImpl: async () => ({ json: async () => ({}) }), sleep: async () => {} })).status).toBe('PENDING');
});

describe('a Solana route: simulate → sign → FEELESS sends once → confirmed', () => {
  const provider = { signTransaction: jest.fn() };
  beforeEach(() => {   // CRA resets mock implementations before each test
    Object.values(mockConn).forEach(f => f.mockReset());
    provider.signTransaction.mockImplementation(async tx => ({ ...tx, serialize: () => new Uint8Array([9, 9]) }));
    mockConn.getLatestBlockhash.mockResolvedValue({ blockhash: 'FRESH', lastValidBlockHeight: 100 });
    mockConn.getBalance.mockResolvedValue(1e9); mockConn.getBlockHeight.mockResolvedValue(50);
    global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ signature: 'SIG' }) }));
  });
  test('clean simulation → fresh blockhash, signed, sent through FEELESS, confirmed', async () => {
    mockConn.simulateTransaction.mockResolvedValue({ value: { err: null, accounts: [{ lamports: 1e9 - 20_005_000 }] } });
    mockConn.getSignatureStatuses.mockResolvedValue({ value: [{ confirmationStatus: 'confirmed' }] });
    const steps = [];
    const out = await executeSolRoute({ quote: quote(), provider, address: 'ME', payTo: EVM, onStep: (t, p) => steps.push(p), sleep: async () => {} });
    expect(out).toEqual({ hash: 'SIG' }); expect(mockTx.message.recentBlockhash).toBe('FRESH');
    expect(mockConn.simulateTransaction.mock.calls[0][1]).toMatchObject({ sigVerify: false, accounts: { addresses: ['ME'] } });
    expect(global.fetch.mock.calls[0][0]).toMatch(/\/api\/lifi\/solana\/send$/); expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({ signed: 'CQk=' });
    expect(steps).toEqual(['sim', 'sign', 'source']);
  });
  test('a failing or over-spending simulation is never signed', async () => {
    mockConn.simulateTransaction.mockResolvedValueOnce({ value: { err: { InstructionError: [2, 'x'] }, logs: ['boom'] } });
    await expect(executeSolRoute({ quote: quote(), provider, address: 'ME', payTo: EVM })).rejects.toThrow(/nothing was signed/);
    mockConn.simulateTransaction.mockResolvedValueOnce({ value: { err: null, accounts: [{ lamports: 1e9 - 0.5e9 }] } });
    await expect(executeSolRoute({ quote: quote(), provider, address: 'ME', payTo: EVM })).rejects.toThrow(/more SOL/);
    expect(provider.signTransaction).not.toHaveBeenCalled(); expect(global.fetch).not.toHaveBeenCalled();
  });
  test('a quote paying someone else never reaches the wallet; a refused send surfaces the server reason', async () => {
    await expect(executeSolRoute({ quote: quote(), provider, address: 'ME', payTo: '0x0000000000000000000000000000000000000009' })).rejects.toThrow(/pays out/);
    mockConn.simulateTransaction.mockResolvedValue({ value: { err: null, accounts: [{ lamports: 1e9 - 20_005_000 }] } });
    global.fetch = jest.fn(async () => ({ ok: false, json: async () => ({ detail: 'This transaction was not quoted by FEELESS' }) }));
    await expect(executeSolRoute({ quote: quote(), provider, address: 'ME', payTo: EVM })).rejects.toThrow(/not quoted/);
  });
});
