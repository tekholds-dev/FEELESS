import { relayConnection, signSend } from './launchRail';

// 🛡 Revoke a token approval: one SPL `Revoke` on your own token account (no one else's key, nothing moves) — simulated first, your wallet signs.
export async function revokeApproval({ provider, owner, account, program, onStatus }) {
  const [{ web3, connection }, spl] = await Promise.all([relayConnection(), import('@solana/spl-token')]);
  const ownerKey = new web3.PublicKey(owner);
  const tx = new web3.Transaction().add(spl.createRevokeInstruction(new web3.PublicKey(account), ownerKey, [], new web3.PublicKey(program)));
  return signSend(web3, connection, provider, tx, ownerKey, [], onStatus);
}
// pure: what one approval means in words
export const approvalLine = a => `${a.delegate.slice(0, 4)}…${a.delegate.slice(-4)} can move ${a.amount ?? 'some'} of ${a.mint.slice(0, 4)}…${a.mint.slice(-4)} (you hold ${a.balance ?? '?'})`;
