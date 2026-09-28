import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { CROP } from '../../lib/cropImage';
import { apiUrl } from '../../lib/api';
import { UploadButton } from './WalletProfilePage';

const FIELDS = [['description', 'About this coin'], ['website', 'Website (https://)'], ['twitter', 'X / Twitter (https://)'], ['telegram', 'Telegram (https://)']];

// A coin's profile belongs to its creator wallet: shown to everyone, editable only after signing as that wallet.
export function CoinProfileClaim({ mint, creator }) {
  const { wallet, signMessage } = useWallet() || {};
  const [prof, setProf] = useState(null);
  const [draft, setDraft] = useState(null);
  useEffect(() => { fetch(apiUrl(`/api/reputation/coin-profile/${mint}`)).then(r => r.json()).then(setProf).catch(() => setProf({})); }, [mint]);
  const mine = !!wallet?.address && wallet.address === creator;
  const save = async () => {
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/coin-profile'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, mint, ...draft }) });
      const b = await r.json(); if (!r.ok) throw new Error(b.detail);
      setProf(b); setDraft(null); toast.success('Coin profile saved');
    } catch (e) { toast.error(e.message || 'Could not save'); }
  };
  if (!prof) return null;
  const links = [['website', '🌐'], ['twitter', '𝕏'], ['telegram', '✈']].filter(([k]) => prof[k]);
  return <div className="coin-claim" data-testid="coin-claim">
    {prof.bannerUrl && <img className="coin-claim-banner" src={prof.bannerUrl} alt="" />}
    {prof.claimedBy ? <><p>{prof.description}</p>{links.length > 0 && <div className="coin-claim-links">{links.map(([k, i]) => <a key={k} href={prof[k]} target="_blank" rel="noopener noreferrer">{i} {k}</a>)}</div>}<small className="wp-bio">✓ Claimed by the creator wallet</small></>
      : <small className="wp-bio">{mine ? "You created this coin — claim its profile below." : "Not claimed yet. Only the creator's wallet can claim it."}</small>}
    {mine && !draft && <button type="button" className="btn-outline" onClick={() => setDraft({ description: prof.description || '', bannerUrl: prof.bannerUrl || '', website: prof.website || '', twitter: prof.twitter || '', telegram: prof.telegram || '' })}>{prof.claimedBy ? 'Edit coin profile' : 'Claim coin profile'}</button>}
    {draft && <div className="coin-claim-form">
      <UploadButton label="Banner" shape={CROP.banner} onDone={url => setDraft(d => ({ ...d, bannerUrl: url }))} />
      {FIELDS.map(([k, l]) => k === 'description' ? <textarea key={k} maxLength={600} rows={3} placeholder={l} value={draft[k]} onChange={e => setDraft(d => ({ ...d, [k]: e.target.value }))} /> : <input key={k} placeholder={l} value={draft[k]} onChange={e => setDraft(d => ({ ...d, [k]: e.target.value }))} />)}
      <div className="coin-claim-act"><button type="button" className="btn-primary" onClick={save}>Sign & save</button><button type="button" className="btn-outline" onClick={() => setDraft(null)}>Cancel</button></div>
    </div>}
  </div>;
}
