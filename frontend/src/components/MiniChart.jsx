import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLivePrices } from '../lib/livePrices';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { openWarRoom } from './WarRoomHost';
import '../styles/miniChart.css';

import { tiny } from '../lib/num';
const MiniChartBody = React.lazy(() => import('./MiniChartBody'));   // the SAME chart + your lines, loaded only when a mini chart is open
const KEY = 'feeless.miniChart';
const TFS = ['1m', '5m', '15m'];
const read = () => { try { const v = JSON.parse(window.localStorage.getItem(KEY) || 'null'); return v?.pairAddress ? v : null; } catch { return null; } };
const write = v => { try { if (v) window.localStorage.setItem(KEY, JSON.stringify(v)); else window.localStorage.removeItem(KEY); } catch { /* private window: lasts for this visit */ } };
const mcf = n => { const v = Number(n); if (!(v > 0)) return ''; return v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(0)}`; };
const px = n => { const v = Number(n); if (!(v > 0)) return '—'; return v >= 1 ? `$${v.toFixed(2)}` : `$${tiny(v, 4)}`; };

// 📌 MINI CHART: openMiniChart(pair) from any chart → the war room / drawer closes and the coin's chart stays in a small floating
// window on EVERY page (one host, mounted once in the terminal shell; the coin + the window's place are remembered).
export const openMiniChart = pair => { if (!pair?.pairAddress) return;
  const coin = { chainId: pair.chainId || 'solana', pairAddress: pair.pairAddress, mint: pair.baseToken?.address || pair.mint || '', symbol: pair.baseToken?.symbol || pair.symbol || '', logo: pair.info?.imageUrl || pair.logo || '',
    fuse: pair.fuse?.entry > 0 ? pair.fuse : null };   /* a Fuse card's levels travel with the chart */
  window.dispatchEvent(new CustomEvent('feeless:mini-chart', { detail: coin })); };

export function MiniChartHost() {
  const [coin, setCoin] = useState(read);
  const [tf, setTf] = useState('5m');
  const [metric, setMetric] = useState('marketCap');   // MC first, like the war room; tap to see price
  const [pos, setPos] = useState(() => read()?.pos || null);   // {x, y} from the left / top once dragged; null = docked bottom-left
  const drag = useRef(null);
  useEffect(() => { const on = e => { setCoin(c => ({ ...e.detail, pos: c?.pos || null })); }; window.addEventListener('feeless:mini-chart', on); return () => window.removeEventListener('feeless:mini-chart', on); }, []);
  useEffect(() => { write(coin ? { ...coin, pos } : null); }, [coin, pos]);
  const live = useLivePrices(coin?.pairAddress ? [coin.pairAddress] : []).get(coin?.pairAddress);
  if (!coin) return null;
  const pair = { chainId: coin.chainId, pairAddress: coin.pairAddress, baseToken: { address: coin.mint, symbol: coin.symbol }, info: { imageUrl: coin.logo }, priceUsd: live?.price ?? null, marketCap: live?.mc || null };
  const mc = Number(live?.mc) || 0; const asMc = metric === 'marketCap' && mc > 0;
  const m5 = Number(live?.m5);
  const down = e => { if (e.target.closest('button, a')) return; const r = e.currentTarget.parentElement.getBoundingClientRect(); drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { if (!drag.current) return; setPos({ x: Math.max(4, Math.min(window.innerWidth - 120, e.clientX - drag.current.dx)), y: Math.max(4, Math.min(window.innerHeight - 60, e.clientY - drag.current.dy)) }); };
  const up = () => { drag.current = null; };
  return createPortal(<aside className="mch" style={pos ? { left: pos.x, top: pos.y, bottom: 'auto' } : undefined} data-testid="mini-chart" aria-label={`Mini chart $${coin.symbol}`}>
    <i className="mch-edge" aria-hidden />
    <header className="mch-head" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} data-tip="Drag to move">
      <TokenAvatar pair={pair} size={22} /><b>${coin.symbol || `${(coin.mint || '').slice(0, 4)}…`}</b>
      <em className="m-num" key={asMc ? mcf(mc) : px(live?.price)} data-tip={asMc ? `Market cap · price ${px(live?.price)}` : 'Price'}>{asMc ? `${mcf(mc)} MC` : px(live?.price)}</em>{Number.isFinite(m5) && <u className={m5 >= 0 ? 'm-pos' : 'm-neg'}>{m5 >= 0 ? '+' : ''}{m5.toFixed(1)}%</u>}
      <span className="mch-acts">
        {TFS.map(t => <button key={t} type="button" className={tf === t ? 'active' : ''} onClick={() => setTf(t)} aria-pressed={tf === t} data-testid={`mch-tf-${t}`}>{t}</button>)}
        {mc > 0 && <button type="button" onClick={() => setMetric(asMc ? 'price' : 'marketCap')} data-testid="mch-metric" data-tip={asMc ? 'Showing market cap — tap for price' : 'Showing price — tap for market cap'} aria-label="Switch market cap / price">{asMc ? 'MC' : '$'}</button>}
        <button type="button" onClick={() => { openWarRoom(pair); }} data-testid="mch-war" data-tip="Open the full war room (the mini chart stays)" aria-label="Open war room">⚔</button>
        <button type="button" onClick={() => setCoin(null)} data-testid="mch-close" aria-label="Close mini chart">×</button></span>
    </header>
    <div className="mch-body"><React.Suspense fallback={<p className="m-dim mch-wait">Loading chart…</p>}><MiniChartBody pair={pair} tf={tf} fuse={coin.fuse || null} metric={metric} /></React.Suspense></div>
  </aside>, document.body);
}
