import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Coins, Filter, Globe2, Gauge, LockKeyhole, Rocket, Search, ShieldCheck, Waves } from 'lucide-react';
import { LAUNCHPADS } from '../../lib/launchpads';
import { useWorkspace } from '../../hooks/useWorkspace';
import LaunchpadLogo from '../LaunchpadLogo';

const GUIDE = [
  { icon: Coins, number: '01', title: 'Token identity', body: 'Name, ticker, public image, and whole-token supply. This is what traders see before they connect.' },
  { icon: Gauge, number: '02', title: 'Bonding curve', body: 'Set the opening market cap, curve shape, and graduation target. Price discovery stays explicit.' },
  { icon: Waves, number: '03', title: 'Pool graduation', body: 'Choose SOL or USDC, pick the Raydium destination, and keep graduated liquidity permanently locked.' },
  { icon: ShieldCheck, number: '04', title: 'Fee routing', body: 'Declare the swap fee split before signing. Creator, holders, and buyback-and-burn must total 100%.' },
  { icon: LockKeyhole, number: '05', title: 'Opening protection', body: 'Add a visible anti-sniper window and tax. It fades on schedule instead of hiding behind a private wallet.' },
  { icon: Rocket, number: '06', title: 'Community release', body: 'Reserve holder supply and name airdrop recipients before the provider prepares any transaction.' },
];

const VENUE_FEATURES = {
  pump: ['Curve-first launch', 'Fast community discovery'],
  bonk: ['Community-native', 'BONK ecosystem'],
  raydium: ['CPMM / CLMM paths', 'Deep liquidity rail'],
  meteora: ['Dynamic liquidity', 'Managed market depth'],
  moonit: ['Fair-launch flow', 'Community distribution'],
  four: ['BNB Chain native', 'Meme launch discovery'],
};
const VENUES = LAUNCHPADS.filter(p => !p.isFeelessLaunch);

export const LaunchpadDirectory = () => {
  const { setEcosystem } = useWorkspace(); const nav = useNavigate();
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const feeless = LAUNCHPADS.find(p => p.isFeelessLaunch);
  const filteredVenues = useMemo(() => VENUES.filter(p => {
    const matchesFilter = filter === 'all' || (filter === 'solana' ? p.chainId === 'solana' : p.chainId === 'bsc');
    const matchesQuery = !query.trim() || `${p.name} ${p.tag} ${p.description}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesFilter && matchesQuery;
  }), [filter, query]);
  const openMetaLaunch = () => { setEcosystem(feeless.id); nav('/terminal/launch?setup=feeless'); };
  return <div className="directory-page launchpad-directory">
    <div className="page-heading launchpad-page-heading">
      <div><span className="eyebrow">THE LAUNCHPAD RADAR</span><h1>Launch without the noise.</h1><p>Compare the rails, see what each one actually does, then open a real market context. FEELESS is the only flow that lets you review every mechanic before a wallet approval.</p></div>
      <div className="launchpad-directory-signal"><span><b>{LAUNCHPADS.length}</b><small>tracked rails</small></span><span><b>06</b><small>FEELESS boxes</small></span><span><b>100%</b><small>fee route check</small></span></div>
    </div>
    <section className="feeless-launch-hero" data-testid="feeless-launch-hero">
      <div className="launchpad-hero-copy"><div className="launchpad-hero-title"><LaunchpadLogo launchpad={feeless} size={62} /><div><span className="eyebrow"><Rocket size={13} /> FEELESS NATIVE META LAUNCHPAD</span><h2>Build the launch. Show the receipts.</h2></div></div><p>A pump.fun-speed creation flow with Infinity-style visibility and Raydium-ready graduation. Every box has a job: identity, curve, pool, fee routing, protection, and community release.</p><div className="launchpad-hero-meta"><span><i />Wallet signs only after review</span><span><i />Permanent liquidity by default</span><span><i />No fake launch status</span></div></div>
      <button className="btn-primary launchpad-hero-cta" data-testid="launchpad-warroom-feeless-launch" onClick={openMetaLaunch}>Build on FEELESS<ArrowUpRight size={16} /></button>
    </section>
    <section className="launchpad-guide" id="launchpad-steps" data-testid="launchpad-guide"><div className="launchpad-guide-heading"><div><span className="eyebrow">HOW THE NATIVE FLOW WORKS</span><h2>Six boxes. One accountable launch.</h2></div><Link to="/terminal/whitepaper" data-testid="launchpad-guide-whitepaper-link">Read the why before you fill the what.<ArrowRight size={12} /></Link></div><div className="launchpad-guide-grid">{GUIDE.map(({ icon: Icon, number, title, body }) => <article key={number} className="launchpad-guide-card"><span className="launchpad-guide-number">{number}</span><Icon size={18} /><h3>{title}</h3><p>{body}</p></article>)}</div></section>
    <section className="launchpad-venue-toolbar" data-testid="launchpad-venue-toolbar"><div className="launchpad-venue-heading"><span className="eyebrow">OTHER LAUNCH RAILS</span><h2>Use the rail that fits the move.</h2></div><label className="launchpad-search"><Search size={14} /><input aria-label="Search launchpads" placeholder="Search launchpads" value={query} onChange={event => setQuery(event.target.value)} /></label><div className="launchpad-filters"><Filter size={13} />{[['all', 'All rails'], ['solana', 'Solana'], ['bsc', 'BNB Chain']].map(([id, label]) => <button key={id} type="button" className={filter === id ? 'active' : ''} data-testid={`launchpad-filter-${id}`} onClick={() => setFilter(id)}>{label}</button>)}</div></section>
    <div className="launchpad-grid">{filteredVenues.map(p => <article className="launchpad-card" key={p.id} style={{ '--pad-color': p.color }} data-testid={`launchpad-card-${p.id}`}><div className="launchpad-card-top"><LaunchpadLogo launchpad={p} size={52} /><span className="pad-tag">{p.tag}</span></div><h2>{p.name}</h2><p>{p.description}</p><div className="pad-feature-list">{(VENUE_FEATURES[p.id] || ['Provider indexed', 'Open market context']).map(feature => <span key={feature}><i />{feature}</span>)}</div><div className="pad-chain"><i />{p.chainId === 'bsc' ? 'BNB Chain' : 'Solana'}<span>Provider indexed</span></div><button className="btn-primary launchpad-warroom" data-testid={`launchpad-warroom-${p.id}`} onClick={() => { setEcosystem(p.id); nav('/terminal'); }}>Open market context<ArrowRight size={15} /></button><div className="pad-links">{p.url ? <a href={p.url} target="_blank" rel="noreferrer" data-testid={`launchpad-visit-${p.id}`}>Visit platform<ArrowUpRight size={16} /></a> : <span className="provider-note" data-testid={`launchpad-visit-unavailable-${p.id}`}>Platform unavailable</span>}<Link to={`/?node=${p.id}`} data-testid={`launchpad-globe-${p.id}`} title="Locate on the globe"><Globe2 size={17} /></Link></div></article>)}</div>{!filteredVenues.length && <div className="truth-empty" data-testid="launchpad-empty">No launch rails match that filter.</div>}<p className="provider-note launchpad-disclosure"><ShieldCheck size={13} /> Venue coverage is provider-limited. A provider match is not a security endorsement, bonding-curve status, or migration confirmation.</p>
  </div>;
};