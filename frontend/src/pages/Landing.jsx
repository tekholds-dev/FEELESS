import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Rocket, Globe2, ArrowRight } from 'lucide-react';
import Globe3D from '../components/Globe3D';
import EcosystemWorld from '../components/EcosystemWorld';
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
  const setSelected = id => { updateSelected(id); if (id) setEcosystem(id); };
  useEffect(() => { if (params.get('node')) setEcosystem(params.get('node')); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [group, setGroup] = useState('ecosystems');
  const [walletOpen, setWalletOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const pad = LAUNCHPADS.find(p => p.id === selected);
  const ecosystem = pad ? launchpadEcosystem(pad) : getEcosystem(selected);

  return <div className={`globe-page globe-cinematic ${ecosystem ? 'world-open' : ''}`}><MouseGlow />
    <TerminalHeader onWallet={() => setWalletOpen(true)} onMenu={() => setMenu(v => !v)} /><MarketTicker /><ContextBar />
    {menu && <nav className="landing-menu" data-testid="landing-menu">{[['/terminal', 'The terminal'], ['/terminal/launch', 'Launchpads'], ['/terminal/whitepaper', 'Whitepaper']].map(([path, title]) => <Link data-testid={`landing-menu-${title.replace(/\s/g, '-').toLowerCase()}`} to={path} key={path}>{title}<ArrowUpRight size={15} /></Link>)}</nav>}

    <main className="globe-cinema" data-testid="globe-hero">
      <div className="globe-cinema-stage">
        <Globe3D onSelect={setSelected} selectedId={selected} size={760} />
        <div className="globe-cinema-copy">
          <span className="eyebrow"><span className="live-dot" /> ONE WORLD · ALL THE OPPORTUNITY</span>
          <h1>Where degens<br />come <span>alive.</span></h1>
          <p>Tap any world. Drop into its live chat,<br />see what's fresh, feel the flow.</p>
          <div className="globe-cinema-cta">
            <Link className="btn-primary" to="/terminal" data-testid="enter-terminal">Enter the terminal<ArrowUpRight size={16} /></Link>
            <Link className="landing-whitepaper" to="/terminal/whitepaper" data-testid="landing-whitepaper">Whitepaper<ArrowRight size={13} /></Link>
          </div>
        </div>
        <div className="globe-cinema-hint" data-testid="globe-hint">CLICK A NODE TO STEP INSIDE ITS WORLD</div>
      </div>

      <section className="node-dock" data-testid="node-dock">
        <div className="node-dock-head">
          <div className="node-group-switch">
            <button data-testid="globe-filter-ecosystems" onClick={() => setGroup('ecosystems')} className={group === 'ecosystems' ? 'active' : ''}><Globe2 size={14} />Ecosystems</button>
            <button data-testid="globe-filter-launchpads" onClick={() => setGroup('launchpads')} className={group === 'launchpads' ? 'active' : ''}><Rocket size={14} />Launchpads</button>
          </div>
          <Link to="/terminal/launch" data-testid="globe-launchpads-directory">Open directory<ArrowUpRight size={13} /></Link>
        </div>
        <div className="node-chips">{(group === 'launchpads' ? LAUNCHPADS : ECOSYSTEMS.filter(e => !e.isFeeless)).map(e => <button data-testid={`globe-node-${e.id}`} key={e.id} onClick={() => setSelected(e.id)} className={selected === e.id ? 'active' : ''} style={{ '--node-color': e.color }}><span className="node-initial">{e.symbol.slice(0, 1)}</span><span>{e.name}<small>{group === 'launchpads' ? e.chainId === 'bsc' ? 'BNB Chain' : 'Solana' : 'Ecosystem'}</small></span><ArrowUpRight size={12} /></button>)}</div>
        <div className="globe-bottom-note"><span>REAL MARKETS · REAL COMMUNITY · NO MADE-UP ALPHA</span><span>Explore freely. Verify independently.</span></div>
      </section>
    </main>

    {ecosystem && <EcosystemWorld ecosystem={ecosystem} pad={pad} onClose={() => setSelected(null)} />}
    <WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} />
  </div>;
}
