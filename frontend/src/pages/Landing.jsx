import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Menu, Bell, Search, Zap } from 'lucide-react';
import Globe3D from '../components/Globe3D';
import EcosystemChat from '../components/EcosystemChat';
import TopCoins from '../components/TopCoins';
import EcosystemPlatforms from '../components/EcosystemPlatforms';
import WalletModal from '../components/WalletModal';
import { FeelessMark, FeelessWordmark } from '../components/FeelessLogo';
import { ECOSYSTEMS, getEcosystem } from '../lib/ecosystems';

export default function Landing() {
  const [selected, setSelected] = useState(null);
  const [walletOpen, setWalletOpen] = useState(false);
  const [connectedWallet, setConnectedWallet] = useState(null);
  const nav = useNavigate();

  const ecosystem = getEcosystem(selected);
  const panelOpen = !!ecosystem;

  return (
    <div className="min-h-screen bg-[#03080a] text-white relative overflow-hidden">
      {/* backdrop grid */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.12]"
        style={{ backgroundImage: 'linear-gradient(rgba(20,241,149,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(20,241,149,0.5) 1px, transparent 1px)', backgroundSize: '80px 80px' }} />
      <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(20,241,149,0.14), transparent 60%)' }} />
      <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(20,241,149,0.10), transparent 60%)' }} />

      {/* Nav */}
      <header className="relative z-30 flex items-center justify-between px-6 lg:px-10 py-5">
        <FeelessWordmark size={22} />
        <div className="hidden md:flex items-center gap-2 bg-black/50 border border-[#14F195]/15 rounded-full px-4 py-2 w-[380px]">
          <Search size={14} className="text-white/40"/>
          <input placeholder="Search tokens, wallets, or contract…" className="flex-1 bg-transparent outline-none text-sm placeholder:text-white/30"/>
        </div>
        <div className="flex items-center gap-3">
          <button className="relative w-10 h-10 rounded-full bg-black/50 border border-[#14F195]/15 hover:border-[#14F195]/40 flex items-center justify-center transition-colors">
            <Bell size={15} className="text-white/70"/>
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#14F195] text-black text-[9px] font-bold rounded-full flex items-center justify-center">1</span>
          </button>
          <button onClick={() => setWalletOpen(true)}
            className="px-5 py-2.5 rounded-full bg-[#14F195] hover:bg-[#00FFA3] text-black font-bold text-sm shadow-[0_0_25px_-5px_rgba(20,241,149,0.6)] transition-all flex items-center gap-2">
            <Zap size={14}/>{connectedWallet ? `${connectedWallet.name} • Connected` : 'Connect Wallet'}
          </button>
          <button className="w-10 h-10 rounded-full bg-black/50 border border-[#14F195]/15 hover:border-[#14F195]/40 flex items-center justify-center"><Menu size={16} className="text-white/70"/></button>
        </div>
      </header>

      {/* ticker strip */}
      <div className="relative z-20 mx-6 lg:mx-10 mb-4 flex items-center gap-6 flex-wrap text-xs bg-black/40 border border-[#14F195]/10 rounded-full px-5 py-2.5">
        {[
          ['SOL','$142.37','+2.4%'],['24h Volume','$2.14B',''],['New Launches','1,247',''],
          ['Trending','87',''],['Market Cap','$58.3B',''],['Liquidity','$4.1B','']
        ].map(([k,v,c],i) => (
          <div key={i} className="flex items-center gap-2"><span className="text-white/40">{k}</span><span className="text-white font-mono">{v}</span>{c && <span className="text-[#14F195]">{c}</span>}</div>
        ))}
        <div className="ml-auto text-[#14F195] tracking-[0.28em] font-semibold">TRADE . DISCOVER . LAUNCH . EARN</div>
      </div>

      {/* Main */}
      <main className="relative z-10 flex px-6 lg:px-10 pb-10 gap-6">
        {/* Left: hero + globe */}
        <section className={`flex-1 transition-all duration-500 ${panelOpen ? 'lg:max-w-[55%]' : ''}`}>
          <div className="flex flex-col lg:flex-row items-center gap-6">
            <div className="flex-1 max-w-xl">
              <div className="text-[11px] tracking-[0.32em] text-[#14F195]">THE SOLANA-FIRST TERMINAL</div>
              <h1 className="mt-3 text-5xl lg:text-6xl font-black leading-[0.95] tracking-tight">
                SAME<br/>TRANSACTIONS.<br/>
                <span className="text-[#14F195] drop-shadow-[0_0_25px_rgba(20,241,149,0.55)]">ZERO FEES.</span><br/>
                MORE FOR YOU.
              </h1>
              <p className="mt-5 text-white/60 text-sm max-w-md leading-relaxed">
                Trade. <span className="text-[#14F195]">Discover</span>. Launch. <span className="text-[#14F195]">Earn</span>. Explore every major ecosystem from one premium terminal.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <button onClick={() => setWalletOpen(true)}
                  className="px-6 py-3 rounded-full bg-[#14F195] hover:bg-[#00FFA3] text-black font-bold text-sm shadow-[0_0_35px_-8px_rgba(20,241,149,0.7)] transition-all">
                  Connect Wallet
                </button>
                <button onClick={() => nav('/terminal')}
                  className="group px-6 py-3 rounded-full bg-black/50 border border-[#14F195]/40 hover:border-[#14F195] text-white font-bold text-sm flex items-center gap-2 transition-all">
                  Enter FEELESS Terminal <ArrowRight size={15} className="group-hover:translate-x-1 transition-transform"/>
                </button>
              </div>
              <div className="mt-8 flex flex-wrap gap-2">
                {ECOSYSTEMS.filter(e => !e.isFeeless).map(e => (
                  <button key={e.id} onClick={() => setSelected(e.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                      selected === e.id ? 'bg-white/10 text-white border-white/40' : 'text-white/60 border-white/10 hover:border-white/30 hover:text-white'
                    }`}
                    style={selected === e.id ? { borderColor: e.color, color: e.color, background: `${e.color}12` } : {}}>
                    {e.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-shrink-0">
              <Globe3D onSelect={setSelected} selectedId={selected} size={panelOpen ? 460 : 560} />
              <div className="text-center mt-2 text-[11px] text-white/40">Click a node → open ecosystem panel</div>
            </div>
          </div>
        </section>

        {/* Right Degen Panel */}
        {panelOpen && (
          <aside className="w-[520px] xl:w-[560px] flex-shrink-0 animate-[slideIn_.4s_ease-out]">
            <div className="sticky top-4 flex flex-col gap-4">
              <div className="rounded-2xl bg-[#050908]/95 border border-[#14F195]/20 shadow-[0_0_60px_-20px_rgba(20,241,149,0.4)] overflow-hidden backdrop-blur-xl">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#14F195]/10" style={{ background: `linear-gradient(90deg, ${ecosystem.color}14, transparent)` }}>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center border" style={{ background: `${ecosystem.color}22`, borderColor: `${ecosystem.color}55` }}>
                      {ecosystem.isFeeless ? <FeelessMark size={22} glow={false}/> : <span className="text-sm font-bold" style={{color: ecosystem.color}}>{ecosystem.symbol}</span>}
                    </div>
                    <div>
                      <div className="text-white font-bold">{ecosystem.name}</div>
                      <div className="text-[10px] uppercase tracking-[0.2em] text-white/40">Degen Panel</div>
                    </div>
                  </div>
                  <button onClick={() => setSelected(null)} className="text-white/40 hover:text-white text-xl leading-none">×</button>
                </div>
                <div className="h-[420px]"><EcosystemChat ecosystem={ecosystem} /></div>
              </div>

              <div className="rounded-2xl bg-[#050908]/95 border border-[#14F195]/20 overflow-hidden backdrop-blur-xl">
                <div className="h-[380px]"><TopCoins ecosystem={ecosystem} /></div>
              </div>

              <div className="rounded-2xl bg-[#050908]/95 border border-[#14F195]/20 overflow-hidden backdrop-blur-xl">
                <EcosystemPlatforms ecosystem={ecosystem} />
              </div>
            </div>
          </aside>
        )}
      </main>

      <WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} onConnect={setConnectedWallet} />
    </div>
  );
}
