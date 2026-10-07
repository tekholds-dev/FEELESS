import '../styles/fuseMoney.css';
import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { uploadImage, useAdmin } from '../lib/adminCall';
import { apiUrl } from '../lib/api';

// 🪪 The creator edits one of their own Circle wallets' public profile (name, @handle, bio, picture, cover). The server checks
// the wallet is one of the owner's Circle wallets and that the session is the creator's; this file only draws the form.
export const profileDraft = w => ({ address: w.address, profile: { name: w.profile?.name || w.name || '', handle: w.profile?.handle || '', bio: w.profile?.bio || '', avatar: w.profile?.avatar || '', banner: w.profile?.banner || '' } });

export function CircleProfileForm({ call, start, onDone }) {
  const [edit, setEdit] = useState(start);
  const [up, setUp] = useState('');
  useEffect(() => { setEdit(start); }, [start]);
  const save = () => call('/admin/circle/profile', { method: 'POST', body: JSON.stringify({ address: edit.address, profile: edit.profile }) })
    .then(() => { toast.success('Profile saved'); onDone(true); }).catch(e => toast.error(e.message));
  return <div className="ff-detail" data-testid="cp-form"><b>✏️ {edit.address.slice(0, 6)}…</b>
      {['name', 'handle', 'bio'].map(k => <label key={k} className="fw-grid">{k}<input className="m-input" value={edit.profile[k]} onChange={e => setEdit(x => ({ ...x, profile: { ...x.profile, [k]: e.target.value } }))} /></label>)}
      {[['avatar', 'Picture'], ['banner', 'Cover']].map(([k, label]) => <div key={k} className="fw-grid cp-img">{label}
        <span className="m-row">{edit.profile[k] && <img src={apiUrl(edit.profile[k])} alt="" className={`cp-thumb is-${k}`} />}
          <label className="m-btn cp-up">{up === k ? 'Uploading…' : '⬆ Upload image / GIF'}<input type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden disabled={!!up} data-testid={`cp-up-${k}`}
            onChange={async e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f) return; setUp(k); try { const url = await uploadImage(f); setEdit(x => ({ ...x, profile: { ...x.profile, [k]: url } })); toast.success(`${label} uploaded — press Save`); } catch (err) { toast.error(err.message || 'Upload failed'); } setUp(''); }} /></label>
          {edit.profile[k] && <button type="button" className="m-btn" onClick={() => setEdit(x => ({ ...x, profile: { ...x.profile, [k]: '' } }))}>Remove</button>}</span>
        <input className="m-input" placeholder="…or paste an https:// link" value={edit.profile[k]} onChange={e => setEdit(x => ({ ...x, profile: { ...x.profile, [k]: e.target.value } }))} /></div>)}
      <small className="m-note">GIFs stay animated. From the creator wallet a GIF can be any size (stills up to 25 MB).</small>
      <span className="m-row"><button type="button" className="m-btn primary m-go" onClick={save} data-testid="cp-save">Save profile</button><button type="button" className="m-btn" onClick={() => onDone(false)}>Cancel</button></span></div>;
}

// On a wallet's profile page: the creator's ✏️ button. Opens the same form in a pop-up when the wallet is one of their Circle wallets.
export function CircleProfileEditButton({ address, onSaved }) {
  const { isAdmin, call } = useAdmin();
  const [start, setStart] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (!start) return undefined; const on = e => e.key === 'Escape' && setStart(null); window.addEventListener('keydown', on); return () => window.removeEventListener('keydown', on); }, [start]);
  if (!isAdmin) return null;
  const open = () => { setBusy(true); call('/admin/circle/profiles').then(d => { const w = (d.wallets || []).find(x => x.address === address);
    if (w) setStart(profileDraft(w)); else toast.error('Not one of your Circle wallets — only those can be edited from the creator wallet.'); }).catch(e => toast.error(e.message)).finally(() => setBusy(false)); };
  return <><button type="button" className="btn-outline cpe-btn" onClick={open} disabled={busy} data-testid="cp-edit-here">{busy ? 'Opening…' : '✏️ Edit profile'}</button>
    {start && createPortal(<div className="cpe-shade" onClick={e => e.target === e.currentTarget && setStart(null)} data-testid="cp-pop"><div className="m-card cpe-pop" role="dialog" aria-label="Edit wallet profile">
      <CircleProfileForm call={call} start={start} onDone={saved => { setStart(null); if (saved && onSaved) onSaved(); }} /></div></div>, document.body)}</>;
}
