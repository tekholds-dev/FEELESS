import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ShieldCheck, ShieldAlert, Shield, ShieldQuestion, Wallet, ExternalLink, Copy, ArrowLeft, Share2, Star, Rocket, Link2, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchCreator, watchCreator, unwatchCreator, fetchWatchlist, fetchWatchlistFeed, BADGE_LABEL } from '../../lib/reputation';
import { shortAddress } from '../../lib/dexscreener';
import { useWallet } from '../../hooks/useWallet';

const ICON = { trusted: ShieldCheck, building: Shield, unproven: ShieldQuestion, flagged: ShieldAlert };
const BADGE_COLOR = { risky: '#ff9f45', trusted: '#00e9a0', building: '#9bd6aa', unproven: '#899b93', flagged: '#fa708c' };

export const timeAgo = seconds => {
  if (!seconds) return 'just now';
  const delta = Date.now() / 1000 - seconds;
  if (delta < 3600) return `${Math.max(1, Math.round(delta / 60))}m ago`;
  if (delta < 86400) return `${Math.round(delta / 3600)}h ago`;
  return `${Math.round(delta / 86400)}d ago`;
};

export const copyText = async (text, message) => {
  try { await navigator.clipboard.writeText(text); toast.success(message || 'Copied'); }
  catch { toast.error('Clipboard unavailable'); }
};

function ScoreGauge({ score, badge, size = 92 }) {
  const color = BADGE_COLOR[badge] || '#899b93';
  const r = (size - 10) / 2;
  const circumference = 2 * Math.PI * r;
  const has = score != null && Number.isFinite(Number(score));
  const offset = circumference * (1 - (has ? Math.min(100, Math.max(0, score)) : 0) / 100);
  return <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="score-gauge">
    <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#ffffff10" strokeWidth="7" />
    <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
      strokeDasharray={circumference} strokeDashoffset={offset}
      transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ filter: `drop-shadow(0 0 6px ${color}70)`, transition: 'stroke-dashoffset .6s ease' }} />
    <text x="50%" y="46%" textAnchor="middle" dominantBaseline="middle" fill="#edf3ef" fontSize={size * 0.24} fontWeight="700" fontFamily="'JetBrains Mono',monospace">{has ? score : '—'}</text>
    <text x="50%" y="66%" textAnchor="middle" dominantBaseline="middle" fill="#8ca394" fontSize={size * 0.1}>{has ? '/ 100' : 'no score'}</text>
  </svg>;
}

export function AddressPill({ address }) {
  return <button type="button" className="address-pill" onClick={() => copyText(address, 'Address copied')} title="Copy full address"><code>{shortAddress(address)}</code><Copy size={11} /></button>;
}

export function FollowButton({ chain, address }) {
  const { wallet, connect } = useWallet();
  const [following, setFollowing] = useState(null); // null = unknown yet
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!wallet?.address) { setFollowing(null); return; }
    let alive = true;
    fetchWatchlist(wallet.address).then(({ rows }) => {
      if (alive) setFollowing(rows.some(r => r.chain === chain && r.address === address));
    }).catch(() => { if (alive) setFollowing(false); });
    return () => { alive = false; };
  }, [wallet?.address, chain, address]);

  const toggle = async () => {
    if (!wallet?.address) {
      try { await connect?.(chain === 'solana' ? 'solana' : chain); }
      catch { toast.error('Connect a wallet to follow creators.'); }
      return;
    }
    setBusy(true);
    try {
      if (following) { await unwatchCreator(wallet.address, chain, address); setFollowing(false); toast.success('Unfollowed'); }
      else { await watchCreator(wallet.address, chain, address); setFollowing(true); toast.success('Following — you\'ll see this wallet\'s new launches and flags in your watchlist'); }
    } catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  };

  return <button type="button" className={`btn-outline follow-button ${following ? 'is-following' : ''}`} onClick={toggle} disabled={busy} title={wallet?.address ? (following ? 'Unfollow this wallet' : 'Follow this wallet') : 'Connect a wallet to follow'}>
    <Star size={14} fill={following ? 'currentColor' : 'none'} />{following ? 'Following' : 'Follow'}
  </button>;
}

function WalletClusterPanel({ chain, address, result }) {
  const [expanded, setExpanded] = useState(false);
  const linked = result.linkedWallets || [];
  if (!result.fundingSource) return null;
  return <div className="rep-cluster-panel" data-testid="rep-cluster-panel">
    <button type="button" className="rep-cluster-toggle" onClick={() => setExpanded(v => !v)}>
      <Link2 size={13} />
      <span>{linked.length > 0
        ? `Wallet cluster detected — ${linked.length} other wallet${linked.length === 1 ? '' : 's'} share this funding source`
        : 'Funding source resolved — no linked wallets tracked yet'}</span>
      {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
    </button>
    {expanded && <div className="rep-cluster-body">
      <div className="rep-cluster-source"><small>FUNDED FROM</small><AddressPill address={result.fundingSource} /></div>
      {linked.length > 0 ? <>
        <p className="provider-note">These wallets were each first funded by the same upstream address — a real on-chain link, not a guess. Worth treating as one operator across multiple "clean" identities.</p>
        <div className="rep-cluster-list">{linked.map(m => {
          const Icon = ICON[m.badge] || Shield;
          return <Link key={m.address} to={`/terminal/reputation/${m.chain}/${m.address}`} className={`rep-cluster-row badge-${m.badge}`}>
            <Icon size={13} /><code>{shortAddress(m.address)}</code><span>{m.tokenCount} token{m.tokenCount === 1 ? '' : 's'}</span>{m.ruggedCount > 0 && <b className="negative">{m.ruggedCount} flagged</b>}<strong>{m.score}</strong>
          </Link>;
        })}</div>
      </> : <p className="provider-note">No other tracked creator wallet shares this funding source yet — that can change as FEELESS observes more launches.</p>}
    </div>}
  </div>;
}

const VERDICT_ICON = { trusted: ShieldCheck, caution: ShieldAlert, avoid: ShieldAlert, unknown: ShieldQuestion };
function TrustVerdict({ verdict }) {
  const Icon = VERDICT_ICON[verdict.level] || Shield;
  return <div className={`trust-verdict verdict-${verdict.level}`} data-testid="trust-verdict">
    <div className="trust-verdict-head"><Icon size={18} /><div><small>FEELESS VERDICT</small><strong>{verdict.label}</strong></div></div>
    <ul>{verdict.reasons.map((r, i) => <li key={i} className={`reason-${r.tone}`}><i />{r.text}</li>)}</ul>
  </div>;
}

const fmtUsd = v => (v == null || !Number.isFinite(Number(v)) ? '—' : Number(v) >= 1e6 ? `$${(Number(v) / 1e6).toFixed(2)}M` : Number(v) >= 1e3 ? `$${(Number(v) / 1e3).toFixed(1)}K` : `$${Number(v).toFixed(0)}`);

function LaunchTable({ chain, tokens }) {
  const navigate = useNavigate();
  const listed = tokens.filter(t => t.market?.listed).length;
  return <div className="launch-table" data-testid="launch-table">
    <div className="rep-scan-tokens-head"><span className="eyebrow">EVERY LAUNCH FROM THIS WALLET</span><small>{tokens.length} launches · {listed} currently trading</small></div>
    {!tokens.length && <p className="provider-note">No tokens recorded for this wallet yet.</p>}
    <div className="launch-rows">{tokens.map(t => {
      const m = t.market;
      const change = Number(m?.change24h);
      const mint = t.baseTokenAddress;
      return <div key={t.pairAddress} className={`launch-row status-${t.status} ${m && !m.listed ? 'is-unlisted' : ''}`}>
        <span className="launch-sym">{m?.imageUrl ? <img src={m.imageUrl} alt="" /> : <i>{(t.symbol || '?').slice(0, 2)}</i>}<span><b>{t.symbol || 'Unknown'}</b><small>{timeAgo(t.firstSeenAt)} · {t.status}</small></span></span>
        <span><small>MARKET CAP</small><b>{m?.listed ? fmtUsd(m.marketCap) : m ? 'Not listed' : '…'}</b></span>
        <span><small>24H</small><b className={Number.isFinite(change) ? (change >= 0 ? 'positive' : 'negative') : ''}>{Number.isFinite(change) ? `${change.toFixed(1)}%` : '—'}</b></span>
        <span><small>VOL 24H</small><b>{fmtUsd(m?.volume24h)}</b></span>
        <span className="launch-actions">
          {m?.listed && m.pairAddress && <button type="button" className="btn-outline" onClick={() => navigate(`/terminal/trade?chain=${chain}&pair=${m.pairAddress}`)}>Open</button>}
          {m?.url && <a href={m.url} target="_blank" rel="noreferrer" title="DexScreener"><ExternalLink size={12} />DEX</a>}
          {mint && chain === 'solana' && <a href={`https://pump.fun/coin/${mint}`} target="_blank" rel="noreferrer" title="pump.fun"><Rocket size={12} />Pump</a>}
          {mint && <button type="button" className="icon-btn small-icon" title="Copy token mint" onClick={() => copyText(mint, 'Token address copied')}><Copy size={12} /></button>}
        </span>
      </div>;
    })}</div>
    {tokens.some(t => t.market && !t.market.listed) && <small className="reputation-wallet-caveat">"Not listed" = no DEX market exists for this token right now. On pump.fun that usually means it never left the bonding curve or died.</small>}
  </div>;
}

export function CreatorProfileCard({ chain, address, result, loading, error, variant = 'full', onClose }) {
  const profileUrl = typeof window !== 'undefined' ? `${window.location.origin}/terminal/reputation/${chain}/${address}` : '';
  return <section className={`rep-scan rep-scan-${variant}`} data-testid="rep-scan">
    {variant === 'full' ? <Link to="/terminal/reputation" className="rep-scan-back"><ArrowLeft size={14} />All creators</Link>
      : <div className="reputation-report-head"><span className="eyebrow">QUICK SCAN REPORT</span>{onClose && <button type="button" className="icon-btn small-icon" onClick={onClose} aria-label="Close">×</button>}</div>}
    {loading && <p className="reputation-view-hint">Scanning on-chain history…</p>}
    {error && <p className="reputation-lookup-error" data-testid="reputation-lookup-error">{error}</p>}
    {result && <>
      {result.verdict && <TrustVerdict verdict={result.verdict} />}
      <div className="rep-scan-hero">
        <ScoreGauge score={result.scoring.score} badge={result.scoring.badge} size={variant === 'full' ? 110 : 80} />
        <div className="rep-scan-identity">
          <span className={`reputation-badge badge-${result.scoring.badge}`}>{React.createElement(ICON[result.scoring.badge] || Shield, { size: 12 })}{BADGE_LABEL[result.scoring.badge]}</span>
          <AddressPill address={result.address || address} />
          <small>Tracking since {timeAgo(result.firstSeen)} · last active {timeAgo(result.lastSeen)}</small>{result.feelessLaunches?.length > 0 && <span className="feeless-launcher-chip">FEELESS launcher · {result.feelessLaunches.length} verified launch{result.feelessLaunches.length === 1 ? '' : 'es'}</span>}
        </div>
        <div className="rep-scan-actions"><FollowButton chain={chain} address={result.address || address} />{variant === 'full' && <button type="button" className="btn-outline" onClick={() => copyText(profileUrl, 'Profile link copied')}><Share2 size={14} />Share profile</button>}</div>
      </div>
      <div className="reputation-lookup-stats"><span><small>TOKENS TRACKED</small><b>{result.scoring.tokenCount}</b></span><span><small>FLAGGED</small><b className={result.scoring.ruggedCount ? 'negative' : ''}>{result.scoring.ruggedCount}</b></span><span><small>SUSTAINED 3D+</small><b>{result.scoring.sustainedCount}</b></span><span><small>AUTHORITY RENOUNCED</small><b>{result.scoring.renouncedCount}</b></span></div>
      {result.wallet && <div className="reputation-wallet-panel">
        <div className="reputation-wallet-head"><Wallet size={13} /><span>WALLET PROFILE</span>{result.wallet.solBalance != null && <strong>{result.wallet.solBalance.toFixed(3)} SOL</strong>}</div>
        {result.wallet.recentSignatures?.length > 0 ? <div className="reputation-signature-list">
          {result.wallet.recentSignatures.map(s => <a key={s.signature} href={`https://solscan.io/tx/${s.signature}`} target="_blank" rel="noreferrer" className={s.err ? 'sig-failed' : ''}><code>{s.signature.slice(0, 14)}…</code><span>{s.blockTime ? timeAgo(s.blockTime) : ''}</span><ExternalLink size={11} /></a>)}
        </div> : <p className="provider-note">No recent on-chain activity found for this wallet.</p>}
        <small className="reputation-wallet-caveat">On-chain signatures only — a full buy/sell ledger needs a dedicated transaction indexer, which isn't wired up yet.</small>
      </div>}
      <WalletClusterPanel chain={chain} address={address} result={result} />
      <LaunchTable chain={chain} tokens={result.tokenList || Object.values(result.tokens || {})} />
    </>}
  </section>;
}

const BRAIN_OPTIONS = [
  ['claude-opus', 'Claude Opus 5.5'], ['gpt-astra', 'GPT-6 Astra'], ['grok', 'Grok 4.7'], ['gemini', 'Gemini 3.8 Flash'],
];

function WatchedCreatorRow({ watch, ownerWallet, onChanged }) {
  const [busy, setBusy] = useState(false);
  const Icon = ICON[watch.badge] || Shield;
  const update = async patch => {
    setBusy(true);
    try { await watchCreator(ownerWallet, watch.chain, watch.address, { notifyNewToken: watch.notifyNewToken, notifyFlag: watch.notifyFlag, botEnabled: watch.botEnabled, botBrain: watch.botBrain, ...patch }); onChanged(); }
    catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    setBusy(true);
    try { await unwatchCreator(ownerWallet, watch.chain, watch.address); onChanged(); }
    catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  };
  return <div className="watch-row" data-testid={`watch-row-${watch.address}`}>
    <div className="watch-row-head">
      <Link to={`/terminal/reputation/${watch.chain}/${watch.address}`} className="address-pill"><code>{shortAddress(watch.address)}</code></Link>
      <span className={`reputation-badge badge-${watch.badge}`}><Icon size={11} />{BADGE_LABEL[watch.badge]}</span>
      {watch.score != null && <strong className="reputation-score">{watch.score}</strong>}
      <button type="button" className="icon-btn small-icon watch-remove" onClick={remove} disabled={busy} title="Unfollow"><Star size={14} fill="currentColor" /></button>
    </div>
    <div className="watch-row-controls">
      <label><input type="checkbox" checked={watch.notifyNewToken} disabled={busy} onChange={e => update({ notifyNewToken: e.target.checked })} />New launches</label>
      <label><input type="checkbox" checked={watch.notifyFlag} disabled={busy} onChange={e => update({ notifyFlag: e.target.checked })} />Rug flags</label>
      <label className="watch-bot-toggle"><input type="checkbox" checked={watch.botEnabled} disabled={busy} onChange={e => update({ botEnabled: e.target.checked, botBrain: watch.botBrain || BRAIN_OPTIONS[0][0] })} />AI watch bot</label>
      {watch.botEnabled && <select value={watch.botBrain || BRAIN_OPTIONS[0][0]} disabled={busy} onChange={e => update({ botBrain: e.target.value })}>{BRAIN_OPTIONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select>}
    </div>
  </div>;
}

const FEED_ICON = { new_token: Rocket, flagged: ShieldAlert };

export function WatchlistDashboard() {
  const { wallet, connect } = useWallet();
  const [rows, setRows] = useState([]);
  const [feed, setFeed] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = React.useCallback(() => {
    if (!wallet?.address) return;
    setLoading(true);
    Promise.all([fetchWatchlist(wallet.address), fetchWatchlistFeed(wallet.address)])
      .then(([wl, fd]) => { setRows(wl.rows); setFeed(fd.events); })
      .catch(err => toast.error(err.message))
      .finally(() => setLoading(false));
  }, [wallet?.address]);

  useEffect(() => { load(); }, [load]);

  if (!wallet?.address) return <section className="watch-dashboard-empty" data-testid="watchlist-connect">
    <Star size={22} /><h2>Follow creators to build your dashboard.</h2>
    <p>Connect a wallet to save which wallets you're watching, get notified when they launch a new coin or get flagged for a rug, and optionally hand a wallet off to an AI watch bot.</p>
    <button type="button" className="btn-primary" onClick={() => connect?.('solana')}><Wallet size={16} />Connect wallet</button>
  </section>;

  return <section className="watch-dashboard" data-testid="watchlist-dashboard">
    <div className="watch-dashboard-grid">
      <div>
        <div className="command-section-title"><span>YOUR WATCHLIST</span><small>{rows.length} wallet{rows.length === 1 ? '' : 's'}</small></div>
        {loading && !rows.length && <p className="reputation-view-hint">Loading…</p>}
        {!loading && !rows.length && <div className="truth-empty">Not following anyone yet. Open any creator's scan report and hit Follow.</div>}
        <div className="watch-row-list">{rows.map(watch => <WatchedCreatorRow key={watch.address} watch={watch} ownerWallet={wallet.address} onChanged={load} />)}</div>
      </div>
      <div>
        <div className="command-section-title"><span>NOTIFICATIONS</span><small>{feed.length}</small></div>
        {!feed.length && <div className="truth-empty">No new activity yet from wallets you follow.</div>}
        <div className="watch-feed-list">{feed.map(event => { const Icon = FEED_ICON[event.type] || Rocket; return <div key={event.id} className={`watch-feed-row type-${event.type}`}><Icon size={14} /><span><b>{shortAddress(event.address)}</b><small>{event.detail}</small></span><time>{timeAgo(event.ts)}</time></div>; })}</div>
      </div>
    </div>
  </section>;
}

export function CreatorProfilePage({ chain, address }) {
  const [state, setState] = useState({ loading: true, error: '', result: null });
  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: '', result: null });
    fetchCreator(chain, address).then(result => { if (alive) setState({ loading: false, error: '', result }); })
      .catch(err => { if (alive) setState({ loading: false, error: err.message, result: null }); });
    return () => { alive = false; };
  }, [chain, address]);
  return <div className="rep-scan-page"><CreatorProfileCard chain={chain} address={address} variant="full" {...state} /></div>;
}
