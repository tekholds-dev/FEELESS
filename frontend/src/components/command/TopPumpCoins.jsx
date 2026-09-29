import React from 'react';
import { Flame } from 'lucide-react';
import { useMarket } from '../../hooks/useMarket';
import { TokenAvatar, Change } from '../terminal/MarketPrimitives';
import { LiveMarketCap } from '../terminal/LiveCells';
import { BoltSignal } from '../terminal/BoltSignal';
import { formatUSD } from '../../lib/dexscreener';

// Trade page, left rail: the top 10 Pump.fun coins from the ranked launchpad board, with live market cap
// (price stream) and a 15s board refresh. Picking one loads it into the swap as the coin you receive.
export const pickForSwap = pair => window.dispatchEvent(new CustomEvent('feeless:swap-set-output', { detail: {
  mint: pair.baseToken?.address, symbol: pair.baseToken?.symbol, name: pair.baseToken?.name, icon: pair.info?.imageUrl,
} }));

export function TopPumpCoins() {
  const { data, loading } = useMarket('/feed?kind=trending&chain=solana&page=1&scope=pump', 15000);
  const coins = (data?.pairs || []).filter(p => p.chainId === 'solana' && p.baseToken?.address).slice(0, 10);
  return <aside className="top-pump" data-testid="top-pump-coins">
    <header><span><Flame size={14} />Top 10 on Pump</span><small><i className="live-dot" />LIVE</small></header>
    {loading && !coins.length && <p className="top-pump-empty">Loading the board…</p>}
    <ol>{coins.map((p, i) => <li key={p.pairAddress}>
      <button type="button" onClick={() => pickForSwap(p)} data-testid={`top-pump-${p.baseToken.address}`} title={`Swap into ${p.baseToken.symbol}`}>
        <em>{i + 1}</em><TokenAvatar pair={p} size={30} />
        <span className="tp-name"><b>{p.baseToken.symbol}<BoltSignal pair={p} size={11} /></b><small>MC <LiveMarketCap pair={p} /></small></span>
        <span className="tp-moves"><Change value={p.priceChange?.m5} /><small>1h {Number.isFinite(Number(p.priceChange?.h1)) ? `${Number(p.priceChange.h1) >= 0 ? '+' : ''}${Number(p.priceChange.h1).toFixed(0)}%` : '—'} · {formatUSD(p.volume?.h1)}</small></span>
      </button>
    </li>)}</ol>
    {!loading && !coins.length && <p className="top-pump-empty">No Pump coins are passing the quality gates right now.</p>}
  </aside>;
}
