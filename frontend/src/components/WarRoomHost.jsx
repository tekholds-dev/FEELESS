import React, { Suspense, useEffect, useState } from 'react';
import { ECOSYSTEMS } from '../lib/ecosystems';

const EcosystemWorld = React.lazy(() => import('./EcosystemWorld'));

// Open any coin's war room from anywhere in the terminal: openWarRoom(pair). One host, loaded on first use.
export const openWarRoom = pair => window.dispatchEvent(new CustomEvent('feeless:war-room', { detail: pair }));

export function WarRoomHost() {
  const [pair, setPair] = useState(null);
  useEffect(() => {
    const open = e => e.detail?.pairAddress && setPair(e.detail);
    window.addEventListener('feeless:war-room', open);
    return () => window.removeEventListener('feeless:war-room', open);
  }, []);
  if (!pair) return null;
  const eco = ECOSYSTEMS.find(e => e.chainId === pair.chainId) || ECOSYSTEMS[0];
  return <Suspense fallback={null}><EcosystemWorld ecosystem={eco} initialPair={{ chainId: pair.chainId, pairAddress: pair.pairAddress, fuse: pair.fuse || null }} onClose={() => setPair(null)} /></Suspense>;
}
