/** @jest-environment node */
import * as web3 from '@solana/web3.js';
import { getAssociatedTokenAddressSync } from '@solana/spl-token';
import { createFeeAccounts, WSOL_MINT, USDC_MINT } from './feeAccounts';

const mockConnection = {
  getLatestBlockhash: async () => ({ blockhash: web3.Keypair.fromSeed(new Uint8Array(32).fill(9)).publicKey.toBase58(), lastValidBlockHeight: 100 }),
  simulateTransaction: async () => ({ value: { err: null } }),
  sendRawTransaction: jest.fn(async () => 'sig1'),
  getSignatureStatuses: async () => ({ value: [{ confirmationStatus: 'confirmed' }] }),
  getBlockHeight: async () => 1,
};
jest.mock('./launchRail', () => ({ relayConnection: async () => ({ web3: require("@solana/web3.js"), connection: mockConnection }) }));

test('creates the wSOL + USDC fee accounts owned by the fee wallet, paid by the signer, in one approval', async () => {
  const payer = web3.Keypair.fromSeed(new Uint8Array(32).fill(1));
  const owner = web3.Keypair.fromSeed(new Uint8Array(32).fill(2)).publicKey;
  const provider = { signTransaction: jest.fn(async tx => { tx.sign(payer); return tx; }) };
  const out = await createFeeAccounts({ provider, payer: payer.publicKey.toBase58(), owner: owner.toBase58() });
  expect(out.sol).toBe(getAssociatedTokenAddressSync(new web3.PublicKey(WSOL_MINT), owner, true).toBase58());
  expect(out.usdc).toBe(getAssociatedTokenAddressSync(new web3.PublicKey(USDC_MINT), owner, true).toBase58());
  expect(provider.signTransaction).toHaveBeenCalledTimes(1);
  const tx = provider.signTransaction.mock.calls[0][0];
  expect(tx.instructions).toHaveLength(2);
  expect(tx.feePayer.toBase58()).toBe(payer.publicKey.toBase58());
  expect(mockConnection.sendRawTransaction).toHaveBeenCalledTimes(1);
});
