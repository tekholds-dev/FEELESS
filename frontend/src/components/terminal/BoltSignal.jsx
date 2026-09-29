import React from 'react';
import { Zap } from 'lucide-react';
import { useReputation } from '../../lib/reputation';
import { usePumpPulse, pulseSummary } from '../../lib/pumpPulse';

const BAD_CREATOR = new Set(['flagged', 'risky']);

// Pump Pulse: the pink bolt marks a coin with real, rising 5-minute flow (server rule in market.py
// pulse_stats). Coins from flagged or risky creators never get a bolt.
export function usePulse(pair) {
  const mint = pair?.chainId === 'solana' ? pair?.baseToken?.address : null;
  const stats = usePumpPulse(mint);
  const rep = useReputation(pair);
  if (!stats?.pulse || BAD_CREATOR.has(rep?.badge)) return null;
  return stats;
}

export function BoltSignal({ pair, size = 13 }) {
  const pulse = usePulse(pair);
  if (!pulse) return null;
  return <i className={`pink-bolt pulse-${pulse.level}`} title={`Pump Pulse · 5m ${pulseSummary(pulse)}`} data-testid="bolt-signal"><Zap size={size} /></i>;
}

// Coin chat banner: shown while the coin is pulsing, refreshed with the rest of the pulse hub.
export function PumpPulseBanner({ pair }) {
  const pulse = usePulse(pair);
  if (!pulse) return null;
  const change = Number.isFinite(pulse.m5Change) ? `${pulse.m5Change >= 0 ? '+' : ''}${pulse.m5Change.toFixed(1)}%` : '—';
  return <div className={`pump-pulse-banner pulse-${pulse.level}`} role="status" data-testid="pump-pulse-banner">
    <Zap size={14} /><b>PUMP PULSE</b>
    <span><small>5m</small>{change}</span>
    <span><small>trades</small>{pulse.buys + pulse.sells}</span>
    <span><small>buys</small>{pulse.buyShare}%</span>
    <span><small>vol</small>${Math.round(pulse.volumeM5).toLocaleString()}</span>
  </div>;
}

export function BoltLegend() {
  return <span className="bolt-legend" title="Pump Pulse: 20+ trades, $5K+ volume and price up 2%+ in the last 5 minutes, with real two-sided flow (micro-buy bots excluded)."><Zap size={11} /> Bolt = Pump Pulse · hot 5m flow</span>;
}
