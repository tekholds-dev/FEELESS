import { LaunchRadar } from '../LaunchRadar';
import { TrendingCards, TrenchLanding, TrenchBar, HotCalls, LiveCalls, CallerBoard } from './TrenchesTools';
import { LivePrice } from './LiveCells';
import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, Radio, Rocket, Compass, Star, BarChart3, ArrowUpRight, CandlestickChart, Layers3 } from 'lucide-react';
import EcosystemChat from '../EcosystemChat';
import { useWorkspace } from '../../hooks/useWorkspace';

import { MarketAvailabilityNotice, TokenAvatar, Change } from './MarketPrimitives';
import { ReputationBadge } from './ReputationBadge';
import { TokenFocus } from './TokenFocus';
import { useMarket } from '../../hooks/useMarket';
import { AdBanner } from '../AdBanner';
import { RadarPanel } from '../command/MetaPanels';
import { formatUSD, pairKey, coinIdentity, coinRoom, normalizeRoomPerspective, shortAddress } from '../../lib/dexscreener';
import { apiUrl } from '../../lib/api';
import { BoltLegend, BoltSignal, PumpPulseBanner } from './BoltSignal';
import { DegenWeather } from './DegenWeather';
import { mergePumpCallouts, visiblePumpCallouts, isPumpCoin } from '../../lib/pumpCallouts';

export const LivePoolsPanel = ({ pairs = [], newPairs = [], onSelect }) => {
  const { data, loading, refreshing, error } = useMarket('/feed?kind=trending&chain=all&page=1', 15000);
  const providerPairs = Array.isArray(data?.pairs) ? data.pairs : [];
  const snapshotPairs = Array.isArray(pairs) && pairs.length ? pairs : Array.isArray(newPairs) ? newPairs : [];
  const livePairs = providerPairs.length ? providerPairs : snapshotPairs;
  const usingSnapshot = !providerPairs.length && snapshotPairs.length > 0;
  const liquidity = livePairs.reduce((sum, pair) => sum + Number(pair.liquidity?.usd || 0), 0);
  const marketCapValues = livePairs.filter(pair => pair.marketCap != null && Number.isFinite(Number(pair.marketCap)));
  const marketCap = marketCapValues.length ? marketCapValues.reduce((sum, pair) => sum + Number(pair.marketCap), 0) : null;
  const volume = livePairs.reduce((sum, pair) => sum + Number(pair.volume?.h24 || 0), 0);
  const chains = new Set(livePairs.map(pair => pair.chainId).filter(Boolean)).size;
  return <div className="live-pools-panel" data-testid="live-pools-panel">
    <div className="live-pools-summary">
      <div><small>LIVE POOLS</small><strong data-testid="live-pools-count">{loading && !livePairs.length ? '—' : livePairs.length}</strong></div>
      <div><small>LIQUIDITY</small><strong data-testid="live-pools-liquidity">{formatUSD(liquidity)}</strong></div>
      <div><small>MARKET CAP</small><strong data-testid="live-pools-market-cap">{formatUSD(marketCap)}</strong></div>
      <div><small>24H FLOW</small><strong data-testid="live-pools-volume">{formatUSD(volume)}</strong></div>
      <div><small>CHAINS</small><strong data-testid="live-pools-chains">{chains || '—'}</strong></div>
    </div>
    <div className="live-pools-status" data-testid="live-pools-status"><i className={refreshing ? 'is-refreshing' : ''} />{usingSnapshot ? 'Page snapshot fallback' : error ? 'Provider snapshot unavailable' : data?.provider ? `${data.provider} · ${refreshing ? 'updating' : 'live'}` : 'Connecting to live providers'}</div>
    <MarketAvailabilityNotice data={data} error={error} id="live-pools-availability" />
    <div className="live-pools-list">
      {livePairs.slice(0, 12).map(pair => <button className="live-pool-row" key={pairKey(pair)} data-testid={`live-pool-${pairKey(pair)}`} onClick={() => onSelect?.(pair)}>
        <TokenAvatar pair={pair} size={32} />
        <span className="live-pool-name"><b>{pair.baseToken?.symbol || 'Unknown'}</b><small>{pair.baseToken?.name || 'Coin name unavailable'}</small><small>{pair.chainId || 'chain unavailable'} · {pair.dexId || 'venue unavailable'}</small></span>
        <span className="live-pool-price"><strong><LivePrice pair={pair} precise /></strong><Change value={pair.priceChange?.h24} /></span>
        <span className="live-pool-numbers"><small>LIQ <b>{formatUSD(pair.liquidity?.usd)}</b></small><small>MC <b>{formatUSD(pair.marketCap)}</b></small></span>
      </button>)}
      {!livePairs.length && <div className="truth-empty" data-testid="live-pools-empty">{error ? 'Live pool data is unavailable right now.' : 'Waiting for provider-indexed pools…'}</div>}
    </div>
  </div>;
};

// Pump user callouts for a Pump coin. Owned by the coin (not the bulls/bears tab) so switching tabs
// keeps the entry time and the every-3rd cadence.
const usePumpCallouts = pair => {
  const mint = pair?.baseToken?.address;
  const enabled = isPumpCoin(pair);
  const [state, setState] = useState({ calls: [], enteredAt: 0, status: 'idle' });
  useEffect(() => {
    setState({ calls: [], enteredAt: Date.now(), status: enabled ? 'loading' : 'idle' });
    if (!enabled) return undefined;
    let alive = true;
    const controller = new AbortController();
    let timer;
    let failed = false;
    const load = async () => {
      failed = false;
      try {
        const response = await fetch(apiUrl(`/api/market/pump/callouts/${encodeURIComponent(mint)}`), { signal: controller.signal });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || 'Pump callouts unavailable.');
        if (alive) setState(current => ({ ...current, calls: mergePumpCallouts(current.calls, data.items, mint), status: 'live' }));
      } catch (error) {
        failed = true;
        if (alive && error.name !== 'AbortError') setState(current => ({ ...current, status: 'unavailable' }));
      } finally {
        // Unavailable (no provider access) → check again in 5 minutes instead of hammering every 15s.
        if (alive) timer = setTimeout(load, failed ? 300000 : 15000);
      }
    };
    load();
    return () => { alive = false; controller.abort(); clearTimeout(timer); };
  }, [enabled, mint]);
  return useMemo(() => ({ ...state, enabled, mint, visible: visiblePumpCallouts(state.calls, state.enteredAt) }), [state, enabled, mint]);
};

const TrenchCoinCard = ({ pair, rank, callCount, onPick }) => {
  return <button className="trenches-coin" data-testid={`trenches-coin-${pairKey(pair)}`} onClick={onPick}>
    <TokenAvatar pair={pair} size={38} /><span><b>{pair.baseToken?.symbol || 'Unknown'}<BoltSignal pair={pair} rank={rank} callCount={callCount} size={12} /></b><small>{pair.baseToken?.name || 'Coin name unavailable'}</small><small>{pair.chainId} · {pair.dexId}</small><small>LIQ {formatUSD(pair.liquidity?.usd)} · MC {formatUSD(pair.marketCap)}</small><ReputationBadge pair={pair} compact /></span><Change value={pair.priceChange?.h24} />
  </button>;
};

export const ChatRoom = ({ large = false, pairs = [], newPairs = [], onSelect, selectedPair = null, selectedPerspective = null, onPerspectiveChange, onConnect }) => {
  const { ecosystem } = useWorkspace();
  const [channel, setChannel] = useState(selectedPair ? (normalizeRoomPerspective(selectedPerspective) || 'bulls') : 'general');
  const identity = coinIdentity(selectedPair);
  const hasSelectedPair = Boolean(identity);
  const coinChannels = [['bulls', 'Bulls'], ['trenches', 'Trenches'], ['bears', 'Bears']];
  const channels = [['general', 'General'], ['alpha', 'FRSV'], ['launches', 'Launches'], ['trading', 'Trading'], ['whales', 'Whales'], ['pools', 'Pools']];
  React.useEffect(() => {
    setChannel(hasSelectedPair ? (normalizeRoomPerspective(selectedPerspective) || 'bulls') : 'general');
  }, [identity?.key, hasSelectedPair, selectedPerspective]);
  const tabs = selectedPair ? coinChannels : channels;
  const room = selectedPair ? coinRoom(selectedPair, channel) : `${ecosystem.id}-${channel}`;
  const roomName = selectedPair ? `${selectedPair.baseToken?.symbol || 'Coin'} / ${channel}` : `${ecosystem.name} / ${channel}`;
  const pump = usePumpCallouts(selectedPair);
  const changeChannel = next => {
    setChannel(next);
    if (selectedPair && normalizeRoomPerspective(next)) onPerspectiveChange?.(next);
  };
  return <section className={`community-chat ${large ? 'large-chat' : ''}`}><div className="section-title"><h2><MessageCircle size={18} />{selectedPair ? `${selectedPair.baseToken?.symbol || 'Coin'} discussion` : 'The Trenches'}</h2><span className="positive small" data-testid="chat-active-ecosystem">{selectedPair ? `${selectedPair.chainId} · ${shortAddress(selectedPair.pairAddress)}` : ecosystem.name}</span></div><div className="chat-tabs">{tabs.map(([id, label]) => <button key={id} data-testid={`chat-tab-${id}`} aria-selected={channel === id} title={`${label} discussion`} onClick={() => changeChannel(id)} className={`${channel === id ? 'active' : ''} ${id === 'trenches' ? 'trenches-font' : ''}`}>{label}</button>)}</div>{selectedPair && <PumpPulseBanner pair={selectedPair} />}{selectedPair ? <EcosystemChat key={room} room={room} compact ecosystem={{ id: room, name: roomName }} onConnect={onConnect} pump={pump} /> : channel === 'pools' ? <LivePoolsPanel pairs={pairs} newPairs={newPairs} onSelect={onSelect} /> : <EcosystemChat key={`${ecosystem.id}-${channel}`} compact ecosystem={{ id: `${ecosystem.id}-${channel}`, name: roomName }} onConnect={onConnect} />}</section>;
};

export const TrenchesView = ({ pairs = [], newPairs = [], onSelect, selectedPair: routeSelectedPair = null, selectedPerspective = null, onPerspectiveChange, onConnect }) => {
  const { ecosystem, selectPair, watchlist, has, toggle } = useWorkspace();
  const [stage, setStage] = useState('new');
  const [shown, setShown] = useState(6);
  useEffect(() => { setShown(6); }, [stage]);
  const [callCounts, setCallCounts] = useState({});
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl('/api/reputation/calls/recent?limit=100')).then(r => r.ok ? r.json() : { calls: [] }).then(d => {
      if (!alive) return;
      const next = {}; (d.calls || []).forEach(call => { [...new Set([call.pairAddress, call.mint].filter(Boolean))].forEach(key => { next[key] = (next[key] || 0) + 1; }); }); setCallCounts(next);
    }).catch(() => {});
    load(); const timer = setInterval(load, 8000); return () => { alive = false; clearInterval(timer); };
  }, []);
  // Keep one local active coin. Route restoration may initialize/update it, but a card click updates
  // it synchronously so a stale route/global selection cannot reopen the previous coin.
  const [activePair, setActivePair] = useState(() => routeSelectedPair || null);
  useEffect(() => { if (routeSelectedPair) setActivePair(routeSelectedPair); }, [routeSelectedPair]);
  const chartPair = activePair || pairs[0] || newPairs[0] || null;
  const graduated = pairs.filter(pair => pair.graduated === true || pair.info?.graduated === true || pair.baseToken?.graduated === true);
  const stagePairs = {
    new: newPairs,
    graduated,
    trending: pairs,
    watchlist: watchlist,
  }[stage] || [];
  const [wide, setWide] = useState(() => { try { return localStorage.getItem('feeless-trench-wide') === '1'; } catch { return false; } });
  useEffect(() => { try { localStorage.setItem('feeless-trench-wide', wide ? '1' : '0'); } catch {} window.dispatchEvent(new Event('resize')); }, [wide]);
  // The Trenches tab always opens on the about/discovery page; only a link that names a coin drops you on the floor.
  const [onFloor, setOnFloor] = useState(() => Boolean(routeSelectedPair));
  useEffect(() => { if (routeSelectedPair) setOnFloor(true); }, [routeSelectedPair]); // a coin link always lands on the trading floor
  useEffect(() => { setOnFloor(Boolean(routeSelectedPair)); }, [routeSelectedPair]);
  const setFloor = v => { setOnFloor(v); window.scrollTo?.({ top: 0 }); };
  const pickCall = async c => {
    try {
      const res = await fetch(`/api/market/pairs/${c.chain}/${c.pairAddress}`);
      const body = await res.json();
      const p = (body?.pairs || [])[0];
      if (p) { setActivePair(p); selectPair(p); window.scrollTo?.({ top: 0, behavior: 'smooth' }); }
    } catch { /* keep current chart */ }
  };
  if (!onFloor) return <div className="trenches-page trenches-lit" data-testid="trenches-page"><TrenchLanding ecosystemName={ecosystem.name} onEnter={() => setFloor(true)} /><DegenWeather /><AdBanner placement="trenches" /><RadarPanel compact /><LaunchRadar /><TrendingCards pairs={[...pairs, ...newPairs.filter(n => !pairs.some(p => p.pairAddress === n.pairAddress))]} onPick={p => { setActivePair(p); selectPair(p); setFloor(true); }} /></div>;
  return <div className="trenches-page trenches-lit trenches-floor" data-testid="trenches-page">
    <TrenchBar onAbout={() => setFloor(false)} />
    <div className={`trenches-grid ${wide ? 'is-wide' : ''}`}>
      <section className="trenches-chat-section" data-testid="trenches-chat-section"><ChatRoom large pairs={pairs} newPairs={newPairs} onSelect={onSelect} selectedPair={chartPair} selectedPerspective={selectedPerspective} onPerspectiveChange={onPerspectiveChange} onConnect={onConnect} /></section>
      <section className="trenches-chart-panel"><div className="section-title"><h2><CandlestickChart size={18} />DEX chart</h2><span className="provider-note">Jupiter · OHLCV</span></div>{chartPair ? <TokenFocus pair={chartPair} has={has} toggle={toggle} defaultInterval="1m" onExpand={() => setWide(w => !w)} expanded={wide} /> : <div className="truth-empty" data-testid="trenches-chart-empty"><CandlestickChart size={28} /><span>Select a provider-indexed coin to open its chart.</span></div>}</section>
      <aside className="trenches-tools"><HotCalls onPick={pickCall} /><LiveCalls onPick={pickCall} /><CallerBoard /></aside>
    </div>
    <section className="trenches-stages trenches-stage-panel" data-testid="trenches-stage-panel"><div className="section-title"><h2><Layers3 size={18} />Coin viewer</h2><span className="provider-note">Liquidity · market cap first</span><BoltLegend /></div><div className="trenches-stage-tabs">{[['new', 'New coins'], ['graduated', 'Graduated'], ['trending', 'Trending coins'], ['watchlist', 'Watchlist']].map(([id, label]) => <button key={id} className={stage === id ? 'active' : ''} data-testid={`trenches-stage-${id}`} onClick={() => setStage(id)}>{label}<small>{id === 'graduated' && !graduated.length ? 'unavailable' : stagePairs.length}</small></button>)}</div><div className="trenches-coin-grid">{stagePairs.slice(0, shown).map((pair, index) => <TrenchCoinCard key={pairKey(pair)} pair={pair} rank={index + 1} callCount={callCounts[pair.pairAddress] || callCounts[pair.baseToken?.address] || 0} onPick={() => { setActivePair(pair); selectPair(pair); onSelect?.(pair); }} />)}</div>{stagePairs.length > shown && <button type="button" className="trenches-show-more" data-testid="trenches-show-more" onClick={() => setShown(n => n + 12)}>Show {Math.min(12, stagePairs.length - shown)} more · {stagePairs.length - shown} left</button>}{!stagePairs.length && <div className="truth-empty" data-testid={`trenches-${stage}-empty`}>{stage === 'graduated' ? 'Graduation status is unavailable in the current provider feed.' : `No ${stage} coins are available in this ecosystem snapshot.`}</div>}</section>
  </div>;
};

export const CommunityRail = ({ pairs, onSelect }) => {
  const [filter, setFilter] = useState('all');
  const filtered = pairs.filter(p => filter !== 'gainers' || Number(p.priceChange?.h24) > 0).slice(0, 5);
  return <aside className="community-rail"><ChatRoom pairs={pairs} onSelect={onSelect} /><section className="activity-section"><div className="section-title"><h2><Radio size={17} />On the radar</h2><select aria-label="Activity filter" data-testid="activity-filter" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All pools</option><option value="gainers">Gainers</option></select></div><div>{filtered.map(p => <button key={pairKey(p)} className="radar-item" data-testid={`radar-token-${pairKey(p)}`} onClick={() => onSelect(p)}><TokenAvatar pair={p} size={31} /><span><b>{p.baseToken?.symbol}</b><small>{p.dexId} · {formatUSD(p.volume?.h24)} vol</small></span><ReputationBadge pair={p} compact /><Change value={p.priceChange?.h24} id={`radar-change-${pairKey(p)}`} /></button>)}{!filtered.length && <p className="provider-note" data-testid="radar-empty">No matching activity in this feed.</p>}</div><Link className="section-more" data-testid="radar-view-all" to="/terminal/discover">All markets <ArrowUpRight size={13} /></Link></section><section className="quick-actions"><div className="section-title"><h2>Move with intent.</h2><ArrowUpRight size={15} /></div><div className="quick-grid">{[['pump', 'Pump', 'New pools', Rocket], ['discover', 'Discover', 'Find your edge', Compass], ['launch', 'Launch', 'Pick a launchpad', BarChart3], ['watchlist', 'Watchlist', 'Keep them close', Star]].map(([path, title, sub, Icon]) => <Link data-testid={`quick-${path}`} key={path} to={`/terminal/${path}`}><Icon size={19} /><span><b>{title}</b><small>{sub}</small></span></Link>)}</div></section><div className="risk-note"><span>DYOR, ALWAYS.</span>Tokens are unverified. New pools can be illiquid, manipulated, or malicious. Nothing here is financial advice.</div></aside>;
};
