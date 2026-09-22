import { executeMetaLaunchPlan, getLaunchMint, getLaunchProviderReadiness, getSolanaExplorerUrl, recheckMetaLaunchSignature, requestMetaLaunchPlan } from './launchpads';

let mockConnection;

jest.mock('@solana/web3.js', () => ({
  Connection: jest.fn(() => mockConnection),
  VersionedTransaction: {
    deserialize: () => {
      throw new Error('Use legacy transaction parser in this test.');
    },
  },
  Transaction: {
    from: () => ({ feePayer: { toBase58: () => 'wallet-address' } }),
  },
}));

const originalEnv = { ...process.env };

afterEach(() => {
  process.env = { ...originalEnv };
  jest.restoreAllMocks();
});

test('does not report a launch provider as ready without explicit approval and RPC', () => {
  delete process.env.REACT_APP_LAUNCH_API_URL;
  delete process.env.REACT_APP_SOLANA_RPC_URL;
  delete process.env.REACT_APP_LAUNCH_PROVIDER_APPROVED;
  expect(getLaunchProviderReadiness()).toMatchObject({
    ready: false,
    providerReady: false,
    rpcReady: false,
  });
});

test('builds explorer links for confirmed transactions and created mints', () => {
  expect(getSolanaExplorerUrl('signature-value', 'tx', 'Solana devnet')).toBe('https://explorer.solana.com/tx/signature-value?cluster=devnet');
  expect(getSolanaExplorerUrl('mint-value', 'address', 'Solana mainnet-beta')).toBe('https://explorer.solana.com/address/mint-value?cluster=mainnet-beta');
  expect(getSolanaExplorerUrl('', 'tx')).toBeNull();
  expect(getLaunchMint({ createdMint: 'mint-value' })).toBe('mint-value');
  expect(getLaunchMint({ launch: { mint: 'nested-mint' } })).toBe('nested-mint');
});

test('keeps a timed-out signature pending and never resubmits it during recovery', async () => {
  const connection = {
    getSignatureStatuses: jest.fn().mockResolvedValue({ value: [null] }),
    sendRawTransaction: jest.fn(),
  };

  const result = await recheckMetaLaunchSignature('timed-out-signature', {
    connection,
    label: 'Token creation',
  });

  expect(result).toEqual({
    state: 'pending',
    signature: 'timed-out-signature',
    detail: 'Token creation was submitted; confirmation is still pending. Check again before retrying.',
  });
  expect(connection.getSignatureStatuses).toHaveBeenCalledWith(
    ['timed-out-signature'],
    { searchTransactionHistory: true },
  );
  expect(connection.sendRawTransaction).not.toHaveBeenCalled();
});

test('reports a recovered signature as confirmed', async () => {
  const result = await recheckMetaLaunchSignature('confirmed-signature', {
    connection: {
      getSignatureStatuses: jest.fn().mockResolvedValue({
        value: [{ confirmationStatus: 'confirmed', err: null }],
      }),
    },
    label: 'Initial liquidity',
    network: 'Solana devnet',
  });

  expect(result).toMatchObject({
    state: 'confirmed',
    signature: 'confirmed-signature',
    explorerUrl: 'https://explorer.solana.com/tx/confirmed-signature?cluster=devnet',
  });
});

test('reports a recovered signature as failed when RPC returns an on-chain error', async () => {
  const result = await recheckMetaLaunchSignature('failed-signature', {
    connection: {
      getSignatureStatuses: jest.fn().mockResolvedValue({
        value: [{ confirmationStatus: 'confirmed', err: { InstructionError: [0, 'Custom'] } }],
      }),
    },
    label: 'Fee policy',
  });

  expect(result).toEqual({
    state: 'failed',
    signature: 'failed-signature',
    detail: 'Fee policy failed on-chain.',
  });
});

test('preserves a submitted signature when confirmation times out', async () => {
  mockConnection = {
    sendRawTransaction: jest.fn().mockResolvedValue('timeout-signature'),
    confirmTransaction: jest.fn().mockRejectedValue(Object.assign(
      new Error('Transaction confirmation timed out'),
      { name: 'TransactionExpiredTimeoutError' },
    )),
  };
  const onStep = jest.fn();

  const result = await executeMetaLaunchPlan({
    transactions: [{ id: 'token', transaction: 'AA==' }],
  }, {
    provider: {
      signTransaction: jest.fn().mockResolvedValue({ serialize: () => Uint8Array.from([1]) }),
    },
    wallet: { chain: 'solana', address: 'wallet-address' },
    onStep,
  });

  expect(result).toMatchObject({
    state: 'pending',
    detail: 'Token creation was submitted, but confirmation timed out. Check its signature before retrying.',
    results: [{
      id: 'token',
      state: 'pending',
      signature: 'timeout-signature',
    }],
  });
  expect(mockConnection.sendRawTransaction).toHaveBeenCalledTimes(1);
  expect(onStep).toHaveBeenLastCalledWith('token', expect.objectContaining({
    state: 'pending',
    signature: 'timeout-signature',
  }));
});

test('prepares an unsigned five-step plan without accepting private key material', async () => {
  process.env.REACT_APP_LAUNCH_API_URL = 'https://provider.example/launch/';
  process.env.REACT_APP_SOLANA_RPC_URL = 'https://rpc.example';
  process.env.REACT_APP_LAUNCH_PROVIDER_APPROVED = 'true';
  const transactions = ['token', 'liquidity', 'fee', 'holder', 'airdrop'].map(id => ({ id, transaction: 'unsigned-base64' }));
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ provider: { approved: true }, transactions }),
  });

  const form = {
    name: 'Meta Coin',
    symbol: 'meta',
    supply: '1000',
    decimals: '9',
    liquidityPair: 'SOL',
    liquidityAmount: '1',
    buyTax: '0',
    sellTax: '1',
    holderAllocation: '10',
    airdropAmount: '5',
    airdropRecipients: 'wallet-one\nwallet-two',
  };
  await requestMetaLaunchPlan(form, { chain: 'solana', address: 'wallet-address' });
  const body = JSON.parse(global.fetch.mock.calls[0][1].body);

  expect(global.fetch).toHaveBeenCalledWith('https://provider.example/launch/prepare', expect.anything());
  expect(body).toEqual({
    wallet: 'wallet-address',
    chain: 'solana',
    launch: {
      name: 'Meta Coin',
      symbol: 'META',
      supply: '1000',
      decimals: 9,
      liquidityPair: 'SOL',
      liquidityAmount: '1',
      buyTax: 0,
      sellTax: 1,
      holderAllocation: 10,
      airdropAmount: 5,
      airdropRecipients: ['wallet-one', 'wallet-two'],
    },
  });
  expect(JSON.stringify(body)).not.toMatch(/private|secret|key/i);
});