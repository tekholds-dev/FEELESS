import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';

const TIER_COLOR = { Recruit: '#8fa89a', Bronze: '#d08a4e', Silver: '#cfd8dc', Gold: '#f5c542', Diamond: '#7cc8ff', Legend: '#ff5ad1' };
const HOW = [['📣', 'Sharp calls', 'Calls that hit 2× on the Call Ledger'], ['🧹', 'Clean trading', 'Never sniping, bundling or funding snipers'], ['🚩', 'Rug reports', 'Flag bundlers & snipers from Launch forensics'], ['💎', 'Hold $FEE', 'Daily holder claims + perk tiers'], ['🔥', 'Show up', 'Daily streaks, posts, profile + invites']];

function useSeason() {
  const { wallet } = useWallet() || {};
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/season${wallet?.address ? `?address=${wallet.address}` : ''}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [wallet?.address]);
  return d;
}
const left = s => { if (s == null) return ''; const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); return d ? `${d}d ${h}h` : `${h}h ${m}m`; };

// Thin ticker under the network bar: the live season, always in the corner of your eye.
export function SeasonBanner() {
  const d = useSeason();
  const s = d?.season;
  if (!s) return null;
  const leader = d.top?.[0];
  const items = [`👑 SEASON ${s.id.replace('s', '')} · ${s.name.toUpperCase()}`, `⏳ ends in ${left(d.endsIn)}`, `🏆 ${s.prize}`, leader ? `🥇 @${leader.handle || leader.name} leads with ${leader.score.toLocaleString()} pts` : '🥇 no leader yet — be first',
    d.me?.rank ? `⚡ you're #${d.me.rank} · ${d.me.tier}` : '⚡ earn by being trustworthy', `${d.players} players`, s.multiplier > 1 ? `✖️ ${s.multiplier}× points` : null].filter(Boolean);
  return <Link to="/terminal/seasons" className="season-banner" style={{ '--season': s.accent }} data-testid="season-banner">
    <div className="season-banner-track">{[...items, ...items].map((t, i) => <span key={i}>{t}</span>)}</div>
  </Link>;
}

export function SeasonsPage() {
  const d = useSeason();
  if (!d) return <p className="wp-bio">Loading the season…</p>;
  const s = d.season;
  if (!s) return <section className="season-hero"><h1>Between seasons</h1><p>{d.upcoming ? `Season "${d.upcoming.name}" starts ${new Date(d.upcoming.start * 1000).toLocaleDateString()}.` : 'The next season is being forged.'}</p></section>;
  const me = d.me;
  const tierPct = me ? (() => { const idx = d.tiers.findIndex(([n]) => n === me.tier); const cur = d.tiers[idx][1]; const nxt = d.tiers[idx + 1]?.[1]; return nxt ? ((me.score - cur) / (nxt - cur)) * 100 : 100; })() : 0;
  return <div className="seasons" style={{ '--season': s.accent }} data-testid="seasons-page">
    <section className="season-hero">
      <div className="season-sigil"><Crown size={34} /><i /><i /><i /></div>
      <span className="eyebrow">SEASON {s.id.replace('s', '')}</span>
      <h1>{s.name}</h1>
      <p>{s.theme}</p>
      <div className="season-stats"><div><b>{left(d.endsIn)}</b><small>left</small></div><div><b>{d.players}</b><small>players</small></div><div><b>{s.multiplier}×</b><small>points</small></div></div>
      <p className="season-prize">🏆 {s.prize}</p>
    </section>
    <div className="season-grid">
      <section className="season-card">
        <h3>Your run</h3>
        {me ? <><div className="season-me"><b style={{ color: TIER_COLOR[me.tier] }}>{me.tier}</b><span>{me.score.toLocaleString()} pts{me.rank ? ` · #${me.rank} of ${me.players}` : ''}</span></div>
          <div className="season-bar"><i style={{ width: `${Math.min(100, tierPct)}%`, background: TIER_COLOR[me.next || me.tier] }} /></div>
          <small>{me.next ? `${me.toNext.toLocaleString()} pts to ${me.next}` : 'Max tier — Legend.'}</small></>
          : <p className="wp-bio">Connect a wallet to join the season.</p>}
        <div className="season-tiers">{d.tiers.map(([n, need]) => <span key={n} style={{ '--t': TIER_COLOR[n] }}><i />{n}<small>{need.toLocaleString()}</small></span>)}</div>
      </section>
      <section className="season-card">
        <h3>How to score</h3>
        <div className="season-how">{HOW.map(([e, t, x]) => <div key={t}><em>{e}</em><b>{t}</b><small>{x}</small></div>)}</div>
        <small className="season-rule">Blocklisted wallets can't place. Points come from Rewards claims on your profile.</small>
      </section>
    </div>
    <section className="season-card season-board">
      <h3>Leaderboard</h3>
      {!d.top.length ? <p className="wp-bio">No one on the board yet — claim a reward on your profile to take #1.</p>
        : d.top.map(r => <Link key={r.address} to={`/terminal/profile/${r.address}`} className={`season-row rank-${r.rank}`}><span className="season-rank">{r.rank <= 3 ? ['🥇', '🥈', '🥉'][r.rank - 1] : `#${r.rank}`}</span><b>{r.name}</b><small>@{r.handle}</small><em style={{ color: TIER_COLOR[r.tier] }}>{r.tier}</em><strong>{r.score.toLocaleString()}</strong></Link>)}
    </section>
  </div>;
}
