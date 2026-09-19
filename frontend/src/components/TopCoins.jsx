import React, { useEffect, useState } from 'react';
import { Loader2, Flame, Rocket, Droplets } from 'lucide-react';
import { searchTokens, getLatestBoosts } from '../lib/dexscreener';
import TokenCard from './TokenCard';

export default function TopCoins({ ecosystem }) {
  const [tab, setTab] = useState('trending');
  const [pairs, setPairs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      let results = [];
      const chain = ecosystem?.chainId;
      if (tab === 'trending') {
        // Use search by chain name to get active pairs
        const q = ecosystem?.symbol || ecosystem?.name || 'sol';
        const r = await searchTokens(q);
        results = r.filter(p => !chain || p.chainId === chain).slice(0, 10);
      } else if (tab === 'new') {
        const boosts = await getLatestBoosts();
        const filtered = boosts.filter(b => !chain || b.chainId === chain).slice(0, 12);
        // fetch pair data for each
        const detailed = await Promise.all(filtered.map(async b => {
          const r = await searchTokens(b.tokenAddress);
          return r.find(p => p.baseToken?.address?.toLowerCase() === b.tokenAddress.toLowerCase()) || r[0];
        }));
        results = detailed.filter(Boolean).slice(0, 10);
      } else if (tab === 'volume') {
        const q = ecosystem?.symbol || 'usdc';
        const r = await searchTokens(q);
        results = r.filter(p => !chain || p.chainId === chain)
          .sort((a, b) => (b.volume?.h24 || 0) - (a.volume?.h24 || 0))
          .slice(0, 10);
      }
      if (!cancelled) { setPairs(results); setLoading(false); }
    };
    load();
    return () => { cancelled = true; };
  }, [tab, ecosystem?.id]);

  const tabs = [
    { id: 'trending', label: 'Trending', Icon: Flame },
    { id: 'new', label: 'New', Icon: Rocket },
    { id: 'volume', label: 'Volume', Icon: Droplets },
  ];

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[#14F195]/10">
        <div className="text-[10px] uppercase tracking-[0.2em] text-white/40">Top Coins</div>
        <div className="text-white font-bold">{ecosystem?.name || 'All Chains'}</div>
      </div>
      <div className="flex gap-1 px-3 pt-3">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
              tab === t.id
                ? 'bg-[#14F195]/15 text-[#14F195] border border-[#14F195]/40'
                : 'text-white/50 hover:text-white/80 border border-transparent'
            }`}>
            <t.Icon size={11}/>{t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2 custom-scroll">
        {loading && (
          <div className="flex items-center justify-center py-8 text-white/40 text-xs"><Loader2 className="animate-spin mr-2" size={14}/>Loading…</div>
        )}
        {!loading && pairs.length === 0 && (
          <div className="text-center py-8 text-white/40 text-xs">No data available</div>
        )}
        {pairs.map((p, i) => <TokenCard key={p.pairAddress || i} pair={p} />)}
      </div>
    </div>
  );
}
