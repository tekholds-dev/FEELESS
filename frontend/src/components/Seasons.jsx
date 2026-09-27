import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown } from 'lucide-react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { WeeklyDrops } from './SeasonBadges';
import { SeasonEditor } from './SeasonEditor';
import { useAdmin } from '../lib/adminCall';

const TIER_COLOR = { Recruit: '#8fa89a', Bronze: '#d08a4e', Silver: '#cfd8dc', Gold: '#f5c542', Diamond: '#7cc8ff', Legend: '#ff5ad1' };
const HOW = [['📣', 'Sharp calls', '+100 for each Call Ledger call that reaches 2×'], ['🚩', 'Rug reports', '+25 per sniper/bundler you flag first (proof required, max 100 per coin)'], ['💎', 'Hold $FEE', '+20 a day while you hold $1+ of $FEE'], ['🔥', 'Show up', 'Daily check-in +10 (+5 per streak day), post +5, invites +75, profile +50'], ['🧹', 'Stay clean', 'Blocklisted wallets score zero — sniping or bundling ends your season']];

// How points turn into rewards. Mirrors the server rules exactly; keep in sync with _distribute_drops.
function SeasonRules({ s }) {
  return <section className="season-card season-rules" data-testid="season-rules">
    <h3>How rewards reach you</h3>
    <ol>
      <li><b>Earn points.</b><span>Claim rewards on the Rewards tab; every point is multiplied by this season's {s.multiplier}× and counted toward both the week and the season.</span></li>
      <li><b>Weekly drop, automatic.</b><span>When each 7-day week ends, that week's board is ranked and badges land in your profile Vault — no claim, no gas: Top 3 → Legendary · Top 10% → Epic · 300+ pts → Rare · 50+ pts → Common.</span></li>
      <li><b>Season finale.</b><span>At season end everyone with points gets the season badge at their tier (Legend → Legendary, Diamond → Epic, Gold → Rare, others → Common). Prize: {s.prize}.</span></li>
      <li><b>Token airdrops.</b><span>Any $FEE / token airdrop is picked by the team from the leaderboard or holder snapshots, sent straight to your wallet from the FEELESS wallet, and published here with its on-chain transaction. FEELESS never asks you to connect to a "claim" site or sign to receive.</span></li>
    </ol>
    <small>Badges are FEELESS collectibles in your profile, not on-chain NFTs. Only wallets that are not blocklisted can earn.</small>
  </section>;
}

const FX_GLYPHS = { money: ['💸', '💵', '🤑', '💰'], fire: ['🔥', '✦', '🔥'], snow: ['❄️', '❅', '❆'], leaves: ['🍂', '🍁', '🍃'], stars: ['✨', '⭐', '✦'] };
// Season weather: the admin-picked effect rains across the hero (decorative, reduced-motion aware).
function SeasonFx({ fx }) {
  const glyphs = FX_GLYPHS[fx];
  if (!glyphs) return null;
  return <div className={`season-fx fx-${fx}`} aria-hidden="true">{Array.from({ length: 22 }, (_, i) => <span key={i} style={{ left: `${(i * 47) % 100}%`, animationDelay: `${(i * 0.73) % 8}s`, animationDuration: `${6 + (i % 5) * 1.6}s`, fontSize: `${14 + (i % 4) * 6}px` }}>{glyphs[i % glyphs.length]}</span>)}</div>;
}

function useSeason() {
  const { wallet } = useWallet() || {};
  const [d, setD] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/season${wallet?.address ? `?address=${wallet.address}` : ''}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [wallet?.address, tick]);
  return [d, () => setTick(t => t + 1)];
}
const left = s => { if (s == null) return ''; const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); return d ? `${d}d ${h}h` : `${h}h ${m}m`; };

// Thin ticker under the network bar: the live season, always in the corner of your eye.
export function SeasonBanner() {
  const [d] = useSeason();
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
  const [d, reload] = useSeason();
  const { isAdmin, call } = useAdmin();
  const [editing, setEditing] = useState(false);
  if (!d) return <p className="wp-bio">Loading the season…</p>;
  const s = d.season;
  if (!s) return <section className="season-hero"><h1>Between seasons</h1><p>{d.upcoming ? `Season "${d.upcoming.name}" starts ${new Date(d.upcoming.start * 1000).toLocaleDateString()}.` : 'The next season is being forged.'}</p></section>;
  const me = d.me;
  const tierPct = me ? (() => { const idx = d.tiers.findIndex(([n]) => n === me.tier); const cur = d.tiers[idx][1]; const nxt = d.tiers[idx + 1]?.[1]; return nxt ? ((me.score - cur) / (nxt - cur)) * 100 : 100; })() : 0;
  return <div className="seasons" style={{ '--season': s.accent, '--season2': s.accent2 || '#ff2bd6' }} data-testid="seasons-page">
    {isAdmin && !editing && <button type="button" className="btn-outline season-edit-btn" onClick={() => setEditing(true)} data-testid="season-edit">✎ Edit season</button>}
    {editing && <SeasonEditor season={s} call={call} onDone={changed => { setEditing(false); if (changed) reload(); }} />}
    {s.bannerUrl ? <section className="season-hero has-banner">
      {/* The art carries its own title, so nothing is drawn over it; the info sits in a panel below. */}
      <div className="season-art"><img src={s.bannerUrl} alt={`${s.name} season art`} decoding="async" /><SeasonFx fx={s.bgFx} /></div>
      <div className="season-info">
        <div className="season-info-text"><span className="eyebrow">SEASON {s.id.replace('s', '')}</span><h1>{s.name}</h1><p>{s.theme}</p></div>
        <div className="season-stats"><div><b>{left(d.endsIn)}</b><small>left</small></div><div><b>{d.players}</b><small>players</small></div><div><b>{s.multiplier}×</b><small>points</small></div></div>
        <p className="season-prize">🏆 {s.prize}</p>
      </div>
    </section> : <section className="season-hero">
      <SeasonFx fx={s.bgFx} />
      <div className="season-sigil"><Crown size={34} /><i /><i /><i /></div>
      <span className="eyebrow">SEASON {s.id.replace('s', '')}</span>
      <h1>{s.name}</h1>
      <p>{s.theme}</p>
      <div className="season-stats"><div><b>{left(d.endsIn)}</b><small>left</small></div><div><b>{d.players}</b><small>players</small></div><div><b>{s.multiplier}×</b><small>points</small></div></div>
      <p className="season-prize">🏆 {s.prize}</p>
    </section>}
    <SeasonRules s={s} />
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
    <WeeklyDrops />
    <section className="season-card season-board">
      <h3>Leaderboard</h3>
      {!d.top.length ? <p className="wp-bio">No one on the board yet — claim a reward on your profile to take #1.</p>
        : d.top.map(r => <Link key={r.address} to={`/terminal/profile/${r.address}`} className={`season-row rank-${r.rank}`}><span className="season-rank">{r.rank <= 3 ? ['🥇', '🥈', '🥉'][r.rank - 1] : `#${r.rank}`}</span><b>{r.name}</b><small>@{r.handle}</small><em style={{ color: TIER_COLOR[r.tier] }}>{r.tier}</em><strong>{r.score.toLocaleString()}</strong></Link>)}
    </section>
  </div>;
}
