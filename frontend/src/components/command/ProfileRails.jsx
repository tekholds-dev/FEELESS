import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { investigate } from '../CaseFile';
import { WatchButton } from '../WatchButton';
import { apiUrl } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { FeeReport } from './FeeReport';

// Sticky side rails beside the centred profile card: the case verdict (same cited evidence as the case file)
// on the left, the season run + reserve-pool share and quick moves on the right. Hidden on narrow screens.
const LEVEL_TONE = { clean: 'ok', feeless: 'ok', watch: 'warn', suspect: 'bad', high: 'bad' };
const TIER_ICON = { Legend: '👑', Diamond: '💎', Gold: '🥇', Silver: '🥈', Bronze: '🥉', Recruit: '🪖' };

function useJson(path) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true; setD(null);
    if (path) fetch(apiUrl(path)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {});
    return () => { alive = false; };
  }, [path]);
  return d;
}

export function IntelRail({ address }) {
  const c = useJson(`/api/reputation/case/${address}`);
  const ev = Array.isArray(c?.evidence) ? c.evidence.filter(e => e.weight > 0).slice(0, 3) : [];
  const tone = LEVEL_TONE[c?.level] || 'ok';
  return <aside className="wp-rail wp-rail-left" data-testid="profile-rail-intel">
    <div className="wpr-card">
      <small>INTEL</small>
      {!c ? <p className="wpr-dim">Pulling the case…</p> : <>
        <div className={`wpr-verdict t-${tone}`}><b>{c.score ?? 0}</b><span>{c.label || 'No red flags'}</span></div>
        <p className="wpr-sum">{c.summary}</p>
        {ev.length > 0 && <ul className="wpr-ev">{ev.map((e, i) => <li key={i}><span>{e.claim}</span><em>{e.source}</em></li>)}</ul>}
        {c.trail?.fundedBy && <Link className="wpr-link" to={`/terminal/profile/${c.trail.fundedBy}`}>funded by {shortAddress(c.trail.fundedBy)} →</Link>}
      </>}
      <button type="button" className="wpr-btn" onClick={() => investigate(address)}>🔎 Open case file</button>
    </div>
    <RecentMoves address={address} />
  </aside>;
}

export function SeasonRail({ address }) {
  const s = useJson(`/api/reputation/season?address=${address}`);
  const r = useJson(`/api/reputation/season/reserve?address=${address}`);
  const pools = (useJson(`/api/reputation/badge-pools?address=${address}`)?.pools || []).filter(p => p.me);
  const me = s?.me;
  const tiers = Array.isArray(s?.tiers) ? s.tiers : [];
  const idx = me ? tiers.findIndex(([n]) => n === me.tier) : -1;
  const pct = idx >= 0 && tiers[idx + 1] ? Math.min(100, ((me.score - tiers[idx][1]) / (tiers[idx + 1][1] - tiers[idx][1])) * 100) : 100;
  const copy = (text, what) => navigator.clipboard?.writeText(text).then(() => toast.success(`${what} copied`)).catch(() => {});
  return <aside className="wp-rail wp-rail-right" data-testid="profile-rail-season">
    <FeeReport address={address} />
    <div className="wpr-card">
      <small>SEASON RUN</small>
      {!s?.season ? <p className="wpr-dim">{s ? 'Between seasons.' : 'Loading…'}</p> : <>
        <div className="wpr-tier"><i>{TIER_ICON[me?.tier] || '🪖'}</i><b>{me?.tier || 'Recruit'}</b><span>{(me?.score || 0).toLocaleString()} pts{me?.rank ? ` · #${me.rank}` : ''}</span></div>
        <div className="wpr-bar"><i style={{ width: `${pct}%` }} /></div>
        <p className="wpr-dim">{me?.next ? `${me.toNext.toLocaleString()} pts to ${me.next}` : 'Max tier.'}</p>
      </>}
      {r?.active && <div className="wpr-pot"><span>💰 Reserve pot</span><b>{r.potSol} SOL</b><em>{r.me ? `this wallet ≈ ${r.me.sol} SOL` : 'Bronze+ earns a cut'}</em></div>}
      {pools.map(p => <div key={p.id} className="wpr-pot"><span>🎖 {p.name}</span><b>{p.me.sol} SOL</b><em>{p.me.why ? `earned by ${p.me.why}` : `${p.me.sharePct}% of the pot`}</em></div>)}
      <Link className="wpr-link" to="/terminal/seasons">Season board →</Link>
    </div>
    <TopBags address={address} />
    <div className="wpr-card">
      <small>MOVES</small>
      <div className="wpr-moves">
        <WatchButton target={address} className="wpr-btn" />
        <Link to="/terminal/chat" className="wpr-btn">⚔️ Trenches</Link>
        <button type="button" className="wpr-btn" onClick={() => copy(address, 'Address')}>⧉ Address</button>
        <button type="button" className="wpr-btn" onClick={() => copy(window.location.href, 'Profile link')}>↗ Share</button>
      </div>
    </div>
  </aside>;
}

// Your sells vs where the coin is now: FeeCat's "after the sell" lesson, pointed at your own trades.
export function AfterSell({ address }) {
  const d = useJson(`/api/reputation/after-sell/${address}`);
  if (!d?.rows?.length) return null;
  return <section className="wp-card after-sell" data-testid="after-sell"><h3>👀 After the sell <small>{d.runners} runner{d.runners === 1 ? '' : 's'} sold early · {d.saved} good exit{d.saved === 1 ? '' : 's'}</small></h3>
    <div className="after-sell-list">{d.rows.map(x => <Link key={x.token + x.ts} to={x.pair ? `/terminal/chat?chain=solana&pair=${x.pair}` : `/terminal/coin/solana/${x.token}`} className={`after-sell-row l-${x.lesson}`}>
      <b>${x.symbol || x.token.slice(0, 4)}</b><span>{x.movePct >= 0 ? '+' : ''}{x.movePct >= 900 ? `${(x.movePct / 100 + 1).toFixed(1)}x` : `${x.movePct}%`} since you sold</span>
      <em>{x.lesson === 'runner' ? '🧠 sold a runner' : x.lesson === 'saved' ? '✅ good exit' : '·'}</em></Link>)}</div></section>;
}

const usdC = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const agoS = ts => { const s2 = Math.max(0, Date.now() / 1000 - ts); return s2 < 3600 ? `${Math.floor(s2 / 60)}m` : s2 < 86400 ? `${Math.floor(s2 / 3600)}h` : `${Math.floor(s2 / 86400)}d`; };

// Last few swaps this wallet made, newest first: side, coin, size, when. One click to the coin.
function RecentMoves({ address }) {
  const d = useJson(`/api/reputation/wallet-trades/${address}`);
  const rows = (d?.trades || []).slice(0, 4);
  if (!rows.length) return null;
  const buys = (d.trades || []).filter(t => t.side === 'buy').length;
  return <div className="wpr-card" data-testid="rail-moves"><small>RECENT MOVES <em>{buys}B · {(d.trades || []).length - buys}S</em></small>
    {rows.map(t => <Link key={t.tx || t.ts} className="wpr-move" to={t.pair ? `/terminal/chat?chain=solana&pair=${t.pair}` : `/terminal/coin/solana/${t.token}`}>
      <i className={t.side === 'buy' ? 'b' : 's'}>{t.side === 'buy' ? 'B' : 'S'}</i><b>${t.symbol || String(t.token).slice(0, 4)}</b><span>{usdC(t.usd)}</span><em>{agoS(t.ts)}</em></Link>)}
  </div>;
}

// Biggest bags right now, with the total value. Links to each coin.
function TopBags({ address }) {
  const d = useJson(`/api/reputation/portfolio/${address}`);
  const rows = (d?.tokens || []).filter(t => t.usd).slice(0, 3);
  if (!d || d.supported === false || (!rows.length && !d.totalUsd)) return null;
  return <div className="wpr-card" data-testid="rail-bags"><small>TOP BAGS <em>{usdC(d.totalUsd)} total</em></small>
    {rows.map(t => <Link key={t.mint} className="wpr-move" to={`/terminal/coin/solana/${t.mint}`}>{t.logo ? <img src={t.logo} alt="" /> : <i className="b">{(t.symbol || '?').slice(0, 1)}</i>}<b>${t.symbol || t.mint.slice(0, 4)}</b><span>{usdC(t.usd)}</span><em>{d.totalUsd ? `${Math.round((t.usd / d.totalUsd) * 100)}%` : ''}</em></Link>)}
  </div>;
}
