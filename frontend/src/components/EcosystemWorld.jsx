import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, ArrowUpRight, Rocket, Radio, Compass, Sparkles, Cat, Infinity as InfinityIcon } from 'lucide-react';
import { searchTokens } from '../lib/dexscreener';
import EcosystemChat from './EcosystemChat';
import NewStuffFeed from './NewStuffFeed';
// Same chart as the trenches: every tool, your P&L + entries, Quick trade, Dip/Rip, rug shield.
const TrenchChart = React.lazy(() => import('./terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
import { useMarket } from '../hooks/useMarket';
import { DegenWeather } from './terminal/DegenWeather';

const ROOM_LAYOUT_KEY = 'feeless-room-layout';
const ROOM_EXPANDED_KEY = 'feeless-room-expanded';
const readRoomLayout = () => {
  try {
    const saved = localStorage.getItem(ROOM_LAYOUT_KEY);
    return ['balanced', 'chat-first', 'feed-first', 'chart'].includes(saved) ? saved : 'balanced';
  } catch { return 'balanced'; }
};
const readRoomExpanded = () => {
  try { return localStorage.getItem(ROOM_EXPANDED_KEY) === 'true'; }
  catch { return false; }
};

// Blur-reveal immersive ecosystem "world": chat on the LEFT, blurred globe behind,
// live activity pulse + new-stuff feed + onboarding + minimal quick links on the RIGHT.
export default function EcosystemWorld({ ecosystem, pad, initialPair, onClose }) {
  const [layout, setLayout] = useState(readRoomLayout);
  const [expanded, setExpanded] = useState(readRoomExpanded);
  const [chartPair, setChartPair] = useState(null);
  // Opened from a globe coin: chart that exact pool in the war-room card.
  useEffect(() => {
    if (!initialPair) return;
    let alive = true;
    searchTokens(initialPair.pairAddress).then(ps => { const p = (ps || []).find(x => x.pairAddress === initialPair.pairAddress && x.chainId === initialPair.chainId); if (alive && p) { setChartPair(p); setLayout('chart'); } }).catch(() => {});
    return () => { alive = false; };
  }, [initialPair?.chainId, initialPair?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  // No coin picked yet: open the room on its top coin, so the chart and tools are there in every layout.
  const roomChain = ecosystem?.chainId || 'solana';
  const roomScope = ['pump', 'bonk', 'raydium'].includes(ecosystem?.id) ? `&scope=${ecosystem.id}` : '';
  const { data: roomTop } = useMarket(initialPair ? null : `/feed?kind=trending&chain=${roomChain}&page=1${roomScope}`, 60000);
  useEffect(() => {
    if (chartPair || initialPair) return;
    const top = (roomTop?.pairs || []).find(p => p.pairAddress && p.chainId === roomChain);
    if (top) setChartPair(top);
  }, [roomTop]); // eslint-disable-line react-hooks/exhaustive-deps
  const [chartBig, setChartBig] = useState(false);
  // Live pool data (price, mcap, volume) every 3s, same feed as the trench chart.
  const { data: chartLive } = useMarket(chartPair ? `/pair/${chartPair.chainId}/${chartPair.pairAddress}` : null, 3000);
  const livePool = chartLive?.pairs?.[0];
  const liveChartPair = chartPair && livePool?.pairAddress === chartPair.pairAddress ? { ...chartPair, ...livePool } : chartPair;
  // Floating chart opens centred and fully on screen (its CSS width is min(1100px, 86vw)).
  const centred = () => ({ x: Math.max(8, (window.innerWidth - Math.min(1100, window.innerWidth * 0.86)) / 2), y: Math.max(8, Math.min(80, (window.innerHeight - Math.min(640, window.innerHeight * 0.72)) / 2)) });
  const [winPos, setWinPos] = useState(centred);
  const drag = e => {
    if (!chartBig || e.target.closest('button,a')) return;
    const sx = e.clientX - winPos.x; const sy = e.clientY - winPos.y;
    const move = ev => setWinPos({ x: Math.min(window.innerWidth - 160, Math.max(0, ev.clientX - sx)), y: Math.min(window.innerHeight - 80, Math.max(0, ev.clientY - sy)) });
    const up = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  };
  useEffect(() => { const k = e => { if (e.key === 'Escape') setChartBig(false); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, []);
  useEffect(() => { try { localStorage.setItem(ROOM_LAYOUT_KEY, layout); } catch {} }, [layout]);
  useEffect(() => { try { localStorage.setItem(ROOM_EXPANDED_KEY, String(expanded)); } catch {} }, [expanded]);
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [onClose]);

  const room = `${ecosystem.id}-general`;
  const { data: community } = useMarket(`/api/intelligence/community?context=${ecosystem.id}`, 30000);
  const { data: online } = useMarket(`/api/chat/${room}/online`, 20000);
  const inRoom = online?.online ?? online?.count ?? online?.users?.length;
  const fresh = useMarket(`/feed?kind=new&chain=${ecosystem.chainId}`, 60000);
  const freshCount = fresh.data?.pairs?.length;

  const pulse = [
    ['IN THE ROOM', inRoom ?? '—', 'recent posters'],
    ['MESSAGES / 7D', community?.messages ?? '—', 'community activity'],
    ['FRESH TODAY', freshCount ?? '—', 'new indexed markets'],
    ['NETWORK', ecosystem.chainId.toUpperCase(), 'live link'],
  ];

  const links = [
    pad && ['Launchpad', pad.url, Rocket],
    ecosystem.dex && ['DEX', ecosystem.dex, Compass],
    ecosystem.explorer && ['Explorer', ecosystem.explorer, Radio],
  ].filter(Boolean);

  return <div className="eco-world" role="dialog" aria-modal="true" aria-label={`${ecosystem.name} network room`} data-testid="ecosystem-world" style={{ '--eco-accent': ecosystem.color }}>
    <div className="eco-world-scrim" onClick={onClose} aria-hidden="true" />
    <div className={`eco-world-inner eco-layout-${layout} ${expanded ? 'is-expanded' : ''}`}>
      <header className="eco-world-head">
        <div className="eco-world-id">
          <span className="eco-dot" style={{ background: ecosystem.color }} />
          <span className="eco-network-mark" aria-hidden="true">{ecosystem.symbol?.slice(0, 1) || ecosystem.name.slice(0, 1)}</span><div><small>YOU'RE INSIDE</small><h2 data-testid="eco-world-name">{ecosystem.name} {ecosystem.isLaunchpad ? 'WAR ROOM' : 'NETWORK'}</h2></div>
        </div>
        <div className="eco-world-head-actions">{(pad?.id === 'feeless-launch' || ecosystem.id === 'feeless-launch') && <a className="btn-primary eco-launch-btn" data-testid="eco-launch-btn" href="/terminal/launch?setup=feeless">🚀 Launch a coin</a>}
          <Link className="eco-enter-terminal" to="/terminal" data-testid="eco-world-enter-terminal">Enter {ecosystem.name} terminal<ArrowUpRight size={14} /></Link>
          <div className="eco-layout-controls" role="group" aria-label="Network room layout">
            <span>LAYOUT</span>
            {[['balanced', 'Balanced'], ['chart', 'Chart'], ['chat-first', 'Chat first'], ['feed-first', 'Feed first']].map(([id, label]) => <button type="button" key={id} className={layout === id ? 'active' : ''} aria-pressed={layout === id} data-testid={`eco-layout-${id}`} onClick={() => setLayout(id)}>{label}</button>)}
            <button type="button" className="eco-expand-toggle" data-testid="eco-layout-expand" aria-pressed={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? 'Exit expanded' : 'Expand window'}</button>
          </div>
          <button className="eco-world-close" title="Close" data-testid="eco-world-close" onClick={onClose}><X size={18} /></button>
        </div>
      </header>

      <div className="eco-world-grid">
        <div className="eco-chat-col" data-testid="eco-world-chat">
          <div className="eco-chat-label"><Radio size={13} /> LIVE COMMUNITY · #{room}</div>
          <EcosystemChat key={room} ecosystem={{ ...ecosystem, id: room, name: ecosystem.name }} />
        </div>

        <div className="eco-right-col custom-scroll">
          {chartPair && <div className={`eco-chart m-live ${chartBig ? 'is-big' : ''}`} data-testid="eco-room-chart" style={chartBig ? { left: winPos.x, top: winPos.y } : undefined}>
            <div className="eco-chart-head" onPointerDown={drag} title={chartBig ? 'Drag to move · resize from the corner' : undefined}><b>${chartPair.baseToken?.symbol}</b><span>{chartPair.baseToken?.name}</span><a href={`/terminal/chat?chain=${chartPair.chainId}&pair=${chartPair.pairAddress}&room=bulls`} target="_blank" rel="noreferrer">Profile ↗</a><button type="button" className="eco-chart-x" aria-label={chartBig ? 'Shrink chart' : 'Expand chart'} title={chartBig ? 'Shrink (Esc)' : 'Expand'} onClick={() => { if (!chartBig) setWinPos(centred()); setChartBig(b => !b); setTimeout(() => window.dispatchEvent(new Event('resize')), 60); }}>{chartBig ? '⤡' : '⤢'}</button><button type="button" className="eco-chart-x" aria-label="Close chart" onClick={() => { setChartPair(null); setChartBig(false); }}><X size={14} /></button></div>
            <div className="eco-chart-body"><React.Suspense fallback={<div className="chart-message"><span className="loader" />Loading chart…</div>}><TrenchChart key={chartPair.pairAddress} pair={liveChartPair} className="eco-trench"
              aside={<div className="eco-chart-chat" data-testid="eco-chart-chat"><EcosystemChat key={chartPair.pairAddress} compact room={`coin-${chartPair.chainId}-${chartPair.pairAddress}-trenches`} ecosystem={{ id: `coin-${chartPair.pairAddress}`, name: `$${chartPair.baseToken?.symbol || ''}` }} /></div>} /></React.Suspense></div>
          </div>}
          {(ecosystem?.chainId || 'solana') === 'solana' && <DegenWeather compact scope={['pump', 'bonk', 'raydium'].includes(ecosystem?.id) ? ecosystem.id : 'launchpads'} />}
          <div className="activity-pulse" data-testid="eco-activity-pulse">
            {pulse.map(([label, value, sub]) => <div className="pulse-pill" key={label}>
              <small><i />{label}</small>
              <strong data-testid={`eco-pulse-${label.split(' ')[0].toLowerCase()}`}>{value}</strong>
              <em>{sub}</em>
            </div>)}
          </div>

          <div className="eco-idea-card" data-testid="eco-idea-card">
            <span className="eco-idea-eyebrow"><Sparkles size={12} /> NEW HERE? THE IDEA</span>
            <p><b>FEELESS</b> is where every chain becomes one social floor. Fee-free $FEE ecosystem swaps, with any platform, provider and network costs shown before you sign — <span>no hidden fee claims.</span></p>
            <div className="eco-idea-row">
              <div><Cat size={15} /><b>FeeCat</b><small>The zero-fee router mascot — routes liquidity & burns fees.</small></div>
              <div><InfinityIcon size={15} /><b>Fee-Back</b><small>Trading rebates flow back to your wallet & $FEE liquidity.</small></div>
            </div>
          </div>

          <div className="eco-section-label"><Sparkles size={13} /> WHAT'S NEW ON {ecosystem.name.toUpperCase()} <small className="eco-tip">tap a coin to chart it here</small></div>
          <NewStuffFeed ecosystem={ecosystem} activePair={chartPair?.pairAddress} onPick={p => { setChartPair(p); if (layout === 'chat-first') setLayout('chart'); document.querySelector('.eco-right-col')?.scrollTo({ top: 0, behavior: 'smooth' }); }} />
        </div>
      </div>

      {links.length > 0 && <div className="eco-quick-dock" data-testid="eco-quick-dock">
        {links.map(([label, url, Icon]) => <a key={label} href={url} target="_blank" rel="noreferrer" data-testid={`eco-quick-${label.toLowerCase()}`} title={label}><Icon size={13} /><span>{label}</span></a>)}
      </div>}
    </div>
  </div>;
}
