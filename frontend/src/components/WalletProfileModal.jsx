import React, { useEffect, useMemo, useState } from 'react';
import { ExternalLink, Image, Link2, Lock, Save, ShieldAlert, UserRound, X } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { fetchOwnProfile, profileLabel, walletProof, PROFILE_API } from '../lib/profile';

const CATEGORIES = ['Trader', 'Builder', 'Artist', 'Collector', 'Researcher'];
const EMPTY = { displayName: '', username: '', bio: '', category: 'Trader', avatarUrl: '', backgroundUrl: '', xUrl: '', websiteUrl: '', isPrivate: false };

export default function WalletProfileModal({ open, onClose }) {
  const { wallet, signMessage } = useWallet();
  const [profile, setProfile] = useState(null);
  const [draft, setDraft] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!open || !wallet) return undefined;
    let cancelled = false;
    setBusy(true); setError(''); setSaved(false);
    fetchOwnProfile(wallet, signMessage)
      .then(({ profile: next }) => { if (!cancelled) { setProfile(next); setDraft({ ...EMPTY, ...next }); } })
      .catch(error => { if (!cancelled) setError(error.message || 'Could not load your profile.'); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [open, wallet?.address]); // eslint-disable-line react-hooks/exhaustive-deps

  const update = field => event => setDraft(current => ({ ...current, [field]: event.target.value }));
  const coverStyle = useMemo(() => draft.backgroundUrl ? { backgroundImage: `linear-gradient(120deg, #07140d99, #07140d55), url(${draft.backgroundUrl})` } : {}, [draft.backgroundUrl]);
  const save = async event => {
    event.preventDefault();
    if (!wallet || busy) return;
    setBusy(true); setError(''); setSaved(false);
    try {
      const proof = await walletProof(wallet, signMessage);
      const response = await fetch(`${PROFILE_API}/profile/save`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...proof, ...draft }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Profile could not be saved.');
      setProfile(data); setDraft({ ...EMPTY, ...data }); setSaved(true);
    } catch (nextError) {
      setError(nextError.message || 'Profile could not be saved.');
    } finally { setBusy(false); }
  };

  if (!open) return null;
  return <div className="profile-modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="profile-modal" role="dialog" aria-modal="true" aria-labelledby="profile-modal-title" data-testid="wallet-profile-modal">
      <div className="profile-modal-header"><div><span className="eyebrow"><UserRound size={14} />WALLET PROFILE</span><h2 id="profile-modal-title">Your identity on the trenches.</h2></div><button className="icon-btn" type="button" aria-label="Close profile" onClick={onClose}><X size={18} /></button></div>
      <div className="profile-preview">
        <div className="profile-cover" style={coverStyle}><span>CONNECTED WALLET</span></div>
        <div className="profile-preview-body"><div className="profile-picture">{draft.avatarUrl ? <img src={draft.avatarUrl} alt="" /> : <UserRound size={27} />}</div><div className="profile-preview-copy"><strong>{profileLabel({ ...draft, address: wallet?.address })}</strong><small>{wallet?.address}</small><div className="profile-badges"><span>{draft.category}</span>{draft.isPrivate && <span><Lock size={11} />Private</span>}</div></div></div>
        <div className="profile-preview-stats"><span><b>{profile?.flagCount ?? '—'}</b> flags</span><span><b>{draft.isPrivate ? 'Hidden' : 'Public'}</b> visibility</span><span><b>Signed</b> ownership</span></div>
      </div>
      <form className="profile-form" onSubmit={save}>
        <div className="profile-form-grid"><label>Display name<input value={draft.displayName} onChange={update('displayName')} maxLength={64} placeholder="How the room should know you" /></label><label>Username<input value={draft.username} onChange={update('username')} maxLength={32} placeholder="alpha_hunter" /></label></div>
        <label>Bio<textarea value={draft.bio} onChange={update('bio')} maxLength={160} rows={3} placeholder="What are you watching?" /></label>
        <label>Category<select value={draft.category} onChange={update('category')}>{CATEGORIES.map(category => <option key={category}>{category}</option>)}</select></label>
        <div className="profile-form-grid"><label><Image size={13} />Profile picture URL<input type="url" value={draft.avatarUrl} onChange={update('avatarUrl')} placeholder="https://..." /></label><label><Image size={13} />Background URL<input type="url" value={draft.backgroundUrl} onChange={update('backgroundUrl')} placeholder="https://..." /></label></div>
        <div className="profile-form-grid"><label><ExternalLink size={13} />X profile URL<input type="url" value={draft.xUrl} onChange={update('xUrl')} placeholder="https://x.com/..." /></label><label><Link2 size={13} />Website URL<input type="url" value={draft.websiteUrl} onChange={update('websiteUrl')} placeholder="https://..." /></label></div>
        <label className="profile-privacy-toggle"><span><b>Private profile</b><small>Hide your profile details and aggregate flag count from other wallets.</small></span><input type="checkbox" checked={draft.isPrivate} onChange={event => setDraft(current => ({ ...current, isPrivate: event.target.checked }))} /></label>
        {error && <div className="market-error" role="alert" data-testid="profile-error"><ShieldAlert size={15} />{error}</div>}
        {saved && <p className="profile-saved" role="status">Profile saved after wallet signature.</p>}
        <div className="profile-modal-actions"><small><Lock size={12} />Non-custodial. Your wallet signs the ownership proof.</small><button className="btn-primary" type="submit" disabled={busy || !wallet}><Save size={15} />{busy ? 'Waiting for signature…' : 'Save profile'}</button></div>
      </form>
    </section>
  </div>;
}