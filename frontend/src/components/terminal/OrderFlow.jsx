import React from 'react';
import { Activity, Droplets, Gauge, Layers, Scale, Timer, Zap } from 'lucide-react';
import { formatUSD, formatPct, formatCompact } from '../../lib/dexscreener';
import { AnimatedNumber } from './AnimatedNumber';
import { useTradeStream } from '../../lib/tradeStream';
import { formatLivePrice } from '../../lib/livePrice';

const TX_EXPLORER = { solana: 'https://solscan.io/tx/', ethereum: 'https://etherscan.io/tx/', base: 'https://basescan.org/tx/', bsc: 'https://bscscan.com/tx/', arbitrum: 'https://arbiscan.io/tx/', avalanche: 'https://snowtrace.io/tx/', polygon: 'https://polygonscan.com/tx/', sui: 'https://suiscan.xyz/mainnet/tx/' };
const WINDOWS = [['m5', '5M'], ['h1', '1H'], ['h6', '6H'], ['h24', '24H']];
const n = v => (Number.isFinite(Number(v)) ? Number(v) : null);
const pct = v => (v == null ? '—' : formatPct(v));

function ageLabel(ms) {
  if (!ms) return '—';
  const h = (Date.now() - ms) / 3_600_000;
  return h < 1 ? `${Math.round(h * 60)}m` : h < 48 ? `${h.toFixed(1)}h` : `${Math.round(h / 24)}d`;
}

// Live order flow + market structure, derived only from the pair's real DexScreener snapshot.
export function OrderFlow({ pair }) {
  const { trades, fresh } = useTradeStream(pair);
  if (!pair) return null;
  const tx = pair.txns || {};
  const vol = pair.volume || {};
  const ch = pair.priceChange || {};
  const liq = n(pair.liquidity?.usd);
  const mc = n(pair.marketCap);
  const fdv = n(pair.fdv);
  const rows = WINDOWS.map(([k, label]) => {
    const b = (n(tx[k]?.buys) || 0) + fresh.buys; const s = (n(tx[k]?.sells) || 0) + fresh.sells;
    const v = n(vol[k]) != null ? n(vol[k]) + fresh.buyUsd + fresh.sellUsd : null;
    return { k, label, buys: b, sells: s, total: b + s, buyShare: b + s ? b / (b + s) : null, vol: v, change: n(ch[k]) };
  });
  const h24 = rows[3];
  const turnover = liq && h24.vol != null ? h24.vol / liq : null;
  const avgTrade = h24.total ? (h24.vol || 0) / h24.total : null;
  const depth = liq && mc ? (liq / mc) * 100 : null;
  const dilution = mc && fdv && fdv > mc ? ((fdv - mc) / fdv) * 100 : 0;
  const m5 = rows[0]; const h1 = rows[1];
  let read = 'Balanced flow — no strong edge either way.';
  if (m5.buyShare != null && h1.buyShare != null) {
    if (m5.buyShare >= 0.6 && (m5.change ?? 0) > 0) read = 'Buyers in control right now — short-term flow and price agree.';
    else if (m5.buyShare >= 0.6 && (m5.change ?? 0) <= 0) read = 'Many buys but price not moving — possible absorption by a seller.';
    else if (m5.buyShare <= 0.4 && (m5.change ?? 0) < 0) read = 'Sellers in control right now — short-term flow and price agree.';
    else if (m5.buyShare <= 0.4 && (m5.change ?? 0) >= 0) read = 'Sells hitting but price holding — dip is being absorbed.';
    else if (h1.buyShare >= 0.58) read = 'Steady accumulation over the last hour.';
    else if (h1.buyShare <= 0.42) read = 'Distribution over the last hour — more sellers than buyers.';
  }
  const depthLabel = depth == null ? '—' : depth >= 10 ? 'Deep' : depth >= 3 ? 'Healthy' : depth >= 1 ? 'Thin' : 'Very thin';
  return <section className="order-flow" data-testid="order-flow">
    <div className="order-flow-head"><span><Activity size={14} /> LIVE ORDER FLOW & MARKET STRUCTURE</span><small>DexScreener · updates every 3s</small></div>
    <p className="order-flow-read"><Zap size={13} />{read}</p>
    <div className="order-flow-windows">{rows.map(r => <div key={r.k} className="flow-window">
      <div className="flow-window-top"><b>{r.label}</b><span className={r.change == null ? '' : r.change >= 0 ? 'positive' : 'negative'}><AnimatedNumber value={r.change} format={v => pct(v)} /></span></div>
      <div className="flow-bar" title={`${r.buys} buys / ${r.sells} sells`}><i style={{ width: `${(r.buyShare ?? 0.5) * 100}%` }} /></div>
      <div className="flow-window-foot"><span className="positive"><AnimatedNumber value={r.buys} format={v => formatCompact(Math.round(v))} /> buys</span><span className="negative"><AnimatedNumber value={r.sells} format={v => formatCompact(Math.round(v))} /> sells</span></div>
      <small>{r.vol != null ? <><AnimatedNumber value={r.vol} format={formatUSD} /> vol</> : '—'}</small>
    </div>)}</div>
    <div className="order-flow-metrics">
      <div><Droplets size={13} /><small>LIQUIDITY DEPTH</small><b>{depth == null ? '—' : `${depth.toFixed(1)}% of MC`}</b><em>{depthLabel}</em></div>
      <div><Gauge size={13} /><small>24H TURNOVER</small><b>{turnover == null ? '—' : `${turnover.toFixed(2)}×`}</b><em>volume ÷ liquidity</em></div>
      <div><Scale size={13} /><small>AVG TRADE</small><b>{avgTrade == null ? '—' : formatUSD(avgTrade)}</b><em>{h24.total ? `${formatCompact(h24.total)} trades 24h` : '—'}</em></div>
      <div><Layers size={13} /><small>DILUTION GAP</small><b>{fdv && mc ? `${dilution.toFixed(1)}%` : '—'}</b><em>{dilution > 1 ? 'supply not yet circulating' : 'fully circulating'}</em></div>
      <div><Timer size={13} /><small>POOL AGE</small><b>{ageLabel(pair.pairCreatedAt)}</b><em>{pair.dexId || '—'}</em></div>
    </div>
    <div className="trade-tape">
      <div className="trade-tape-head"><span><i />LIVE TRADE TAPE</span><small>{trades.length ? `last trade ${Math.max(0, Math.round((Date.now() - Date.parse(trades[0].ts)) / 1000))}s ago · GeckoTerminal` : 'waiting for trades…'}</small></div>
      <div className="trade-tape-list">{trades.slice(0, 14).map(t => <a key={t.tx} className={`tape-row ${t.kind}`} href={TX_EXPLORER[pair.chainId] ? `${TX_EXPLORER[pair.chainId]}${t.tx}` : undefined} target="_blank" rel="noopener noreferrer">
        <b>{t.kind === 'buy' ? 'BUY' : 'SELL'}</b><span>{formatUSD(t.usd)}</span><span>{formatLivePrice(t.price)}</span><code>{(t.wallet || '').slice(0, 4)}…{(t.wallet || '').slice(-4)}</code><time>{new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
      </a>)}</div>
    </div>
  </section>;
}
