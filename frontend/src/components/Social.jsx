import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { MessageCircle, Send, Gift } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { getChatSession, readChatSession } from '../lib/chatSession';
import { Hint } from './Hint';
import { currentSubscription, enablePush, readPushPrefs, savePushPrefs, syncPush } from '../lib/push';

const ago = ts => { const s = Math.max(0, Date.now() / 1000 - ts); return s < 60 ? 'now' : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };
const q = o => new URLSearchParams(o).toString();

// Header bell: wall posts, DMs, @mentions, invites, rewards.
export function NotificationBell() {
  const { wallet, signMessage } = useWallet() || {};
  const [open, setOpen] = useState(false);
  const [d, setD] = useState(null);
  const session = wallet?.address ? readChatSession(wallet.address) : null;
  useEffect(() => {
    if (!wallet?.address || !session) { setD(null); return undefined; }
    let alive = true;
    const load = () => fetch(`/api/reputation/notifications?${q({ address: wallet.address, session })}`).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [wallet?.address, session]);
  const signIn = async () => { try { await getChatSession(wallet.address, signMessage); setD({ unread: 0, items: [] }); } catch (e) { toast.error(e.message); } };
  const markRead = () => { if (d?.unread) fetch('/api/reputation/notifications/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session }) }).then(() => setD(x => ({ ...x, unread: 0, items: x.items.map(n => ({ ...n, read: true })) }))); };
  const phone = async () => { try { const prefs = { ...readPushPrefs(), address: wallet.address }; let wl = []; try { wl = JSON.parse(localStorage.getItem('feeless-watchlist') || '[]'); } catch { /* ignore */ } if (await currentSubscription()) await syncPush(wl, prefs); else await enablePush(wl, prefs); savePushPrefs(prefs); toast.success('📱 Phone alerts on for messages, wall posts and mentions.'); } catch (e) { toast.error(e.message); } };
  const wrap = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const out = e => { if (wrap.current && !wrap.current.contains(e.target)) setOpen(false); };
    const esc = e => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', out); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('pointerdown', out); document.removeEventListener('keydown', esc); };
  }, [open]);
  if (!wallet?.address) return null;
  return <span className="notif-wrap" ref={wrap}><button type="button" className="icon-btn notif-btn" data-testid="notif-bell" aria-label="Notifications" onClick={() => { setOpen(o => !o); if (!open) setTimeout(markRead, 1500); }}><MessageCircle size={17} />{d?.unread ? <i className="notif-dot">{d.unread > 9 ? '9+' : d.unread}</i> : null}</button>
    {open && <div className="notif-pop" data-testid="notif-pop">
      <div className="np-head"><b>Notifications</b><button type="button" onClick={phone}>📱 Phone alerts</button></div>
      {!session ? <div className="np-empty"><p>Sign once to get messages, wall posts and mentions.</p><button type="button" className="btn-primary" onClick={signIn}>Sign in (free)</button></div>
        : !d?.items?.length ? <p className="np-empty">Nothing yet. Messages, wall posts and @mentions land here.</p>
          : <NotificationList items={d.items} />}
      <a className="np-all" href={`/terminal/profile/${wallet.address}?dm=1`}>Open my inbox →</a>
    </div>}</span>;
}

const ICONS = { dm: '💬', wall: '🧱', mention: '📣', invite: '🎉', reward: '🎁', snipers: '🎯' };
const compactUsd = v => (!(v > 0) ? null : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
// Older alerts carry only text ("Every sniper on your coin XYZ has sold out"): recover the ticker from it.
const sniperCoin = n => n.meta || { symbol: (n.text.match(/your coin (\S+) has/) || [])[1] || 'coin' };

// Snipers-out alerts collapse into one dropdown (one row per coin); everything else lists normally.
export function NotificationList({ items }) {
  const snipers = items.filter(n => n.kind === 'snipers');
  const rest = items.filter(n => n.kind !== 'snipers');
  const unreadSnipers = snipers.filter(n => !n.read).length;
  return <>
    {snipers.length > 0 && <details className="np-group" data-testid="np-snipers">
      <summary className={unreadSnipers ? 'unread' : ''}><span>🎯</span><p><b>Snipers out</b> · {snipers.length} coin{snipers.length === 1 ? '' : 's'}</p>{unreadSnipers > 0 && <i className="np-count">{unreadSnipers}</i>}</summary>
      {snipers.map(n => { const c = sniperCoin(n); const mc = compactUsd(c.mcap); return <div key={n.id} className="np-sniper">
        <a href={n.url || '#'} className="np-coin" title={c.name || c.symbol}><b>${c.symbol}</b>{c.name && <em>{c.name}</em>}</a>
        {mc && <span className="np-mc">MC {mc}</span>}
        <small>{ago(n.at)}</small>
        {n.url && <a className="np-buy" href={`${n.url}${n.url.includes('?') ? '&' : '?'}buy=1`}>Buy →</a>}
      </div>; })}
    </details>}
    {rest.map((n, i) => <a key={n.id} href={n.url || '#'} style={{ '--i': Math.min(i, 12) }} className={`np-item ${n.read ? '' : 'unread'} k-${n.kind}`}><span>{ICONS[n.kind] || '🔔'}</span><p>{n.text}</p><small>{ago(n.at)}</small></a>)}
  </>;
}

// Private chat between two wallets (profile chat).
export function ProfileDM({ peer, mine, initialOpen }) {
  const { wallet, signMessage, connect } = useWallet() || {};
  const [open, setOpen] = useState(Boolean(initialOpen));
  const [session, setSession] = useState(null);
  const [threads, setThreads] = useState([]);
  const [with_, setWith] = useState(mine ? null : peer);
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState('');
  const [policy, setPolicy] = useState(null);
  const end = useRef(null);
  const prefs = body => fetch('/api/reputation/dm-settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, ...body }) }).then(r => r.json()).then(p => setPolicy(p.policy));
  useEffect(() => { if (mine && open && session && wallet?.address) fetch(`/api/reputation/dm-settings?${q({ address: wallet.address, session })}`).then(r => r.json()).then(p => setPolicy(p.policy)).catch(() => {}); }, [mine, open, session, wallet?.address]);
  const pending = mine && threads.find(t => t.peer === with_)?.request;
  useEffect(() => { if (wallet?.address) setSession(readChatSession(wallet.address)); }, [wallet?.address, open]);
  useEffect(() => { setWith(mine ? null : peer); }, [mine, peer]);
  useEffect(() => {
    if (!open || !session || !wallet?.address) return undefined;
    let alive = true;
    const load = () => {
      if (mine) fetch(`/api/reputation/dm-inbox?${q({ address: wallet.address, session })}`).then(r => r.json()).then(x => alive && setThreads(x.threads || [])).catch(() => {});
      if (with_) fetch(`/api/reputation/dm/${with_}?${q({ address: wallet.address, session })}`).then(r => r.json()).then(x => { if (alive) { setMsgs(x.messages || []); setTimeout(() => end.current?.scrollIntoView({ block: 'nearest' }), 50); } }).catch(() => {});
    };
    load(); const t = setInterval(load, 8000);
    return () => { alive = false; clearInterval(t); };
  }, [open, session, with_, mine, wallet?.address]);
  const start = async () => { if (!wallet) { await connect?.('solana'); return; } try { setSession(await getChatSession(wallet.address, signMessage)); } catch (e) { toast.error(e.message); } };
  const send = async e => {
    e.preventDefault(); if (!text.trim()) return;
    const r = await fetch('/api/reputation/dm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, to: with_, text }) });
    const b = await r.json().catch(() => ({}));
    if (!r.ok) { toast.error(b.detail || 'Not sent'); return; }
    setText(''); setMsgs(m => [...m, b.message]);
  };
  if (!open) return <button type="button" className="btn-outline dm-open" data-testid="dm-open" onClick={() => setOpen(true)}><MessageCircle size={14} />{mine ? 'Inbox' : 'Message'}</button>;
  return <section className="wp-card dm-card" data-testid="profile-dm">
    <div className="wpj-head"><h3><MessageCircle size={15} /> {mine ? 'Inbox' : 'Private chat'}</h3><button type="button" className="dm-x" onClick={() => setOpen(false)}>×</button></div>
    {!wallet || !session ? <div className="np-empty"><p>{wallet ? 'Sign once to chat privately (free, 7 days).' : 'Connect a wallet to chat.'}</p><button type="button" className="btn-primary" onClick={start}>{wallet ? 'Sign in' : 'Connect'}</button></div> : <div className={`dm-body ${mine ? 'with-list' : ''}`}>
      {mine && <div className="dm-threads">{policy && <label className="dm-policy"><span>Who can message me</span><select value={policy} onChange={e => prefs({ policy: e.target.value })}><option value="everyone">Everyone</option><option value="requests">Requests — I accept first</option><option value="nobody">Nobody</option></select></label>}{!threads.length ? <p className="np-empty">No conversations yet.</p> : threads.map(t => <button key={t.peer} type="button" className={with_ === t.peer ? 'on' : ''} onClick={() => setWith(t.peer)}><b>@{t.handle}{t.request && <em className="dm-req">request</em>}</b><small>{t.last.text.slice(0, 40)}</small></button>)}</div>}
      {with_ ? <div className="dm-thread"><div className="dm-msgs">{msgs.map(m => <div key={m.id} className={`dm-msg ${m.from === (msgs.find(x => x.from !== with_)?.from || '') || m.from !== with_ ? 'me' : ''}`}><p>{m.text}</p><small>{ago(m.at)}</small></div>)}<i ref={end} /></div>
        {pending && <div className="dm-request-bar"><span>@{threads.find(t => t.peer === with_)?.handle} wants to message you.</span><button type="button" className="btn-primary" onClick={() => prefs({ accept: with_ }).then(() => setThreads(ts => ts.map(t => (t.peer === with_ ? { ...t, request: false } : t))))}>Accept</button></div>}<form onSubmit={send} className="dm-compose"><input maxLength={500} value={text} onChange={e => setText(e.target.value)} placeholder="Write a private message…" /><button className="btn-primary" aria-label="Send"><Send size={14} /></button></form></div> : mine && <p className="np-empty">Pick a conversation.</p>}
    </div>}
  </section>;
}

// Rewards: points with several ways to earn; claim with your chat session.
export function RewardsCard({ address, mine }) {
  const { wallet, signMessage } = useWallet() || {};
  const [d, setD] = useState(null);
  const load = () => fetch(`/api/reputation/rewards/${address}`).then(r => r.json()).then(setD).catch(() => {});
  useEffect(() => { load(); }, [address]); // eslint-disable-line react-hooks/exhaustive-deps
  const claim = async id => {
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch('/api/reputation/rewards/claim', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, reward: id }) });
      const b = await r.json(); if (!r.ok) throw new Error(b.detail);
      toast.success(`🎁 +${b.gained} points${b.streak > 1 ? ` · ${b.streak}-day streak` : ''}`); load();
    } catch (e) { toast.error(e.message || 'Could not claim'); }
  };
  if (!d) return null;
  return <section className="wp-card rewards-card" data-testid="rewards">
    <div className="wpj-head"><h3><Gift size={15} /> Rewards <Hint text="Points come from real activity: daily check-ins (streaks grow the bonus), posting, calls that hit 2×, invites, holding $FEE and linking accounts. Points feed FEELESS airdrops and the leaderboard." /></h3><span className="wpj-count"><b>{d.total.toLocaleString()}</b> pts · rank #{d.rank}{d.streak ? ` · 🔥 ${d.streak}d` : ''}</span></div>
    <p className="wp-bio">Points track real activity and feed FEELESS airdrops and the leaderboard. {mine ? 'Claim what you\'ve earned:' : ''}</p>
    <div className="rw-list">{d.items.map(it => <div key={it.id} className={`rw-item ${it.claimable ? 'ready' : ''}`}><div><b>{it.label}</b><small>{it.how}</small></div><span>+{it.amount}</span>{mine && <button type="button" className={it.claimable ? 'btn-primary' : 'btn-outline'} disabled={!it.claimable} onClick={() => claim(it.id)}>{it.claimable ? 'Claim' : it.claimed ? '✓' : '—'}</button>}</div>)}</div>
    {d.log.length > 0 && <div className="rw-log">{d.log.slice(0, 6).map((l, i) => <small key={i}>+{l.points} · {l.label} · {ago(l.at)} ago</small>)}</div>}
  </section>;
}
