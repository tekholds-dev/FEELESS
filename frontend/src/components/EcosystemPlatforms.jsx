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
  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#14F195]/10">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-white/40">Ecosystem Platforms</div>
          <div className="text-white font-bold">{ecosystem.name}</div>
        </div>
        <a href={ecosystem.website} target="_blank" rel="noreferrer" className="text-[10px] text-[#14F195] hover:underline flex items-center gap-1">Official <ExternalLink size={10}/></a>
      </div>
      <div className="grid grid-cols-2 gap-2 p-3">
        {ecosystem.platforms.map((p, i) => {
          const Icon = TYPE_ICON[p.type] || Globe;
          return (
            <a key={i} href={p.url} target={p.url.startsWith('/') ? '_self' : '_blank'} rel="noreferrer"
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
