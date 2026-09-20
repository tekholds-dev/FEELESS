import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, Radio, Rocket, Compass, Star, BarChart3, ArrowUpRight } from 'lucide-react';
import EcosystemChat from '../EcosystemChat';
import { useWorkspace } from '../../hooks/useWorkspace';
import { AlphaTape } from '../command/WorkspaceChrome';
import { TokenAvatar, Change } from './MarketPrimitives';
import { formatUSD, pairKey } from '../../lib/dexscreener';

export const ChatRoom = ({ large = false }) => {
  const { ecosystem } = useWorkspace();
  const [channel, setChannel] = useState('general');
  return <section className={`community-chat ${large ? 'large-chat' : ''}`}><div className="section-title"><h2><MessageCircle size={18} />The Trenches</h2><span className="positive small" data-testid="chat-active-ecosystem">{ecosystem.name}</span></div><div className="chat-tabs">{['general', 'alpha', 'launches', 'trading', 'whales', 'new-pools'].map(t => <button key={t} data-testid={`chat-tab-${t}`} onClick={() => setChannel(t)} className={channel === t ? 'active' : ''}>{t.replace('-', ' ')}</button>)}</div><EcosystemChat key={`${ecosystem.id}-${channel}`} compact ecosystem={{ id: `${ecosystem.id}-${channel}`, name: `${ecosystem.name} / ${channel}` }} /></section>;
};

export const CommunityRail = ({ pairs, onSelect }) => {
  const [filter, setFilter] = useState('all');
  const filtered = pairs.filter(p => filter !== 'gainers' || Number(p.priceChange?.h24) > 0).slice(0, 5);
  return <aside className="community-rail"><ChatRoom /><section className="activity-section"><div className="section-title"><h2><Radio size={17} />On the radar</h2><select aria-label="Activity filter" data-testid="activity-filter" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All pools</option><option value="gainers">Gainers</option></select></div><div>{filtered.map(p => <button key={pairKey(p)} className="radar-item" data-testid={`radar-token-${pairKey(p)}`} onClick={() => onSelect(p)}><TokenAvatar pair={p} size={31} /><span><b>{p.baseToken?.symbol}</b><small>{p.dexId} · {formatUSD(p.volume?.h24)} vol</small></span><Change value={p.priceChange?.h24} id={`radar-change-${pairKey(p)}`} /></button>)}{!filtered.length && <p className="provider-note" data-testid="radar-empty">No matching activity in this feed.</p>}</div><Link className="section-more" data-testid="radar-view-all" to="/terminal/discover">All markets <ArrowUpRight size={13} /></Link></section><section className="quick-actions"><div className="section-title"><h2>Move with intent.</h2><ArrowUpRight size={15} /></div><div className="quick-grid">{[['pump', 'Pump', 'New pools', Rocket], ['discover', 'Discover', 'Find your edge', Compass], ['launch', 'Launch', 'Pick a launchpad', BarChart3], ['watchlist', 'Watchlist', 'Keep them close', Star]].map(([path, title, sub, Icon]) => <Link data-testid={`quick-${path}`} key={path} to={`/terminal/${path}`}><Icon size={19} /><span><b>{title}</b><small>{sub}</small></span></Link>)}</div></section><div className="risk-note"><span>DYOR, ALWAYS.</span>Tokens are unverified. New pools can be illiquid, manipulated, or malicious. Nothing here is financial advice.</div></aside>;
};