import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, ArrowUpRight, Rocket, Radio, Compass, Sparkles, Cat, Infinity as InfinityIcon } from 'lucide-react';
import EcosystemChat from './EcosystemChat';
import NewStuffFeed from './NewStuffFeed';
import { useMarket } from '../hooks/useMarket';

// Blur-reveal immersive ecosystem "world": chat on the LEFT, blurred globe behind,
// live activity pulse + new-stuff feed + onboarding + minimal quick links on the RIGHT.
export default function EcosystemWorld({ ecosystem, pad, onClose }) {
  const [layout, setLayout] = useState('balanced');
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [onClose]);

  const room = `${ecosystem.id}-general`;
  const { data: community } = useMarket(`/api/intelligence/community?context=${ecosystem.id}`, 30000);
  const { data: online } = useMarket(`/api/chat/${room}/online`, 20000);
  const inRoom = online?.online ?? online?.count ?? online?.users?.length;
  const fresh = useMarket(`/feed?kind=new&chain=${ecosystem.chainId}`, 60000);
  const freshCount = fresh.data?.pairs?.length;

  const pulse = [
    ['IN THE ROOM', inRoom ?? '—', 'recent posters'],
    ['MESSAGES / 7D', community?.messages ?? '—', 'community activity'],
    ['FRESH TODAY', freshCount ?? '—', 'new indexed markets'],
    ['NETWORK', ecosystem.chainId.toUpperCase(), 'live link'],
  ];

  const links = [
    pad && ['Launchpad', pad.url, Rocket],
    ecosystem.dex && ['DEX', ecosystem.dex, Compass],
    ecosystem.explorer && ['Explorer', ecosystem.explorer, Radio],
  ].filter(Boolean);

  return <div className="eco-world" role="dialog" aria-modal="true" aria-label={`${ecosystem.name} network room`} data-testid="ecosystem-world" style={{ '--eco-accent': ecosystem.color }}>
    <div className="eco-world-scrim" onClick={onClose} aria-hidden="true" />
    <div className={`eco-world-inner eco-layout-${layout} ${expanded ? 'is-expanded' : ''}`}>
      <header className="eco-world-head">
        <div className="eco-world-id">
          <span className="eco-dot" style={{ background: ecosystem.color }} />
          <span className="eco-network-mark" aria-hidden="true">{ecosystem.symbol?.slice(0, 1) || ecosystem.name.slice(0, 1)}</span><div><small>YOU'RE INSIDE</small><h2 data-testid="eco-world-name">{ecosystem.name} {ecosystem.isLaunchpad ? 'WAR ROOM' : 'NETWORK'}</h2></div>
        </div>
        <div className="eco-world-head-actions">
          <Link className="eco-enter-terminal" to="/terminal" data-testid="eco-world-enter-terminal">Enter {ecosystem.name} terminal<ArrowUpRight size={14} /></Link>
          <div className="eco-layout-controls" role="group" aria-label="Network room layout">
            <span>LAYOUT</span>
            {[['balanced', 'Balanced'], ['chat-first', 'Chat first'], ['feed-first', 'Feed first']].map(([id, label]) => <button type="button" key={id} className={layout === id ? 'active' : ''} aria-pressed={layout === id} data-testid={`eco-layout-${id}`} onClick={() => setLayout(id)}>{label}</button>)}
            <button type="button" className="eco-expand-toggle" data-testid="eco-layout-expand" aria-pressed={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? 'Exit expanded' : 'Expand window'}</button>
          </div>
          <button className="eco-world-close" title="Close" data-testid="eco-world-close" onClick={onClose}><X size={18} /></button>
        </div>
      </header>

      <div className="eco-world-grid">
        <div className="eco-chat-col" data-testid="eco-world-chat">
          <div className="eco-chat-label"><Radio size={13} /> LIVE COMMUNITY · #{room}</div>
          <EcosystemChat key={room} ecosystem={{ ...ecosystem, id: room, name: ecosystem.name }} />
        </div>

        <div className="eco-right-col custom-scroll">
          <div className="activity-pulse" data-testid="eco-activity-pulse">
            {pulse.map(([label, value, sub]) => <div className="pulse-pill" key={label}>
              <small><i />{label}</small>
              <strong data-testid={`eco-pulse-${label.split(' ')[0].toLowerCase()}`}>{value}</strong>
              <em>{sub}</em>
            </div>)}
          </div>

          <div className="eco-idea-card" data-testid="eco-idea-card">
            <span className="eco-idea-eyebrow"><Sparkles size={12} /> NEW HERE? THE IDEA</span>
            <p><b>FEELESS</b> is where every chain becomes one social floor. Same transactions, zero platform fees — <span>more for you.</span></p>
            <div className="eco-idea-row">
              <div><Cat size={15} /><b>FeeCat</b><small>The zero-fee router mascot — routes liquidity & burns fees.</small></div>
              <div><InfinityIcon size={15} /><b>Fee-Back</b><small>Trading rebates flow back to your wallet & $FEE liquidity.</small></div>
            </div>
          </div>

          <div className="eco-section-label"><Sparkles size={13} /> WHAT'S NEW ON {ecosystem.name.toUpperCase()}</div>
          <NewStuffFeed ecosystem={ecosystem} />
        </div>
      </div>

      {links.length > 0 && <div className="eco-quick-dock" data-testid="eco-quick-dock">
        {links.map(([label, url, Icon]) => <a key={label} href={url} target="_blank" rel="noreferrer" data-testid={`eco-quick-${label.toLowerCase()}`} title={label}><Icon size={13} /><span>{label}</span></a>)}
      </div>}
    </div>
  </div>;
}
