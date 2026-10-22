import React, { useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { approvalLine, revokeApproval } from '../lib/revoke';
import '../styles/defence.css';

// 🛡 APPROVALS CHECK (owner, 2026-10-21: "real web3 defence … drainers, approvals"): which of YOUR token accounts let another address move your
// tokens (an SPL delegate — the thing a drainer leaves behind). One tap revokes it: your wallet signs a Revoke on your own account, nothing moves.
export function ApprovalsCheck({ compact = false }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [st, setSt] = useState('');
  const sol = wallet?.chain === 'solana' && wallet?.address;
  const check = async () => {
    if (!sol) { await connect?.('solana'); return; }
    setBusy('check');
    try { const r = await fetch(apiUrl(`/api/reputation/approvals/${wallet.address}`)); const b = await r.json(); if (!r.ok) throw new Error(b.detail || 'Check failed'); setD(b); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  const revoke = async a => {
    setBusy(a.account);
    try { await revokeApproval({ provider, owner: wallet.address, account: a.account, program: a.program, onStatus: setSt }); toast.success('🛡 Approval revoked'); setD(x => ({ ...x, approvals: x.approvals.filter(y => y.account !== a.account) })); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); setSt(''); }
  };
  const n = d?.approvals?.length;
  return <section className={`apc ${compact ? 'is-compact' : ''} ${n ? 'is-risk' : d ? 'is-safe' : ''}`} data-testid="approvals-check">
    <header><span className="apc-shield" aria-hidden="true"><i /></span><b>🛡 APPROVALS</b><small>who can move your tokens besides you</small>
      <button type="button" className="m-btn" disabled={!!busy} onClick={check} data-tip="Reads your token accounts on Solana — nothing is signed" data-testid="apc-check">{busy === 'check' ? 'Checking…' : sol ? (d ? 'Check again' : 'Check my wallet') : 'Connect wallet'}</button></header>
    {d && !n ? <p className="apc-ok">✅ No approvals. Nothing can move your tokens but you.</p> : null}
    {n ? <ul className="apc-list">{d.approvals.map((a, i) => <li key={a.account} style={{ '--i': i }}><span className="apc-dot" aria-hidden="true" /><span>{approvalLine(a)}</span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => revoke(a)} data-tip="Your wallet signs a Revoke on your own token account — simulated first" data-testid={`apc-revoke-${i}`}>{busy === a.account ? '…' : 'Revoke'}</button></li>)}</ul> : null}
    {st ? <p className="apc-st" aria-live="polite">{st}</p> : null}
  </section>;
}
