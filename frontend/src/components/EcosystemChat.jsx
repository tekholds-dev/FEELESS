import React, { useEffect, useRef, useState } from 'react';
import { ExternalLink, Flag, Heart, Link2, Lock, MessageCircle, Reply, Send, UserRound, X } from 'lucide-react';
import { searchTokenByAddress, formatTime } from '../lib/dexscreener';
import TokenCard from './TokenCard';
import { IntelligenceCard } from './command/IntelligenceCard';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { displayAddress, profileLabel, walletProof } from '../lib/profile';
import { useCreatorTrust, BADGE_LABEL } from '../lib/reputation';
import { ReputationBadge } from './terminal/ReputationBadge';

function AuthorTrust({ chain, address }) {
  const trust = useCreatorTrust(chain, address);
  if (!trust) return null;
  return <span className={`reputation-badge badge-${trust.badge} chat-author-trust`} title={`This poster has launched ${trust.tokenCount} tracked token${trust.tokenCount === 1 ? '' : 's'} · ${trust.ruggedCount} flagged · score ${trust.score}/100`}>{trust.badge === 'flagged' ? '⚠ ' : ''}{BADGE_LABEL[trust.badge]} · {trust.score}</span>;
}
const API = apiUrl('/api');
const registeredCalls = new Set();
// Call Ledger: any coin posted in chat becomes a tracked call. The server prices it itself.
function registerCalls(room, messages) {
  (messages || []).forEach(m => (m.tokens || []).forEach(t => {
    const pair = t.pair || {};
    const chain = pair.chainId || t.chainId;
    const pairAddress = pair.pairAddress || t.pairAddress;
    if (!chain || !pairAddress) return;
    const key = `${m.id}:${pairAddress}`;
    if (registeredCalls.has(key)) return;
    registeredCalls.add(key);
    fetch(apiUrl('/api/reputation/calls'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room, messageId: String(m.id), caller: m.profile?.hidden ? 'anon' : (m.username || 'anon'), callerAddress: m.profile?.address || m.address || null, chain, pairAddress, ts: m.ts }) }).catch(() => {});
  }));
}
const detectAddress = text => text.match(/\b0x[a-fA-F0-9]{40}\b/)?.[0] || text.match(/\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/)?.[0];

export default function EcosystemChat({ ecosystem, room: roomProp, compact = false, onConnect }) {
  const room = roomProp || ecosystem?.id || 'general';
  const { wallet, signMessage } = useWallet() || {};
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [replyTarget, setReplyTarget] = useState(null);
  const [inspected, setInspected] = useState(null);
  const scroller = useRef(null);
  const stick = useRef(true);
  const refresh = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setMessages([]); setLoading(true); setInput(''); setError('');
    const load = async () => {
      try {
        const res = await fetch(`${API}/chat/${encodeURIComponent(room)}`, { signal: controller.signal });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!controller.signal.aborted) { setMessages(data.messages); setError(''); registerCalls(room, data.messages); }
      } catch (e) { if (e.name !== 'AbortError') setError('Chat connection interrupted. Retry the room connection.'); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    };
    refresh.current = load; load(); const timer = setInterval(() => { if (!document.hidden) load(); }, 6000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [room, wallet?.address, wallet?.chain]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (stick.current && scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight; }, [messages]);
  const send = async e => {
    e.preventDefault(); const text = input.trim();
    if (!text || sending) return;
    setSending(true); setError(''); let tokens = null;
    try {
      if (!wallet) throw Object.assign(new Error('Connect your wallet to post in the trenches.'), { code: 'WALLET_REQUIRED' });
      const proof = await walletProof(wallet, signMessage);
      const res = await fetch(`${API}/chat/${encodeURIComponent(room)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...proof, text, tokens, parentId: replyTarget?.id || null }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Message not sent.');
      setInput(''); stick.current = true; await refresh.current?.();
      setReplyTarget(null);
    } catch (nextError) { setError(nextError.code === 'WALLET_REQUIRED' ? nextError.message : nextError.message || 'Message not sent. Your draft is preserved; please retry.'); }
    finally { setSending(false); }
  };
  const interact = async (message, action) => {
    if (!wallet) { setError('Connect your wallet to interact in the trenches.'); return; }
    try {
      const proof = await walletProof(wallet, signMessage);
      const res = await fetch(`${API}/chat/${encodeURIComponent(room)}/${encodeURIComponent(message.id)}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...proof, ...(action === 'reply' ? { text: input.trim() } : {}) }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Interaction failed.');
      if (action === 'like') setMessages(current => current.map(item => item.id === message.id ? { ...item, likedByMe: data.liked, likeCount: data.likeCount } : item));
      else { setInput(''); setReplyTarget(null); await refresh.current?.(); }
    } catch (nextError) { setError(nextError.message || 'Interaction failed.'); }
  };
  const flagProfile = async profile => {
    if (!wallet) { setError('Connect your wallet to flag a profile.'); return; }
    try {
      const proof = await walletProof(wallet, signMessage);
      const res = await fetch(`${API}/profile/${encodeURIComponent(profile.address)}/flag`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...proof, targetChain: profile.chain }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Profile flag was not recorded.');
      setInspected(current => current ? { ...current, flagCount: data.flagCount } : current);
    } catch (nextError) { setError(nextError.message || 'Profile flag was not recorded.'); }
  };
  const openProfile = message => setInspected(message.profile || { address: message.address, chain: message.chain, username: message.username });
  return <div className={`ecosystem-chat ${compact ? 'compact-chat' : ''}`} data-testid={`chat-${room}`}>
    {!compact && <div className="chat-room-heading"><MessageCircle size={17} /><strong>{ecosystem?.name || 'General'}</strong><span className="data-status"><i />POLLING</span></div>}
    <div className="chat-identity" data-testid={`chat-identity-${room}`}><span>#{room}</span>{wallet ? <span className="chat-wallet-state"><i />SIGNED · {displayAddress(wallet.address)}</span> : <button type="button" onClick={onConnect}>Connect wallet to post</button>}</div>
    <div className="chat-messages custom-scroll" ref={scroller} onScroll={() => { const e = scroller.current; stick.current = e.scrollHeight - e.scrollTop - e.clientHeight < 65; }}>
      {loading && <div className="chat-empty" data-testid={`chat-loading-${room}`}><span className="loader" />Connecting to the room…</div>}
      {!loading && !messages.length && <div className="chat-empty" data-testid={`chat-empty-${room}`}><MessageCircle size={28} /><strong>The next alpha starts here.</strong><span>No messages in this channel yet.</span></div>}
      {messages.map(m => <div className={`chat-message ${m.parentId ? 'chat-reply' : ''}`} key={m.id} data-testid={`chat-message-${m.id}`}><button type="button" className="chat-avatar" onClick={() => openProfile(m)} title={`Open ${m.username} profile`}>{m.profile?.avatarUrl ? <img src={m.profile.avatarUrl} alt="" /> : <span>{m.username.slice(-2).toUpperCase()}</span>}</button><div><div className="message-meta"><button type="button" onClick={() => openProfile(m)}><b>{m.profile?.hidden ? 'Private wallet' : m.username}</b></button><time>{formatTime(m.ts)}</time>{m.profile?.category && <span className="message-category">{m.profile.category}</span>}<AuthorTrust chain={m.profile?.chain || m.chain} address={m.profile?.address || m.address} /></div>{m.parentId && <small className="reply-context"><Reply size={11} />reply</small>}<p>{m.text}</p>{m.tokens?.map((t, i) => t.pair ? <div key={i} className="chat-token-wrap"><div className="chat-token-trust"><ReputationBadge pair={t.pair} /></div><IntelligenceCard id={`chat-token-${m.id}-${i}`} pair={t.pair} snapshotTime={t.fetched_at} /></div> : <TokenCard key={i} testId={`chat-token-${m.id}-${i}`} compact pair={{ chainId: t.chainId, baseToken: { name: t.name, symbol: t.symbol, address: t.address }, priceUsd: t.priceUsd, priceChange: { h24: t.priceChange24h }, liquidity: { usd: t.liquidity }, volume: { h24: t.volume }, marketCap: t.mcap, url: t.url, pairCreatedAt: t.pairCreatedAt, info: { imageUrl: t.imageUrl } }} />)}<div className="message-actions"><button type="button" className={m.likedByMe ? 'is-liked' : ''} onClick={() => interact(m, 'like')}><Heart size={13} />{m.likeCount || 0}</button><button type="button" onClick={() => { setReplyTarget(m); setInput(''); }}><Reply size={13} />Reply</button></div></div></div>)}
    </div>
    {error && <div className="chat-error" role="alert" data-testid={`chat-error-${room}`}><span>{error}</span><button type="button" data-testid={`chat-retry-${room}`} onClick={() => refresh.current?.()}>Retry connection</button></div>}
    {replyTarget && <div className="chat-replying"><Reply size={13} />Replying to {replyTarget.username}<button type="button" aria-label="Cancel reply" onClick={() => setReplyTarget(null)}><X size={13} /></button></div>}
    <form onSubmit={send} className="chat-compose"><input aria-label="Chat message" data-testid={`chat-input-${room}`} value={input} onChange={e => setInput(e.target.value)} maxLength={1000} placeholder={replyTarget ? 'Write a reply…' : 'Drop alpha or paste a CA…'} /><button aria-label="Send message" data-testid={`chat-send-${room}`} disabled={sending || !input.trim()}>{sending ? <span className="loader" /> : <Send size={16} />}</button></form>
    {inspected && <div className="chat-profile-popover" role="dialog" aria-label="Chat profile"><button type="button" className="chat-profile-close" aria-label="Close profile" onClick={() => setInspected(null)}><X size={14} /></button><div className="profile-cover small-cover" style={inspected.backgroundUrl ? { backgroundImage: `url(${inspected.backgroundUrl})` } : {}} /><div className="chat-profile-body"><div className="profile-picture small-picture">{inspected.avatarUrl ? <img src={inspected.avatarUrl} alt="" /> : <UserRound size={20} />}</div>{inspected.hidden ? <><strong>Private wallet</strong><p>This creator keeps profile details and flag count private.</p></> : <><strong>{profileLabel(inspected)}</strong><small>{displayAddress(inspected.address)} · {inspected.category || 'Trader'}</small>{inspected.bio && <p>{inspected.bio}</p>}<div className="chat-profile-links">{inspected.xUrl && <a href={inspected.xUrl} target="_blank" rel="noreferrer"><ExternalLink size={12} />X</a>}{inspected.websiteUrl && <a href={inspected.websiteUrl} target="_blank" rel="noreferrer"><Link2 size={12} />Website</a>}</div><div className="chat-profile-footer"><span><Flag size={12} />{inspected.flagCount || 0} flags</span><button type="button" onClick={() => flagProfile(inspected)}><Flag size={12} />Flag profile</button></div></>}</div></div>}
  </div>;
}