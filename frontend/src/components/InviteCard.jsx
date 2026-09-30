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
  const usd = v => `$${Number(v || 0).toFixed(Number(v) >= 1 ? 2 : 4)}`;
  return <section className="m-card is-hot m-stack invite-card" data-testid="invite-card">
    <div className="m-row cs-bar"><span className="m-label"><Gift size={13} /> YOUR INVITE LINK <Hint text="Friends are credited once when they first sign in to chat. 3 invites = Recruiter badge, each invite = +75 points, plus your % of their FEELESS fees." /></span>
      {d.pct > 0 && <span className="m-chip ok">you earn {d.pct}% of their fees</span>}</div>
    <div className="m-row"><code className="m-input invite-code">{link}</code><button type="button" className="m-btn primary" onClick={copy}><Copy size={13} />Copy</button></div>
    {!base && <p className="m-dim">Your code is ready — the full link appears once FEELESS HQ sets the public site domain.</p>}
    <div className="m-grid"><div className="m-stat"><small>Invited</small><b className="m-num">{d.invited}</b></div><div className="m-stat"><small>Trading</small><b className="m-num">{d.tradingInvitees || 0}</b></div>
      <div className="m-stat"><small>Earned</small><b className="m-num m-pos">{usd(d.earnedUsd)}</b>{d.earnedSol > 0 && <span className="m-dim">{d.earnedSol.toFixed(4)} SOL</span>}</div></div>
    <p className="m-dim">Invite 3 for the 📣 Recruiter badge, 10 for Legendary Recruiter{d.pct > 0 ? `, and earn ${d.pct}% of the FEELESS fees your invitees pay, forever` : ''}.</p>
    {d.recent?.length > 0 && <div className="m-row">{d.recent.map(r => <a key={r.address} className="m-chip" href={`/terminal/profile/${r.address}`}>{r.address.slice(0, 4)}…{r.address.slice(-4)}</a>)}</div>}
  </section>;
}

// Settings version: uses whichever wallet is connected.
export function MyInviteCard() {
  const { wallet } = useWallet() || {};
  if (!wallet?.address) return <section className="wp-card invite-card"><h3><Gift size={15} /> Your invite link</h3><p className="wp-bio">Connect a wallet to get your personal invite link.</p></section>;
  return <InviteCard address={wallet.address} />;
}
