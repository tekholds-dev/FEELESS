import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, ArrowUpRight, Radio, BarChart3, ShieldCheck, Star } from 'lucide-react';
import { useWorkspace } from '../hooks/useWorkspace';
import EcosystemChat from './EcosystemChat';
import { PriceChart } from './terminal/PriceChart';
import { LaunchForensics } from './terminal/LaunchForensics';
import { ReputationBadge } from './terminal/ReputationBadge';
import { formatUSD, formatPct } from '../lib/dexscreener';
import { OrderFlow } from './terminal/OrderFlow';
import { AnimatedNumber } from './terminal/AnimatedNumber';
import { fetchLivePrice, formatLivePrice } from '../lib/livePrice';

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'];
const CHAT_ROOMS = [['bulls', 'Bulls'], ['trenches', 'Trenches'], ['bears', 'Bears']];

// War room for a single $10M+ token opened from the globe: live chat, live chart, and edge data.
export default function CoinWorld({ token, onClose }) {
  const [pair, setPair] = useState(null);
  const { has, toggle } = useWorkspace() || {};
  const [error, setError] = useState('');
  const [interval, setIntervalValue] = useState('1m');
  const [metric, setMetric] = useState('price');
  const [chatRoom, setChatRoom] = useState('bulls');
  const [updatedAt, setUpdatedAt] = useState(null);
  const [live, setLive] = useState(null);
  const [, forceTick] = useState(0);
  useEffect(() => { const t = setInterval(() => forceTick(x => x + 1), 1000); return () => clearInterval(t); }, []);
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [onClose]);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch(`https://api.dexscreener.com/latest/dex/pairs/${token.chain}/${token.pairAddress}`);
        const body = await res.json();
        const p = (body?.pairs || [])[0] || body?.pair;
        if (alive) { if (p) { setPair(p); setError(''); setUpdatedAt(Date.now()); } else setError('DexScreener has no live market for this pool right now.'); }
      } catch { if (alive) setError('Live market data unavailable — retrying.'); }
    };
    load();
    const t = setInterval(() => { if (!document.hidden) load(); }, 3000);
    return () => { alive = false; clearInterval(t); };
  }, [token.chain, token.pairAddress]);

  const symbol = token.symbol || pair?.baseToken?.symbol || '…';
  useEffect(() => {
    if (!pair) return undefined;
    let alive = true;
    const tick = async () => { if (document.hidden) return; const r = await fetchLivePrice(pair); if (alive && r) { setLive(r); setUpdatedAt(Date.now()); } };
    tick();
    const t = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(t); };
  }, [pair?.chainId, pair?.baseToken?.address, pair?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  const livePrice = live?.usd ?? Number(pair?.priceUsd);
  const supplyRatio = pair?.priceUsd && (pair?.marketCap || pair?.fdv) ? (pair.marketCap || pair.fdv) / Number(pair.priceUsd) : null;
  const liveMc = supplyRatio && livePrice ? livePrice * supplyRatio : (pair?.marketCap || pair?.fdv || token.marketCap);
  const room = `coin-${token.chain}-${(pair?.baseToken?.address || token.address || token.pairAddress).slice(0, 44)}`;
  // 24h % = live price against DexScreener's own 24h-ago baseline, so it moves live but stays
  // consistent with every other number on the site.
  const dexCh = Number(pair?.priceChange?.h24 ?? token.change24h);
  const base24 = Number(pair?.priceUsd) > 0 && Number.isFinite(dexCh) ? Number(pair.priceUsd) / (1 + dexCh / 100) : null;
  const change = base24 && live?.usd ? (live.usd / base24 - 1) * 100 : dexCh;
  const stats = [
    ['PRICE', livePrice, '', formatLivePrice],
    ['24H', change, Number.isFinite(change) ? (change >= 0 ? 'positive' : 'negative') : '', formatPct],
    [token.mcKind === 'FDV' && !pair?.marketCap ? 'FDV' : 'MARKET CAP', liveMc, '', formatUSD],
    ['LIQUIDITY', pair?.liquidity?.usd ?? token.liquidityUsd, '', formatUSD],
    ['VOL 24H', pair?.volume?.h24 ?? token.volume24h, '', formatUSD],
  ];
  return <div className="eco-world coin-world" role="dialog" aria-modal="true" aria-label={`${symbol} war room`} data-testid="coin-world">
    <div className="eco-world-scrim" onClick={onClose} aria-hidden="true" />
    <div className="eco-world-inner eco-layout-balanced">
      <header className="eco-world-head">
        <div className="eco-world-id">
          <span className="coin-world-avatar">{(token.imageUrl || pair?.info?.imageUrl) ? <img src={token.imageUrl || pair?.info?.imageUrl} alt="" /> : symbol.slice(0, 2)}</span>
          <div><small>YOU'RE INSIDE · {token.chain.toUpperCase()}</small><h2>{symbol} WAR ROOM</h2></div>
        </div>
        <div className="eco-world-head-actions">
          {pair && toggle && <button type="button" className={`coin-star ${has?.(pair) ? 'is-starred' : ''}`} onClick={() => toggle(pair)} title={has?.(pair) ? 'Remove from watchlist' : 'Star — keep tracking with live alerts'} data-testid="coin-world-star"><Star size={16} fill={has?.(pair) ? 'currentColor' : 'none'} />{has?.(pair) ? 'Starred' : 'Star'}</button>}
          <Link className="eco-enter-terminal" target="_blank" rel="noopener noreferrer" to={`/terminal/trade?chain=${token.chain}&pair=${token.pairAddress}`}>Trade {symbol} in terminal<ArrowUpRight size={14} /></Link>
          <button className="eco-world-close" title="Close" onClick={onClose}><X size={18} /></button>
        </div>
      </header>
      <div className="eco-world-grid">
        <div className="eco-chat-col"><div className="eco-chat-label"><Radio size={13} /> LIVE CHAT · ${symbol}</div>
          <div className="coin-chat-rooms" role="tablist" aria-label="Chat rooms">{CHAT_ROOMS.map(([id, label]) => <button type="button" role="tab" aria-selected={chatRoom === id} key={id} className={`room-${id} ${id === 'trenches' ? 'trenches-font' : ''} ${chatRoom === id ? 'active' : ''}`} onClick={() => setChatRoom(id)}>{label}</button>)}</div>
          <EcosystemChat key={`${room}-${chatRoom}`} ecosystem={{ id: `${room}-${chatRoom}`, name: `${symbol} · ${CHAT_ROOMS.find(r => r[0] === chatRoom)[1]}` }} /></div>
        <div className="eco-right-col custom-scroll">
          <div className="activity-pulse coin-world-stats">{stats.map(([label, value, cls, fmt]) => <div className="pulse-pill" key={label}><small><i />{label}</small><strong className={cls || ''}><AnimatedNumber value={value} format={fmt} /></strong></div>)}</div>
          <section className="coin-world-chart">
            <div className="coin-world-chart-head"><span><BarChart3 size={14} /> LIVE CHART<em className="live-stamp"><i />{updatedAt ? `${live?.source || 'live'} · ${Math.max(0, Math.round((Date.now() - updatedAt) / 1000))}s ago` : 'connecting'}</em></span><div className="coin-world-metric" role="group" aria-label="Chart metric">{[['price', 'Price'], ['marketCap', 'MC']].map(([id, label]) => <button type="button" key={id} className={metric === id ? 'active' : ''} onClick={() => setMetric(id)}>{label}</button>)}</div><div>{INTERVALS.map(i => <button type="button" key={i} className={interval === i ? 'active' : ''} onClick={() => setIntervalValue(i)}>{i.toUpperCase()}</button>)}</div></div>
            {pair ? <PriceChart key={`${pair.pairAddress}-${interval}-${metric}`} pair={pair} interval={interval} metric={metric} showVolume /> : <div className="chart-message"><span className="loader" />{error || 'Loading live market…'}</div>}
          </section>
          <OrderFlow pair={pair} />
          <div className="eco-section-label"><ShieldCheck size={13} /> THE EDGE · CREATOR & LAUNCH FORENSICS</div>
          {pair && <div className="coin-world-rep"><span>Creator trust</span><ReputationBadge pair={pair} /></div>}
          {pair && <LaunchForensics pair={pair} />}
        </div>
      </div>
    </div>
  </div>;
}
