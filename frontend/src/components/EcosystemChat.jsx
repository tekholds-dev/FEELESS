import React, { useEffect, useRef, useState } from 'react';
import { Send, MessageCircle } from 'lucide-react';
import { searchTokenByAddress, formatTime } from '../lib/dexscreener';
import TokenCard from './TokenCard';
import { IntelligenceCard } from './command/IntelligenceCard';
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const detectAddress = text => text.match(/\b0x[a-fA-F0-9]{40}\b/)?.[0] || text.match(/\b[1-9A-HJ-NP-Za-km-z]{32,44}\b/)?.[0];

export default function EcosystemChat({ ecosystem, compact = false }) {
  const room = ecosystem?.id || 'general';
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [username] = useState(() => {
    const saved = localStorage.getItem('feeless_user');
    if (saved) return saved;
    const created = 'degen_' + Math.random().toString(36).slice(2, 7);
    localStorage.setItem('feeless_user', created); return created;
  });
  const scroller = useRef(null);
  const stick = useRef(true);
  const refresh = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setMessages([]); setLoading(true); setInput(''); setError('');
    const load = async () => {
      try {
        const res = await fetch(`${API}/chat/${room}`, { signal: controller.signal });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!controller.signal.aborted) { setMessages(data.messages); setError(''); }
      } catch (e) { if (e.name !== 'AbortError') setError('Chat connection interrupted. Retrying…'); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    };
    refresh.current = load; load(); const timer = setInterval(load, 4000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [room]);
  useEffect(() => { if (stick.current && scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight; }, [messages]);
  const send = async e => {
    e.preventDefault(); const text = input.trim();
    if (!text || sending) return;
    setSending(true); setError(''); let tokens = null;
    try {
      // The server resolves contract cards; client-provided market claims are not trusted.
      const res = await fetch(`${API}/chat/${room}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, text, tokens }) });
      if (!res.ok) throw new Error();
      setInput(''); stick.current = true; await refresh.current?.();
    } catch { setError('Message not sent. Your draft is preserved; please retry.'); }
    finally { setSending(false); }
  };
  return <div className={`ecosystem-chat ${compact ? 'compact-chat' : ''}`} data-testid={`chat-${room}`}>
    {!compact && <div className="chat-room-heading"><MessageCircle size={17} /><strong>{ecosystem?.name || 'General'}</strong><span className="data-status"><i />POLLING</span></div>}
    <div className="chat-identity" data-testid={`chat-identity-${room}`}>#{room}<span>{username}</span></div>
    <div className="chat-messages custom-scroll" ref={scroller} onScroll={() => { const e = scroller.current; stick.current = e.scrollHeight - e.scrollTop - e.clientHeight < 65; }}>
      {loading && <div className="chat-empty" data-testid={`chat-loading-${room}`}><span className="loader" />Connecting to the room…</div>}
      {!loading && !messages.length && <div className="chat-empty" data-testid={`chat-empty-${room}`}><MessageCircle size={28} /><strong>The next alpha starts here.</strong><span>No messages in this channel yet.</span></div>}
      {messages.map(m => <div className="chat-message" key={m.id} data-testid={`chat-message-${m.id}`}><span className="chat-avatar">{m.username.slice(-2).toUpperCase()}</span><div><div className="message-meta"><b>{m.username}</b><time>{formatTime(m.ts)}</time></div><p>{m.text}</p>{m.tokens?.map((t, i) => t.pair ? <IntelligenceCard key={i} id={`chat-token-${m.id}-${i}`} pair={t.pair} snapshotTime={t.fetched_at} /> : <TokenCard key={i} testId={`chat-token-${m.id}-${i}`} compact pair={{ chainId: t.chainId, baseToken: { name: t.name, symbol: t.symbol, address: t.address }, priceUsd: t.priceUsd, priceChange: { h24: t.priceChange24h }, liquidity: { usd: t.liquidity }, volume: { h24: t.volume }, marketCap: t.mcap, url: t.url, pairCreatedAt: t.pairCreatedAt, info: { imageUrl: t.imageUrl } }} />)}</div></div>)}
    </div>
    {error && <div className="chat-error" role="alert" data-testid={`chat-error-${room}`}>{error}</div>}
    <form onSubmit={send} className="chat-compose"><input aria-label="Chat message" data-testid={`chat-input-${room}`} value={input} onChange={e => setInput(e.target.value)} maxLength={1000} placeholder="Drop alpha or paste a CA…" /><button aria-label="Send message" data-testid={`chat-send-${room}`} disabled={sending || !input.trim()}>{sending ? <span className="loader" /> : <Send size={16} />}</button></form>
  </div>;
}