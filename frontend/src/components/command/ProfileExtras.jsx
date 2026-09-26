import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Hint } from '../Hint';
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
    <div className="wpj-head"><h3>$FEE holder perks <Hint text="Your tier is checked live from the $FEE in your wallet — no subscriptions. Hold more to unlock more." /></h3><span className="wpj-count">holding <b>${perks.feeUsd}</b></span></div>
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

// Live portfolio: every coin held, with logos, values and links to each coin's profile.
export function PortfolioCard({ address }) {
  const [d, setD] = useState(null);
  const [logos, setLogos] = useState({});
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/portfolio/${address}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 60000);
    fetch(apiUrl('/api/market/assets')).then(r => r.json()).then(x => alive && setLogos(Object.fromEntries((x.assets || []).map(a => [a.mint, { logo: a.logo || a.pair?.info?.imageUrl, pair: a.pair?.pairAddress }])))).catch(() => {});
    return () => { alive = false; clearInterval(t); };
  }, [address]);
  if (!d?.supported) return null;
  const fmt = v => (v == null ? '—' : v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(2)}`);
  return <section className="wp-card portfolio-card" data-testid="portfolio">
    <div className="wpj-head"><h3>Portfolio</h3><span className="wpj-count">net worth <b>{fmt(d.totalUsd)}</b></span></div>
    <div className="pf-grid">
      <a className="pf-coin pf-sol" href="https://solscan.io/account/" onClick={e => { e.preventDefault(); window.open(`https://solscan.io/account/${d.address}`, '_blank', 'noopener'); }}><span className="pf-logo sol">◎</span><b>SOL</b><small>{d.sol.toFixed(3)}</small><em>{fmt(d.solUsd)}</em></a>
      {d.tokens.map(t => { const pair = t.pairAddress || logos[t.mint]?.pair; const logo = t.logo || logos[t.mint]?.logo; const href = pair ? `/terminal/coin/solana/${pair}` : `/terminal/trade?q=${t.mint}`; const up = Number(t.change24h) >= 0;
        return <a key={t.mint} className="pf-coin" href={href} title={`${t.name || t.mint} · ${t.amount.toLocaleString()}`}>
          {logo ? <img className="pf-logo" src={logo} alt="" /> : <span className="pf-logo">{(t.symbol || '?').slice(0, 2)}</span>}
          <b>{t.symbol ? `$${t.symbol}` : `${t.mint.slice(0, 4)}…`}</b>
          <small>{t.amount >= 1e6 ? `${(t.amount / 1e6).toFixed(2)}M` : t.amount >= 1e3 ? `${(t.amount / 1e3).toFixed(1)}K` : t.amount.toFixed(2)}</small>
          <em>{fmt(t.usd)}{t.change24h != null && <i className={up ? 'positive' : 'negative'}> {up ? '+' : ''}{Number(t.change24h).toFixed(1)}%</i>}</em>
        </a>; })}
    </div>
    {d.unpriced > 0 && <small className="cc-empty">{d.unpriced} token{d.unpriced === 1 ? '' : 's'} without a market price are listed without value.</small>}
  </section>;
}
