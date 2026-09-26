import React from 'react';

// Recognizable, simplified brand marks (not the trademarked logos) so the connect list
// shows something better than a bare letter without shipping third-party artwork.
const ICONS = {
  phantom: { bg: '#ab9ff2', path: 'M12 3c4.5 0 8 3.6 8 8v7a2 2 0 0 1-2 2h-1.5a2 2 0 0 1-2-2v-2a1 1 0 0 0-2 0v2a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2v-7c0-4.4 3.5-8 8-8h-3zm-2.5 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm5 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z' },
  trust: { bg: '#3375bb', path: 'M12 2l7 3v6c0 5-3 8.5-7 11-4-2.5-7-6-7-11V5z' },
  solflare: { bg: '#fda94c', path: 'M12 2l2.2 6.8H21l-5.6 4.1 2.2 6.9L12 15.6l-5.6 4.2 2.2-6.9L3 8.8h6.8z' },
  backpack: { bg: '#e33e3f', path: 'M8 3h8a2 2 0 0 1 2 2v1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h1V5a2 2 0 0 1 2-2zm1 3h6V5H9zm-1 6h8v2H8z' },
  coinbase: { bg: '#0052ff', path: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 6a4 4 0 1 1 0 8 4 4 0 0 1 0-8z' },
  metamask: { bg: '#f6851b', path: 'M12 3l5 3-1 5-4 2-4-2-1-5zm0 10l3.5 2L14 19h-4l-1.5-4z' },
  rabby: { bg: '#7084ff', path: 'M12 3a5 5 0 0 1 5 5v1.2a5 5 0 0 1-3 4.6V16a4 4 0 0 1-4 4 4 4 0 0 1-4-4v-2.2a5 5 0 0 1-3-4.6V8a5 5 0 0 1 5-5h4z' },
  evm: { bg: '#627eea', path: 'M12 2l7 10-7 4-7-4zM12 22l7-10-7 4-7-4z' },
};

export function WalletIcon({ brand, size = 22 }) {
  const spec = ICONS[brand] || ICONS.evm;
  return <span className="wallet-icon" style={{ width: size, height: size, background: spec.bg }}>
    <svg viewBox="0 0 24 24" width={size * 0.62} height={size * 0.62} fill="#fff" aria-hidden="true"><path d={spec.path} /></svg>
  </span>;
}
