import { keepReceipt } from './receipts';
import { relayConnection } from './launchRail';

// Airdrops / holder fee-shares sent straight from the owner's wallet: transfers are packed into
// a few transactions, each simulated, then the wallet approves them all in one prompt.
const PER_TX = { sol: 18, spl: 6 };

async function confirm(connection, sig, lastValidBlockHeight) {
  for (let i = 0; i < 60; i++) {
    const st = (await connection.getSignatureStatuses([sig])).value[0];
    if (st?.err) throw new Error(`Batch transaction failed: ${JSON.stringify(st.err)}`);
    if (st?.confirmationStatus === 'confirmed' || st?.confirmationStatus === 'finalized') return;
    if ((await connection.getBlockHeight('confirmed')) > lastValidBlockHeight) throw new Error(`Transaction ${sig} expired before landing; the rest were not sent.`);
    await new Promise(r => setTimeout(r, 1500));
  }
}

export async function batchSend({ provider, owner, mint, recipients, onStatus, kind = 'airdrop', source = null }) {
  const { web3, connection } = await relayConnection();
  const spl = await import('@solana/spl-token');
  const payer = new web3.PublicKey(owner);
  const isSol = !mint;
  let decimals = 9, programId, mintKey;
  if (!isSol) {
    mintKey = new web3.PublicKey(mint);
    const info = await connection.getParsedAccountInfo(mintKey);
    decimals = info.value?.data?.parsed?.info?.decimals;
    if (decimals == null) throw new Error('Could not read the token mint.');
    programId = info.value.owner;
  }
  const src = isSol ? null : source ? new web3.PublicKey(source) : spl.getAssociatedTokenAddressSync(mintKey, payer, true, programId);
  const size = isSol ? PER_TX.sol : PER_TX.spl;
  const chunks = [];
  for (let i = 0; i < recipients.length; i += size) chunks.push(recipients.slice(i, i + size));
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
  const txs = chunks.map(chunk => {
    const tx = new web3.Transaction({ feePayer: payer, recentBlockhash: blockhash });
    chunk.forEach(r => {
      const to = new web3.PublicKey(r.address);
      const raw = BigInt(Math.round(Number(r.amount) * 10 ** decimals));
      if (isSol) { tx.add(web3.SystemProgram.transfer({ fromPubkey: payer, toPubkey: to, lamports: raw })); return; }
      const dst = spl.getAssociatedTokenAddressSync(mintKey, to, true, programId);
      tx.add(spl.createAssociatedTokenAccountIdempotentInstruction(payer, dst, to, mintKey, programId));
      tx.add(spl.createTransferCheckedInstruction(src, mintKey, dst, payer, raw, decimals, [], programId));
    });
    return tx;
  });
  onStatus?.(`Dry-running ${txs.length} transaction${txs.length > 1 ? 's' : ''}…`);
  for (const tx of txs) {
    const sim = await connection.simulateTransaction(new web3.VersionedTransaction(tx.compileMessage()), { sigVerify: false });
    if (sim.value.err) throw new Error(`Simulation failed (check your balance): ${JSON.stringify(sim.value.err)}`);
  }
  onStatus?.('Approve in your wallet…');
  const signed = provider.signAllTransactions ? await provider.signAllTransactions(txs) : await Promise.all(txs.map(t => provider.signTransaction(t)));
  const sigs = [];
  for (const [i, tx] of signed.entries()) {
    onStatus?.(`Sending ${i + 1}/${signed.length}…`);
    const sig = await connection.sendRawTransaction(tx.serialize(), { skipPreflight: true, maxRetries: 3 });
    await confirm(connection, sig, lastValidBlockHeight);
    keepReceipt(sig, owner, kind);
    sigs.push(sig);
  }
  return sigs;
}
