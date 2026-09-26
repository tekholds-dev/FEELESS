import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Globe, Send, Pencil, Save, X, Plus, Image as ImageIcon, Trophy, ShieldCheck } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { useWallet } from '../../hooks/useWallet';
import { useWorkspace } from '../../hooks/useWorkspace';
import { LivePrice } from '../terminal/LiveCells';
import { shortAddress } from '../../lib/dexscreener';
import { Badges } from '../terminal/Badges';
import EcosystemChat from '../EcosystemChat';
import { BadgeJourney } from './BadgeJourney';
import { ReceiptsCard } from './ReceiptsCard';
import { CommandCenter, ReportBug } from './CommandCenter';

const THEMES = [['grid', 'Midnight grid'], ['glitter', 'Glitter'], ['matrix', 'Matrix rain'], ['sunset', 'Sunset'], ['vapor', 'Vaporwave']];

function FriendCard({ address }) {
  const [p, setP] = useState(null);
  useEffect(() => { fetch(apiUrl(`/api/reputation/profiles?addresses=${address}`)).then(r => r.json()).then(d => setP(d.profiles?.[address] || {})).catch(() => setP({})); }, [address]);
  return <Link to={`/terminal/profile/${address}`} className="wp-friend">{p?.avatarUrl ? <img src={p.avatarUrl} alt="" /> : <i style={p?.accent ? { color: p.accent } : undefined}>{(p?.displayName || address).slice(0, 2).toUpperCase()}</i>}<b>{p?.displayName || shortAddress(address)}</b></Link>;
}

const ACCENTS = ['#00e9a0', '#e9bd65', '#5ec8ff', '#b388ff', '#ff6b8b', '#ff9f45', '#ffffff'];
const XIcon = () => <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23 22h-6.8l-5.3-6.9L4.8 22H1.7l8.1-9.3L1 2h7l4.8 6.3L18.9 2Zm-1.2 18h1.9L7.4 3.9H5.4L17.7 20Z" /></svg>;

async function uploadImage(file, max) {
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) throw new Error('PNG, JPG, WEBP or GIF');
  let dataUrl;
  if (file.type === 'image/gif') {
    // Keep GIFs animated: upload as-is (server caps at 2 MB).
    if (file.size > 2_000_000) throw new Error('GIFs must be under 2 MB');
    dataUrl = await new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
  } else {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, max / Math.max(bmp.width, bmp.height));
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height);
    dataUrl = c.toDataURL('image/webp', 0.9);
  }
  const res = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataUrl }) });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || 'Upload failed');
  return body.url;
}

function UploadButton({ label, max, onDone }) {
  const [busy, setBusy] = useState(false);
  return <label className="wp-upload"><input type="file" hidden accept="image/png,image/jpeg,image/webp,image/gif" onChange={async e => { const f = e.target.files?.[0]; if (!f) return; setBusy(true); try { onDone(await uploadImage(f, max)); } catch (err) { toast.error(err.message); } finally { setBusy(false); } }} /><ImageIcon size={12} />{busy ? 'Uploading…' : label}</label>;
}

export function WalletProfilePage({ address }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const { watchlist } = useWorkspace() || { watchlist: [] };
  const [data, setData] = useState(null);
  const [edit, setEdit] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [ca, setCa] = useState('');
  const mine = wallet?.address === address;
  const [isAdmin, setIsAdmin] = useState(false);
  const [ccOpen, setCcOpen] = useState(false);
  useEffect(() => { if (!mine) { setIsAdmin(false); return; } fetch(apiUrl(`/api/reputation/admin/whoami?address=${address}`)).then(r => r.json()).then(d => setIsAdmin(Boolean(d.isAdmin))).catch(() => {}); }, [mine, address]);
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/profile/${address}`)).then(r => r.json()).then(setData).catch(() => setData({ profile: null })), [address]);
  useEffect(() => { load(); }, [load]);
  const p = (edit ? draft : data?.profile) || {};
  const accent = p.accent || '#00e9a0';
  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }));
  const startEdit = () => { setDraft({ displayName: '', bio: '', mood: '', accent: '#00e9a0', links: {}, top8: [], theme: 'grid', friends: [], ...(data?.profile || {}) }); setEdit(true); };
  const addCoin = coin => setDraft(d => (d.top8.some(t => t.pairAddress === coin.pairAddress) || d.top8.length >= 8 ? d : { ...d, top8: [...d.top8, coin] }));
  const addByCa = async () => {
    try {
      const r = await (await fetch(`https://api.dexscreener.com/latest/dex/search?q=${encodeURIComponent(ca.trim())}`)).json();
      const pr = (r.pairs || []).sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0))[0];
      if (!pr) throw new Error('No market found for that address.');
      addCoin({ chain: pr.chainId, pairAddress: pr.pairAddress, mint: pr.baseToken?.address, symbol: pr.baseToken?.symbol, imageUrl: pr.info?.imageUrl || '' });
      setCa('');
    } catch (e) { toast.error(e.message); }
  };
  const save = async () => {
    if (!wallet?.address || wallet.chain !== 'solana') { toast.error('Connect the Solana wallet that owns this profile.'); return; }
    setSaving(true);
    try {
      const message = `FEELESS profile update\naddress:${wallet.address}\nts:${Math.floor(Date.now() / 1000)}`;
      const signature = await signMessage(message);
      const res = await fetch(apiUrl('/api/reputation/profile'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, message, signature, profile: draft }) });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || 'Save failed');
      toast.success('Profile saved'); setEdit(false); load();
    } catch (e) { toast.error(e.code === 4001 ? 'Signature declined — nothing saved.' : e.message); } finally { setSaving(false); }
  };
  const caller = data?.caller;
  const [friend, setFriend] = useState('');
  if (ccOpen && isAdmin) return <CommandCenter address={address} signMessage={signMessage} onClose={() => setCcOpen(false)} />;
  return <div className={`wallet-profile-page theme-${p.theme || 'grid'}`} style={{ '--wp-accent': accent }} data-testid="wallet-profile-page">
    <div className="wp-banner" style={p.bannerUrl ? { backgroundImage: `url(${p.bannerUrl})` } : undefined}>{edit && <UploadButton label="Banner" max={1600} onDone={url => set('bannerUrl', url)} />}</div>
    <div className="wp-head">
      <div className="wp-avatar">{p.avatarUrl ? <img src={p.avatarUrl} alt="" /> : <span>{(p.displayName || address).slice(0, 2).toUpperCase()}</span>}{edit && <UploadButton label="GIF / pic" max={512} onDone={url => set('avatarUrl', url)} />}</div>
      <div className="wp-id">
        {edit ? <input className="wp-name-input" maxLength={32} placeholder="Display name" value={draft.displayName} onChange={e => set('displayName', e.target.value)} /> : <h1>{p.displayName || shortAddress(address)}</h1>}
        <code>{shortAddress(address)}</code>
        <Badges address={address} />
        {edit ? <input className="wp-mood-input" maxLength={40} placeholder="Mood / status (e.g. 🔥 hunting 10×s)" value={draft.mood} onChange={e => set('mood', e.target.value)} /> : p.mood && <span className="wp-mood">{p.mood}</span>}
      </div>
      <div className="wp-actions">{isAdmin && <button type="button" className="cc-launch" data-testid="open-command-center" onClick={() => setCcOpen(true)}>👑 Command Center</button>}{mine ? (edit ? <><button type="button" className="btn-primary" disabled={saving} onClick={save}><Save size={14} />{saving ? 'Sign in wallet…' : 'Save (sign)'}</button><button type="button" className="btn-outline" onClick={() => setEdit(false)}><X size={14} />Cancel</button></> : <button type="button" className="btn-outline" onClick={startEdit}><Pencil size={14} />Edit profile</button>) : !wallet?.address && <button type="button" className="btn-outline" onClick={() => connect?.('solana')}>Connect to edit yours</button>}</div>
    </div>
    <div className="wp-grid">
      <section className="wp-card">
        <h3>About</h3>
        {edit ? <textarea maxLength={280} rows={4} value={draft.bio} placeholder="Say something. 280 chars." onChange={e => set('bio', e.target.value)} /> : <p className="wp-bio">{p.bio || (mine ? 'Tell the trenches who you are — hit Edit profile.' : 'No bio yet.')}</p>}
        {edit ? <div className="wp-links-edit">{[['x', 'https://x.com/you'], ['website', 'https://yoursite.xyz'], ['telegram', 'https://t.me/you']].map(([k, ph]) => <input key={k} placeholder={ph} value={draft.links?.[k] || ''} onChange={e => set('links', { ...draft.links, [k]: e.target.value })} />)}</div>
          : <div className="wp-links">{p.links?.x && <a href={p.links.x} target="_blank" rel="noopener noreferrer"><XIcon />X</a>}{p.links?.website && <a href={p.links.website} target="_blank" rel="noopener noreferrer"><Globe size={13} />Website</a>}{p.links?.telegram && <a href={p.links.telegram} target="_blank" rel="noopener noreferrer"><Send size={13} />Telegram</a>}</div>}
        {edit && <div className="wp-themes"><small>Theme</small>{THEMES.map(([id, label]) => <button type="button" key={id} className={`wp-theme-swatch swatch-${id} ${draft.theme === id ? 'active' : ''}`} onClick={() => set('theme', id)}>{label}</button>)}</div>}
        {edit && <div className="wp-accents"><small>Accent</small>{ACCENTS.map(c => <button type="button" key={c} style={{ background: c }} className={draft.accent === c ? 'active' : ''} onClick={() => set('accent', c)} aria-label={`Accent ${c}`} />)}</div>}
      </section>
      <section className="wp-card">
        <h3><Trophy size={14} /> Receipts</h3>
        {caller ? <div className="wp-receipts"><div><small>CALLS · 30D</small><b>{caller.calls}</b></div><div><small>HIT RATE</small><b>{Math.round(caller.hitRate * 100)}%</b></div><div><small>AVG PEAK</small><b>{caller.avgPeakX.toFixed(2)}×</b></div><div><small>BEST</small><b>{caller.best ? `${caller.best.symbol} ${caller.best.peakX.toFixed(1)}×` : '—'}</b></div></div> : <p className="wp-bio">No calls on the ledger yet. Post a CA in the Trenches to start a record.</p>}
        <Link className="wp-rep-link" to={`/terminal/reputation/solana/${address}`}><ShieldCheck size={13} />Creator reputation for this wallet</Link>
      </section>
    </div>
    <section className="wp-card wp-friends">
      <h3>{(p.displayName || 'Their')}'s Top 8</h3>
      {edit && <div className="wp-top8-add"><input placeholder="Paste a friend's wallet address…" value={friend} onChange={e => setFriend(e.target.value)} /><button type="button" className="btn-outline" disabled={!/^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/.test(friend.trim()) || (draft.friends || []).length >= 8} onClick={() => { set('friends', [...(draft.friends || []), friend.trim()]); setFriend(''); }}><Plus size={13} />Add friend</button></div>}
      {!(p.friends || []).length ? <p className="wp-bio">{edit ? 'Add up to 8 wallets — your trench crew.' : 'No Top 8 friends yet.'}</p> : <div className="wp-friends-grid">{p.friends.map((f, i) => <div key={f} className="wp-friend-wrap"><FriendCard address={f} />{edit && <button type="button" className="wp-coin-x" onClick={() => set('friends', draft.friends.filter((_, j) => j !== i))} aria-label="Remove">×</button>}</div>)}</div>}
    </section>
    <section className="wp-card wp-top8">
      <h3>Top 8 coins</h3>
      {edit && <div className="wp-top8-add"><input placeholder="Paste a CA to add…" value={ca} onChange={e => setCa(e.target.value)} /><button type="button" className="btn-outline" onClick={addByCa} disabled={!ca.trim()}><Plus size={13} />Add</button>{watchlist.slice(0, 6).map(w => <button type="button" key={w.pairAddress} className="wp-chip" onClick={() => addCoin({ chain: w.chainId, pairAddress: w.pairAddress, mint: w.baseToken?.address, symbol: w.baseToken?.symbol, imageUrl: w.info?.imageUrl || '' })}>+ {w.baseToken?.symbol}</button>)}</div>}
      {!(p.top8 || []).length ? <p className="wp-bio">{edit ? 'Add up to 8 coins you ride with.' : 'No Top 8 yet.'}</p> : <div className="wp-top8-grid">{p.top8.map((t, i) => <div key={t.pairAddress} className="wp-coin">
        {t.imageUrl ? <img src={t.imageUrl} alt="" /> : <i>{(t.symbol || '?').slice(0, 2)}</i>}<b>{t.symbol}</b>
        <LivePrice pair={{ chainId: t.chain, baseToken: { address: t.mint }, pairAddress: t.pairAddress }} precise />
        {edit ? <button type="button" className="wp-coin-x" onClick={() => setDraft(d => ({ ...d, top8: d.top8.filter((_, j) => j !== i) }))} aria-label="Remove">×</button> : <a href={`/?coin=${t.chain}:${t.pairAddress}`} target="_blank" rel="noopener noreferrer" className="wp-coin-open">war room ↗</a>}
      </div>)}</div>}
    </section>
    <section className="wp-card wp-wall">
      <h3>Wall</h3>
      <p className="wp-bio">Leave {p.displayName || 'them'} a message. Every comment is signed by the poster's wallet.</p>
      <EcosystemChat compact room={`wall-${address}`} ecosystem={{ id: `wall-${address}`, name: 'Wall' }} onConnect={() => connect?.('solana')} />
    </section>
    <BadgeJourney address={address} mine={mine} />
    <ReceiptsCard address={address} />
    <div className="wp-foot"><ReportBug address={wallet?.address} /></div>
  </div>;
}
