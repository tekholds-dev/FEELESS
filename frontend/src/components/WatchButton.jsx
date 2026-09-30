import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession, readChatSession } from '../lib/chatSession';

// One tap from any case file or profile: alerts on this wallet's next buys and sells (suspect dumps called out).
let listCache = null;
export function WatchButton({ target, className = '' }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const session = wallet?.address && readChatSession(wallet.address);
    if (!session) return;
    if (listCache?.addr !== wallet.address) listCache = { addr: wallet.address, p: fetch(apiUrl(`/api/reputation/wallet-watch?address=${wallet.address}&session=${encodeURIComponent(session)}`)).then(r => r.json()).catch(() => ({ targets: [] })) };
    listCache.p.then(d => setOn((d.targets || []).some(t => t.address === target)));
  }, [wallet?.address, target]);
  if (!target || target === wallet?.address) return null;
  const toggle = async () => {
    if (!wallet?.address || wallet.chain !== 'solana') { connect?.('solana'); return; }
    setBusy(true);
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/wallet-watch'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, target, on: !on }) });
      const body = await r.json();
      if (!r.ok) throw new Error(body.detail || 'Could not update the watch.');
      listCache = null; setOn(!on);
      toast.success(!on ? '👁 Watching: you get an alert on its next trade.' : 'Stopped watching.');
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <button type="button" className={`watch-btn ${on ? 'on' : ''} ${className}`} data-testid="watch-wallet" disabled={busy} aria-pressed={on} onClick={toggle}>{on ? '👁 Watching' : '👁 Watch wallet'}</button>;
}
