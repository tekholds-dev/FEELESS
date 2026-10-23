import React from 'react';
import MetaLaunchSetup from '../components/terminal/MetaLaunchSetup';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/launch`): the launch wizard pre-filled (no wallet, nothing signs) — press Review to see the lit review page.
export default function LaunchHarness() {
  return <div className="terminal-app" style={{ minHeight: '100vh', padding: 16, background: '#030403', boxSizing: 'border-box' }}>
    <WalletProvider><MetaLaunchSetup initialValues={{ name: 'Degen Rocket', symbol: 'DRKT', imageUrl: `${window.location.origin}/favicon.svg`, description: 'A dev preview coin — nothing launches from this page.' }} /></WalletProvider>
  </div>;
}
