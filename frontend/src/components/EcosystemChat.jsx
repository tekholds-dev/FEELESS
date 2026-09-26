import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Flag, Heart, Link2, Lock, MessageCircle, Reply, Send, UserRound, X } from 'lucide-react';
import { searchTokenByAddress, formatTime } from '../lib/dexscreener';
import TokenCard from './TokenCard';
import { IntelligenceCard } from './command/IntelligenceCard';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { displayAddress, profileLabel, walletProof } from '../lib/profile';
import { useCreatorTrust, BADGE_LABEL } from '../lib/reputation';
import { ReputationBadge } from './terminal/ReputationBadge';
import { Badges } from './terminal/Badges';
import { SlashMenu, CommandCard, runCommand } from './ChatCommands';

function AuthorTrust({ chain, address }) {
  const trust = useCreatorTrust(chain, address);
  if (!trust) return null;
  return <span className={`reputation-badge badge-${trust.badge} chat-author-trust`} title={`This poster has launched ${trust.tokenCount} tracked token${trust.tokenCount === 1 ? '' : 's'} · ${trust.ruggedCount} flagged · score ${trust.score}/100`}>{trust.badge === 'flagged' ? '⚠ ' : ''}{BADGE_LABEL[trust.badge]} · {trust.score}</span>;
}
const API = apiUrl('/api');
const registeredCalls = new Set();
const EMOJIS = ['🔥', '🚀', '💎', '💀'];
let callerBoard = { at: 0, map: new Map() };
const voterId = wallet => {
  if (wallet?.address) return wallet.address;
  try { let v = localStorage.getItem('feeless-voter'); if (!v) { v = `browser-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`; localStorage.setItem('feeless-voter', v); } return v; } catch { return 'browser-anon'; }
};
// Reactions, per-message call performance and caller track records for one room.
function useChatMeta(room, wallet) {
  const [meta, setMeta] = useState({ reactions: {}, calls: {}, board: callerBoard.map });
  const load = React.useCallback(async () => {
    if (typeof fetch !== 'function') return;
    try {
      const [r, c] = await Promise.all([
        fetch(apiUrl(`/api/reputation/reactions?room=${encodeURIComponent(room)}&voter=${encodeURIComponent(voterId(wallet))}`)).then(x => (x.ok ? x.json() : {})),
        fetch(apiUrl(`/api/reputation/calls/by-room?room=${encodeURIComponent(room)}`)).then(x => (x.ok ? x.json() : {})),
      ]);
      if (Date.now() - callerBoard.at > 60000) {
        const b = await fetch(apiUrl('/api/reputation/calls/leaderboard?days=30')).then(x => (x.ok ? x.json() : {})).catch(() => ({}));
        callerBoard = { at: Date.now(), map: new Map((b.rows || []).map(row => [row.caller, row])) };
      }
      setMeta({ reactions: r.reactions || {}, calls: c.calls || {}, board: callerBoard.map });
    } catch { /* keep last meta */ }
  }, [room, wallet]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 8000); return () => clearInterval(t); }, [load]);
  const react = async (messageId, emoji) => {
    await fetch(apiUrl('/api/reputation/reactions'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room, messageId: String(messageId), emoji, voter: voterId(wallet) }) }).catch(() => {});
    load();
  };
  return { ...meta, react };
}
const CA_SPLIT = /(@[A-Za-z0-9_.-]{2,32}|\$[A-Za-z][A-Za-z0-9]{1,11}\b|\bCA:|\b0x[0-9a-fA-F]{40}\b|\b[1-9A-HJ-NP-Za-km-z]{32,44}\b)/g;
export const trackClick = (kind, value, room) => { try { fetch(apiUrl('/api/reputation/clicks'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind, value, room: room || '' }), keepalive: true }).catch(() => {}); } catch { /* never block a click */ } };
function RichText({ text, tokens, me, room, people }) {
  return <>{String(text).split(CA_SPLIT).map((part, i) => {
    if (!part) return null;
    if (part.startsWith('@')) return <a key={i} className={`chat-mention ${me && part.slice(1).toLowerCase() === me.toLowerCase() ? 'is-me' : ''}`} href={people?.[part.slice(1).toLowerCase()] ? `/terminal/profile/${people[part.slice(1).toLowerCase()]}` : `/terminal/trade?q=${encodeURIComponent(part.slice(1))}`} target="_blank" rel="noopener noreferrer" onClick={() => trackClick('mention', part.slice(1), room)}>{part}</a>;
    if (part === 'CA:') return <span key={i} className="chat-ca-label">CA:</span>;
    if (part.startsWith('$')) {
      const t = (tokens || []).find(x => String(x.symbol || '').toLowerCase() === part.slice(1).toLowerCase());
      const href = t?.pairAddress ? `/?coin=${t.chainId}:${t.pairAddress}` : `/terminal/trade?q=${encodeURIComponent(part.slice(1))}`;
      return <a key={i} className="chat-ticker" href={href} target="_blank" rel="noopener noreferrer" title={`Open ${part} in FEELESS`} onClick={() => trackClick('ticker', part, room)}>{part}</a>;
    }
    if (/^(0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})$/.test(part)) {
      const t = (tokens || []).find(x => x.address === part);
      const href = t?.pairAddress ? `/?coin=${t.chainId}:${t.pairAddress}` : `/terminal/trade?q=${part}`;
      return <a key={i} className="chat-ca" href={href} target="_blank" rel="noopener noreferrer" title={`${part} — open in FEELESS`} onClick={() => trackClick('ca', part, room)}>{t?.symbol ? `$${t.symbol}` : `${part.slice(0, 4)}…${part.slice(-4)}`} ↗</a>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  })}</>;
}
const fmtX = v => (v == null ? '—' : `${v >= 100 ? v.toFixed(0) : v.toFixed(2)}×`);
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
  const { wallet, signMessage, switchTo } = useWallet() || {};
  const [switching, setSwitching] = useState(false);
  const hopToSolana = async () => { setSwitching(true); try { await switchTo?.('solana'); } catch (err) { setError?.(err.message || 'Switch declined.'); } finally { setSwitching(false); } };
  const chatMeta = useChatMeta(room, wallet);
  const [gate, setGate] = useState(null);
  useEffect(() => {
    if (typeof fetch !== 'function') return undefined;
    let alive = true;
    fetch(apiUrl(`/api/reputation/chat/gate?room=${encodeURIComponent(room)}${wallet?.address ? `&address=${wallet.address}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(g => alive && setGate(g)).catch(() => {});
    return () => { alive = false; };
  }, [room, wallet?.address]);
  const [messages, setMessages] = useState([]);
  const [fx, setFx] = useState({});
  const [cmdCard, setCmdCard] = useState(null);
  const [myTier, setMyTier] = useState(0);
  const [boostNext, setBoostNext] = useState(false);
  useEffect(() => { if (!wallet?.address) { setMyTier(0); return; } fetch(apiUrl(`/api/reputation/perks/${wallet.address}`)).then(r => r.json()).then(d => setMyTier(d.tier || 0)).catch(() => {}); }, [wallet?.address]);
  const people = useMemo(() => { const out = {}; messages.forEach(m => { const a = m.profile?.address || m.address; if (!a || m.system) return; [m.username, fx[a]?.displayName].filter(Boolean).forEach(n => { out[String(n).toLowerCase()] = a; }); }); return out; }, [messages, fx]);
  const authorKey = messages.map(m => m.profile?.address || m.address).filter(Boolean).sort().join(',');
  useEffect(() => {
    const list = [...new Set(authorKey.split(',').filter(Boolean))];
    if (!list.length || typeof fetch !== 'function') return;
    fetch(apiUrl(`/api/reputation/profiles?addresses=${list.join(',')}`)).then(r => (r.ok ? r.json() : {})).then(d => setFx(d.profiles || {})).catch(() => {});
  }, [authorKey]);
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
        const res = await fetch(apiUrl(`/api/reputation/chat/${encodeURIComponent(room)}`), { signal: controller.signal });
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
    e.preventDefault(); let text = input.trim(); let boost = boostNext;
    if (!text || sending) return;
    if (text.startsWith('/')) {
      setSending(true); setError('');
      try {
        const out = await runCommand(text, { room, wallet, tier: myTier });
        if (out.card) { setCmdCard(out.card); setInput(''); return; }
        text = out.post; boost = boost || Boolean(out.boost);
      } catch (err) { setCmdCard({ title: 'Command failed', lines: [err.message || 'Try again.'] }); return; }
      finally { setSending(false); }
    }
    setSending(true); setError(''); let tokens = null;
    try {
      if (!wallet) throw Object.assign(new Error('Connect your wallet to post in the trenches.'), { code: 'WALLET_REQUIRED' });
      if (gate?.needsChain === 'solana' && wallet.chain !== 'solana') throw new Error(`${gate.symbol} lives on Solana — switch your wallet to Solana to chat here.`);
      if (gate?.gated && !gate.allowed) throw new Error(`Hold at least $${gate.minUsd} of ${gate.symbol} to chat here.`);
      const ts = Math.floor(Date.now() / 1000);
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))).map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
      const signature = await signMessage(`FEELESS chat\nroom:${room}\naddress:${wallet.address}\nts:${ts}\nhash:${digest}`);
      const res = await fetch(apiUrl('/api/reputation/chat'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room, address: wallet.address, text, ts, signature, parentId: replyTarget?.id || null, boost }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Message not sent.');
      setInput(''); setBoostNext(false); stick.current = true; await refresh.current?.();
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
      {messages.map(m => <div className={`chat-message ${m.parentId ? 'chat-reply' : ''} ${m.boosted ? 'is-boosted' : ''} tier-${m.tier || 0}`} key={m.id} data-testid={`chat-message-${m.id}`}><button type="button" className="chat-avatar" onClick={() => openProfile(m)} title={`Open ${m.username} profile`}>{(fx[m.profile?.address || m.address]?.avatarUrl || m.profile?.avatarUrl) ? <img src={fx[m.profile?.address || m.address]?.avatarUrl || m.profile.avatarUrl} alt="" /> : <span>{m.username.slice(-2).toUpperCase()}</span>}</button><div><div className="message-meta"><button type="button" onClick={() => openProfile(m)}><b style={fx[m.profile?.address || m.address]?.accent ? { color: fx[m.profile?.address || m.address].accent } : undefined}>{m.profile?.hidden ? 'Private wallet' : (fx[m.profile?.address || m.address]?.displayName || m.username)}</b></button>{!m.profile?.hidden && (m.profile?.address || m.address) && !m.system && <Badges address={m.profile?.address || m.address} compact featured={fx[m.profile?.address || m.address]?.featuredBadges} />}{m.system && <span className="fee-system-chip">LEADER CAT</span>}{!m.profile?.hidden && (m.profile?.address || m.address) && !m.system && <a className="chat-profile-link" href={`/terminal/profile/${m.profile?.address || m.address}`} target="_blank" rel="noopener noreferrer" title="Open profile">↗</a>}{(() => { const rec = chatMeta.board.get(m.profile?.hidden ? 'anon' : m.username); return rec ? <span className="caller-chip" title={`Call Ledger (30d): ${rec.calls} calls, ${Math.round(rec.hitRate * 100)}% reached 2×, avg peak ${fmtX(rec.avgPeakX)}`}>🎯 {Math.round(rec.hitRate * 100)}% · {rec.calls}</span> : null; })()}<time>{formatTime(m.ts)}</time>{m.profile?.category && <span className="message-category">{m.profile.category}</span>}<AuthorTrust chain={m.profile?.chain || m.chain} address={m.profile?.address || m.address} /></div>{m.parentId && <small className="reply-context"><Reply size={11} />reply</small>}<p><RichText text={m.text} tokens={m.tokens} me={fx[wallet?.address]?.displayName} room={room} people={people} /></p>{m.tokens?.map((t, i) => t.pair ? <div key={i} className="chat-token-wrap"><div className="chat-token-trust"><ReputationBadge pair={t.pair} /></div><IntelligenceCard id={`chat-token-${m.id}-${i}`} pair={t.pair} snapshotTime={t.fetched_at} /></div> : <TokenCard key={i} testId={`chat-token-${m.id}-${i}`} compact pair={{ chainId: t.chainId, baseToken: { name: t.name, symbol: t.symbol, address: t.address }, priceUsd: t.priceUsd, priceChange: { h24: t.priceChange24h }, liquidity: { usd: t.liquidity }, volume: { h24: t.volume }, marketCap: t.mcap, url: t.url, pairCreatedAt: t.pairCreatedAt, info: { imageUrl: t.imageUrl } }} />)}{(chatMeta.calls[String(m.id)] || []).map(c => <div key={c.pairAddress} className={`call-perf ${(c.x || 1) >= 1 ? 'up' : 'down'}`}><span>📣 {c.symbol} since posted</span><b>{fmtX(c.x)}</b><small>peak {fmtX(c.peakX)}</small></div>)}<div className="message-reactions">{EMOJIS.map(e => { const r = chatMeta.reactions[String(m.id)]?.[e]; return <button type="button" key={e} className={r?.mine ? 'mine' : ''} onClick={() => chatMeta.react(m.id, e)} aria-label={`React ${e}`}>{e}{r?.count ? <span>{r.count}</span> : null}</button>; })}</div><div className="message-actions"><button type="button" className={m.likedByMe ? 'is-liked' : ''} onClick={() => interact(m, 'like')}><Heart size={13} />{m.likeCount || 0}</button><button type="button" onClick={() => { setReplyTarget(m); setInput(''); }}><Reply size={13} />Reply</button></div></div></div>)}
    </div>
    {error && <div className="chat-error" role="alert" data-testid={`chat-error-${room}`}><span>{error}</span><button type="button" data-testid={`chat-retry-${room}`} onClick={() => refresh.current?.()}>Retry connection</button></div>}
    {replyTarget && <div className="chat-replying"><Reply size={13} />Replying to {replyTarget.username}<button type="button" aria-label="Cancel reply" onClick={() => setReplyTarget(null)}><X size={13} /></button></div>}
    {gate?.gated && <div className={`chat-gate ${gate.allowed ? 'ok' : ''}`} data-testid="chat-gate">{gate.needsChain === 'solana' && wallet?.chain !== 'solana' ? <>🔁 {gate.symbol} lives on Solana — your {wallet?.name || 'wallet'} is on EVM. <button type="button" className="chat-switch-eco" onClick={hopToSolana} disabled={switching}>{switching ? 'Switching…' : 'Switch to Solana'}</button></> : gate.allowed ? `✓ Holder · ${gate.symbol} room (you hold $${Number(gate.holdingUsd).toFixed(2)})` : wallet ? `🔒 Hold ≥ $${gate.minUsd} of ${gate.symbol} to chat here — you hold $${Number(gate.holdingUsd || 0).toFixed(2)}` : `🔒 Holders only — connect a wallet holding ≥ $${gate.minUsd} of ${gate.symbol}`}</div>}
    {cmdCard && <CommandCard card={cmdCard} onClose={() => setCmdCard(null)} />}
    <form onSubmit={send} className="chat-compose"><SlashMenu input={input} tier={myTier} onPick={c => setInput(`/${c.cmd}${c.args ? ' ' : ''}`)} />{myTier >= 2 && <button type="button" className={`chat-boost ${boostNext ? 'on' : ''}`} onClick={() => setBoostNext(b => !b)} title="Boost this message (Fee Insider perk, 1 per 10 min)" aria-label="Boost message">⚡</button>}<input aria-label="Chat message" data-testid={`chat-input-${room}`} value={input} onChange={e => setInput(e.target.value)} maxLength={500} disabled={Boolean(gate?.gated && !gate.allowed && wallet && !gate.needsChain)} placeholder={replyTarget ? 'Write a reply…' : 'Drop alpha, $TICKER, CA: … or type / for commands'} /><button aria-label="Send message" data-testid={`chat-send-${room}`} disabled={sending || !input.trim()}>{sending ? <span className="loader" /> : <Send size={16} />}</button></form>
    {inspected && <div className="chat-profile-popover" role="dialog" aria-label="Chat profile"><button type="button" className="chat-profile-close" aria-label="Close profile" onClick={() => setInspected(null)}><X size={14} /></button><div className="profile-cover small-cover" style={inspected.backgroundUrl ? { backgroundImage: `url(${inspected.backgroundUrl})` } : {}} /><div className="chat-profile-body"><div className="profile-picture small-picture">{inspected.avatarUrl ? <img src={inspected.avatarUrl} alt="" /> : <UserRound size={20} />}</div>{inspected.hidden ? <><strong>Private wallet</strong><p>This creator keeps profile details and flag count private.</p></> : <><strong>{profileLabel(inspected)}</strong><small>{displayAddress(inspected.address)} · {inspected.category || 'Trader'}</small>{inspected.bio && <p>{inspected.bio}</p>}<div className="chat-profile-links">{inspected.xUrl && <a href={inspected.xUrl} target="_blank" rel="noreferrer"><ExternalLink size={12} />X</a>}{inspected.websiteUrl && <a href={inspected.websiteUrl} target="_blank" rel="noreferrer"><Link2 size={12} />Website</a>}</div><div className="chat-profile-footer"><span><Flag size={12} />{inspected.flagCount || 0} flags</span><button type="button" onClick={() => flagProfile(inspected)}><Flag size={12} />Flag profile</button></div></>}</div></div>}
  </div>;
}