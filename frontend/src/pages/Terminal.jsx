import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, ArrowLeft, ArrowRight, Flame, RefreshCw, SlidersHorizontal, Activity, Radio } from 'lucide-react';
import WalletModal from '../components/WalletModal';
import WalletProfileModal from '../components/WalletProfileModal';
import { useMarket } from '../hooks/useMarket';
import { coinIdentity, hasProviderImage, isExactPair, isNewPoolDeal, isSupportedPairChain, MARKET_RETENTION_DAYS, NEW_POOL_DEAL_PERCENT, normalizeRoomPerspective } from '../lib/dexscreener';
import { useWorkspace } from '../hooks/useWorkspace';
import { normalizeAutoRefresh, normalizeChartInterval, normalizeCompact, normalizeFontScale, normalizeReducedMotion, useLocalSettings, usePriceAlerts, AlertsPage } from '../components/terminal/LocalTools';
import { TerminalHeader, TerminalSidebar, MarketTicker, TerminalFooter } from '../components/terminal/TerminalShell';
import { DataStatus, MarketAvailabilityNotice, MarketError } from '../components/terminal/MarketPrimitives';
import { ChatRoom, TrenchesView } from '../components/terminal/CommunityRail';
import { TokenFocus } from '../components/terminal/TokenFocus';
import { MarketTable } from '../components/terminal/MarketTable';
import { LaunchpadDirectory } from '../components/terminal/LaunchpadDirectory';
import MetaLaunchSetup from '../components/terminal/MetaLaunchSetup';
import { LAUNCHPADS, matchesPad } from '../lib/launchpads';
import { FeeHeartbeat, Tokenomics, FeeAssetPage } from '../components/command/FeeCommand';
import { ContextBar, MouseGlow, AmbientFlakes, AlphaTape, PulseGrid, ContractScanner } from '../components/command/WorkspaceChrome';
import { FeeBackCenter, FeeCatCenter, FeelessCats } from '../components/command/FeeBack';
import FeeCatsPlatform from '../components/command/FeeCatsPlatform';
import { SwapWorkspace } from '../components/command/SwapWorkspace';
import { WatchlistDashboard } from '../components/command/CreatorProfile';
import { AdvancedWatchlist } from '../components/command/AdvancedWatchlist';
import { WalletProfilePage } from '../components/command/WalletProfilePage';
import { TrustSignals, CaseStudies, LiveProof, RoadmapVoting, NetworkStatus } from '../components/command/LiveTrust';
import { RadarView, PumpRadarView, SignalMovers, ParticipationBoard, MetaDetector } from '../components/command/DiscoveryViews';
import { CommandWhitepaper, MissionRoadmap, UnderstandFeeless, TerminalConfiguration } from '../components/command/CommandDocuments';
import { ReputationCenter } from '../components/command/ReputationCenter';
import { LegalPage } from '../components/LegalConsent';
import { FeeCatProfile } from '../components/command/FeeCatProfile';
import { LiveIntelStats } from '../components/command/LiveIntelStats';
import { AdBanner } from '../components/AdBanner';
import { MyInviteCard } from '../components/InviteCard';
import { CreatorProfilePage } from '../components/command/CreatorProfile';

const CHAINS = [['solana', 'Solana'], ['all', 'All chains'], ['ethereum', 'Ethereum'], ['base', 'Base'], ['bsc', 'BNB Chain'], ['arbitrum', 'Arbitrum'], ['avalanche', 'Avalanche'], ['polygon', 'Polygon'], ['sui', 'Sui']];
const STANDARD = ['', 'trade', 'pump', 'discover', 'new', 'movers'];

export default function Terminal() {
  const page = useParams()['*'] || ''; const nav = useNavigate(); const [params, setParams] = useSearchParams();
  const { ecosystem, setEcosystem, selectedPair, selectPair, watchlist, toggle, has, alertPair } = useWorkspace();
  const query = params.get('q') || ''; const metaLaunchRequested = params.get('setup') === 'feeless'; const chain = params.get('chain') === 'all' ? 'all' : ecosystem.chainId;
  const screen = ['quality', 'momentum', 'volume', 'new'].includes(params.get('screen')) ? params.get('screen') : '';
  const requestedScreener = query ? null : screen || 'quality';
  const screenParam = screen ? `&screen=${encodeURIComponent(screen)}` : '';
  const hasPairRoute = params.has('pair');
  const routePairAddress = (params.get('pair') || '').trim();
  const routeChain = (params.get('chain') || '').trim();
  const lastRouteNetwork = useRef(null);
  const routePairValid = hasPairRoute && Boolean(routePairAddress && isSupportedPairChain(routeChain) && /^[a-zA-Z0-9]+$/.test(routePairAddress));
  const pairLookupPath = routePairValid ? `/pair/${encodeURIComponent(routeChain)}/${encodeURIComponent(routePairAddress)}` : null;
  const [walletOpen, setWalletOpen] = useState(false); const [profileOpen, setProfileOpen] = useState(false); const [menuOpen, setMenuOpen] = useState(false);
  const [pad, setPad] = useState('all'); const [minLiquidity, setMinLiquidity] = useState('0'); const [pagination, setPagination] = useState(1);
  const [settings, setSettings] = useLocalSettings(); const [alerts, setAlerts] = usePriceAlerts();
  const compact = normalizeCompact(settings.compact);
  const autoRefresh = normalizeAutoRefresh(settings.autoRefresh);
  const reducedMotion = normalizeReducedMotion(settings.reducedMotion);
  const fontScale = normalizeFontScale(settings.fontScale);
  const chartInterval = normalizeChartInterval(settings.chartInterval);
  useEffect(() => {
    document.body.classList.toggle('reduced-motion-setting', reducedMotion);
    return () => document.body.classList.remove('reduced-motion-setting');
  }, [reducedMotion]);
  const tab = params.get('mode') || (['new', 'pump'].includes(page) ? 'new' : 'trending');
  const kind = ['new', 'pump'].includes(page) || tab === 'new' ? 'new' : 'trending';
  const cadence = page === 'pump' ? 15000 : autoRefresh ? 90000 : 0;
  const pumpScope = ecosystem.isLaunchpad ? `&scope=${encodeURIComponent(ecosystem.id)}` : '';
  const market = useMarket(query ? `/search?q=${encodeURIComponent(query)}` : `/feed?kind=${kind}&chain=${chain}&page=${pagination}${screenParam}${page === 'pump' ? pumpScope : ''}`, cadence);
  const newFeed = useMarket(`/feed?kind=new&chain=${chain}&page=${pagination}${screenParam}${pumpScope}`, cadence);
  const pumpTrendingFeed = useMarket(page === 'pump' ? `/feed?kind=trending&chain=${ecosystem.chainId}&page=1${screenParam}${pumpScope}` : null, page === 'pump' ? 15000 : 0);
  const pairLookup = useMarket(pairLookupPath, 60000);
  const assets = useMarket('/assets', 90000); const feeAssets = assets.data?.assets || []; const fee = feeAssets.find(a => a.id === 'fee'); const feeCat = feeAssets.find(a => a.id === 'feecat');
  const { data: community } = useMarket(`/api/intelligence/community?context=${ecosystem.id}`, 30000);
  const restoredPair = routePairValid
    ? (pairLookup.data?.pairs || []).find(pair => isExactPair(pair, routeChain, routePairAddress)) || null
    : null;
  const pairRouteState = !hasPairRoute
    ? null
    : !routePairValid
      ? 'invalid'
      : pairLookup.loading && !pairLookup.data
        ? 'loading'
        : restoredPair
          ? null
          : 'unavailable';
  const selected = hasPairRoute ? restoredPair : selectedPair || null;
  const perspective = normalizeRoomPerspective(params.get('room')) || 'bulls';
  const activePad = ecosystem.isLaunchpad ? ecosystem.id : pad;
  const pairs = useMemo(() => {
    const modeMatches = requestedScreener == null || !market.data?.screener || market.data.screener === requestedScreener;
    let list = (modeMatches ? market.data?.pairs || [] : []).filter(p => (chain === 'all' || p.chainId === chain) && Number(p.liquidity?.usd || 0) >= Number(minLiquidity) && matchesPad(p, activePad));
    if (tab === 'gainers') list.sort((a, b) => Number(b.priceChange?.h24 || 0) - Number(a.priceChange?.h24 || 0));
    if (tab === 'volume') list.sort((a, b) => Number(b.volume?.h24 || 0) - Number(a.volume?.h24 || 0));
    if (tab === 'movers') list.sort((a, b) => Math.abs(Number(b.priceChange?.h1 ?? b.priceChange?.m5 ?? 0)) - Math.abs(Number(a.priceChange?.h1 ?? a.priceChange?.m5 ?? 0)));
    if (kind === 'new' && !query) list.sort((a, b) => (b.pairCreatedAt || 0) - (a.pairCreatedAt || 0));
    if (page === 'new' && !query) list = list.filter(isNewPoolDeal);
    return list;
  }, [market.data, requestedScreener, chain, minLiquidity, activePad, tab, kind, query, page]);
  const marketModeMatches = requestedScreener == null || !market.data?.screener || market.data.screener === requestedScreener;
  const providerCanRequestNextPage = market.data?.provider_pagination?.can_request_next_page;
  const newPairs = (newFeed.data?.pairs || []).filter(p => matchesPad(p, activePad) && hasProviderImage(p) && (p.marketStage === 'new' || isNewPoolDeal(p)));
  useEffect(() => { setPagination(1); setPad('all'); setMinLiquidity('0'); setMenuOpen(false); if (page === 'pump' && ecosystem.id !== 'pump') setEcosystem('pump'); }, [page]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setPagination(1); setPad('all'); setMinLiquidity('0'); }, [ecosystem.id, query, kind]);
  useEffect(() => { if (page === 'launch' && metaLaunchRequested && ecosystem.id !== 'feeless-launch') setEcosystem('feeless-launch'); }, [page, metaLaunchRequested, ecosystem.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!routePairValid || lastRouteNetwork.current === `${routeChain}:${routePairAddress}`) return;
    lastRouteNetwork.current = `${routeChain}:${routePairAddress}`;
    if (routeChain !== ecosystem.chainId) setEcosystem(routeChain === 'bsc' ? 'bnb' : routeChain);
  }, [routePairValid, routeChain, routePairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!hasPairRoute) return;
    selectPair(restoredPair);
  }, [hasPairRoute, restoredPair?.chainId, restoredPair?.pairAddress, routeChain, routePairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (hasPairRoute || !selectedPair) return;
    const identity = coinIdentity(selectedPair);
    if (!identity) return;
    const next = new URLSearchParams(params);
    next.set('chain', identity.chainId);
    next.set('pair', identity.pairAddress);
    next.set('room', 'bulls');
    setParams(next, { replace: true });
  }, [hasPairRoute, selectedPair?.chainId, selectedPair?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  const onSelect = p => {
    const identity = coinIdentity(p);
    if (!identity) return;
    selectPair(p);
    if (identity.chainId !== ecosystem.chainId) setEcosystem(identity.chainId === 'bsc' ? 'bnb' : identity.chainId);
    const next = new URLSearchParams(params);
    next.set('chain', identity.chainId);
    next.set('pair', identity.pairAddress);
    next.set('room', 'bulls');
    nav(`/terminal/chat?${next.toString()}`);
  };
  const onPerspectiveChange = nextPerspective => {
    const normalized = normalizeRoomPerspective(nextPerspective);
    if (!normalized) return;
    const next = new URLSearchParams(params);
    next.set('room', normalized);
    setParams(next);
  };
  const resetSelectedPair = () => {
    selectPair(null);
    const next = new URLSearchParams(params);
    next.delete('pair');
    next.delete('room');
    setParams(next);
  };
  const setChain = value => { const next = new URLSearchParams(params); if (value === 'all') next.set('chain', 'all'); else { next.delete('chain'); setEcosystem(value === 'bsc' ? 'bnb' : value); } setParams(next); };
  const isHome = page === ''; const isMarket = STANDARD.includes(page);
  const focusKey = selected ? `token-${selected.chainId}-${selected.pairAddress}` : 'fee';
  const focus = <div key={focusKey} className="focus-flip">{selected ? <TokenFocus pair={selected} has={has} toggle={toggle} defaultInterval={chartInterval} /> : <FeeHeartbeat asset={fee} assets={feeAssets} loading={assets.loading} />}</div>;
  return <div className={`terminal-app command-terminal ${compact ? 'compact-rows' : ''} ${reducedMotion ? 'reduced-motion' : ''} text-scale-${fontScale}`} style={{ '--context-accent': ecosystem.color }}><MouseGlow /><AmbientFlakes /><div className="theme-flip-wipe" aria-hidden="true" /><TerminalHeader onWallet={() => setWalletOpen(true)} onProfile={() => setProfileOpen(true)} onMenu={() => setMenuOpen(v => !v)} query={query} /><MarketTicker /><ContextBar />
    <div className="terminal-body"><TerminalSidebar open={menuOpen} onClose={() => setMenuOpen(false)} savedCount={watchlist.length} /><main className="terminal-main" data-testid={`terminal-page-${page || 'home'}`}>
      <div className="workspace-topline"><span><i className="live-dot" /> FEELESS OS / <b data-testid="workspace-context-label">{ecosystem.name.toUpperCase()} {ecosystem.isLaunchpad ? 'WAR ROOM' : 'INTELLIGENCE'}</b><span className="workspace-mode">{page || '$FEE COMMAND'}</span></span><Link to={`/?node=${ecosystem.id}`} data-testid="workspace-globe-link">Globe view<ArrowUpRight size={12} /></Link></div>
       <div className="context-transition" key={ecosystem.id}>
       {pairRouteState === 'loading' && <p className="pair-route-status" role="status" data-testid="selected-pair-route-loading">Restoring {routeChain} coin {routePairAddress} from the market provider…</p>}
       {pairRouteState === 'invalid' && <MarketError id="selected-pair-route-error" error="Invalid selected coin link. A supported chain and pair address are required." description="No coin was selected." />}
       {pairRouteState === 'unavailable' && <MarketError id="selected-pair-route-error" error={pairLookup.error ? `Selected coin is unavailable: ${pairLookup.error}` : `Selected coin ${routeChain} / ${routePairAddress} was not returned by the market provider.`} description="No substitute coin was selected." reload={pairLookup.reload} retryLabel="Retry selected coin" />}
      {isMarket && <div className={`terminal-content-grid ${!isHome && page !== 'trade' ? 'market-wide' : ''}`}><div className="terminal-primary">
         {isHome && <><div className="command-home-heading"><div><span className="eyebrow">THE FEELESS NETWORK COMMAND CENTER</span><h1>$FEE is the heartbeat.</h1></div><button className="btn-outline" data-testid="reset-to-fee" onClick={resetSelectedPair}><Activity size={14} />$FEE focus</button></div>{focus}<PulseGrid pairs={pairs} community={community} fee={fee} feeCat={feeCat} loading={market.loading || !market.data} /><Tokenomics compact /></>}
          {page === 'trade' && <><div className="command-page-title"><span className="eyebrow">INTELLIGENCE → ROUTE → SIMULATE → APPROVE</span><h1>Your execution workspace.</h1></div>{focus}<SwapWorkspace pair={selected} feeAsset={fee} feeAssets={feeAssets} feeCat={feeCat} fontScale={fontScale} onWallet={() => setWalletOpen(true)} /></>}
       {!['', 'trade', 'pump'].includes(page) && <div className="command-page-title"><span className="eyebrow">{ecosystem.name.toUpperCase()} / ON-CHAIN INTELLIGENCE</span><h1>{query ? 'Follow the contract.' : page === 'new' ? 'New pools, better entry points.' : page === 'movers' ? 'Read the acceleration.' : 'Find the next rotation.'}</h1><p>{query ? `Provider results for “${query}”` : page === 'new' ? `Provider-indexed pools within ${MARKET_RETENTION_DAYS} days with a 24h drawdown of at least ${NEW_POOL_DEAL_PERCENT}%. Not a buy recommendation.` : 'Real signals, within provider coverage. No invented activity.'}</p></div>}
        {page !== 'pump' && <ContractScanner />}
        {(page === 'discover' || isHome) && <MetaDetector pairs={[...pairs, ...(newFeed.data?.pairs || [])]} onSelect={onSelect} />}
         {page === 'pump' && <PumpRadarView newFeed={newFeed} trendingFeed={pumpTrendingFeed} onSelect={onSelect} />}
        {page === 'new' && <RadarView pairs={pairs} onSelect={onSelect} kind="new" />}
        {page === 'movers' && <SignalMovers pairs={pairs} onSelect={onSelect} />}
          <section className="market-section"><div className="section-title market-title"><h2><Flame size={18} />{query ? 'Search results' : page === 'new' ? 'New pool deals ≥5%' : kind === 'new' ? 'New pool deals' : 'Top coin discovery'}</h2><DataStatus data={market.data} id="market-feed-status" />{market.refreshing && <span className="live-feed-badge" data-testid="market-feed-refreshing">LIVE</span>}<button title="Refresh market feed" data-testid="market-refresh" className="icon-btn small-icon" onClick={() => market.reload()}><RefreshCw size={14} /></button>{isHome && <Link to="/terminal/discover" className="section-more" data-testid="markets-view-all">Expand<ArrowUpRight size={13} /></Link>}</div>
           <div className="market-controls"><div className="market-tabs">{[['trending', 'Top coins'], ['new', 'New coins'], ['gainers', 'Gainers'], ['movers', 'Top movers'], ['volume', 'Volume']].map(([id, label]) => <button key={id} className={tab === id ? 'active' : ''} data-testid={`market-tab-${id}`} onClick={() => { const next = new URLSearchParams(params); next.set('mode', id); if (['new', 'pump', 'movers'].includes(page)) nav(`/terminal/discover?${next}`); else setParams(next); }}>{label}</button>)}</div><label className="chain-select"><span className="live-dot" /><select aria-label="Market chain" data-testid="market-chain-filter" value={chain} onChange={e => setChain(e.target.value)}>{CHAINS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label className="chain-select"><span>Screen</span><select aria-label="Market screener" data-testid="market-screener-filter" value={screen || 'quality'} onChange={e => { const next = new URLSearchParams(params); next.set('screen', e.target.value); setParams(next); }}>{[['quality', 'Best observed'], ['momentum', 'Momentum'], ['volume', 'Volume leaders'], ['new', 'Fresh']].map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label></div>
           {!isHome && <div className="advanced-filters"><SlidersHorizontal size={14} /><label>DEX venue<select data-testid="market-pad-filter" aria-label="DEX venue" value={activePad} disabled={ecosystem.isLaunchpad} onChange={e => setPad(e.target.value)}><option value="all">All venues</option>{LAUNCHPADS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Min. liquidity<select data-testid="market-liquidity-filter" value={minLiquidity} onChange={e => setMinLiquidity(e.target.value)}><option value="0">Any</option><option value="10000">$10K</option><option value="100000">$100K</option><option value="1000000">$1M</option></select></label>{query && <button data-testid="market-clear-search" onClick={() => { const next = new URLSearchParams(params); next.delete('q'); setParams(next); }}>Clear search ×</button>}</div>}
           <MarketAvailabilityNotice data={market.data} error={market.error} errorStatus={market.errorStatus} errorProvider={market.errorProvider} id="market-feed-availability" />{market.error && <MarketError error={market.error} reload={market.reload} id="market-feed-error" />}{marketModeMatches && market.data?.stale && <p className="stale-banner" data-testid="market-stale-warning">Cached data · {market.data.error}</p>}
            <MarketTable pairs={isHome ? pairs.slice(0, 6) : pairs.slice(0, 10)} screenerLabel={marketModeMatches ? market.data?.screener_label : undefined} loading={market.loading || (!marketModeMatches && !market.error)} refreshing={market.refreshing} onSelect={onSelect} has={has} toggle={toggle} />
            <div className="market-bottom"><span data-testid="market-coverage">{market.data?.provider || 'GeckoTerminal'} · {pairs.length} live coin markets · {ecosystem.name} context · Provider-limited{market.data?.provider_pagination?.pages_requested?.length > 1 ? ` · Provider pages ${market.data.provider_pagination.pages_requested[0]}–${market.data.provider_pagination.pages_requested.at(-1)} sampled` : ''}</span>{page === 'new' && <small data-testid="market-deal-window">14-day window · 24h drawdown ≥5%</small>}{!isHome && !query && <div className="pagination"><button data-testid="market-previous-page" title="Previous page" disabled={pagination === 1} onClick={() => setPagination(p => p - 1)}><ArrowLeft size={14} /></button><span data-testid="market-page-number">{pagination} / 10</span><button data-testid="market-next-page" title="Next page" disabled={pagination >= 10 || providerCanRequestNextPage === false || (providerCanRequestNextPage !== true && (market.data?.pairs?.length || 0) < 20)} onClick={() => setPagination(p => p + 1)}><ArrowRight size={14} /></button></div>}</div>
        </section><div className="context-platforms"><Link to="/terminal/launch" data-testid="context-launchpads-link">Ecosystem launchpads<ArrowUpRight size={13} /></Link>{ecosystem.explorer && <a data-testid="context-explorer" href={ecosystem.explorer} target="_blank" rel="noreferrer">{ecosystem.name} explorer<ArrowUpRight size={13} /></a>}{ecosystem.dex && <a data-testid="context-dex" href={ecosystem.dex} target="_blank" rel="noreferrer">Ecosystem DEX<ArrowUpRight size={13} /></a>}</div>
        </div><aside className="community-rail"><ChatRoom pairs={pairs} newPairs={newFeed.data?.pairs || newPairs} onSelect={onSelect} selectedPair={selected} selectedPerspective={perspective} onPerspectiveChange={onPerspectiveChange} /><AlphaTape /><div className="command-quick-links"><Link to="/terminal/feeback" data-testid="quick-feeback">FEE-BACK<span>THE RETURN PATH ↗</span></Link><Link to="/terminal/feecat" data-testid="quick-feecat">FEECAT<span>CULTURE + UTILITY ↗</span></Link><Link to="/terminal/whitepaper" data-testid="quick-whitepaper">WHITEPAPER<span>WEB + ACTUAL PDF ↗</span></Link></div><div className="risk-note">Markets can be illiquid or malicious. Provider matches are not audits. New pools are not necessarily new tokens.</div></aside></div>}
       {page === 'launch' && (params.get('setup') === 'feeless' ? <MetaLaunchSetup onWallet={() => setWalletOpen(true)} /> : <LaunchpadDirectory />)}{page === 'watchlist' && <><AdvancedWatchlist /><div className="command-section-title unified-watch-title"><span>CREATORS YOU FOLLOW</span><small>Launches and rug flags from wallets you've starred</small></div><WatchlistDashboard /></>}
         {page === 'chat' && <TrenchesView pairs={pairs} newPairs={newFeed.data?.pairs || newPairs} onSelect={onSelect} selectedPair={selected} selectedPerspective={perspective} onPerspectiveChange={onPerspectiveChange} onConnect={() => setWalletOpen(true)} />}
      {page === 'alerts' && <><TrustSignals /><AlertsPage alerts={alerts} setAlerts={setAlerts} selected={alertPair || selected} watchlist={watchlist} ecosystem={ecosystem} /></>}
      {page === 'fee' && <FeeAssetPage asset={fee}>{fee?.pair ? <TokenFocus pair={fee.pair} has={has} toggle={toggle} /> : <FeeHeartbeat asset={fee} loading={assets.loading} />}</FeeAssetPage>}
        {page === 'feeback' && <FeeBackCenter feeCat={feeCat} />}{page === 'feecat' && <><FeeCatProfile /><FeeCatCenter asset={feeCat} community={community} onSelect={onSelect} /></>}{page === 'feecat/cats' && <FeelessCats />}{page === 'feecat/agents' && <FeeCatsPlatform />}
      {page === 'reputation' && <ReputationCenter />}
      {!page.startsWith('profile/') && page !== 'legal' && <AdBanner placement="banner" />}
      {page === 'legal' && <LegalPage />}
      {page.startsWith('profile/') && <WalletProfilePage key={page} address={page.split('/')[1]} />}
      {page.startsWith('reputation/') && (() => { const [, repChain, repAddress] = page.split('/'); return repChain && repAddress ? <CreatorProfilePage chain={repChain} address={repAddress} /> : null; })()}
      {page === 'leaderboard' && <ParticipationBoard />}{page === 'whitepaper' && <><LiveProof /><CommandWhitepaper /></>}{page === 'roadmap' && <><MissionRoadmap /><RoadmapVoting /></>}{page === 'learn' && <><LiveIntelStats /><UnderstandFeeless /><CaseStudies /></>}
      {page === 'settings' && <><TerminalConfiguration settings={settings} setSettings={setSettings} onWallet={() => setWalletOpen(true)} /><MyInviteCard /><NetworkStatus /></>}
       {!isMarket && !page.startsWith('reputation') && !page.startsWith('profile/') && !['launch', 'watchlist', 'chat', 'alerts', 'fee', 'feeback', 'feecat', 'feecat/cats', 'feecat/agents', 'leaderboard', 'whitepaper', 'roadmap', 'learn', 'settings', 'legal'].includes(page) && <div className="page-heading"><h1>Off the radar.</h1><Link to="/terminal" className="btn-primary" data-testid="unknown-page-home">Back to terminal</Link></div>}
       </div><TerminalFooter />
     </main></div><WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} /><WalletProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} /></div>;
}