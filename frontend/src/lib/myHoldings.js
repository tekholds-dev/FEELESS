import React, { useCallback, useSyncExternalStore } from 'react';
import { apiUrl } from './api';
import { useWallet } from '../hooks/useWallet';

// What the connected wallet holds (from its verified FEELESS trades): ONE shared poller for every coin card,
// never one per card. Refreshes every 30s while visible and right after any trade confirms.
const EMPTY = new Map();
const store = { address: null, held: EMPTY, listeners: new Set(), timer: null };

async function load() {
  const address = store.address;
  if (!address || document.hidden || typeof fetch !== 'function') return;
  try {
    const res = await fetch(apiUrl(`/api/reputation/pnl/${address}`));
    if (!res.ok) return;
    const body = await res.json();
    if (address !== store.address) return;
    store.held = new Map((body?.tokens || []).filter(t => Number(t.holding) > 0).map(t => [t.mint, t]));
    store.listeners.forEach(l => l());
  } catch { /* keep the last snapshot */ }
}
const onTrade = () => { setTimeout(load, 3000); };

function subscribe(address, listener) {
  if (address !== store.address) {
    store.address = address; store.held = EMPTY;
    clearInterval(store.timer); store.timer = null;
  }
  store.listeners.add(listener);
  if (address && !store.timer) {
    load(); store.timer = setInterval(load, 30000);
    window.addEventListener('feeless:trade-confirmed', onTrade);
  }
  return () => {
    store.listeners.delete(listener);
    if (!store.listeners.size) { clearInterval(store.timer); store.timer = null; window.removeEventListener('feeless:trade-confirmed', onTrade); }
  };
}

export function useHeld(mint) {
  const { wallet } = useWallet() || {};
  const address = wallet?.chain === 'solana' ? wallet.address : null;
  const sub = useCallback(l => subscribe(address, l), [address]);
  const held = useSyncExternalStore(sub, () => (address === store.address ? store.held : EMPTY));
  return mint ? held.get(mint) : undefined;
}

// "YOU HOLD · $12.40" on any coin card; the card itself lights up via `:has(.held-chip)` (see meta.css).
export function HeldChip({ pair }) {
  const h = useHeld(pair?.baseToken?.address);
  if (!h) return null;
  const usd = Number(h.holding) * Number(pair?.priceUsd || 0);
  return React.createElement('span', { className: 'm-chip ok held-chip', 'data-testid': 'held-chip', title: `You hold ${Number(h.holding).toLocaleString('en-US', { maximumFractionDigits: 2 })} ${pair.baseToken?.symbol || ''} (from your FEELESS trades)` },
    usd > 0 ? `YOU HOLD · $${usd >= 1000 ? `${(usd / 1000).toFixed(1)}K` : usd.toFixed(2)}` : 'YOU HOLD');
}
