import React, { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Home, CandlestickChart, Rocket, Compass, Star, MessageCircle, Trophy, Bell, BookOpen, Map, FileText, Settings, Search, Menu, Wallet, Globe2, ArrowUpRight, X, Coins, Cat, Activity, Sun, Moon, UserRound, ShieldCheck } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { FeelessMark, FeelessWordmark } from '../FeelessLogo';
import { useMarket } from '../../hooks/useMarket';
import { useWallet } from '../../hooks/useWallet';
import { formatUSD, shortAddress } from '../../lib/dexscreener';
import { Change, DataStatus } from './MarketPrimitives';
import { FlashValue } from './FlashValue';

const ITEMS = [
  ['', 'Home', Home], ['reputation', 'Reputation', ShieldCheck], ['trade', 'Trade', CandlestickChart], ['pump', 'Pump radar', Rocket],
  ['discover', 'Discover', Compass], ['launch', 'Launchpads', Rocket],
  ['watchlist', 'Watchlist', Star], ['chat', 'The Trenches', MessageCircle],
  ['alerts', 'Signal alerts', Bell], ['feeback', 'Fee-Back', Coins], ['fee', '$FEE', Activity], ['feecat', 'FeeCat', Cat], ['leaderboard', 'Leaderboard', Trophy], ['learn', 'Learn', BookOpen], ['roadmap', 'Roadmap', Map],
  ['whitepaper', 'Whitepaper', FileText], ['settings', 'Settings', Settings],
];

export const TerminalHeader = ({ onWallet, onProfile, onMenu, query = '' }) => {
  const { ecosystem } = useWorkspace();
  const { wallet } = useWallet();
  const [search, setSearch] = useState(query);
  const [dayMode, setDayMode] = useState(() => {
    try { return localStorage.getItem('feeless-theme') === 'day'; } catch { return false; }
  });
  const nav = useNavigate();
  const flipTheme = event => {
    const rect = event.currentTarget.getBoundingClientRect();
    document.documentElement.style.setProperty('--theme-flip-x', `${rect.left + rect.width / 2}px`);
    document.documentElement.style.setProperty('--theme-flip-y', `${rect.top + rect.height / 2}px`);
    document.body.classList.add('theme-flipping');
    setDayMode(value => !value);
    window.setTimeout(() => document.body.classList.remove('theme-flipping'), 650);
  };
  useEffect(() => {
    document.body.classList.toggle('theme-day', dayMode);
    document.documentElement.setAttribute('data-theme', dayMode ? 'light' : 'dark');
    document.documentElement.style.colorScheme = dayMode ? 'light' : 'dark';
    document.documentElement.style.backgroundColor = dayMode ? '#ffffff' : '';
    let meta = document.querySelector('meta[name="color-scheme"]');
    if (!meta) { meta = document.createElement('meta'); meta.name = 'color-scheme'; document.head.appendChild(meta); }
    meta.setAttribute('content', dayMode ? 'light' : 'dark');
    try { localStorage.setItem('feeless-theme', dayMode ? 'day' : 'night'); } catch {}
    return () => document.body.classList.remove('theme-day');
  }, [dayMode]);
  return <header className="terminal-header"><Link to="/" className="brand-link" data-testid="terminal-logo-link"><FeelessWordmark size={27} /></Link><form className="terminal-search" onSubmit={async e => { e.preventDefault(); const q = search.trim(); if (!q) return; if (/^@|^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$/.test(q)) { try { const r = await fetch(`/api/reputation/resolve/${encodeURIComponent(q)}`); if (r.ok) { const d = await r.json(); nav(`/terminal/profile/${d.address}`); return; } } catch { /* fall through to coin search */ } } nav(`/terminal/discover?q=${encodeURIComponent(q.replace(/^@/, ''))}`); }}><Search size={17} /><input data-testid="terminal-search-input" aria-label="Search tokens or contract address" placeholder={`${ecosystem.name} · search tokens or paste a contract…`} maxLength={120} value={search} onChange={e => setSearch(e.target.value)} /><button data-testid="terminal-search-submit" title="Search markets" type="submit"><ArrowUpRight size={16} /></button></form><div className="header-actions"><button className="icon-btn theme-toggle" data-testid="theme-toggle" title={dayMode ? 'Switch to night mode' : 'Switch to day mode'} aria-label={dayMode ? 'Switch to night mode' : 'Switch to day mode'} onClick={flipTheme}>{dayMode ? <Moon size={18} /> : <Sun size={18} />}</button><Link className="icon-btn" data-testid="header-alerts-link" title="Price alerts" to="/terminal/alerts"><Bell size={19} /></Link>{wallet && <button onClick={onProfile} className="icon-btn profile-trigger" data-testid="header-profile" title="Edit wallet profile" aria-label="Edit wallet profile"><UserRound size={18} /></button>}<button onClick={onWallet} className="btn-primary wallet-trigger" data-testid="header-connect-wallet"><Wallet size={16} /><span>{wallet ? shortAddress(wallet.address) : 'Connect Wallet'}</span></button><button onClick={onMenu} data-testid="terminal-menu-toggle" title="Toggle navigation" className="icon-btn"><Menu size={21} /></button></div></header>;
};

export const MarketTicker = () => {
  const { ecosystem } = useWorkspace();
  const ticker = { solana: 'SOL', ethereum: 'WETH', base: 'WETH', arbitrum: 'WETH', bsc: 'WBNB', avalanche: 'WAVAX', polygon: 'WPOL', sui: 'SUI' }[ecosystem.chainId];
  const { data } = useMarket(`/search?q=${ecosystem.chainId === 'solana' ? 'So11111111111111111111111111111111111111112' : ticker}`, 60000);
  const sol = data?.pairs?.filter(p => p.chainId === ecosystem.chainId && p.baseToken?.symbol === ticker).sort((a, b) => Number(b.liquidity?.usd || 0) - Number(a.liquidity?.usd || 0))[0];
  return <div className="market-ticker"><div><span className="sol-icon">≋</span><b data-testid="ticker-native-symbol">{ticker}</b><FlashValue raw={sol?.priceUsd}><strong className="mono" data-testid="ticker-native-price">{formatUSD(sol?.priceUsd)}</strong></FlashValue><Change value={sol?.priceChange?.h24} id="ticker-native-change" /></div><span className="ticker-divider" /><div><span>Coin 24h volume</span><FlashValue raw={sol?.volume?.h24}><b className="mono" data-testid="ticker-native-volume">{formatUSD(sol?.volume?.h24)}</b></FlashValue></div><span className="ticker-divider" /><div className="ticker-source"><span>DexScreener</span><DataStatus data={data} id="ticker-data-status" /></div><span className="ticker-motto">THE EDGE IS IN THE DETAILS.<span className="positive"> STAY EARLY.</span></span></div>;
};

const FeeCatNav = ({ onClose }) => {
  const location = useLocation();
  const [expanded, setExpanded] = useState(() => location.pathname.startsWith('/terminal/feecat'));
  const active = location.pathname.startsWith('/terminal/feecat');
  useEffect(() => { if (active) setExpanded(true); }, [active]);
  return <div className={`sidebar-feecat-group ${active ? 'active-group' : ''}`}>
    <div className="sidebar-feecat-row">
      <NavLink end to="/terminal/feecat" onClick={onClose} data-testid="nav-feecat" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}><Cat size={18} /><span>FeeCat</span></NavLink>
      <button type="button" className="sidebar-feecat-toggle" aria-label={expanded ? 'Collapse FeeCat menu' : 'Expand FeeCat menu'} aria-expanded={expanded} data-testid="nav-feecat-toggle" onClick={() => setExpanded(value => !value)}>{expanded ? '−' : '+'}</button>
    </div>
    {expanded && <div className="sidebar-feecat-subnav" data-testid="feecat-subnav">
      <NavLink end to="/terminal/feecat" onClick={onClose} data-testid="nav-feecat-home">Cat home</NavLink>
      <NavLink to="/terminal/feecat/cats" onClick={onClose} data-testid="nav-feeless-cats">Feeless Cats <span>50</span></NavLink>
      <NavLink to="/terminal/feecat/agents" onClick={onClose} data-testid="nav-feecat-agents">Create an agent <span>NEW</span></NavLink>
    </div>}
  </div>;
};

function SidebarProfileLink({ onClose }) {
  const { wallet } = useWallet() || {};
  if (!wallet?.address) return null;
  return <NavLink to={`/terminal/profile/${wallet.address}`} onClick={onClose} title="My profile" className={({ isActive }) => `sidebar-link sidebar-profile-link ${isActive ? 'active' : ''}`} data-testid="nav-my-profile"><UserRound size={18} /><span>My profile</span></NavLink>;
}

export const TerminalSidebar = ({ open, onClose, savedCount }) => {
  const [collapsed, setCollapsed] = React.useState(() => { try { return localStorage.getItem('feeless-nav-collapsed') === '1'; } catch { return false; } });
  React.useEffect(() => {
    document.body.classList.toggle('nav-collapsed', collapsed);
    try { localStorage.setItem('feeless-nav-collapsed', collapsed ? '1' : '0'); } catch {}
  }, [collapsed]);
  return <><aside className={`terminal-sidebar ${open ? 'sidebar-open' : ''} ${collapsed ? 'is-collapsed' : ''}`} data-testid="terminal-sidebar"><button type="button" className="nav-collapse-toggle" onClick={() => setCollapsed(c => !c)} title={collapsed ? 'Expand navigation' : 'Collapse navigation'} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'} data-testid="nav-collapse-toggle">{collapsed ? '»' : '«'}</button><SidebarProfileLink onClose={onClose} /><div className="sidebar-section-label">WORKSPACE<button title="Close navigation" className="mobile-close" onClick={onClose} data-testid="sidebar-close"><X size={17} /></button></div><nav>{ITEMS.map(([path, title, Icon]) => <React.Fragment key={path}>{path === 'feeback' && <div className="sidebar-section-label secondary-label">THE ECOSYSTEM</div>}{path === 'feecat' ? <FeeCatNav onClose={onClose} /> : <NavLink end to={`/terminal${path ? `/${path}` : ''}`} onClick={onClose} title={title} data-testid={`nav-${path || 'home'}`} className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}><Icon size={18} /><span className={path === 'chat' ? 'trenches-font' : undefined}>{title}</span>{path === 'pump' && <span className="nav-hot">HOT</span>}{path === 'reputation' && <span className="nav-hot">NEW</span>}{path === 'watchlist' && savedCount > 0 && <span className="nav-count" data-testid="watchlist-count">{savedCount}</span>}</NavLink>}</React.Fragment>)}</nav><div className="sidebar-bottom"><FeelessMark size={50} /><strong>A little less noise.<br /><span>A lot more signal.</span></strong><Link data-testid="sidebar-globe-link" to="/"><Globe2 size={14} />Explore the globe<ArrowUpRight size={13} /></Link><small>YOUR NEXT MOVE STARTS HERE.</small></div></aside>{open && <button className="sidebar-overlay" data-testid="sidebar-overlay" aria-label="Close navigation" onClick={onClose} />}</>;
};

export const TerminalFooter = () => <footer className="terminal-footer"><span>© {new Date().getFullYear()} FEELESS</span><span>Non-custodial · Solana routing via Jupiter · Fee-Back planned</span><Link to="/terminal/whitepaper" data-testid="footer-whitepaper">Whitepaper / PDF ↗</Link></footer>;