import { getLaunchProviderReadiness, requestMetaLaunchPlan } from './launchpads';

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