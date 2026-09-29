import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Polls the FEELESS Pump network (one shared PumpPortal connection on the server).
export function usePumpNetwork(path, intervalMs = 2000) {
  const [state, setState] = useState({ data: null, error: '' });
  useEffect(() => {
    setState({ data: null, error: '' });
    if (!path) return undefined;
    let alive = true;
    let timer;
    const controller = new AbortController();
    const load = async () => {
      try {
        const res = await fetch(apiUrl(path), { signal: controller.signal });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || 'Pump network unavailable.');
        if (alive) setState({ data: body, error: '' });
      } catch (err) {
        if (alive && err.name !== 'AbortError') setState(current => ({ ...current, error: err.message || 'Pump network unavailable.' }));
      } finally {
        if (alive) timer = setTimeout(load, intervalMs);
      }
    };
    load();
    return () => { alive = false; controller.abort(); clearTimeout(timer); };
  }, [path, intervalMs]);
  return state;
}

// A launch seen on the stream, shaped like a market pair so the chart/chat/trade flow can open it.
export const launchToPair = launch => ({
  chainId: 'solana', pairAddress: launch.curve || launch.mint, dexId: 'pump.fun', launchpadId: 'pump',
  url: `https://pump.fun/coin/${launch.mint}`, marketStage: 'new', pairCreatedAt: Math.round(launch.at),
  baseToken: { address: launch.mint, name: launch.name, symbol: launch.symbol },
  marketCap: launch.marketCapUsd ?? null,
});

export const ageLabel = (at, now = Date.now()) => {
  const s = Math.max(0, Math.round((now - at) / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
};

// Buy share of 5-minute flow. Prefers live PumpPortal SOL volume, falls back to DexScreener trade counts.
export function buyPressure(flow, pair) {
  const buySol = Number(flow?.buySol) || 0;
  const sellSol = Number(flow?.sellSol) || 0;
  if (buySol + sellSol > 0) return { pct: Math.round(buySol / (buySol + sellSol) * 100), basis: 'SOL volume · live' };
  const m5 = pair?.txns?.m5;
  const buys = Number(m5?.buys) || 0;
  const sells = Number(m5?.sells) || 0;
  if (buys + sells > 0) return { pct: Math.round(buys / (buys + sells) * 100), basis: 'trade count · DexScreener' };
  return null;
}

export const TRADE_STREAM_NOTE = {
  'no-key': 'Free mode · pressure from DexScreener trade counts.',
  'invalid-key': 'PumpPortal rejected the server API key. Live trade tape is off.',
  unfunded: 'PumpPortal wallet needs at least 0.02 SOL for live trades.',
  capped: 'Daily trade-data budget reached. Tape resumes tomorrow.',
  connecting: 'Connecting to the live trade tape…',
  reconnecting: 'Reconnecting to the live trade tape…',
};
