import React, { useState } from 'react';
import { X, Wallet } from 'lucide-react';

const WALLETS = [
  { id: 'phantom', name: 'Phantom', chain: 'Solana', color: '#AB9FF2', icon: 'https://phantom.app/img/logo.png' },
  { id: 'solflare', name: 'Solflare', chain: 'Solana', color: '#FE9D2A', icon: 'https://solflare.com/logo.svg' },
  { id: 'metamask', name: 'MetaMask', chain: 'EVM', color: '#F6851B', icon: 'https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg' },
  { id: 'walletconnect', name: 'WalletConnect', chain: 'Multi-chain', color: '#3B99FC', icon: '' },
  { id: 'coinbase', name: 'Coinbase Wallet', chain: 'EVM', color: '#0052FF', icon: '' },
  { id: 'backpack', name: 'Backpack', chain: 'Solana + EVM', color: '#E33E3F', icon: '' },
];

export default function WalletModal({ open, onClose, onConnect }) {
  const [connecting, setConnecting] = useState(null);
  if (!open) return null;

  const handle = (w) => {
    setConnecting(w.id);
    setTimeout(() => {
      onConnect && onConnect(w);
      setConnecting(null);
      onClose();
    }, 900);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      <div onClick={e => e.stopPropagation()}
        className="relative w-full max-w-md bg-[#050908] border border-[#14F195]/25 rounded-2xl shadow-[0_0_60px_-15px_rgba(20,241,149,0.35)] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#14F195]/10">
          <div className="flex items-center gap-2">
            <Wallet size={18} className="text-[#14F195]"/>
            <div className="text-white font-bold">Connect Wallet</div>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X size={18}/></button>
        </div>
        <div className="p-4 space-y-2">
          {WALLETS.map(w => (
            <button key={w.id} onClick={() => handle(w)} disabled={!!connecting}
              className="w-full flex items-center gap-3 p-3 bg-gradient-to-r from-[#0a1310] to-[#050908] hover:from-[#0f2018] hover:to-[#08120f] border border-[#14F195]/10 hover:border-[#14F195]/40 rounded-xl transition-all disabled:opacity-40">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${w.color}22`, border: `1px solid ${w.color}55` }}>
                {w.icon ? <img src={w.icon} alt={w.name} className="w-6 h-6 object-contain" onError={e=>e.target.style.display='none'}/> : <span className="text-xs font-bold" style={{color:w.color}}>{w.name[0]}</span>}
              </div>
              <div className="flex-1 text-left">
                <div className="text-white text-sm font-semibold">{w.name}</div>
                <div className="text-[10px] text-white/40">{w.chain}</div>
              </div>
              <div className="text-[11px] text-[#14F195]">{connecting === w.id ? 'Connecting…' : 'Connect'}</div>
            </button>
          ))}
        </div>
        <div className="px-5 py-3 border-t border-[#14F195]/10 text-[10px] text-white/40">
          Wallet-ready architecture. Signing not enabled in demo mode.
        </div>
      </div>
    </div>
  );
}
