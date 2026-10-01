import { useCoinEdge } from './coinEdge';

// Pump Pulse: 5m flow for a coin — read from the shared coin edge poller (lib/coinEdge.js), no poller of its own.
export function usePumpPulse(mint) {
  return useCoinEdge(mint)?.pulse || null;
}

export const pulseSummary = s => {
  if (!s) return '';
  const change = Number.isFinite(s.m5Change) ? `${s.m5Change >= 0 ? '+' : ''}${s.m5Change.toFixed(1)}%` : '—';
  return `${change} · ${s.buys + s.sells} trades (${s.buyShare}% buys) · $${Math.round(s.volumeM5).toLocaleString()} vol`;
};
