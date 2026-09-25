import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Radar, Radio, Activity, Star, Bell, Users, ExternalLink, RefreshCw, Zap, Layers3, TrendingUp, Droplets } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { useMarket } from '../../hooks/useMarket';
import { MarketAvailabilityNotice, TokenAvatar, Change } from '../terminal/MarketPrimitives';
import { ReputationBadge } from '../terminal/ReputationBadge';
import { useTilt } from '../../hooks/useTilt';
import { FlashValue } from '../terminal/FlashValue';
import { useClock } from './WorkspaceChrome';
import { formatUSD, formatAge, formatTime, pairKey, dexUrl, hasProviderImage } from '../../lib/dexscreener';
import { LAUNCHPADS, matchesPad } from '../../lib/launchpads';

export const RadarView = ({ pairs, onSelect, kind = 'pump' }) => {
  useClock(10000); const { ecosystem } = useWorkspace();
  const freshest = pairs.reduce((min, p) => Math.min(min, Number(p.pairCreatedAt) || Infinity), Infinity);
  const totalLiquidity = pairs.reduce((sum, p) => sum + (Number(p.liquidity?.usd) || 0), 0);
  const gainers = pairs.filter(p => Number(p.priceChange?.m5) > 0).length;
  return <section className="launch-radar"><div className="radar-overview">
    <div className="radar-stat-rail">
      <div><small>OBSERVED POOLS</small><FlashValue raw={pairs.length}><strong data-testid="radar-count">{pairs.length}</strong></FlashValue></div>
      <div><small>COMBINED LIQUIDITY</small><FlashValue raw={totalLiquidity}><strong>{formatUSD(totalLiquidity)}</strong></FlashValue></div>
      <div><small>5M GAINERS</small><strong className={gainers ? 'positive' : ''}>{gainers}</strong></div>
      <div><small>FRESHEST POOL</small><strong>{Number.isFinite(freshest) ? formatAge(freshest) : '—'}</strong></div>
    </div>
    <div><span className="eyebrow">{ecosystem.name.toUpperCase()} / LAUNCH VELOCITY</span><h2>Early is a signal.<br /><span>Not a promise.</span></h2><p>Pool age, recent price movement and observed liquidity. Bonding-curve progress and launchpad provenance stay unavailable unless the provider establishes them.</p><span className="state-tag">{pairs.length ? 'PROVIDER FEED CONNECTED' : 'AWAITING MATCHING POOLS'}</span></div>
  </div><div className="radar-pool-grid">{pairs.slice(0, 6).map(p => <button key={pairKey(p)} data-testid={`radar-pool-${pairKey(p)}`} onClick={() => onSelect(p)} className="radar-pool"><div><TokenAvatar pair={p} /><span><b>{p.baseToken?.symbol}</b><small>{p.dexId}</small></span><span className="pool-age" data-testid={`pool-age-${pairKey(p)}`}>{formatAge(p.pairCreatedAt)}</span></div><dl><div><dt>5m momentum</dt><dd><Change value={p.priceChange?.m5} /></dd></div><div><dt>Liquidity</dt><dd>{formatUSD(p.liquidity?.usd)}</dd></div><div><dt>24h volume</dt><dd>{formatUSD(p.volume?.h24)}</dd></div></dl><small>Pool indexed by provider <ArrowUpRight size={13} /></small></button>)}</div>{!pairs.length && <div className="truth-empty" data-testid="launch-radar-empty">No verified matching pools in this feed. Parent-chain activity is not relabelled as a launchpad’s activity.</div>}</section>;
};

const PUMP_RADAR_STAGES = [
  ['new', 'New coins', Zap],
  ['graduated', 'Graduated', Layers3],
  ['trending', 'Trending coins', TrendingUp],
  ['gainers', 'Gainers', Activity],
  ['watchlist', 'Watchlist', Star],
];

const formatPoolAddress = address => address.length > 12 ? `${address.slice(0, 6)}…${address.slice(-4)}` : address;

export const PumpRadarCard = ({ pair, onSelect, rank, onLogoExhausted }) => {
  const change = Number(pair.priceChange?.h24);
  const momentum = pair.priceChange?.m5 ?? pair.priceChange?.h1;
  const signal = Number.isFinite(Number(pair.signals?.velocity_pct_min))
    ? `${Number(pair.signals.velocity_pct_min).toFixed(2)}%/min`
    : Number.isFinite(Number(momentum)) ? `${Number(momentum).toFixed(2)}% 5m` : 'Awaiting delta';
  const migrationPool = typeof pair.graduation?.pool_address === 'string' ? pair.graduation.pool_address.trim() : '';
  const tilt = useTilt(7);
  const activate = event => {
    if (event.target.closest('a')) return;
    onSelect(pair);
  };
  const handleKeyDown = event => {
    if (event.target !== event.currentTarget || !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    onSelect(pair);
  };
  return <article ref={tilt.ref} onMouseMove={tilt.onMouseMove} onMouseLeave={tilt.onMouseLeave} className="pump-radar-card tilt-card" data-testid={`pump-radar-card-${pairKey(pair)}`} onClick={activate} onKeyDown={handleKeyDown} role="button" tabIndex="0" aria-label={`Open ${pair.baseToken?.symbol || 'token'} market`}>
     <div className="pump-radar-card-top"><span className="pump-radar-rank">{String(rank).padStart(2, '0')}</span><TokenAvatar pair={pair} size={38} maxAttempts={onLogoExhausted ? 3 : undefined} onExhausted={onLogoExhausted} /><span className="pump-radar-token"><b>{pair.baseToken?.symbol || 'Unknown'}</b><small>{pair.baseToken?.name || 'Coin name unavailable'}</small><small>{pair.chainId || 'chain unavailable'} · {pair.dexId || 'venue unavailable'}</small></span><span className="pump-radar-alive" title="Recent provider snapshot"><i />ALIVE</span><span className="pump-radar-age">{formatAge(pair.pairCreatedAt)}</span></div>
    <div className="pump-radar-price-row"><span className="pump-radar-value-block"><small>PRICE</small><FlashValue raw={pair.priceUsd}><strong>{formatUSD(pair.priceUsd)}</strong></FlashValue></span><Change value={pair.priceChange?.h24} id={`pump-radar-change-${pairKey(pair)}`} /><span className={change >= 0 ? 'positive' : 'negative'}><Activity size={11} />{signal}</span></div>
    <div className="pump-radar-reputation-row"><ReputationBadge pair={pair} /></div>
    <div className="pump-radar-metrics"><span><small>LIQUIDITY</small><FlashValue raw={pair.liquidity?.usd}><b>{formatUSD(pair.liquidity?.usd)}</b></FlashValue></span><span><small>MARKET CAP</small><FlashValue raw={pair.marketCap}><b>{formatUSD(pair.marketCap)}</b></FlashValue></span><span><small>24H VOL</small><FlashValue raw={pair.volume?.h24}><b>{formatUSD(pair.volume?.h24)}</b></FlashValue></span></div>
    {pair.graduation && <div className="pump-radar-migration" data-testid={`pump-radar-migration-${pairKey(pair)}`}><small>MIGRATION POOL</small>{migrationPool ? <a href={`https://solscan.io/account/${encodeURIComponent(migrationPool)}`} target="_blank" rel="noreferrer" aria-label={`Open provider-reported migration pool ${migrationPool}`} onClick={event => event.stopPropagation()}><span>Provider-reported destination</span><code>{formatPoolAddress(migrationPool)}</code><ExternalLink size={11} /></a> : <span className="pump-radar-migration-unavailable" data-testid={`pump-radar-migration-unavailable-${pairKey(pair)}`}>Unavailable from Pump.fun</span>}</div>}
    <span className="pump-radar-card-foot"><span><Droplets size={11} />Provider snapshot</span><ArrowUpRight size={13} /></span>
  </article>;
};

export const PumpRadarView = ({ newFeed, trendingFeed, onSelect }) => {
  const { ecosystem, watchlist } = useWorkspace();
  const [stage, setStage] = useState('new');
  const [failedNewLogos, setFailedNewLogos] = useState(() => new Set());
  const now = useClock(1000);
  const matches = useMemo(() => pair => matchesPad(pair, ecosystem.id) && (ecosystem.chainId === 'all' || pair.chainId === ecosystem.chainId), [ecosystem.id, ecosystem.chainId]);
  const newPairs = useMemo(() => (newFeed.data?.pairs || []).filter(pair => {
    const fresh = Number.isFinite(Number(pair.pairCreatedAt)) && Date.now() - Number(pair.pairCreatedAt) <= 14 * 24 * 60 * 60 * 1000;
    return matches(pair) && (pair.marketStage === 'new' || fresh) && hasProviderImage(pair) && !failedNewLogos.has(pairKey(pair));
  }), [newFeed.data, matches, failedNewLogos]);
  const trendingPairs = useMemo(() => (trendingFeed.data?.pairs || []).filter(matches), [trendingFeed.data, matches]);
  const allObserved = useMemo(() => [...new Map([...newPairs, ...trendingPairs].map(pair => [pairKey(pair), pair])).values()], [newPairs, trendingPairs]);
  const graduationMints = useMemo(() => [...new Set(allObserved.map(pair => pair.baseToken?.address).filter(Boolean))].join(','), [allObserved]);
  // Debounced: the observed-pairs set churns on nearly every feed tick, and each distinct
  // mint list is a fresh SWR key. Without this, the provider (Pump.fun) sees a burst of
  // requests every few seconds and starts returning "refresh limit reached" errors.
  const [stableGraduationMints, setStableGraduationMints] = useState(graduationMints);
  useEffect(() => {
    const timer = setTimeout(() => setStableGraduationMints(graduationMints), 20000);
    return () => clearTimeout(timer);
  }, [graduationMints]);
  const graduationFeed = useMarket(stableGraduationMints ? `/graduations?mints=${encodeURIComponent(stableGraduationMints)}` : null, 30000);
  const graduationByMint = useMemo(() => new Map((graduationFeed.data?.graduations || []).map(item => [item.mint, item])), [graduationFeed.data]);
  const graduated = useMemo(() => allObserved
    .map(pair => {
      const graduation = graduationByMint.get(pair.baseToken?.address);
      return graduation?.status === 'graduated' ? { ...pair, graduation } : null;
    })
    .filter(Boolean), [allObserved, graduationByMint]);
  const gainers = [...trendingPairs].filter(pair => Number.isFinite(Number(pair.priceChange?.h24))).sort((a, b) => Number(b.priceChange.h24) - Number(a.priceChange.h24));
  const stagePairs = { new: newPairs, graduated, trending: trendingPairs, gainers, watchlist: watchlist.filter(matches) }[stage] || [];
  const feed = stage === 'graduated' ? graduationFeed : stage === 'new' ? newFeed : trendingFeed;
  const providerError = feed.error || feed.data?.error;
  const fallbackReason = feed.data?.fallback_reason || feed.data?.fallbackReason;
  const sourceLabel = feed.data?.sourceLabel || feed.data?.source_label || feed.data?.label || 'Public market feed';
  const coverage = feed.data?.coverage || {};
  const actualProvider = feed.data?.provider || 'Provider';
  const primaryProvider = feed.data?.primary_provider || feed.data?.primaryProvider || actualProvider;
  const pumpLaunchpadFeed = primaryProvider === 'Pump.fun' || actualProvider === 'Pump.fun';
  const fetchedAt = feed.data?.fetched_at ? Date.parse(feed.data.fetched_at) : 0;
  const ageSeconds = fetchedAt ? Math.max(0, Math.floor((now - fetchedAt) / 1000)) : null;
  const nextRefresh = providerError ? 'RETRYING' : feed.refreshing ? 'SYNCING' : ageSeconds == null ? 'CONNECTING' : `NEXT SYNC ~${Math.max(0, 15 - (ageSeconds % 15))}s`;
  const totalLiquidity = stagePairs.reduce((sum, pair) => sum + Number(pair.liquidity?.usd || 0), 0);
  const marketCapValues = stagePairs.filter(pair => pair.marketCap != null && Number.isFinite(Number(pair.marketCap)));
  const totalMarketCap = marketCapValues.length ? marketCapValues.reduce((sum, pair) => sum + Number(pair.marketCap), 0) : null;
  const stageUnavailable = stage === 'graduated' && !graduated.length;
  return <section className="pump-radar" data-testid="pump-radar">
    <div className="pump-radar-hero"><div><span className="eyebrow"><span className="live-dot" /> PUMP RADAR / LIVE COIN VIEWER</span><h2>Track the next rotation.</h2><p>Provider-backed {pumpLaunchpadFeed ? 'coin' : 'market'} stages refresh every 15 seconds. Prices and deltas are live snapshots, not a trade signal or a claim of launchpad activity.</p></div><div className="pump-radar-live-orbit" aria-hidden="true"><div /><div /><strong>{stagePairs.length}<small>VISIBLE COINS</small></strong></div></div>
    <div className="pump-radar-toolbar"><div className="pump-radar-stages">{PUMP_RADAR_STAGES.map(([id, label, Icon]) => <button key={id} className={stage === id ? 'active' : ''} data-testid={`pump-radar-stage-${id}`} onClick={() => setStage(id)}><Icon size={14} />{label}<small>{id === 'graduated' && stageUnavailable ? '—' : id === 'watchlist' ? stagePairs.length : { new: newPairs.length, trending: trendingPairs.length, gainers: gainers.length }[id] ?? stagePairs.length}</small></button>)}</div><div className="pump-radar-sync"><span><i className={feed.refreshing ? 'is-refreshing' : ''} />{providerError ? 'Provider unavailable' : actualProvider}{primaryProvider !== actualProvider ? ` · primary ${primaryProvider}` : ''} · {nextRefresh}</span><button type="button" title="Refresh Pump radar" aria-label="Refresh Pump radar" data-testid="pump-radar-refresh" onClick={() => feed.reload()}><RefreshCw size={14} /></button></div></div>
    <div className="pump-radar-summary"><span><small>VISIBLE COINS</small><b>{stagePairs.length}</b></span><span><small>LIQUIDITY</small><b>{formatUSD(totalLiquidity)}</b></span><span><small>MARKET CAP</small><b>{formatUSD(totalMarketCap)}</b></span><span><small>{stage === 'graduated' ? 'STATUS OBSERVED' : 'LAST SNAPSHOT'}</small><b>{fetchedAt ? formatTime(feed.data.fetched_at) : '—'}</b></span></div>
    <MarketAvailabilityNotice data={feed.data} error={feed.error} id={`pump-radar-${stage}-availability`} />
    {stage === 'graduated' && <p className="provider-note" data-testid="pump-radar-graduation-source">{sourceLabel} · {feed.data?.status === 'unavailable' || feed.error ? `Unavailable${feed.data?.error ? `: ${feed.data.error}` : feed.error ? `: ${feed.error}` : ''}` : feed.data?.error ? `Error: ${feed.data.error}` : feed.data?.status === 'verified' ? 'Verified completion events only' : 'No verified completion events observed'}{feed.data?.fetched_at ? ` · Observed ${formatTime(feed.data.fetched_at)}` : ''}</p>}
    {providerError && <p className="pump-radar-error" role="alert" data-testid="pump-radar-error">{providerError} <button type="button" onClick={() => feed.reload()}>Retry</button></p>}
    {!providerError && feed.loading && !stagePairs.length && <p className="truth-empty" role="status" data-testid="pump-radar-loading">Connecting to live provider snapshots…</p>}
    {!providerError && !feed.loading && !stagePairs.length && <div className="truth-empty" data-testid={`pump-radar-${stage}-empty`}>{stageUnavailable ? (feed.data?.status === 'unavailable' ? 'Graduation status is unavailable from Pump.fun right now.' : 'No Pump.fun completion event matches an observed coin.') : stage === 'watchlist' ? 'Star provider-indexed coins to build a personal radar.' : `No ${stage} coins are currently visible in this provider snapshot.`}</div>}
     <div className="pump-radar-grid">{stagePairs.slice(0, 8).map((pair, index) => <PumpRadarCard
       key={pairKey(pair)}
       pair={pair}
       rank={index + 1}
       onSelect={onSelect}
       onLogoExhausted={stage === 'new' ? () => setFailedNewLogos(previous => {
         const next = new Set(previous);
         next.add(pairKey(pair));
         return next;
       }) : undefined}
     />)}</div>
    <div className="pump-radar-disclosure"><span><Zap size={13} />{pumpLaunchpadFeed ? 'Pump.fun coins are provider-indexed, not guaranteed launches.' : 'Provider-indexed coins are not guaranteed launches.'}</span><span>{sourceLabel} · {feed.data?.sourceUrl || feed.data?.source_url || 'source boundary unavailable'}</span>{fallbackReason && <span data-testid="pump-radar-fallback">Fallback: {fallbackReason}</span>}{coverage.discovery && <span data-testid="pump-radar-coverage">Coverage: {coverage.discovery}</span>}</div>
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
  const { data, error, errorStatus, errorProvider } = useMarket(`/pair/${pair.chainId}/${pair.pairAddress}`, 60000);
  const p = data?.pairs?.[0] || pair;
  return <article className="watched-token" data-testid={`watch-card-${pairKey(p)}`}><div><TokenAvatar pair={p} /><span><b>{p.baseToken.symbol}</b><small>{p.chainId} / {p.dexId}</small></span><button data-testid={`watch-remove-${pairKey(p)}`} title="Remove from watchlist" onClick={() => toggle(p)}><Star size={15} fill="currentColor" /></button></div><MarketAvailabilityNotice data={data} error={error} errorStatus={errorStatus} errorProvider={errorProvider} id={`watch-market-availability-${pairKey(p)}`} /><button className="watched-chart" data-testid={`watch-chart-${pairKey(p)}`} onClick={() => onSelect(p)}><strong>{formatUSD(p.priceUsd)}</strong><Change value={p.priceChange?.h24} /><MiniHistory rows={p.signals?.history} /></button><div className="watch-liquidity"><span>Liquidity {formatUSD(p.liquidity?.usd)}</span><small>{p.signals?.liquidity_change_pct != null ? `${p.signals.liquidity_change_pct.toFixed(2)}% snapshot Δ` : 'Awaiting baseline delta'}</small></div><div className="watch-card-actions"><button data-testid={`watch-trade-${pairKey(p)}`} onClick={() => { selectPair(p); nav('/terminal/trade'); }}>Trade<ArrowUpRight size={13} /></button><button data-testid={`watch-alert-${pairKey(p)}`} title="Create alert" onClick={() => { setAlertPair(p); nav('/terminal/alerts'); }}><Bell size={14} /></button></div>{(error || data?.stale) && <small className="stale">Cached / saved snapshot</small>}</article>;
};
export const LivingWatchlist = ({ onSelect }) => {
  const { watchlist } = useWorkspace();
  return <div className="living-watchlist"><div className="command-page-title"><span className="eyebrow">YOUR PERSONAL SIGNAL NETWORK</span><h1>Conviction, connected.</h1><p>Real observations. Live movement. {watchlist.length} tokens saved in this browser.</p></div><div className="watch-card-grid">{watchlist.map(p => <WatchedToken key={pairKey(p)} pair={p} onSelect={onSelect} />)}</div>{!watchlist.length && <div className="truth-empty" data-testid="living-watchlist-empty"><Star size={29} />No watchlisted tokens. Star a real market to start tracking.</div>}</div>;
};

export const ParticipationBoard = () => {
  const { ecosystem } = useWorkspace(); const { data, error } = useMarket(`/api/intelligence/community?context=${ecosystem.id}`, 15000);
  return <div className="participation-board"><div className="command-page-title"><span className="eyebrow">MEASURABLE PARTICIPATION / {ecosystem.name.toUpperCase()}</span><h1>The community is the edge.</h1><p>Actual messages over the last seven days. Public handles are not verified identities.</p></div>{data?.rankings?.map((row, i) => <div className="participation-row" key={row.handle} data-testid={`participation-rank-${i}`}><span>{String(i + 1).padStart(2, '0')}</span><Users size={19} /><b>{row.handle}</b><strong>{row.messages}<small>MESSAGES</small></strong></div>)}{!data?.rankings?.length && <div className="truth-empty" data-testid="participation-empty">{error ? 'Community metrics unavailable.' : 'Awaiting real participation in this ecosystem. No fabricated rankings.'}</div>}</div>;
};
const META_STOPWORDS = new Set(['the', 'coin', 'token', 'inu', 'sol', 'eth', 'official', 'of', 'on', 'and', 'a', 'to', 'in', 'for', 'is', 'by', 'my', 'ai']);
const metaWords = pair => {
  const raw = `${pair.baseToken?.symbol || ''} ${pair.baseToken?.name || ''}`.toLowerCase();
  const words = new Set(raw.split(/[^a-z0-9]+/).filter(w => w.length >= 3 && !META_STOPWORDS.has(w)));
  const sym = (pair.baseToken?.symbol || '').toLowerCase().replace(/[^a-z]/g, '');
  // Also catch fused tickers (JEANWORK, JEANCAT) via 4-letter prefixes/suffixes.
  if (sym.length >= 6) { words.add(sym.slice(0, 4)); words.add(sym.slice(-4)); }
  return words;
};

// Groups live tokens that share a theme word into "metas" — ranked by combined volume
// and average 24h move. Every number comes from the provider pairs on screen.
export function detectMetas(pairs, minMembers = 2) {
  const groups = new Map();
  const unique = [...new Map(pairs.filter(p => p?.baseToken).map(p => [p.baseToken.address || p.pairAddress, p])).values()];
  for (const pair of unique) for (const word of metaWords(pair)) {
    if (!groups.has(word)) groups.set(word, []);
    groups.get(word).push(pair);
  }
  const symbolOf = p => (p.baseToken?.symbol || '').trim().toUpperCase();
  const metas = [...groups.entries()].filter(([, members]) => new Set(members.map(symbolOf)).size >= minMembers).map(([word, members]) => {
    const bySymbol = new Map();
    members.forEach(p => bySymbol.set(symbolOf(p), [...(bySymbol.get(symbolOf(p)) || []), p]));
    const copycats = [...bySymbol.entries()].filter(([, list]) => list.length > 1).map(([sym, list]) => ({ sym, count: list.length }));
    const vol = members.reduce((s, p) => s + (Number(p.volume?.h24) || 0), 0);
    const changes = members.map(p => Number(p.priceChange?.h24)).filter(Number.isFinite);
    const avg = changes.length ? changes.reduce((a, b) => a + b, 0) / changes.length : null;
    return { word, copycats, distinct: bySymbol.size, members: members.sort((a, b) => (Number(b.volume?.h24) || 0) - (Number(a.volume?.h24) || 0)), vol, avg };
  }).sort((a, b) => b.members.length - a.members.length || b.vol - a.vol);
  const seen = new Set();
  return metas.filter(m => { const sig = m.members.map(p => p.pairAddress).sort().join(); if (seen.has(sig)) return false; seen.add(sig); return true; }).slice(0, 6);
}

export const MetaDetector = ({ pairs, onSelect }) => {
  const metas = useMemo(() => detectMetas(pairs || []), [pairs]);
  const [open, setOpen] = useState(null);
  return <section className="meta-detector" data-testid="meta-detector">
    <div className="section-title"><h2><Layers3 size={18} />Meta detector</h2><small>Themes forming across live markets right now</small></div>
    {!metas.length && <div className="truth-empty">No shared theme across two or more live coins yet. Metas show up here the moment they form.</div>}
    <div className="meta-grid">{metas.map(meta => <div key={meta.word} className={`meta-card ${open === meta.word ? 'is-open' : ''}`}>
      <button type="button" className="meta-card-head" onClick={() => setOpen(open === meta.word ? null : meta.word)}>
        <b>#{meta.word.toUpperCase()}</b>
        <span className="meta-count">{meta.distinct} tickers · {meta.members.length} pools</span>
        <span className={meta.avg == null ? '' : meta.avg >= 0 ? 'positive' : 'negative'}>{meta.avg == null ? '—' : `${meta.avg >= 0 ? '+' : ''}${meta.avg.toFixed(1)}% avg`}</span>
        <small>{formatUSD(meta.vol)} vol 24h</small>
      </button>
      {meta.copycats.length > 0 && <div className="meta-copycats" title="Several different contracts are using the exact same ticker — a common clone/scam pattern. Verify the contract before buying.">⚠ Copycats: {meta.copycats.map(c => `${c.sym} ×${c.count}`).join(' · ')}</div>}
      <div className="meta-avatars">{meta.members.slice(0, 6).map(p => <TokenAvatar key={p.pairAddress} pair={p} size={22} />)}</div>
      {open === meta.word && <div className="meta-members">{meta.members.map(p => <button type="button" key={p.pairAddress} onClick={() => onSelect?.(p)}>
        <TokenAvatar pair={p} size={20} /><b>{p.baseToken.symbol}</b><ReputationBadge pair={p} compact /><span className={Number(p.priceChange?.h24) >= 0 ? 'positive' : 'negative'}>{Number.isFinite(Number(p.priceChange?.h24)) ? `${Number(p.priceChange.h24).toFixed(1)}%` : '—'}</span><small>{formatUSD(p.volume?.h24)}</small>
      </button>)}</div>}
    </div>)}</div>
  </section>;
};
