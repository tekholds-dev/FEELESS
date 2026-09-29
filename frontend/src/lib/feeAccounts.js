import { relayConnection } from './launchRail';

// Creates the FEELESS fee token accounts (wSOL + USDC) owned by the fee wallet, paid and signed by the
// connected wallet in one approval. Idempotent: re-running just returns the existing accounts.
export const WSOL_MINT = 'So11111111111111111111111111111111111111112';
export const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';

// The fee accounts are deterministic (associated token accounts), so an existing setup is found with no transaction.
export async function findFeeAccounts(owner) {
  const [{ PublicKey }, spl] = await Promise.all([import('@solana/web3.js'), import('@solana/spl-token')]);
  const ownerKey = new PublicKey(owner);
  const [sol, usdc] = [WSOL_MINT, USDC_MINT].map(m => spl.getAssociatedTokenAddressSync(new PublicKey(m), ownerKey, true).toBase58());
  return { sol, usdc };
}

export async function createFeeAccounts({ provider, payer, owner, onStatus }) {
  const { web3, connection } = await relayConnection();
  const spl = await import('@solana/spl-token');
  const payerKey = new web3.PublicKey(payer);
  const ownerKey = new web3.PublicKey(owner);
  const accounts = [WSOL_MINT, USDC_MINT].map(m => ({ mint: new web3.PublicKey(m), address: spl.getAssociatedTokenAddressSync(new web3.PublicKey(m), ownerKey, true) }));
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
  const tx = new web3.Transaction({ feePayer: payerKey, recentBlockhash: blockhash });
  accounts.forEach(a => tx.add(spl.createAssociatedTokenAccountIdempotentInstruction(payerKey, a.address, ownerKey, a.mint)));
  onStatus?.('Checking…');
  const sim = await connection.simulateTransaction(new web3.VersionedTransaction(tx.compileMessage()), { sigVerify: false });
  if (sim.value.err) throw new Error('Simulation failed: the paying wallet needs about 0.005 SOL.');
  onStatus?.('Approve in your wallet…');
  const signed = await provider.signTransaction(tx);
  const sig = await connection.sendRawTransaction(signed.serialize(), { skipPreflight: true, maxRetries: 3 });
  onStatus?.('Confirming…');
  for (let i = 0; i < 60; i++) {
    const st = (await connection.getSignatureStatuses([sig])).value[0];
    if (st?.err) throw new Error('Transaction failed on-chain. Nothing was created.');
    if (['confirmed', 'finalized'].includes(st?.confirmationStatus)) return { sol: accounts[0].address.toBase58(), usdc: accounts[1].address.toBase58(), signature: sig };
    if ((await connection.getBlockHeight('confirmed')) > lastValidBlockHeight) throw new Error('Transaction expired before landing. Try again.');
    await new Promise(r => setTimeout(r, 1500));
  }
  throw new Error('Still confirming. Check your wallet activity, then press the button again (it is safe to repeat).');
}
