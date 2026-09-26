import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Copy, Gift } from 'lucide-react';
import { Hint } from './Hint';
import { useWallet } from '../hooks/useWallet';

export function InviteCard({ address }) {
  const [d, setD] = useState(null);
  const [site, setSite] = useState('');
  useEffect(() => { if (address) fetch(`/api/reputation/referral/${address}`).then(r => r.json()).then(setD).catch(() => {}); fetch('/api/reputation/site').then(r => r.json()).then(x => setSite(x.publicUrl || '')).catch(() => {}); }, [address]);
  if (!address || !d) return null;
  const local = /localhost|127\.0\.0\.1/.test(window.location.hostname);
  const base = site || (local ? '' : window.location.origin);
  const link = base ? `${base}/r/${d.code}` : `Invite code: ${d.code}`;
  const copy = () => { navigator.clipboard?.writeText(link).then(() => toast.success('Invite link copied')).catch(() => toast(link)); };
  return <section className="wp-card invite-card" data-testid="invite-card">
    <div className="wpj-head"><h3><Gift size={15} /> Your invite link <Hint text="Friends are credited once when they first sign in to chat. 3 invites = Recruiter badge, each invite = +75 points." /></h3><span className="wpj-count"><b>{d.invited}</b> invited</span></div>
    <div className="invite-link"><code>{link}</code><button type="button" className="btn-primary" onClick={copy}><Copy size={13} />Copy</button></div>
    {!base && <p className="wp-bio">Your code is ready — the full link appears once FEELESS HQ sets the public site domain.</p>}
    <p className="wp-bio">Friends who open your link and sign in to chat are credited to you — invite 3 for the 📣 Recruiter badge, 10 for Legendary Recruiter.</p>
    {d.recent?.length > 0 && <div className="invite-recent">{d.recent.map(r => <a key={r.address} href={`/terminal/profile/${r.address}`}>{r.address.slice(0, 4)}…{r.address.slice(-4)}</a>)}</div>}
  </section>;
}

// Settings version: uses whichever wallet is connected.
export function MyInviteCard() {
  const { wallet } = useWallet() || {};
  if (!wallet?.address) return <section className="wp-card invite-card"><h3><Gift size={15} /> Your invite link</h3><p className="wp-bio">Connect a wallet to get your personal invite link.</p></section>;
  return <InviteCard address={wallet.address} />;
}
