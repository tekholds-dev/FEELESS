import { executeMetaLaunchPlan, getLaunchMint, getLaunchProviderReadiness, getSolanaExplorerUrl, META_LAUNCH_STEPS, recheckMetaLaunchSignature, requestMetaLaunchPlan } from './launchpads';

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
  const transactions = ['token', 'curve', 'liquidity', 'fee', 'buyback', 'holder', 'airdrop'].map(id => ({ id, transaction: 'unsigned-base64' }));
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ provider: { approved: true }, transactions }),
  });

  const form = {
    name: 'Meta Coin',
    symbol: 'meta',
    supply: '1000',
    openingMarketCap: '35',
    curveType: 'linear',
    graduationTarget: '85',
    liquidityPair: 'SOL',
    swapFee: '1',
    creatorFeeShare: '50',
    holderRewardShare: '0',
    buybackBurnShare: '50',
    antiSniperTax: '50',
    antiSniperWindow: '6',
    devBuyAmount: '0',
    migrationVenue: 'raydium-cpmm',
    liquidityLock: 'permanent',
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
      openingMarketCap: 35,
      curveType: 'linear',
      graduationTarget: 85,
      liquidityPair: 'SOL',
      swapFee: 1,
      creatorFeeShare: 50,
      holderRewardShare: 0,
      buybackBurnShare: 50,
      antiSniperTax: 50,
      antiSniperWindowSeconds: 6,
      devBuyAmount: 0,
      migrationVenue: 'raydium-cpmm',
      liquidityLock: 'permanent',
      holderAllocation: 10,
      airdropAmount: 5,
      airdropRecipients: ['wallet-one', 'wallet-two'],
    },
  });
  expect(JSON.stringify(body)).not.toMatch(/private|secret|key/i);
});

test('executes an approved provider seven-step plan with explorer links and its returned mint', async () => {
  process.env.REACT_APP_LAUNCH_API_URL = 'https://provider.example/launch';
  process.env.REACT_APP_SOLANA_RPC_URL = 'https://rpc.example';
  process.env.REACT_APP_LAUNCH_PROVIDER_APPROVED = 'true';
  process.env.REACT_APP_LAUNCH_NETWORK = 'Solana devnet';
  const stepIds = ['token', 'curve', 'liquidity', 'fee', 'buyback', 'holder', 'airdrop'];
  const signatures = stepIds.map(id => `${id}-signature`);
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      provider: { approved: true },
      mint: 'provider-returned-mint',
      transactions: stepIds.map(id => ({ id, transaction: 'AA==' })),
    }),
  });
  const connection = {
    sendRawTransaction: jest.fn()
      .mockResolvedValueOnce(signatures[0])
      .mockResolvedValueOnce(signatures[1])
      .mockResolvedValueOnce(signatures[2])
      .mockResolvedValueOnce(signatures[3])
      .mockResolvedValueOnce(signatures[4])
      .mockResolvedValueOnce(signatures[5])
      .mockResolvedValueOnce(signatures[6]),
    confirmTransaction: jest.fn().mockResolvedValue({ value: { err: null } }),
  };
  const provider = {
    signTransaction: jest.fn().mockResolvedValue({ serialize: () => Uint8Array.from([1]) }),
  };
  const wallet = { chain: 'solana', address: 'wallet-address' };
  const form = {
    name: 'Meta Coin',
    symbol: 'META',
    supply: '1000',
    openingMarketCap: '35',
    curveType: 'linear',
    graduationTarget: '85',
    liquidityPair: 'SOL',
    swapFee: '1',
    creatorFeeShare: '50',
    holderRewardShare: '0',
    buybackBurnShare: '50',
    antiSniperTax: '50',
    antiSniperWindow: '6',
    devBuyAmount: '0',
    migrationVenue: 'raydium-cpmm',
    liquidityLock: 'permanent',
    holderAllocation: '10',
    airdropAmount: '5',
    airdropRecipients: 'wallet-one',
  };

  const plan = await requestMetaLaunchPlan(form, wallet);
  const result = await executeMetaLaunchPlan(plan, { provider, wallet, connection });

  expect(result).toMatchObject({
    state: 'confirmed',
    mint: 'provider-returned-mint',
  });
  expect(result.results).toEqual(stepIds.map((id, index) => ({
    id,
    label: META_LAUNCH_STEPS[index].label,
    state: 'confirmed',
    signature: signatures[index],
    explorerUrl: `https://explorer.solana.com/tx/${signatures[index]}?cluster=devnet`,
  })));
  expect(global.fetch).toHaveBeenCalledWith('https://provider.example/launch/prepare', expect.anything());
  expect(provider.signTransaction).toHaveBeenCalledTimes(7);
  expect(connection.sendRawTransaction).toHaveBeenCalledTimes(7);
  expect(connection.confirmTransaction).toHaveBeenCalledTimes(7);
});

test('keeps pending and failed execution results link-free', async () => {
  const provider = {
    signTransaction: jest.fn().mockResolvedValue({ serialize: () => Uint8Array.from([1]) }),
  };
  const wallet = { chain: 'solana', address: 'wallet-address' };
  const plan = { transactions: [{ id: 'token', transaction: 'AA==' }] };

  const pending = await executeMetaLaunchPlan(plan, {
    provider,
    wallet,
    connection: {
      sendRawTransaction: jest.fn().mockResolvedValue('pending-signature'),
      confirmTransaction: jest.fn().mockResolvedValue({ value: null }),
    },
  });
  const failed = await executeMetaLaunchPlan(plan, {
    provider,
    wallet,
    connection: {
      sendRawTransaction: jest.fn().mockResolvedValue('failed-signature'),
      confirmTransaction: jest.fn().mockResolvedValue({
        value: { err: { InstructionError: [0, 'Custom'] } },
      }),
    },
  });

  expect(pending.results[0]).toMatchObject({ state: 'pending', signature: 'pending-signature' });
  expect(pending.results[0]).not.toHaveProperty('explorerUrl');
  expect(failed.results[0]).toMatchObject({ state: 'failed', signature: 'failed-signature' });
  expect(failed.results[0]).not.toHaveProperty('explorerUrl');
});
