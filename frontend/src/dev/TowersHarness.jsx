import React from 'react';
import { TrenchList } from '../components/CityAvenue';
import { BrokerDesk } from '../components/BrokerDesk';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/towers`): 🗼 Trench Towers on the LIVE intake (the kernel's real price tape) + the 🔑 Crypto.com key door with its live
// what-your-key-does panel (`?cdc`). No wallet; nothing is signed or sent. Compiled out of production builds.
export default function TowersHarness() {
  const cdc = new URLSearchParams(window.location.search).has('cdc');
  return <WalletProvider><main style={{ padding: 16, background: '#050607', minHeight: '100vh' }}>
    {cdc ? <div style={{ maxWidth: 480 }}><BrokerDesk venue="cdc" /></div> : <div className="av-room" style={{ '--pc': '#ff4d8d' }}><TrenchList /></div>}
  </main></WalletProvider>;
}
