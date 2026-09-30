/**
 * @jest-environment node
 */
if (!globalThis.crypto?.getRandomValues) globalThis.crypto = require('crypto').webcrypto;
// Builds REAL Metaplex Core instructions (only the wallet/send step is faked): the collection + NFT transactions
// target the Core program, carry the right signers and never go out unsigned by the owner's wallet.
jest.mock('./launchRail', () => ({
  relayConnection: async () => ({ web3: require('@solana/web3.js'), connection: { rpcEndpoint: 'http://localhost/rpc' } }),
  signSend: (...a) => mockSend(...a),
}));
const mockSend = jest.fn(async () => '5sig');
const { coreCreateCollection, coreDrop } = require('./metaplexCore');
const CORE = 'CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d';
const OWNER = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU';

test('collection: Core program, owner pays, collection keypair co-signs', async () => {
  mockSend.mockClear();
  const r = await coreCreateCollection({ provider: {}, owner: OWNER, name: 'OG Cards', uri: 'https://f.xyz/c.json', royaltyBps: 500 });
  const [, , , tx, payer, extra] = mockSend.mock.calls[0];
  expect(tx.instructions[0].programId.toBase58()).toBe(CORE);
  expect(payer.toBase58()).toBe(OWNER);
  expect(extra[0].publicKey.toBase58()).toBe(r.address);
});

test('drop: one asset per wallet, 3 per transaction, each owned by its recipient', async () => {
  mockSend.mockClear();
  const to = Array.from({ length: 4 }, (_, i) => require('@solana/web3.js').Keypair.generate().publicKey.toBase58());
  const out = await coreDrop({ provider: {}, owner: OWNER, collection: to[0], name: 'OG', uriFor: n => `https://f.xyz/${n}.json`, recipients: to, start: 1 });
  expect(mockSend).toHaveBeenCalledTimes(2);
  expect(out[0].assets).toHaveLength(3); expect(out[1].assets).toHaveLength(1);
  expect(out.flatMap(o => o.assets).map(a => a.owner)).toEqual(to);
  expect(mockSend.mock.calls[0][3].instructions.every(ix => ix.programId.toBase58() === CORE)).toBe(true);
});
