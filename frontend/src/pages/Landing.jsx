import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Rocket, Globe2, X, ArrowRight } from 'lucide-react';
import Globe3D from '../components/Globe3D';
import EcosystemChat from '../components/EcosystemChat';
import TopCoins from '../components/TopCoins';
import EcosystemPlatforms from '../components/EcosystemPlatforms';
import WalletModal from '../components/WalletModal';
import { TerminalHeader, MarketTicker } from '../components/terminal/TerminalShell';
import { ECOSYSTEMS, getEcosystem } from '../lib/ecosystems';
import { LAUNCHPADS, launchpadEcosystem } from '../lib/launchpads';
import { useWorkspace } from '../hooks/useWorkspace';
import { ContextBar, MouseGlow } from '../components/command/WorkspaceChrome';

export default function Landing() {
  const [params] = useSearchParams();
  const { setEcosystem } = useWorkspace();
  const [selected, updateSelected] = useState(params.get('node'));
  const [ecosystemAnnouncement, setEcosystemAnnouncement] = useState('');
  const setSelected = id => {
    updateSelected(id);
    if (!id) {
      setEcosystemAnnouncement('');
      return;
    }
    setEcosystem(id);
    const nextPad = LAUNCHPADS.find(p => p.id === id);
    const nextEcosystem = nextPad ? launchpadEcosystem(nextPad) : getEcosystem(id);
    if (nextEcosystem) {
      setEcosystemAnnouncement(`${nextEcosystem.name} selected. Top coins and New coins feeds are active.`);
    }
  };
  useEffect(() => { if (params.get('node')) setEcosystem(params.get('node')); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [group, setGroup] = useState('launchpads');
  const [walletOpen, setWalletOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [mobileRadar, setMobileRadar] = useState(() => typeof window !== 'undefined' && window.matchMedia?.('(max-width: 760px)').matches);
  const [radarOpen, setRadarOpen] = useState(false);
  const pad = LAUNCHPADS.find(p => p.id === selected);
  const ecosystem = pad ? launchpadEcosystem(pad) : getEcosystem(selected);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const syncMobileRadar = () => setMobileRadar(media.matches);
    syncMobileRadar();
    media.addEventListener?.('change', syncMobileRadar);
    return () => media.removeEventListener?.('change', syncMobileRadar);
  }, []);
  const radarIsOpen = mobileRadar || radarOpen;
  const toggleRadar = () => setRadarOpen(open => mobileRadar || !open);
  return <div className="globe-page"><p className="sr-only" role="status" aria-live="polite" data-testid="globe-ecosystem-announcement">{ecosystemAnnouncement}</p><MouseGlow /><TerminalHeader onWallet={() => setWalletOpen(true)} onMenu={() => setMenu(v => !v)} /><MarketTicker /><ContextBar />
    {menu && <nav className="landing-menu" data-testid="landing-menu">{[['/terminal', 'The terminal'], ['/terminal/launch', 'Launchpads'], ['/terminal/whitepaper', 'Whitepaper']].map(([path, title]) => <Link data-testid={`landing-menu-${title.replace(/\s/g, '-').toLowerCase()}`} to={path} key={path}>{title}<ArrowUpRight size={15} /></Link>)}</nav>}
    <main className={`globe-layout ${ecosystem ? 'with-panel' : ''}`}><div className="globe-main"><div className="globe-stage"><div className="landing-copy"><span className="eyebrow"><span className="live-dot" /> ONE WORLD. ALL THE OPPORTUNITY.</span><h1>Find the meta.<br />Follow the flow.<br /><span>Stay early.</span></h1><p>Every ecosystem. Your favourite launchpads.<br />One connected degen universe.</p><Link className="btn-primary globe-terminal-cta" to="/terminal" data-testid="enter-terminal">Enter the terminal<ArrowUpRight size={17} /></Link><Link className="landing-whitepaper" to="/terminal/whitepaper" data-testid="landing-whitepaper">Read the whitepaper<ArrowRight size={13} /></Link><div className="globe-legend"><span><i className="legend-chain" />ECOSYSTEM</span><span><i className="legend-launch" />LAUNCHPAD</span></div></div><div className="landing-globe"><Globe3D onSelect={setSelected} selectedId={selected} size={680} /><div className="globe-coordinate-label">GLOBAL ON-CHAIN NETWORK<span>14 CONNECTED NODES</span></div></div></div>
      <section className="node-directory"><div className="node-directory-heading"><div className="node-group-switch"><button data-testid="globe-filter-launchpads" onClick={() => setGroup('launchpads')} className={group === 'launchpads' ? 'active' : ''}><Rocket size={14} />Launchpads</button><button data-testid="globe-filter-ecosystems" onClick={() => setGroup('ecosystems')} className={group === 'ecosystems' ? 'active' : ''}><Globe2 size={14} />Ecosystems</button></div><Link to="/terminal/launch" data-testid="globe-launchpads-directory">Open directory<ArrowUpRight size={13} /></Link></div><div className="node-chips">{(group === 'launchpads' ? LAUNCHPADS : ECOSYSTEMS.filter(e => !e.isFeeless)).map(e => <button data-testid={`globe-node-${e.id}`} key={e.id} onClick={() => setSelected(e.id)} className={selected === e.id ? 'active' : ''} style={{ '--node-color': e.color }}><span className="node-initial">{e.symbol.slice(0, 1)}</span><span>{e.name}<small>{group === 'launchpads' ? e.chainId === 'bsc' ? 'BNB Chain' : 'Solana' : 'Ecosystem'}</small></span><ArrowUpRight size={12} /></button>)}</div><div className="globe-bottom-note"><span>REAL MARKETS. REAL COMMUNITY. NO MADE-UP ALPHA.</span><span>Explore freely. Verify independently.</span></div></section>
       </div>{ecosystem && <aside className="degen-panel" data-testid="degen-panel"><div className="degen-panel-title"><span style={{ background: ecosystem.color }} /><div><small>CONNECTED TO</small><h2 data-testid="degen-panel-name">{ecosystem.name}</h2></div><button title="Close ecosystem panel" data-testid="degen-panel-close" onClick={() => setSelected(null)}><X size={18} /></button></div><Link className="btn-primary globe-terminal-cta degen-enter-context" data-testid="degen-enter-terminal" to="/terminal">Enter {ecosystem.name} command<ArrowUpRight size={15} /></Link>{pad && pad.url && <a data-testid="degen-launchpad-open" className="btn-outline" href={pad.url} target={pad.url.startsWith('/') ? '_self' : '_blank'} rel="noreferrer"><Rocket size={15} />Open {pad.name}<ArrowUpRight size={15} /></a>}<div className="degen-chat"><EcosystemChat key={ecosystem.id} ecosystem={{ ...ecosystem, id: `${ecosystem.id}-general` }} /></div><div className={`degen-coins-rail ${radarIsOpen ? 'is-open' : ''}`} data-testid="degen-coins-rail"><button type="button" className="degen-coins-tab" data-testid="degen-coins-toggle" aria-controls={`degen-coins-popover-${ecosystem.id}`} aria-expanded={radarIsOpen} aria-label={`${radarIsOpen ? 'Close' : 'Open'} coin radar feeds`} onClick={toggleRadar} onFocus={() => setRadarOpen(true)}><b>COIN RADAR</b><small>{radarIsOpen ? 'Close feeds' : 'Open feeds'}</small></button><div className="degen-coins-popover" id={`degen-coins-popover-${ecosystem.id}`}><div className="degen-coins"><TopCoins key={ecosystem.id} ecosystem={ecosystem} /></div></div></div><EcosystemPlatforms ecosystem={ecosystem} /></aside>}</main><WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} />
  </div>;
}