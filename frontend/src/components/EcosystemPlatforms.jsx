import React from 'react';
import { ExternalLink, Globe, BarChart3, Rocket, ArrowLeftRight, Layers } from 'lucide-react';

const TYPE_ICON = {
  dex: ArrowLeftRight,
  aggregator: Layers,
  launch: Rocket,
  explorer: Globe,
  analytics: BarChart3,
  perps: BarChart3,
  terminal: Rocket,
};

export default function EcosystemPlatforms({ ecosystem }) {
  if (!ecosystem) return null;
  const website = typeof ecosystem.website === 'string' ? ecosystem.website : '';
  const platforms = Array.isArray(ecosystem.platforms) ? ecosystem.platforms : [];
  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#14F195]/10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-white/40">Ecosystem Platforms</div>
          <div className="text-white font-bold">{ecosystem.name}</div>
        </div>
        {website ? <a data-testid={`ecosystem-official-${ecosystem.id}`} href={website} target={website.startsWith('/') ? '_self' : '_blank'} rel="noreferrer" className="text-[10px] text-[#14F195] hover:underline flex items-center gap-1">Website <ExternalLink size={10}/></a> : <span data-testid={`ecosystem-official-unavailable-${ecosystem.id}`} className="text-[10px] text-white/30">Website unavailable</span>}
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        {platforms.map((p, i) => {
          const Icon = TYPE_ICON[p.type] || Globe;
          const url = typeof p.url === 'string' ? p.url : '';
          if (!url) return <div data-testid={`ecosystem-platform-unavailable-${ecosystem.id}-${i}`} key={i} className="group relative bg-gradient-to-br from-[#0a1310] to-[#050908] border border-white/10 rounded-lg p-2.5 opacity-60">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-white/5 border border-white/10 flex items-center justify-center"><Icon size={13} className="text-white/50"/></div>
              <div className="flex-1 min-w-0"><div className="text-white/60 text-xs font-semibold truncate">{p.name}</div><div className="text-[9px] uppercase tracking-wider text-white/30">Unavailable</div></div>
            </div>
          </div>;
          return (
            <a data-testid={`ecosystem-platform-${ecosystem.id}-${i}`} key={i} href={url} target={url.startsWith('/') ? '_self' : '_blank'} rel="noreferrer"
              className="group relative bg-gradient-to-br from-[#0a1310] to-[#050908] border border-[#14F195]/15 hover:border-[#14F195]/50 rounded-lg p-2.5 transition-all">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-md bg-[#14F195]/10 border border-[#14F195]/25 flex items-center justify-center">
                  <Icon size={13} className="text-[#14F195]"/>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-xs font-semibold truncate">{p.name}</div>
                  <div className="text-[9px] uppercase tracking-wider text-white/40">{p.type}</div>
                </div>
                <ExternalLink size={11} className="text-white/30 group-hover:text-[#14F195] transition-colors"/>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
