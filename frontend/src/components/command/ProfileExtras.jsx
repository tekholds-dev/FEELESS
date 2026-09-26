import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiUrl } from '../../lib/api';

export function usePerks(address) {
  const [d, setD] = useState(null);
  useEffect(() => { if (!address) return; fetch(apiUrl(`/api/reputation/perks/${address}`)).then(r => r.json()).then(setD).catch(() => {}); }, [address]);
  return d;
}

const ago = ts => { const days = (Date.now() / 1000 - ts) / 86400; return days < 1 ? 'today' : days < 60 ? `${Math.floor(days)}d` : days < 730 ? `${Math.floor(days / 30)}mo` : `${(days / 365).toFixed(1)}y`; };

// Real on-chain stats — every wallet has a profile before it ever sets one up.
export function OnchainStrip({ address }) {
  const [s, setS] = useState(null);
  useEffect(() => { fetch(apiUrl(`/api/reputation/wallet-stats/${address}`)).then(r => r.json()).then(setS).catch(() => setS({})); }, [address]);
  if (!s) return <div className="wp-onchain loading" data-testid="onchain-strip"><span>Reading the chain…</span></div>;
  if (!s.supported) return <div className="wp-onchain" data-testid="onchain-strip"><span><small>Chain</small><b>{s.chain === 'evm' ? 'EVM' : '—'}</b></span></div>;
  return <div className="wp-onchain" data-testid="onchain-strip">
    <span><small>SOL</small><b>{s.sol != null ? s.sol.toFixed(3) : '—'}</b></span>
    <span><small>Tokens held</small><b>{s.tokensHeld ?? '—'}</b></span>
    <span><small>Transactions</small><b>{s.txCount?.toLocaleString()}{s.txCountCapped ? '+' : ''}</b></span>
    <span><small>Wallet age</small><b>{s.firstSeen ? ago(s.firstSeen) : s.txCountCapped ? 'veteran' : '—'}</b></span>
    <a href={`https://solscan.io/account/${address}`} target="_blank" rel="noopener noreferrer">Solscan ↗</a>
  </div>;
}

export function PerksCard({ perks, mine }) {
  if (!perks) return null;
  const pct = perks.next ? Math.min(100, (perks.feeUsd / (perks.feeUsd + perks.next.needUsd)) * 100) : 100;
  return <section className="wp-card wp-perks" data-testid="perks-card">
    <div className="wpj-head"><h3>$FEE holder perks</h3><span className="wpj-count">holding <b>${perks.feeUsd}</b></span></div>
    <p className="wp-bio">No subscriptions. Hold $FEE and FEELESS unlocks more — checked live against the wallet.</p>
    <div className="wpp-ladder">{perks.tiers.map(t => <div key={t.tier} className={`wpp-tier ${t.tier <= perks.tier ? 'on' : ''} ${t.tier === perks.tier ? 'current' : ''}`}>
      <div className="wpp-top"><span>{t.icon}</span><b>{t.name}</b><small>{t.minUsd ? `$${t.minUsd.toLocaleString()}+` : 'free'}</small></div>
      <ul>{t.perks.map(x => <li key={x}>{t.tier <= perks.tier ? '✓' : '🔒'} {x}</li>)}</ul>
    </div>)}</div>
    {perks.next && <div className="wpp-next"><div className="wpj-bar"><i style={{ width: `${pct}%` }} /></div><span>{mine ? 'You are' : 'They are'} ${perks.next.needUsd} of $FEE away from <b>{perks.next.name}</b>{mine && <> · <Link to="/terminal/fee">Get $FEE →</Link></>}</span></div>}
  </section>;
}

export function SetupCallout({ profile, onEdit }) {
  const steps = [['displayName', 'Pick a name'], ['avatarUrl', 'Add a pic or GIF'], ['bio', 'Write a bio'], ['bannerUrl', 'Upload a banner'], ['theme', 'Choose a theme'], ['top8', 'Add your Top 8 coins']];
  const done = steps.filter(([k]) => { const v = profile?.[k]; return Array.isArray(v) ? v.length : k === 'theme' ? v && v !== 'grid' : Boolean(v); }).length;
  if (done === steps.length) return null;
  return <section className="wp-card wp-setup" data-testid="profile-setup">
    <div className="wpj-head"><h3>✨ Your profile is live — make it yours</h3><span className="wpj-count"><b>{done}</b>/{steps.length}</span></div>
    <div className="wpj-bar"><i style={{ width: `${(done / steps.length) * 100}%` }} /></div>
    <div className="wps-steps">{steps.map(([k, l]) => { const v = profile?.[k]; const ok = Array.isArray(v) ? v.length : k === 'theme' ? v && v !== 'grid' : Boolean(v); return <span key={k} className={ok ? 'ok' : ''}>{ok ? '✓' : '○'} {l}</span>; })}</div>
    <button type="button" className="btn-primary" onClick={onEdit}>Set up profile</button>
  </section>;
}
