import React, { useMemo } from 'react';

// Ambient glow + slow-rising embers in the coin's own color. Purely decorative: sits behind the
// content (pointer-events: none), respects reduced motion, and its intensity follows the coin's
// 24h move so a coin that's running literally burns brighter.
export function CoinAura({ color, change24h, count = 14 }) {
  const heat = Math.min(1, Math.abs(Number(change24h) || 0) / 40);
  const embers = useMemo(() => Array.from({ length: count }, (_, i) => ({
    id: i,
    left: `${(i * 61 + 17) % 100}%`,
    size: 2 + ((i * 7) % 4),
    delay: `${((i * 1.37) % 7).toFixed(2)}s`,
    dur: `${7 + ((i * 3) % 6)}s`,
    drift: `${((i % 5) - 2) * 14}px`,
  })), [count]);
  return <div className="coin-aura" aria-hidden="true" style={{ '--coin': color, '--heat': 0.35 + heat * 0.65 }}>
    <i className="coin-aura-glow" />
    <i className="coin-aura-edge" />
    {embers.map(e => <span key={e.id} className="coin-ember" style={{ left: e.left, width: e.size, height: e.size, animationDelay: e.delay, animationDuration: e.dur, '--drift': e.drift }} />)}
  </div>;
}
