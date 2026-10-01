import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useCoinMood } from '../lib/coinMood';

// Animated chat backgrounds, chosen per room in the chat ⚙ panel (saved as themes[room], so a coin's chat keeps its
// look when you come back). Free: Live (follows the coin's mood), FEE glow, FEE rain, Plain. $FEE holders ≥ $5 unlock
// 4 more; ≥ $100 unlock 5 more. Every theme carries the FEE mark. Transform/opacity only; off under fx-lite.
export const CHAT_THEMES = [
  ['live', 'Live mood', 0], ['fee', 'FEE glow', 0], ['feerain', 'FEE rain', 0], ['off', 'Plain', 0],
  ['aurora', 'Aurora', 5], ['grid', 'Neon grid', 5], ['stars', 'Starfield', 5], ['pulse', 'Heartbeat', 5],
  ['matrix', 'Matrix', 100], ['lava', 'Lava', 100], ['warp', 'Warp', 100], ['vortex', 'Vortex', 100], ['gold', 'Gold rush', 100],
];
const NEED = Object.fromEntries(CHAT_THEMES.map(([id, , usd]) => [id, usd]));
export const canUse = (id, feeUsd) => (Number(feeUsd) || 0) >= (NEED[id] ?? Infinity);
// A saved theme you no longer qualify for falls back to Live (nothing breaks, nothing is lost).
export const chatTheme = (prefs, room, feeUsd = Infinity) => { const t = (prefs?.themes || {})[room] || 'live'; return canUse(t, feeUsd) ? t : 'live'; };

const tiers = new Map();
export function useFeeUsd(address) {
  const [usd, setUsd] = useState(0);
  useEffect(() => {
    if (!address) { setUsd(0); return undefined; }
    let alive = true; const hit = tiers.get(address);
    const p = hit && Date.now() - hit.at < 300000 ? hit.p : fetch(apiUrl(`/api/reputation/perks/${address}`)).then(r => (r.ok ? r.json() : null)).then(d => Number(d?.feeUsd) || 0).catch(() => 0);
    if (!hit || hit.p !== p) tiers.set(address, { at: Date.now(), p });
    p.then(v => alive && setUsd(v));
    return () => { alive = false; };
  }, [address]);
  return usd;
}

const RAIN = Array.from({ length: 7 }, (_, i) => i);
export function ChatFx({ theme, room }) {
  const mood = useCoinMood(theme === 'live' ? room : null);
  if (theme === 'off') return null;
  return <div className={`chat-fx fx-${theme}${theme === 'live' ? ` mood-${mood}` : ''}`} aria-hidden="true" data-testid="chat-fx" data-mood={theme === 'live' ? mood : undefined}>
    <i className="chat-fx-a" /><i className="chat-fx-b" />
    {theme === 'feerain' && RAIN.map(i => <img key={i} className="chat-fx-drop" style={{ left: `${8 + i * 13}%`, animationDelay: `${i * 1.3}s` }} src="/assets/feeless-logo.png" alt="" />)}
    <img className="chat-fx-logo" src="/assets/feeless-logo.png" alt="" />
  </div>;
}
