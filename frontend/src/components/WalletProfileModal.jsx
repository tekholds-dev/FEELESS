import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, UserRound, Pencil, ArrowUpRight } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';

// Quick profile window: who you are on FEELESS at a glance, one tap to your profile or its editor.
// Editing happens on the profile page itself (the single source of truth), so changes always show.
export default function WalletProfileModal({ open, onClose }) {
  const { wallet } = useWallet() || {};
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [trust, setTrust] = useState(null);
  const address = wallet?.address;
  useEffect(() => {
    if (!open || !address) return;
    fetch(apiUrl(`/api/reputation/profile/${address}`)).then(r => r.json()).then(d => setP(d.profile || d)).catch(() => setP({}));
    fetch(apiUrl(`/api/reputation/trust/${address}`)).then(r => r.json()).then(d => setTrust(d.score)).catch(() => {});
  }, [open, address]);
  if (!open) return null;
  const go = edit => { onClose?.(); navigate(`/terminal/profile/${address}${edit ? '?edit=1' : ''}`); };
  return <div className="profile-quick-backdrop" onClick={onClose} role="dialog" aria-modal="true" data-testid="wallet-profile-modal">
    <div className="profile-quick" onClick={e => e.stopPropagation()}>
      <button type="button" className="profile-quick-x" onClick={onClose} aria-label="Close"><X size={16} /></button>
      {!address ? <p className="wp-bio">Connect a wallet to see your profile.</p> : <>
        <div className="profile-quick-id">
          {p?.avatarUrl ? <img src={p.avatarUrl} alt="" /> : <span><UserRound size={26} /></span>}
          <div><b>{p?.displayName || `${address.slice(0, 5)}…${address.slice(-4)}`}</b><small>{p?.handle ? `@${p.handle}` : address}</small></div>
          {trust != null && <em className={trust >= 60 ? 'good' : trust < 40 ? 'bad' : ''}>{trust}<small>trust</small></em>}
        </div>
        {p?.bio && <p className="profile-quick-bio">{p.bio}</p>}
        <div className="profile-quick-actions">
          <button type="button" className="btn-primary" onClick={() => go(false)} data-testid="goto-profile"><ArrowUpRight size={15} />Go to profile</button>
          <button type="button" className="btn-outline" onClick={() => go(true)}><Pencil size={14} />Edit profile</button>
        </div>
      </>}
    </div>
  </div>;
}
