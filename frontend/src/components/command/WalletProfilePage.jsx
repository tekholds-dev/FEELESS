import { Explain } from '../Explain';
import { AfterSell, IntelRail, SeasonRail } from './ProfileRails';
import { FeedBar } from '../FeedBar';
import { AlphaRoomsCard } from '../AlphaRooms';
import { investigate } from '../CaseFile';
import { RepMark } from '../RepMark';
import { uploadImage } from '../../lib/adminCall';
import { CROP } from '../../lib/cropImage';
import { WalletSwaps } from '../WalletSwaps';
import { SwapWorkspace } from './SwapWorkspace';
import { useMarket } from '../../hooks/useMarket';
import { CardVault } from '../cards/CardVault';
import { COIN_MAKERS, DEXES } from '../../lib/venues';
import { CopyBtn } from '../CopyBtn';
import { MintedTimeline } from '../MintedTimeline';
import { FuseReceipts, FuseHeldCards, FuseScore, TraderCard } from '../FusePage';
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Globe, Send, Pencil, Save, X, Plus, Image as ImageIcon, Trophy, ShieldCheck } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { isCoinAddress } from '../../lib/resolveCoin';
import { useWallet } from '../../hooks/useWallet';
import { useWorkspace } from '../../hooks/useWorkspace';
import { LivePrice } from '../terminal/LiveCells';
import { shortAddress, formatUSD } from '../../lib/dexscreener';
import { BadgeArtifacts, useBadges } from '../terminal/Badges';
import EcosystemChat from '../EcosystemChat';
import { BadgeJourney } from './BadgeJourney';
import { ReceiptsCard } from './ReceiptsCard';
import { CommandCenter, ReportBug } from './CommandCenter';
import { InviteCard } from '../InviteCard';
import { AdBanner } from '../AdBanner';
import { ProfileMusic } from './ProfileMusic';
import { ProfileDM, RewardsCard } from '../Social';
import { VerifiedMark } from '../terminal/VerifiedMark';
import { PointsShop, PnlTracker } from '../MetaExtras';
import { OnchainStrip, PerksCard, PortfolioCard, SetupCallout, SocialStrip, TradeCards, usePerks } from './ProfileExtras';

const WIDE_Q = '(min-width: 1480px)';
function useWide() {
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && !!window.matchMedia?.(WIDE_Q).matches);
  useEffect(() => {
    const m = window.matchMedia?.(WIDE_Q); if (!m) return undefined;
    const on = () => setWide(m.matches); m.addEventListener?.('change', on);
    return () => m.removeEventListener?.('change', on);
  }, []);
  return wide;
}

const RINGS = [['none', 'Classic', 0], ['mint', 'Mint pulse', 0], ['sunset', 'Sunset', 0], ['ocean', 'Ocean', 0], ['candy', 'Candy', 0], ['neon', 'Neon', 0], ['ghost', 'Ghost', 0], ['emerald', 'Emerald', 1], ['plasma', 'Plasma', 1], ['diamond', 'Diamond', 2], ['aurora', 'Aurora', 2], ['gold', 'Molten Gold', 3], ['royal', 'Royal', 3]];
const NAMEFX = [['none', 'Plain', 0], ['glow', 'Glow', 0], ['gradient', 'Gradient', 0], ['rainbow', 'Rainbow', 1], ['diamond', 'Diamond', 2], ['gold', 'Gold', 3]];
const TIER_NAMES = ['', 'Fee Friend ($10+)', 'Fee Insider ($100+)', 'Fee Whale ($1k+)'];
// Profile backdrops: the whole page behind this profile (only here). Same ids + tiers as the server's PROFILE_THEMES.
const THEME_GROUPS = [
  ['Free', 0, [['midnight', 'Midnight'], ['graphite', 'Graphite'], ['navy', 'Navy'], ['plum', 'Plum'], ['ember', 'Ember'], ['slate', 'Slate'], ['grid', 'FEE Grid'], ['feeglow', 'FEE Glow']]],
  ['Holders · animated', 1, [['glitter', 'Glitter'], ['matrix', 'Matrix rain'], ['sunset', 'Sunset'], ['vapor', 'Vaporwave'], ['aurora', 'Aurora'], ['plasma', 'Plasma'], ['goldrush', 'Gold Rush'], ['neoncat', 'Neon Cat']]],
  ['Alpha · animated', 2, [['alpha', 'Alpha Violet'], ['hologram', 'Hologram']]],
  ['Whale · animated', 3, [['diamond', 'Diamond'], ['whale', 'Deep Whale']]],
];
const TIER_NAME = { 1: '$FEE holder perk: hold $10+ of $FEE', 2: 'Alpha perk: reach Fee Insider tier', 3: 'Whale perk: reach Fee Whale tier' };

// While a profile is open, its backdrop replaces the site background (restored on leave).
function useProfileBackdrop(theme) {
  useEffect(() => {
    document.body.classList.add('profile-bg');
    return () => document.body.classList.remove('profile-bg');
  }, []);
  return theme || 'grid';
}

function FriendCard({ address }) {
  const [p, setP] = useState(null);
  useEffect(() => { fetch(apiUrl(`/api/reputation/profiles?addresses=${address}`)).then(r => r.json()).then(d => setP(d.profiles?.[address] || {})).catch(() => setP({})); }, [address]);
  return <Link to={`/terminal/profile/${address}`} className="wp-friend">{p?.avatarUrl ? <img src={p.avatarUrl} alt="" /> : <i style={p?.accent ? { color: p.accent } : undefined}>{(p?.displayName || address).slice(0, 2).toUpperCase()}</i>}<b>{p?.displayName || shortAddress(address)}</b></Link>;
}

const ACCENTS = ['#19f58f', '#e9bd65', '#5ec8ff', '#b388ff', '#ff6b8b', '#ff9f45', '#ffffff'];
const XIcon = () => <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23 22h-6.8l-5.3-6.9L4.8 22H1.7l8.1-9.3L1 2h7l4.8 6.3L18.9 2Zm-1.2 18h1.9L7.4 3.9H5.4L17.7 20Z" /></svg>;

export function UploadButton({ label, shape, onDone }) {
  const [busy, setBusy] = useState(false);
  return <label className="wp-upload"><input type="file" hidden accept="image/png,image/jpeg,image/webp,image/gif" onChange={async e => { const f = e.target.files?.[0]; if (!f) return; setBusy(true); e.target.value = ''; try { const url = await uploadImage(f, shape); if (url) onDone(url); } catch (err) { toast.error(err.message); } finally { setBusy(false); } }} /><ImageIcon size={12} />{busy ? 'Uploading…' : label}</label>;
}

// FEEd: the community's social feed, by category — post, reply and react like a timeline.
const FEED_CATS = [['feed-general', '🌐', 'Everything', 'All the talk'], ['feed-alpha', '📈', 'Alpha & calls', 'Post a CA — 2×/5×/10× earns points'], ['feed-memes', '😂', 'Memes', 'Culture & coins'], ['feed-launches', '🚀', 'Launches', 'New coins, first looks'], ['feed-help', '🛟', 'Help', 'Ask anything'], ['feeless-updates', '📣', 'FEELESS', 'Official updates']];

// Hot coins beside the FEEd: one click opens the Trenches chart.
function FeedTopCoins() {
  const navigate = useNavigate();
  const { data } = useMarket('/feed?kind=trending&chain=solana', 60000);
  const pairs = (data?.pairs || []).filter(p => p.baseToken?.symbol).slice(0, 8);
  return <aside className="feed-side feed-top" data-testid="feed-top-coins"><h4>🔥 Top coins</h4>
    {!pairs.length ? <p className="wp-bio">Loading…</p> : pairs.map(p => { const ch = Number(p.priceChange?.h24); return <button type="button" key={p.pairAddress} onClick={() => navigate(`/terminal/chat?chain=${p.chainId}&pair=${p.pairAddress}&room=bulls`)}>
      {p.info?.imageUrl ? <img src={p.info.imageUrl} alt="" /> : <span className="ft-dot" />}<b>${p.baseToken.symbol}</b><em className={ch >= 0 ? 'positive' : 'negative'}>{Number.isFinite(ch) ? `${ch >= 0 ? '+' : ''}${ch.toFixed(1)}%` : '—'}</em></button>; })}
  </aside>;
}

function SwapTopCoins({ onSelect }) {
  const { data } = useMarket('/feed?kind=trending&chain=solana', 30000);
  const pairs = (data?.pairs || []).filter(p => p.baseToken?.symbol).slice(0, 10);
  return <aside className="swap-market-rail" data-testid="swap-top-coins"><header><span><i />LIVE</span><b>Top 10 coins</b><small>30s</small></header>
    <div className="swap-market-list">{!pairs.length ? <p className="wp-bio">Loading live markets…</p> : pairs.map((p, index) => { const change = Number(p.priceChange?.h24); const txns = Number(p.txns?.h24?.buys || 0) + Number(p.txns?.h24?.sells || 0); const heat = Math.min(1, Math.log10(Math.max(10, Number(p.volume?.h24 || 0))) / 7); return <button type="button" key={p.pairAddress} onClick={() => onSelect(p)} style={{ '--heat': heat, '--pulse-speed': `${Math.max(1.4, 5 - Math.min(3.6, txns / 500))}s` }}>
      <span className="sm-rank">{index + 1}</span>{p.info?.imageUrl ? <img src={p.info.imageUrl} alt="" /> : <span className="sm-coin">{p.baseToken.symbol.slice(0, 1)}</span>}<span className="sm-name"><b>${p.baseToken.symbol}</b><small>{p.baseToken.name || 'Solana market'}</small></span><em className={change >= 0 ? 'positive' : 'negative'}>{Number.isFinite(change) ? `${change >= 0 ? '+' : ''}${change.toFixed(1)}%` : '—'}</em>
      <span className="sm-metrics"><small>MC <b>{formatUSD(p.marketCap || p.fdv)}</b></small><small>VOL <b>{formatUSD(p.volume?.h24)}</b></small><small>LIQ <b>{formatUSD(p.liquidity?.usd)}</b></small><small>TX <b>{txns || '—'}</b></small></span><i className="sm-activity" aria-hidden="true" /></button>; })}</div>
    <small className="swap-market-source">Provider-ranked activity · tap a coin to load it in the swap</small>
  </aside>;
}

function FeedPanel({ onConnect, mine }) {
  const [cat, setCat] = useState(() => { try { return localStorage.getItem('feeless:feed-cat') || 'feed-general'; } catch { return 'feed-general'; } });
  const pick = v => { setCat(v); try { localStorage.setItem('feeless:feed-cat', v); } catch { /* private */ } };
  const current = FEED_CATS.find(c => c[0] === cat) || FEED_CATS[0];
  return <section className="feed-stage" data-testid="profile-feed">
    {mine && <aside className="feed-side feed-swap"><h4>⚡ Swap</h4><ProfileSwapBox /></aside>}
    <div className="feed-panel">
      <span className="feed-flares" aria-hidden="true"><i /><i /><i /></span>
      <header><b className="feed-wordmark">FEEd</b><small>{current[3]}</small></header>
      <FeedCallers />
      <nav className="feed-cats" aria-label="FEEd categories">{FEED_CATS.map(([id, icon, label]) => <button type="button" key={id} className={cat === id ? 'on' : ''} aria-pressed={cat === id} onClick={() => pick(id)}><span>{icon}</span>{label}</button>)}</nav>
      <EcosystemChat key={cat} compact room={cat} ecosystem={{ id: cat, name: current[2] }} onConnect={onConnect} />
    </div>
    <FeedTopCoins />
  </section>;
}

// Best FEEd callers this week: posts with a coin are tracked; 2×/5×/10× peaks earn season points.
function FeedCallers() {
  const [rows, setRows] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/calls/leaderboard?days=7&room=feed-')).then(r => (r.ok ? r.json() : {})).then(d => setRows(d.rows || [])).catch(() => setRows([])); }, []);
  if (!rows?.length) return <p className="feed-callers-empty">Post a coin address in FEEd — if it runs 2×, 5× or 10× you earn season points.</p>;
  return <ol className="feed-callers" aria-label="Top FEEd callers this week"><li className="fc-head">Top callers this week <Explain>Post a coin address in any FEEd room and it becomes a tracked call. If it later peaks at 2×, 5× or 10× from your post, you earn 50, 150 or 400 season points automatically.</Explain></li>{rows.slice(0, 5).map((r, i) => <li key={r.caller}>
    <i>{i + 1}</i>{r.callerAddress ? <Link to={`/terminal/profile/${r.callerAddress}`}>{r.caller}</Link> : <b>{r.caller}</b>}
    <span>{r.hits}/{r.calls} hits</span>{r.best && <em>best {r.best.symbol} {r.best.peakX.toFixed(1)}×</em>}
  </li>)}</ol>;
}

export function WalletProfilePage({ address }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const navigate = useNavigate();
  const navRef = React.useRef(navigate); navRef.current = navigate;
  // A coin's mint (e.g. rFEE, FEECAT) is not a person: send it to the coin profile instead of an empty wallet page.
  useEffect(() => {
    if (!/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address)) return undefined;
    let alive = true;
    isCoinAddress('solana', address).then(coin => { if (alive && coin) navRef.current(`/terminal/coin/solana/${address}`, { replace: true }); });
    return () => { alive = false; };
  }, [address]);
  useEffect(() => { if (!address.startsWith('@')) return; fetch(apiUrl(`/api/reputation/resolve/${encodeURIComponent(address)}`)).then(r => (r.ok ? r.json() : null)).then(d => { if (d?.address) navigate(`/terminal/profile/${d.address}`, { replace: true }); }).catch(() => {}); }, [address, navigate]);
  // ?view=history deep-links straight to this wallet's swap history + P&L chart (used by search).
  const [flipped, setFlipped] = useState(() => new URLSearchParams(window.location.search).get('view') === 'history');
  const [swapPair, setSwapPair] = useState(null);
  const [actTab, setActTab] = useState(() => (new URLSearchParams(window.location.search).get('view') === 'history' ? 'history' : null));
  const [poolPerk, setPoolPerk] = useState(false);
  const [autoEdit, setAutoEdit] = useState(() => new URLSearchParams(window.location.search).get('edit') === '1');
  const [acts, setActs] = useState(null);
  useEffect(() => { if (!flipped || acts) return; fetch(apiUrl(`/api/reputation/activity/${address}`)).then(r => r.json()).then(setActs).catch(() => setActs({ posts: [] })); }, [flipped, acts, address]);
  // A linked 0x account shows its owner's main (Solana) profile — one identity on every network.
  useEffect(() => { if (!/^0x/.test(address)) return; fetch(apiUrl(`/api/reputation/identity/${address}`)).then(r => r.json()).then(d => { if (d.primary && d.primary !== address) navigate(`/terminal/profile/${d.primary}`, { replace: true }); }).catch(() => {}); }, [address, navigate]);
  const { watchlist } = useWorkspace() || { watchlist: [] };
  const [data, setData] = useState(null);
  const [edit, setEdit] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [ca, setCa] = useState('');
  const [myIds, setMyIds] = useState([]);
  useEffect(() => { if (!wallet?.address) { setMyIds([]); return; } fetch(apiUrl(`/api/reputation/identity/${wallet.address}`)).then(r => r.json()).then(d => setMyIds(d.linked || [])).catch(() => setMyIds([])); }, [wallet?.address]);
  const mine = wallet?.address === address || myIds.includes(address);
  useEffect(() => { if (!mine) { setPoolPerk(false); return; } fetch(apiUrl(`/api/reputation/theme/${address}`)).then(r => r.json()).then(d => setPoolPerk(!!d.poolBuilder)).catch(() => {}); }, [mine, address]);
  useEffect(() => { if (autoEdit && mine && data) { setAutoEdit(false); startEdit(); } }, [autoEdit, mine, data]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (flipped && !actTab) setActTab(mine ? 'swap' : 'holdings'); if (actTab === 'swap' && !mine) setActTab('holdings'); }, [flipped, mine, actTab]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [badgeLimit, setBadgeLimit] = useState(3);
  useEffect(() => { fetch(apiUrl('/api/reputation/badges/limits')).then(r => r.ok ? r.json() : null).then(d => d && setBadgeLimit(d.profile)).catch(() => {}); }, []);
  const perks = usePerks(address);
  const earned = useBadges(address);
  const tier = perks?.tier || 0;
  const [ccOpen, setCcOpen] = useState(false);
  useEffect(() => { if (!mine) { setIsAdmin(false); return; } fetch(apiUrl(`/api/reputation/admin/whoami?address=${address}`)).then(r => r.json()).then(d => setIsAdmin(Boolean(d.isAdmin))).catch(() => {}); }, [mine, address]);
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/profile/${address}`)).then(r => r.json()).then(setData).catch(() => setData({ profile: null })), [address]);
  useEffect(() => { load(); }, [load]);
  const p = (edit ? draft : data?.profile) || {};
  const backdrop = useProfileBackdrop(p.theme);
  const accent = p.accent || '#19f58f';
  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }));
  const startEdit = () => { setDraft({ displayName: '', bio: '', mood: '', accent: '#19f58f', links: {}, top8: [], theme: 'grid', friends: [], featuredBadges: [], ring: 'none', nameFx: 'none', handle: '', songs: [], ...(data?.profile || {}) }); setEdit(true); };
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
    if (!wallet?.address || !mine) { toast.error('Connect a wallet linked to this profile.'); return; }
    setSaving(true);
    try {
      // One wallet session (signed once, 7 days, shared with chat) — no signature per save.
      const { getChatSession, clearChatSession } = await import('../../lib/chatSession');
      const send = async session => fetch(apiUrl('/api/reputation/profile'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, profile: draft, target: address }) });
      let res = await send(await getChatSession(wallet.address, signMessage));
      if (res.status === 401) { clearChatSession(wallet.address); res = await send(await getChatSession(wallet.address, signMessage)); }
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || 'Save failed');
      toast.success('Profile saved'); setEdit(false); load();
    } catch (e) { toast.error(e.code === 4001 ? 'Signature declined — nothing saved.' : e.message); } finally { setSaving(false); }
  };
  const caller = data?.caller;
  const [friend, setFriend] = useState('');
  const wide = useWide();
  if (ccOpen && isAdmin) return <CommandCenter address={address} signMessage={signMessage} onClose={() => setCcOpen(false)} />;
  return <><div className={`profile-backdrop pbg-${backdrop}`} aria-hidden="true" data-testid="profile-backdrop" /><div className={`wp-stage ${wide ? 'has-rails' : ''}`}>{wide && <IntelRail address={address} />}<div className={`wallet-profile-page theme-${p.theme || 'grid'} ptier-${tier}`} style={{ '--wp-accent': accent }} data-testid="wallet-profile-page">
    <header className="xp-card" data-testid="profile-header">
      <div className={`xp-cover ${p.bannerUrl ? 'has-img' : ''}`}>
        {p.bannerUrl ? <img src={p.bannerUrl} alt="" decoding="async" /> : <span className="xp-cover-mark" aria-hidden="true">{p.displayName || shortAddress(address)}</span>}
        {edit && <UploadButton label="Cover" shape={CROP.banner} onDone={url => set('bannerUrl', url)} />}
      </div>
      <div className="xp-row">
        <div className="xp-avatar">{tier >= 3 && <div className="wp-crown" aria-hidden="true"><span>👑</span></div>}<div className={`wp-avatar ring-${p.ring || 'none'}`} data-img-hide><span className="xp-initials">{(p.displayName || address).slice(0, 2).toUpperCase()}</span>{p.avatarUrl && <img src={p.avatarUrl} alt="" />}{edit && <UploadButton label="Pic" shape={CROP.avatar} onDone={url => set('avatarUrl', url)} />}</div></div>
        <div className="xp-name">
          {edit ? <input className="wp-name-input" maxLength={32} placeholder="Display name" value={draft.displayName} onChange={e => set('displayName', e.target.value)} /> : <h1 className={`namefx-${p.nameFx || 'none'}`}>{p.displayName || shortAddress(address)}{data?.verified && <VerifiedMark />}<RepMark address={address} /></h1>}
          <div className="xp-sub">{edit ? <input className="wp-handle-input" maxLength={21} placeholder="@handle (3–20: a-z 0-9 _)" value={draft.handle ? `@${draft.handle}` : ''} onChange={e => set('handle', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '').slice(0, 20))} /> : <span className="wp-handle">@{p.handle || address.slice(0, 6).toLowerCase()}</span>}<span className="xp-dot">·</span><code>{shortAddress(address)}</code><CopyBtn value={address} /></div>
          {edit ? <input className="wp-mood-input" maxLength={40} placeholder="Mood / status (e.g. 🔥 hunting 10×s)" value={draft.mood} onChange={e => set('mood', e.target.value)} /> : p.mood && <p className="wp-mood">{p.mood}</p>}
        </div>
        <div className="xp-actions"><ProfileDM peer={address} mine={mine} initialOpen={new URLSearchParams(window.location.search).get('dm') === '1'} /><button type="button" className="btn-outline xp-case" data-testid="open-case-file" onClick={() => investigate(address)}>🔎 Case file</button><button type="button" className="btn-outline wp-flip-btn" data-testid="profile-flip" onClick={() => setFlipped(f => !f)}>{flipped ? '↺ Profile' : '↻ Activity'}</button>{isAdmin && <button type="button" className="cc-launch" data-testid="open-command-center" onClick={() => setCcOpen(true)}>👑 Command Center</button>}{mine ? (edit ? <><button type="button" className="btn-primary" disabled={saving} onClick={save}><Save size={14} />{saving ? 'Saving…' : 'Save'}</button><button type="button" className="btn-outline" onClick={() => setEdit(false)}><X size={14} />Cancel</button></> : <button type="button" className="btn-outline" onClick={startEdit}><Pencil size={14} />Edit profile</button>) : !wallet?.address && <button type="button" className="btn-outline" onClick={() => connect?.('solana')}>Connect to edit yours</button>}</div>
      </div>
      <div className="xp-meta">
        <SocialStrip address={address} mine={mine} />
        <OnchainStrip address={address} />
      </div>
      <TraderCard address={address} /><div className="xp-badges"><BadgeArtifacts address={address} featured={p.featuredBadges} /></div><MintedTimeline address={address} /><FuseScore address={address} /><FuseHeldCards address={address} /><FuseReceipts address={address} />
    </header>
    <div className="wp-quickrow">{mine && <AlphaRoomsCard />}<FeedBar onOpen={() => { setFlipped(true); setActTab('feed'); }} /></div>
    <ProfileMusic songs={p.songs || []} edit={edit} onChange={v => set('songs', v)} />
    {!flipped && <PortfolioCard address={address} />}
    {!flipped && <TradeCards address={address} />}
    {flipped && <nav className="wp-act-tabs" data-testid="activity-tabs">{[mine && ['swap', 'Swap'], mine && poolPerk && ['builder', '🏗 Pool builder'], ['holdings', 'Holdings'], ['history', 'Swap history'], ['feed', 'FEEd'], ['posts', 'Posts'], ['rewards', 'Rewards'], mine && ['invites', '🎟 Invites'], ['vault', 'Vault']].filter(Boolean).map(([k, l]) => <button key={k} type="button" className={actTab === k ? 'active' : ''} onClick={() => setActTab(k)}>{l}</button>)}</nav>}
    {flipped && actTab === 'swap' && mine && <section className="profile-swap-layout" data-testid="profile-swap"><SwapTopCoins onSelect={setSwapPair} /><div className="wp-card profile-swap"><ProfileSwapBox pair={swapPair} /><small className="wp-bio">Signed in your own wallet — FEELESS never holds funds. Buying $FEE is fee-free; selling it to SOL, USDC or USDT is also free. Other routes show the platform fee before signing.</small></div><div className="profile-swap-receipts"><ReceiptsCard address={address} /></div></section>}
    {flipped && actTab === 'holdings' && <PortfolioCard address={address} onSwap={mine ? pr => { setSwapPair(pr); setActTab('swap'); } : undefined} />}
    {flipped && actTab === 'history' && <><AfterSell address={address} /><WalletSwaps address={address} title="Swap history" /><PnlTracker address={address} /></>}
    {flipped && actTab === 'feed' && <FeedPanel mine={mine} onConnect={() => connect?.('solana')} />}
    {flipped && actTab === 'posts' && <ReceiptsCard address={address} />}
    {flipped && actTab === 'invites' && mine && <InviteCard address={address} />}
    {flipped && actTab === 'posts' && <section className="wp-card wp-activity" data-testid="profile-activity"><h3>Activity</h3>{!acts ? <p className="wp-bio">Loading…</p> : !acts.posts.length ? <p className="wp-bio">No posts yet.</p> : <div className="wpa-list">{acts.posts.map(a => <a key={a.id} className="wpa-row" href={a.room.startsWith('coin-') ? `/terminal/chat` : a.room.startsWith('wall-') ? `/terminal/profile/${a.room.slice(5)}` : '/terminal/chat'} target="_blank" rel="noopener noreferrer"><span className="wpa-room">{a.room.startsWith('wall-') ? '🧱 wall' : a.room.startsWith('coin-') ? `🪙 ${a.room.split('-').pop()}` : `# ${a.room}`}</span><p>{a.text}</p><time>{new Date(a.ts).toLocaleString()}</time></a>)}</div>}</section>}
    {flipped && actTab === 'rewards' && <><RewardsCard address={address} mine={mine} />{mine && <PointsShop address={address} />}</>}
    {flipped && actTab === 'vault' && <CardVault address={address} />}
    {flipped && actTab === 'builder' && mine && <PoolBuilderCard />}
    <div className={`wp-flip-body ${flipped ? 'is-flipped' : ''}`}>
    {mine && !edit && data && <SetupCallout profile={data.profile} onEdit={startEdit} />}
    <div className="wp-grid">
      <section className="wp-card">
        <h3>About</h3>
        {edit ? <textarea maxLength={280} rows={4} value={draft.bio} placeholder="Say something. 280 chars." onChange={e => set('bio', e.target.value)} /> : <p className="wp-bio">{p.bio || (mine ? 'Tell the trenches who you are — hit Edit profile.' : 'No bio yet.')}</p>}
        {edit ? <div className="wp-links-edit">{[['x', 'https://x.com/you'], ['website', 'https://yoursite.xyz'], ['telegram', 'https://t.me/you']].map(([k, ph]) => <input key={k} placeholder={ph} value={draft.links?.[k] || ''} onChange={e => set('links', { ...draft.links, [k]: e.target.value })} />)}</div>
          : <div className="wp-links">{p.links?.x && <a href={p.links.x} target="_blank" rel="noopener noreferrer"><XIcon />X</a>}{p.links?.website && <a href={p.links.website} target="_blank" rel="noopener noreferrer"><Globe size={13} />Website</a>}{p.links?.telegram && <a href={p.links.telegram} target="_blank" rel="noopener noreferrer"><Send size={13} />Telegram</a>}</div>}
        {edit && earned.length > 0 && <div className="wp-feature-pick" data-testid="feature-pick"><small>Featured badges — pick up to {badgeLimit} (Command Center limit; they spin on your profile and lead in chat)</small><div>{earned.map(b => { const on = (draft.featuredBadges || []).includes(b.id); return <button type="button" key={b.id} className={`badge-pill tone-${b.tone} ${on ? 'is-featured' : ''}`} disabled={!on && (draft.featuredBadges || []).length >= badgeLimit} onClick={() => set('featuredBadges', on ? draft.featuredBadges.filter(x => x !== b.id) : [...(draft.featuredBadges || []), b.id])}><i>{b.icon}</i>{b.label}{on && ` · ${(draft.featuredBadges || []).indexOf(b.id) + 1}`}</button>; })}</div></div>}
        {edit && <div className="wp-style-shop" data-testid="style-shop">
          <small>Avatar ring — free styles for everyone, animated premium styles for $FEE holders</small>
          <div className="wp-rings">{RINGS.map(([id, label, need]) => <button type="button" key={id} disabled={need > tier} title={need > tier ? `${TIER_NAMES[need]} style` : label} className={`wp-ring-opt ${draft.ring === id ? 'active' : ''} ${need ? 'premium' : ''}`} onClick={() => set('ring', id)}><span className={`ring-demo ring-${id}`}><i /></span><b>{need > tier ? '🔒 ' : need ? '✦ ' : ''}{label}</b></button>)}</div>
          <small>Name effect</small>
          <div className="wp-rings">{NAMEFX.map(([id, label, need]) => <button type="button" key={id} disabled={need > tier} className={`wp-ring-opt ${draft.nameFx === id ? 'active' : ''} ${need ? 'premium' : ''}`} onClick={() => set('nameFx', id)}><b className={`namefx-${id}`}>{need > tier ? '🔒 ' : ''}{label}</b></button>)}</div>
        </div>}
        {edit && <div className="wp-themes" data-testid="profile-backdrops"><small>Page backdrop</small>
          {THEME_GROUPS.map(([group, need, items], gi) => { const locked = need > tier; const swatches = <div className="wp-theme-row">{items.map(([id, label]) => <button type="button" key={id} disabled={locked} title={locked ? TIER_NAME[need] : label} className={`wp-theme-swatch pbg-${id} ${draft.theme === id ? 'active' : ''}`} onClick={() => set('theme', id)}><span>{label}</span></button>)}</div>;
            // Free options always open; the animated tiers sit in dropdowns (open when one is selected).
            return gi === 0 ? <div key={group} className="wp-theme-group"><em>{group}</em>{swatches}</div>
              : <details key={group} className={`wp-theme-drop ${locked ? 'is-locked' : ''}`} open={items.some(([id]) => id === draft.theme)}><summary><em>{group}</em><span>{items.length} options</span>{locked ? <i>🔒 {TIER_NAME[need]}</i> : <i className="ok">Unlocked</i>}</summary>{swatches}</details>; })}</div>}
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
        {edit ? <button type="button" className="wp-coin-x" onClick={() => setDraft(d => ({ ...d, top8: d.top8.filter((_, j) => j !== i) }))} aria-label="Remove">×</button> : <a href={`/terminal/chat?chain=${t.chain}&pair=${t.pairAddress}&room=bulls`} target="_blank" rel="noopener noreferrer" className="wp-coin-open">war room ↗</a>}
      </div>)}</div>}
    </section>
    <section className="wp-card wp-wall">
      <h3>Wall</h3>
      <p className="wp-bio">Leave {p.displayName || 'them'} a message. Every comment is signed by the poster's wallet.</p>
      <EcosystemChat compact room={`wall-${address}`} ecosystem={{ id: `wall-${address}`, name: 'Wall' }} onConnect={() => connect?.('solana')} />
    </section>
    <AdBanner placement="profile" />
    <PerksCard perks={perks} mine={mine} />
    <BadgeJourney address={address} mine={mine} />
    <ReceiptsCard address={address} />
    </div>
    <div className="wp-foot"><ReportBug address={wallet?.address} /></div>
  </div>{wide && <SeasonRail address={address} />}</div></>;
}

// Your own swap desk inside your profile: any Solana coin to any coin, prefilled when you tap Swap
// on a holding. Same non-custodial Jupiter flow as the Trade tab — your wallet signs every trade.
function ProfileSwapBox({ pair }) {
  const assets = useMarket('/assets', 300000);
  const feeAssets = assets.data?.assets || [];
  return <SwapWorkspace pair={pair} feeAsset={feeAssets.find(a => a.id === 'fee')} feeAssets={feeAssets} onWallet={() => {}} />;
}

// $5k+ FEELESS holders: create coins and pools on vetted venues (signed by their own wallet).
function PoolBuilderCard() {
  return <section className="wp-card pool-builder-card" data-testid="pool-builder-card"><h3>Pool builder <small>unlocked · $5k+ holder</small></h3>
    <h4>Make a coin</h4><div className="pb-grid">{COIN_MAKERS.map(m => <a key={m.name} href={m.url} target="_blank" rel="noopener noreferrer"><b>{m.name}</b><small>{m.chain} · {m.note}</small></a>)}</div>
    <h4>Add liquidity</h4><div className="pb-grid">{DEXES.map(d => <a key={d.id} href={d.url} target="_blank" rel="noopener noreferrer"><b>{d.name}</b><small>{d.note}</small></a>)}</div>
    <small className="wp-bio">Your wallet signs every step on the venue itself — FEELESS never holds funds. Shield your coin after launch.</small>
  </section>;
}
