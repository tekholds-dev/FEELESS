import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Radar, Radio, Activity, Star, Bell, Users, ExternalLink, RefreshCw, Zap, Layers3, TrendingUp, Droplets } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { useMarket } from '../../hooks/useMarket';
import { TokenAvatar, Change } from '../terminal/MarketPrimitives';
import { useClock } from './WorkspaceChrome';
import { formatUSD, formatAge, formatTime, pairKey, dexUrl, isNewPoolDeal } from '../../lib/dexscreener';
import { LAUNCHPADS, matchesPad } from '../../lib/launchpads';

export const RadarView = ({ pairs, onSelect, kind = 'pump' }) => {
  useClock(10000); const { ecosystem } = useWorkspace();
  return <section className="launch-radar"><div className="radar-overview"><div className="radar-instrument"><div className="radar-sweep" /><span className="radar-center" /><div className="radar-ring ring-1" /><div className="radar-ring ring-2" /><div className="radar-ring ring-3" />{pairs.slice(0, 8).map((p, i) => <button key={pairKey(p)} className="radar-blip" data-testid={`radar-blip-${pairKey(p)}`} title={`${p.baseToken?.symbol} · ${formatUSD(p.liquidity?.usd)} liquidity`} onClick={() => onSelect(p)} style={{ left: `${28 + ((i * 23) % 50)}%`, top: `${25 + ((i * 31) % 53)}%` }} />)}<strong data-testid="radar-count">{pairs.length}<small>OBSERVED POOLS</small></strong></div><div><span className="eyebrow">{ecosystem.name.toUpperCase()} / LAUNCH VELOCITY</span><h2>Early is a signal.<br /><span>Not a promise.</span></h2><p>Pool age, recent price movement and observed liquidity. Bonding-curve progress and launchpad provenance stay unavailable unless the provider establishes them.</p><span className="state-tag">{pairs.length ? 'PROVIDER FEED CONNECTED' : 'AWAITING MATCHING POOLS'}</span></div></div><div className="radar-pool-grid">{pairs.map(p => <button key={pairKey(p)} data-testid={`radar-pool-${pairKey(p)}`} onClick={() => onSelect(p)} className="radar-pool"><div><TokenAvatar pair={p} /><span><b>{p.baseToken?.symbol}</b><small>{p.dexId}</small></span><span className="pool-age" data-testid={`pool-age-${pairKey(p)}`}>{formatAge(p.pairCreatedAt)}</span></div><dl><div><dt>5m momentum</dt><dd><Change value={p.priceChange?.m5} /></dd></div><div><dt>Liquidity</dt><dd>{formatUSD(p.liquidity?.usd)}</dd></div><div><dt>24h volume</dt><dd>{formatUSD(p.volume?.h24)}</dd></div></dl><small>Pool indexed by provider <ArrowUpRight size={13} /></small></button>)}</div>{!pairs.length && <div className="truth-empty" data-testid="launch-radar-empty">No verified matching pools in this feed. Parent-chain activity is not relabelled as a launchpad’s activity.</div>}</section>;
};

const PUMP_RADAR_STAGES = [
  ['new', 'New pools', Zap],
  ['graduated', 'Graduated', Layers3],
  ['trending', 'Trending', TrendingUp],
  ['gainers', 'Gainers', Activity],
  ['watchlist', 'Watchlist', Star],
];

const graduatedPair = pair => pair?.graduated === true
  || pair?.info?.graduated === true
  || pair?.baseToken?.graduated === true;

const PumpRadarCard = ({ pair, onSelect, rank }) => {
  const change = Number(pair.priceChange?.h24);
  const momentum = pair.priceChange?.m5 ?? pair.priceChange?.h1;
  const signal = Number.isFinite(Number(pair.signals?.velocity_pct_min))
    ? `${Number(pair.signals.velocity_pct_min).toFixed(2)}%/min`
    : Number.isFinite(Number(momentum)) ? `${Number(momentum).toFixed(2)}% 5m` : 'Awaiting delta';
  return <button className="pump-radar-card" data-testid={`pump-radar-card-${pairKey(pair)}`} onClick={() => onSelect(pair)}>
    <div className="pump-radar-card-top"><span className="pump-radar-rank">{String(rank).padStart(2, '0')}</span><TokenAvatar pair={pair} size={38} /><span className="pump-radar-token"><b>{pair.baseToken?.symbol || 'Unknown'}</b><small>{pair.baseToken?.name || 'Coin name unavailable'}</small><small>{pair.chainId || 'chain unavailable'} · {pair.dexId || 'venue unavailable'}</small></span><span className="pump-radar-age">{formatAge(pair.pairCreatedAt)}</span></div>
    <div className="pump-radar-price-row"><strong>{formatUSD(pair.priceUsd)}</strong><Change value={pair.priceChange?.h24} id={`pump-radar-change-${pairKey(pair)}`} /><span className={change >= 0 ? 'positive' : 'negative'}><Activity size={11} />{signal}</span></div>
    <div className="pump-radar-metrics"><span><small>LIQUIDITY</small><b>{formatUSD(pair.liquidity?.usd)}</b></span><span><small>24H VOL</small><b>{formatUSD(pair.volume?.h24)}</b></span><span><small>FDV</small><b>{formatUSD(pair.fdv || pair.marketCap)}</b></span></div>
    <span className="pump-radar-card-foot"><span><Droplets size={11} />Provider snapshot</span><ArrowUpRight size={13} /></span>
  </button>;
};

export const PumpRadarView = ({ newFeed, trendingFeed, onSelect }) => {
  const { ecosystem, watchlist } = useWorkspace();
  const [stage, setStage] = useState('new');
  const now = useClock(1000);
  const matches = useMemo(() => pair => matchesPad(pair, ecosystem.id) && (ecosystem.chainId === 'all' || pair.chainId === ecosystem.chainId), [ecosystem.id, ecosystem.chainId]);
  const newPairs = useMemo(() => (newFeed.data?.pairs || []).filter(pair => matches(pair) && isNewPoolDeal(pair)), [newFeed.data, matches]);
  const trendingPairs = useMemo(() => (trendingFeed.data?.pairs || []).filter(matches), [trendingFeed.data, matches]);
  const allObserved = useMemo(() => [...new Map([...newPairs, ...trendingPairs].map(pair => [pairKey(pair), pair])).values()], [newPairs, trendingPairs]);
  const graduated = allObserved.filter(graduatedPair);
  const gainers = [...trendingPairs].filter(pair => Number.isFinite(Number(pair.priceChange?.h24))).sort((a, b) => Number(b.priceChange.h24) - Number(a.priceChange.h24));
  const stagePairs = { new: newPairs, graduated, trending: trendingPairs, gainers, watchlist: watchlist.filter(matches) }[stage] || [];
  const activeFeed = stage === 'new' ? newFeed : trendingFeed;
  const fetchedAt = activeFeed.data?.fetched_at ? Date.parse(activeFeed.data.fetched_at) : 0;
  const ageSeconds = fetchedAt ? Math.max(0, Math.floor((now - fetchedAt) / 1000)) : null;
  const nextRefresh = activeFeed.refreshing ? 'SYNCING' : ageSeconds == null ? 'CONNECTING' : `NEXT SYNC ~${Math.max(0, 15 - (ageSeconds % 15))}s`;
  const totalLiquidity = stagePairs.reduce((sum, pair) => sum + Number(pair.liquidity?.usd || 0), 0);
  const totalVolume = stagePairs.reduce((sum, pair) => sum + Number(pair.volume?.h24 || 0), 0);
  const stageUnavailable = stage === 'graduated' && !graduated.length;
  return <section className="pump-radar" data-testid="pump-radar">
    <div className="pump-radar-hero"><div><span className="eyebrow"><span className="live-dot" /> PUMP RADAR / LIVE MARKET TAPE</span><h2>See the next rotation<br /><span>before the crowd catches up.</span></h2><p>Provider-backed pool stages refresh every 15 seconds. Prices and deltas are live snapshots, not a trade signal or a claim of launchpad activity.</p></div><div className="pump-radar-live-orbit" aria-hidden="true"><div /><div /><strong>{stagePairs.length}<small>VISIBLE</small></strong></div></div>
    <div className="pump-radar-toolbar"><div className="pump-radar-stages">{PUMP_RADAR_STAGES.map(([id, label, Icon]) => <button key={id} className={stage === id ? 'active' : ''} data-testid={`pump-radar-stage-${id}`} onClick={() => setStage(id)}><Icon size={14} />{label}<small>{id === 'graduated' && stageUnavailable ? '—' : id === 'watchlist' ? stagePairs.length : { new: newPairs.length, trending: trendingPairs.length, gainers: gainers.length }[id] ?? stagePairs.length}</small></button>)}</div><div className="pump-radar-sync"><span><i className={activeFeed.refreshing ? 'is-refreshing' : ''} />{activeFeed.data?.provider || 'Provider'} · {nextRefresh}</span><button type="button" title="Refresh Pump radar" aria-label="Refresh Pump radar" data-testid="pump-radar-refresh" onClick={() => activeFeed.reload()}><RefreshCw size={14} /></button></div></div>
    <div className="pump-radar-summary"><span><small>VISIBLE POOLS</small><b>{stagePairs.length}</b></span><span><small>LIQUIDITY</small><b>{formatUSD(totalLiquidity)}</b></span><span><small>24H FLOW</small><b>{formatUSD(totalVolume)}</b></span><span><small>LAST SNAPSHOT</small><b>{fetchedAt ? formatTime(activeFeed.data.fetched_at) : '—'}</b></span></div>
    {activeFeed.error && <p className="pump-radar-error" role="alert" data-testid="pump-radar-error">{activeFeed.error} <button type="button" onClick={() => activeFeed.reload()}>Retry</button></p>}
    {!activeFeed.error && activeFeed.loading && !stagePairs.length && <p className="truth-empty" role="status" data-testid="pump-radar-loading">Connecting to live provider snapshots…</p>}
    {!activeFeed.loading && !stagePairs.length && <div className="truth-empty" data-testid={`pump-radar-${stage}-empty`}>{stageUnavailable ? 'Graduation status is not exposed by the current provider feed.' : stage === 'watchlist' ? 'Star provider-indexed pools to build a personal radar.' : `No ${stage} pools are currently visible in this provider snapshot.`}</div>}
    <div className="pump-radar-grid">{stagePairs.slice(0, 18).map((pair, index) => <PumpRadarCard key={pairKey(pair)} pair={pair} rank={index + 1} onSelect={onSelect} />)}</div>
    <div className="pump-radar-disclosure"><span><Zap size={13} />New pools are provider-indexed, not guaranteed launches.</span><span>{activeFeed.data?.label || 'Public market feed'} · {activeFeed.data?.sourceUrl || activeFeed.data?.source_url || 'source boundary unavailable'}</span></div>
  </section>;
};

export const SignalMovers = ({ pairs, onSelect }) => {
  const [metric, setMetric] = useState('velocity');
  const selectors = { velocity: p => p.signals?.velocity_pct_min, acceleration: p => p.signals?.acceleration_indicator,
    volume: p => p.signals?.volume_change_pct, liquidity: p => p.signals?.liquidity_change_pct,
    new: p => p.pairCreatedAt && Date.now() - p.pairCreatedAt < 86400000 ? Number(p.priceChange?.h1) : null,
    established: p => p.pairCreatedAt && Date.now() - p.pairCreatedAt >= 86400000 ? Number(p.priceChange?.h24) : null };
  const ranked = pairs.filter(p => selectors[metric](p) != null && Number.isFinite(selectors[metric](p))).sort((a, b) => selectors[metric](b) - selectors[metric](a));
  return <section className="signal-movers"><div className="signal-modes">{[['velocity', 'Velocity'], ['acceleration', 'Acceleration'], ['volume', 'Volume expansion'], ['liquidity', 'Liquidity expansion'], ['new', 'New pool movers'], ['established', 'Established movers']].map(([id, title]) => <button key={id} data-testid={`mover-mode-${id}`} onClick={() => setMetric(id)} className={metric === id ? 'active' : ''}>{title}</button>)}</div><p className="provider-note">{metric === 'velocity' ? 'Reported 5m price change divided by five minutes.' : metric === 'acceleration' ? 'Recent 5m price-change rate versus the preceding portion of the 1h window; an indicator, not a tick-level derivative.' : ['volume', 'liquidity'].includes(metric) ? 'Same-source snapshot changes. A second observation is required; rolling volume can fall without a sell.' : 'Ranked within the fetched feed, not across every token.'}</p>{ranked.map((p, i) => <button className="signal-mover-row" key={pairKey(p)} data-testid={`signal-mover-${pairKey(p)}`} onClick={() => onSelect(p)}><span className="signal-rank">{String(i + 1).padStart(2, '0')}</span><TokenAvatar pair={p} /><b>{p.baseToken.symbol}</b><div className="signal-strength"><i style={{ width: `${Math.min(100, Math.max(5, Math.abs(selectors[metric](p)) * 10))}%` }} /></div><span className={selectors[metric](p) >= 0 ? 'positive mono' : 'negative mono'}>{selectors[metric](p).toFixed(3)}{metric === 'velocity' || metric === 'acceleration' ? '%/min' : '%'}</span><ArrowUpRight size={13} /></button>)}{!ranked.length && <div className="truth-empty" data-testid="movers-waiting">Awaiting enough real observations for this signal.</div>}</section>;
};

const MiniHistory = ({ rows = [] }) => {
  const values = rows.map(r => r.price).filter(n => Number.isFinite(n));
  if (values.length < 2) return <div className="mini-history-wait">Collecting real price observations…</div>;
  const min = Math.min(...values), max = Math.max(...values); const range = max - min || max * .01 || 1;
  const points = values.map((v, i) => `${i / (values.length - 1) * 240},${48 - (v - min) / range * 38}`).join(' ');
  return <svg viewBox="0 0 240 55" className="mini-history" aria-label="Observed price snapshots"><polyline points={points} fill="none" stroke="#00e9a0" strokeWidth="1.5" /></svg>;
};
const WatchedToken = ({ pair, onSelect }) => {
  const { toggle, setAlertPair, selectPair } = useWorkspace(); const nav = useNavigate();
  const { data, error } = useMarket(`/pair/${pair.chainId}/${pair.pairAddress}`, 60000);
  const p = data?.pairs?.[0] || pair;
  return <article className="watched-token" data-testid={`watch-card-${pairKey(p)}`}><div><TokenAvatar pair={p} /><span><b>{p.baseToken.symbol}</b><small>{p.chainId} / {p.dexId}</small></span><button data-testid={`watch-remove-${pairKey(p)}`} title="Remove from watchlist" onClick={() => toggle(p)}><Star size={15} fill="currentColor" /></button></div><button className="watched-chart" data-testid={`watch-chart-${pairKey(p)}`} onClick={() => onSelect(p)}><strong>{formatUSD(p.priceUsd)}</strong><Change value={p.priceChange?.h24} /><MiniHistory rows={p.signals?.history} /></button><div className="watch-liquidity"><span>Liquidity {formatUSD(p.liquidity?.usd)}</span><small>{p.signals?.liquidity_change_pct != null ? `${p.signals.liquidity_change_pct.toFixed(2)}% snapshot Δ` : 'Awaiting baseline delta'}</small></div><div className="watch-card-actions"><button data-testid={`watch-trade-${pairKey(p)}`} onClick={() => { selectPair(p); nav('/terminal/trade'); }}>Trade<ArrowUpRight size={13} /></button><button data-testid={`watch-alert-${pairKey(p)}`} title="Create alert" onClick={() => { setAlertPair(p); nav('/terminal/alerts'); }}><Bell size={14} /></button></div>{(error || data?.stale) && <small className="stale">Cached / saved snapshot</small>}</article>;
};
export const LivingWatchlist = ({ onSelect }) => {
  const { watchlist } = useWorkspace();
  return <div className="living-watchlist"><div className="command-page-title"><span className="eyebrow">YOUR PERSONAL SIGNAL NETWORK</span><h1>Conviction, connected.</h1><p>Real observations. Live movement. {watchlist.length} tokens saved in this browser.</p></div><div className="watch-card-grid">{watchlist.map(p => <WatchedToken key={pairKey(p)} pair={p} onSelect={onSelect} />)}</div>{!watchlist.length && <div className="truth-empty" data-testid="living-watchlist-empty"><Star size={29} />No watchlisted tokens. Star a real market to start tracking.</div>}</div>;
};

export const ParticipationBoard = () => {
  const { ecosystem } = useWorkspace(); const { data, error } = useMarket(`/api/intelligence/community?context=${ecosystem.id}`, 15000);
  return <div className="participation-board"><div className="command-page-title"><span className="eyebrow">MEASURABLE PARTICIPATION / {ecosystem.name.toUpperCase()}</span><h1>The community is the edge.</h1><p>Actual messages over the last seven days. Public handles are not verified identities.</p></div>{data?.rankings?.map((row, i) => <div className="participation-row" key={row.handle} data-testid={`participation-rank-${i}`}><span>{String(i + 1).padStart(2, '0')}</span><Users size={19} /><b>{row.handle}</b><strong>{row.messages}<small>MESSAGES</small></strong></div>)}{!data?.rankings?.length && <div className="truth-empty" data-testid="participation-empty">{error ? 'Community metrics unavailable.' : 'Awaiting real participation in this ecosystem. No fabricated rankings.'}</div>}</div>;
};