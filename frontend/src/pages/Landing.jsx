import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Rocket, Globe2, ArrowRight, ShieldCheck } from 'lucide-react';
import Globe3D from '../components/Globe3D';
import EcosystemWorld from '../components/EcosystemWorld';
import WalletModal from '../components/WalletModal';
import { TerminalHeader, MarketTicker } from '../components/terminal/TerminalShell';
import { ECOSYSTEMS, getEcosystem } from '../lib/ecosystems';
import { LAUNCHPADS, launchpadEcosystem } from '../lib/launchpads';
import { useWorkspace } from '../hooks/useWorkspace';
import { ContextBar, MouseGlow } from '../components/command/WorkspaceChrome';
import LaunchpadLogo from '../components/LaunchpadLogo';

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
  const [worldOpen, setWorldOpen] = useState(false);
  // Old /?coin= links open the Trenches chart; a coin clicked on the globe opens its network's war room with that coin charted.
  const navigate = useNavigate();
  const [worldPair, setWorldPair] = useState(null);
  const openCoin = t => { const chain = t?.chain || t?.chainId; const pair = t?.pairAddress || t?.address; if (chain && /^[A-Za-z0-9]{20,64}$/.test(pair || '')) navigate(`/terminal/chat?chain=${chain}&pair=${pair}&room=bulls`); };
  const openGlobeCoin = t => {
    const node = t?.chain === 'bsc' ? 'bnb' : t?.chain;
    if (!getEcosystem(node) || !t?.pairAddress) return;
    setWorldPair({ chainId: t.chain, pairAddress: t.pairAddress });
    setSelected(node); setWorldOpen(true);
  };
  useEffect(() => { const [chain, pairAddress] = (params.get('coin') || '').split(':'); if (chain && pairAddress) openCoin({ chain, pairAddress }); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const pad = LAUNCHPADS.find(p => p.id === selected);
  const ecosystem = pad ? launchpadEcosystem(pad) : getEcosystem(selected);
  const openWorld = id => {
    setWorldPair(null);
    setSelected(id);
    setWorldOpen(true);
  };
  return <div className="globe-page"><p className="sr-only" role="status" aria-live="polite" data-testid="globe-ecosystem-announcement">{ecosystemAnnouncement}</p><MouseGlow /><TerminalHeader onWallet={() => setWalletOpen(true)} onMenu={() => setMenu(v => !v)} /><MarketTicker /><ContextBar />
    {menu && <nav className="landing-menu" data-testid="landing-menu">{[['/terminal', 'The terminal'], ['/terminal/launch', 'Launchpads'], ['/terminal/whitepaper', 'Whitepaper']].map(([path, title]) => <Link data-testid={`landing-menu-${title.replace(/\s/g, '-').toLowerCase()}`} to={path} key={path}>{title}<ArrowUpRight size={15} /></Link>)}</nav>}
      <main className="globe-layout"><div className="globe-main"><div className="globe-stage"><div className="landing-copy"><span className="eyebrow"><span className="live-dot" /> THE TRUST LAYER FOR EVERY CHAIN, EVERY LAUNCHPAD.</span><h1>In a FEELESS world,<br /><FeelessWorldLine /></h1><p>Every ecosystem. Every launchpad. One creator reputation graph that remembers every rug, no matter which meta is hot this week.</p><Link className="btn-primary globe-terminal-cta" to="/terminal" data-testid="enter-terminal">Enter the terminal<ArrowUpRight size={17} /></Link><Link className="landing-reputation-cta" to="/terminal/reputation" data-testid="landing-reputation">See the reputation graph<ShieldCheck size={13} /></Link><Link className="landing-whitepaper" to="/terminal/whitepaper" data-testid="landing-whitepaper">Read the whitepaper<ArrowRight size={13} /></Link><div className="globe-legend"><span><i className="legend-chain" />ECOSYSTEM</span><span><i className="legend-launch" />LAUNCHPAD</span><span><i className="legend-token" />$10M+ TOKEN</span></div></div><div className="landing-globe"><Globe3D onSelect={openWorld} onToken={openGlobeCoin} selectedId={selected} size={860} /><div className="globe-coordinate-label">GLOBAL ON-CHAIN NETWORK<span>14 CONNECTED NODES</span></div></div></div>
         <section className="node-directory"><div className="node-directory-heading"><div className="node-group-switch"><button data-testid="globe-filter-launchpads" onClick={() => setGroup('launchpads')} className={group === 'launchpads' ? 'active' : ''}><Rocket size={14} />Launchpads</button><button data-testid="globe-filter-ecosystems" onClick={() => setGroup('ecosystems')} className={group === 'ecosystems' ? 'active' : ''}><Globe2 size={14} />Ecosystems</button></div><Link to="/terminal/launch" data-testid="globe-launchpads-directory">Open directory<ArrowUpRight size={13} /></Link></div><div className="node-chips">{(group === 'launchpads' ? LAUNCHPADS : ECOSYSTEMS.filter(e => !e.isFeeless)).map(e => <button data-testid={`globe-node-${e.id}`} key={e.id} onClick={() => openWorld(e.id)} className={selected === e.id ? 'active' : ''} style={{ '--node-color': e.color }}><LaunchpadLogo launchpad={e} size={30} /><span>{e.name}<small>{group === 'launchpads' ? e.chainId === 'bsc' ? 'BNB Chain' : 'Solana' : 'Ecosystem'}</small></span><ArrowUpRight size={12} /></button>)}</div><div className="globe-bottom-note"><span>REAL MARKETS. REAL COMMUNITY. NO MADE-UP ALPHA.</span><span>Explore freely. Verify independently.</span></div></section>
           </div></main>{worldOpen && ecosystem && <EcosystemWorld ecosystem={ecosystem} pad={pad} initialPair={worldPair} onClose={() => setWorldOpen(false)} />}<WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} />
  </div>;
}

// The second line of the hero: what a FEELESS world means, one truth at a time.
const WORLD_LINES = ['every rug is remembered.', 'trust compounds.', 'trading into $FEE costs nothing.', 'snipers get caught on-chain.', 'your wallet is your reputation.', 'you stay early, safely.'];
function FeelessWorldLine() {
  const [i, setI] = React.useState(0);
  React.useEffect(() => { const t = setInterval(() => setI(x => (x + 1) % WORLD_LINES.length), 3200); return () => clearInterval(t); }, []);
  return <span key={i} className="world-line">{WORLD_LINES[i]}</span>;
}
