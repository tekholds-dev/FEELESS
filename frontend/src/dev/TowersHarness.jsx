import { CardRoom } from '../components/CardRoom';
import { StrikeGame } from '../components/StrikeGame';
import React from 'react';
import { TrenchList } from '../components/CityAvenue';
import { BrokerDesk } from '../components/BrokerDesk';
import { WalletProvider } from '../hooks/useWallet';
import { FeedPanel } from '../components/command/FeedX';
import { BrowserRouter } from 'react-router-dom';

// 🧪 DEV ONLY (`/dev/towers`, `?feed` = FEEd): 🗼 Trench Towers on the LIVE intake (the kernel's real price tape) + the 🔑 Crypto.com key door with its live
// what-your-key-does panel (`?cdc`). No wallet; nothing is signed or sent. Compiled out of production builds.
export default function TowersHarness() {
  const q = new URLSearchParams(window.location.search); const cdc = q.has('cdc');
  if (q.has('strike')) return <StrikeGame catalog={{ guns: { rifle: { name: 'FX-7 RIFLE', dmg: 24, rpm: 600, mag: 30, reload: 2.1, range: 120, spread: 0.012, recoil: 0.35, speed: 1, pellets: 1 } }, parts: {}, default: { gun: 'rifle' } }}
    loadout={{ gun: 'rifle', barrel: 'long', optic: 'dot', mag: 'ext', stock: 'heavy', skin: 'gold' }} mode="bots" diff={q.get('strike') || 'normal'} onExit={() => {}} />;   // 🎯 /dev/towers?strike
  if (q.has('cards')) return <main style={{ padding: 16, background: '#070504', minHeight: '100vh' }}><CardRoom onGo={() => {}} crew={[{ id: 1, k: 'hitter', lvl: 10, xp: 0 }, { id: 2, k: 'spy', lvl: 6, xp: 40, next: 90 },
    { id: 3, k: 'earner', lvl: 4, xp: 10, next: 50, hurt: 312 }, { id: 4, k: 'guard', lvl: 7, xp: 60, next: 110 }, { id: 5, k: 'hitter', lvl: 3, xp: 5, next: 40 }, { id: 6, k: 'guard', lvl: 1, xp: 2, next: 20 }]} /></main>;   // 🃏 /dev/towers?cards
  if (q.has('feed')) return <BrowserRouter><WalletProvider><main style={{ padding: 16, background: '#050607', minHeight: '100vh' }}><FeedPanel /></main></WalletProvider></BrowserRouter>;
  return <WalletProvider><main style={{ padding: 16, background: '#050607', minHeight: '100vh' }}>
    {cdc ? <div style={{ maxWidth: 480 }}><BrokerDesk venue="cdc" /></div> : <div className="av-room" style={{ '--pc': '#ff4d8d' }}><TrenchList /></div>}
  </main></WalletProvider>;
}
