import React from 'react';
import { ExternalLink, TrendingUp, TrendingDown, Droplet, BarChart3, Clock } from 'lucide-react';
import { formatUSD, formatAge } from '../lib/dexscreener';

export default function TokenCard({ pair, compact = false }) {
  if (!pair) return null;
  const base = pair.baseToken || {};
  const priceChange = pair.priceChange?.h24 ?? 0;
  const positive = priceChange >= 0;
  const liquidity = pair.liquidity?.usd;
  const volume = pair.volume?.h24;
  const mcap = pair.marketCap || pair.fdv;
  const price = pair.priceUsd;
  const age = pair.pairCreatedAt ? formatAge(pair.pairCreatedAt) : null;
  const url = pair.url;
  const chain = pair.chainId;

  return (
    <div className="group relative bg-gradient-to-br from-[#0a1310] to-[#050908] border border-[#14F195]/15 hover:border-[#14F195]/45 rounded-xl p-3 transition-all overflow-hidden">
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition pointer-events-none"
        style={{ background: 'radial-gradient(circle at 20% 0%, rgba(20,241,149,0.08), transparent 60%)' }} />
      <div className="flex items-start gap-3 relative">
        <div className="w-10 h-10 rounded-full bg-[#14F195]/10 border border-[#14F195]/30 flex items-center justify-center flex-shrink-0 overflow-hidden">
          {pair.info?.imageUrl ? (
            <img src={pair.info.imageUrl} alt={base.symbol} className="w-full h-full object-cover" onError={e => e.target.style.display='none'} />
          ) : (
            <span className="text-[#14F195] text-xs font-bold">{(base.symbol || '?').slice(0,3)}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-white text-sm truncate">{base.name || base.symbol}</span>
            <span className="text-[10px] uppercase tracking-wider text-[#14F195]/80 bg-[#14F195]/10 px-1.5 py-0.5 rounded">{base.symbol}</span>
            <span className="text-[10px] uppercase text-white/40">{chain}</span>
          </div>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="text-white font-mono text-sm">{formatUSD(price)}</span>
            <span className={`text-xs font-semibold flex items-center gap-0.5 ${positive ? 'text-[#14F195]' : 'text-rose-400'}`}>
              {positive ? <TrendingUp size={11}/> : <TrendingDown size={11}/>}
              {positive ? '+' : ''}{Number(priceChange).toFixed(2)}%
            </span>
          </div>
          {!compact && (
            <div className="grid grid-cols-3 gap-2 mt-2.5 text-[10px]">
              <div><div className="text-white/40 flex items-center gap-1"><Droplet size={9}/>LIQ</div><div className="text-white/90 font-mono mt-0.5">{formatUSD(liquidity)}</div></div>
              <div><div className="text-white/40 flex items-center gap-1"><BarChart3 size={9}/>VOL</div><div className="text-white/90 font-mono mt-0.5">{formatUSD(volume)}</div></div>
              <div><div className="text-white/40 flex items-center gap-1"><Clock size={9}/>AGE</div><div className="text-white/90 font-mono mt-0.5">{age || '—'}</div></div>
            </div>
          )}
          {!compact && mcap && (
            <div className="mt-2 text-[10px] text-white/50">MCap <span className="text-white/80 font-mono">{formatUSD(mcap)}</span></div>
          )}
        </div>
        {url && (
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-[#14F195]/70 hover:text-[#14F195] p-1">
            <ExternalLink size={14}/>
          </a>
        )}
      </div>
    </div>
  );
}
