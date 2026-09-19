import React, { useEffect, useRef, useState } from 'react';
import { Send, Loader2, Search } from 'lucide-react';
import axios from 'axios';
import { searchTokenByAddress } from '../lib/dexscreener';
import TokenCard from './TokenCard';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function detectAddress(text) {
  // EVM address
  const evm = text.match(/0x[a-fA-F0-9]{40}/);
  if (evm) return evm[0];
  // Solana base58 address 32-44 chars
  const sol = text.match(/[1-9A-HJ-NP-Za-km-z]{32,44}/);
  if (sol) return sol[0];
  return null;
}

export default function EcosystemChat({ ecosystem }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [username] = useState(() => {
    let u = localStorage.getItem('feeless_user');
    if (!u) { u = 'anon_' + Math.random().toString(36).slice(2, 7); localStorage.setItem('feeless_user', u); }
    return u;
  });
  const endRef = useRef();

  const room = ecosystem?.id || 'general';

  const fetchMessages = async () => {
    try {
      const res = await axios.get(`${API}/chat/${room}`);
      setMessages(res.data.messages || []);
    } catch (e) { /* silent */ }
  };

  useEffect(() => {
    setLoading(true);
    fetchMessages().finally(() => setLoading(false));
    const t = setInterval(fetchMessages, 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, [room]);

  useEffect(() => {
    const el = endRef.current;
    if (el && el.parentElement) {
      el.parentElement.scrollTop = el.parentElement.scrollHeight;
    }
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setSending(true);
    const addr = detectAddress(text);
    let tokens = null;
    if (addr) {
      const pairs = await searchTokenByAddress(addr);
      if (pairs.length > 0) {
        tokens = pairs.slice(0, 1).map(p => ({
          chainId: p.chainId, address: p.baseToken?.address, symbol: p.baseToken?.symbol,
          name: p.baseToken?.name, priceUsd: p.priceUsd, url: p.url,
          liquidity: p.liquidity?.usd, volume: p.volume?.h24, mcap: p.marketCap || p.fdv,
          priceChange24h: p.priceChange?.h24, pairCreatedAt: p.pairCreatedAt,
          imageUrl: p.info?.imageUrl
        }));
      }
    }
    try {
      await axios.post(`${API}/chat/${room}`, { username, text, tokens });
      setInput('');
      fetchMessages();
    } catch (e) { /* silent */ }
    setSending(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#14F195]/10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-white/40">Ecosystem Chat</div>
          <div className="text-white font-bold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#14F195] animate-pulse"></span>
            {ecosystem?.name || 'General'}
          </div>
        </div>
        <div className="text-[10px] text-white/40 font-mono">you: {username}</div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2 custom-scroll">
        {loading && (
          <div className="flex items-center justify-center py-8 text-white/40 text-xs"><Loader2 className="animate-spin mr-2" size={14}/>Loading messages…</div>
        )}
        {!loading && messages.length === 0 && (
          <div className="text-center py-10 text-white/40 text-xs">
            No messages yet.<br/>Be the first — paste a token CA to auto-preview.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={m.id || i} className="group">
            <div className="flex items-baseline gap-2 mb-0.5">
              <span className="text-xs font-semibold text-[#14F195]">{m.username}</span>
              <span className="text-[10px] text-white/30">{new Date(m.ts).toLocaleTimeString()}</span>
            </div>
            <div className="text-sm text-white/90 leading-relaxed break-words">{m.text}</div>
            {m.tokens && m.tokens.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {m.tokens.map((t, j) => (
                  <TokenCard key={j} pair={{
                    chainId: t.chainId,
                    baseToken: { name: t.name, symbol: t.symbol, address: t.address },
                    priceUsd: t.priceUsd,
                    priceChange: { h24: t.priceChange24h },
                    liquidity: { usd: t.liquidity },
                    volume: { h24: t.volume },
                    marketCap: t.mcap,
                    url: t.url,
                    pairCreatedAt: t.pairCreatedAt,
                    info: { imageUrl: t.imageUrl }
                  }} />
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="p-3 border-t border-[#14F195]/10">
        <div className="flex items-center gap-2 bg-black/60 border border-[#14F195]/20 focus-within:border-[#14F195]/60 rounded-xl px-3 py-2 transition-colors">
          <Search size={14} className="text-white/30"/>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Type a message or paste a CA…"
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none"
          />
          <button onClick={send} disabled={sending || !input.trim()}
            className="w-8 h-8 rounded-lg bg-[#14F195] hover:bg-[#00FFA3] disabled:opacity-40 disabled:cursor-not-allowed text-black flex items-center justify-center transition-colors">
            {sending ? <Loader2 size={14} className="animate-spin"/> : <Send size={14}/>}
          </button>
        </div>
        <div className="text-[10px] text-white/30 mt-1.5 px-1">Paste any SPL / EVM contract address → auto-preview via DexScreener</div>
      </div>
    </div>
  );
}
