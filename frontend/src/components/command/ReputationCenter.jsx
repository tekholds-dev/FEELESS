import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Shield, ShieldQuestion, Search, Layers, Star, HelpCircle, Link2 } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { fetchLeaderboard, fetchCreator, fetchClusters, BADGE_LABEL } from '../../lib/reputation';
import { CreatorProfileCard, AddressPill, WatchlistDashboard } from './CreatorProfile';

const ICON = { trusted: ShieldCheck, building: Shield, unproven: ShieldQuestion, flagged: ShieldAlert };

function CreatorLookup({ chain, onScan }) {
  const [address, setAddress] = useState('');
  const submit = event => {
    event.preventDefault();
    if (!address.trim()) return;
    onScan(address.trim());
  };
  return <form className="reputation-lookup-form" onSubmit={submit}><Search size={15} /><input data-testid="reputation-lookup-input" placeholder="Paste a creator / mint-authority wallet address…" value={address} onChange={e => setAddress(e.target.value)} /><button type="submit" className="btn-primary">Check wallet</button></form>;
}

const VIEWS = [
  ['trusted', 'Most trusted', 'Clean history, highest score'],
  ['serial', 'Serial launchers', 'Most tokens deployed by one wallet'],
  ['rising', 'Rising', 'New in the last 48h, clean so far'],
  ['active', 'Recently active', 'Most recent launch activity'],
  ['flagged', 'Flagged / rugged', 'At least one confirmed liquidity collapse'],
];

function ClusterExplorer({ chain, onScan }) {
  const [state, setState] = useState({ loading: true, error: '', data: null });
  useEffect(() => {
    let alive = true;
    setState({ loading: true, error: '', data: null });
    fetchClusters(chain).then(data => { if (alive) setState({ loading: false, error: '', data }); })
      .catch(err => { if (alive) setState({ loading: false, error: err.message, data: null }); });
    return () => { alive = false; };
  }, [chain]);

  if (state.loading) return <p className="reputation-view-hint">Cross-referencing on-chain funding sources across every tracked wallet…</p>;
  if (state.error) return <p className="reputation-lookup-error">{state.error}</p>;
  const { clusters, creatorsScanned, pendingResolution } = state.data;
  return <section className="reputation-clusters" data-testid="reputation-clusters">
    <p className="reputation-view-hint">Wallets that "look" independent but were each first funded from the same upstream address — a real, verifiable on-chain link, not a heuristic guess. Scanned {creatorsScanned} tracked wallets{pendingResolution > 0 ? ` (${pendingResolution} still resolving — check back shortly)` : ''}.</p>
    {!clusters.length && <div className="truth-empty">No shared-funding clusters found yet among tracked wallets. This builds up automatically as FEELESS observes more launches.</div>}
    <div className="reputation-cluster-grid">{clusters.map(c => <div key={c.fundingSource} className="reputation-cluster-card">
      <div className="reputation-cluster-card-head"><Link2 size={14} /><span onClick={e => e.stopPropagation()}><AddressPill address={c.fundingSource} /></span><small>funding source</small></div>
      <div className="reputation-cluster-card-stats"><span><small>WALLETS</small><b>{c.members.length}</b></span><span><small>TOKENS</small><b>{c.totalTokens}</b></span><span><small>FLAGGED</small><b className={c.totalFlags ? 'negative' : ''}>{c.totalFlags}</b></span></div>
      <div className="reputation-cluster-members">{c.members.map(m => { const Icon = ICON[m.badge] || Shield; return <div key={m.address} className="reputation-cluster-member" role="button" tabIndex={0} onClick={() => onScan(m.address)} onKeyDown={e => e.key === 'Enter' && onScan(m.address)}>
        <Icon size={12} /><span onClick={e => e.stopPropagation()}><AddressPill address={m.address} /></span><em>{m.tokenCount} token{m.tokenCount === 1 ? '' : 's'}</em><strong>{m.score}</strong>
      </div>; })}</div>
    </div>)}</div>
  </section>;
}

export function ReputationCenter() {
  const { ecosystem } = useWorkspace();
  const navigate = useNavigate();
  const [tab, setTab] = useState('leaderboard');
  const [view, setView] = useState('trusted');
  const [data, setData] = useState({ rows: [], totalCreators: 0, totalTokensTracked: 0 });
  const [error, setError] = useState('');
  const [scan, setScan] = useState(null); // { address, loading, error, result }
  const reportRef = useRef(null);

  useEffect(() => {
    let alive = true;
    fetchLeaderboard(ecosystem.chainId, view).then(res => { if (alive) { setData(res); setError(''); } }).catch(err => { if (alive) setError(err.message); });
    return () => { alive = false; };
  }, [ecosystem.chainId, view]);

  const runScan = async address => {
    setScan({ address, loading: true, error: '', result: null });
    requestAnimationFrame(() => reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    try {
      const result = await fetchCreator(ecosystem.chainId, address);
      setScan({ address, loading: false, error: '', result });
    } catch (err) {
      setScan({ address, loading: false, error: err.message, result: null });
    }
  };

  return <div className="reputation-center" data-testid="reputation-center">
    <div className="command-page-title"><span className="eyebrow"><Layers size={13} />THE TRUST LAYER · CHAIN-AGNOSTIC</span><h1>Creators earn trust.<br /><em>Every launch remembers.</em></h1><p>A wallet's launch history, not the current meta, is what should decide whether you buy. Every observation FEELESS makes across every chain and launchpad gets recorded here permanently — mint authority status, liquidity survival, and every past rug. This dataset only gets harder to fake the longer it runs.</p></div>
    <div className="reputation-summary"><div><small>CREATORS TRACKED</small><strong data-testid="reputation-total-creators">{data.totalCreators}</strong></div><div><small>TOKENS OBSERVED</small><strong data-testid="reputation-total-tokens">{data.totalTokensTracked}</strong></div><div><small>ACTIVE CHAIN</small><strong>{ecosystem.name}</strong></div></div>
    <section className="reputation-mechanics" data-testid="reputation-mechanics">
      <div className="reputation-mechanics-head"><HelpCircle size={15} /><h2>How a score actually gets built</h2></div>
      <div className="reputation-mechanics-grid">
        <article><span className="eyebrow">CREATOR IDENTITY</span><p>Every token's deployer wallet is resolved on-chain — the mint authority if one exists, or the fee-payer of the mint's earliest transaction when authority was renounced (the same heuristic real rug-detection tools use). This is how launches get tied to a wallet even on pump.fun, where authority is renounced instantly.</p></article>
        <article><span className="eyebrow">SCORE, 0–100</span><p>Starts at 50. +3 per <b>distinct</b> ticker launched (capped at 10), +8 per token that survives 3+ days with liquidity intact (capped at 6), +2 per token with renounced mint authority. Re-launching the same ticker again and again is clone-farming, not a track record: −6 per clone. Any confirmed rug: −40 each, so one flag sinks a wallet regardless of past launches.</p></article>
        <article><span className="eyebrow">RUG DETECTION</span><p>A token is flagged "rugged" when it's at least 30 minutes old and its liquidity has dropped 80%+ from its observed peak. That's a real, observed liquidity collapse — not a price dip, not a guess. Fresh tokens under 30 minutes old are never flagged; there isn't enough signal yet.</p></article>
        <article><span className="eyebrow">BADGES</span><p><b>Flagged</b> — any rug on record, regardless of anything else. <b>Trusted</b> — 3+ distinct tickers with zero rugs and zero clones, or at least one token sustained 3+ days. <b>Building</b> — clean history, still short. <b>Unproven</b> — no observations yet; not a penalty, just no data.</p></article>
        <article><span className="eyebrow">COIN TRUST vs WALLET TRUST</span><p>A token's own trust is its creator's trust — FEELESS doesn't score coins independently of who made them, because that's the actual signal: the same wallet behind five clean sustained launches is a better predictor than any individual coin's chart.</p></article>
        <article><span className="eyebrow">WHY IT COMPOUNDS</span><p>Every observation is permanent and file-backed — nothing decays, nothing resets when a meta rotates. A wallet that rugs today stays flagged next month, next chain cycle, next meta. That's the moat: the dataset gets harder to fake the longer FEELESS runs, not easier.</p></article>
      </div>
    </section>
    <div className="reputation-top-tabs"><button type="button" className={tab === 'leaderboard' ? 'active' : ''} onClick={() => setTab('leaderboard')}><Layers size={14} />Leaderboard</button><button type="button" className={tab === 'clusters' ? 'active' : ''} onClick={() => setTab('clusters')}><Link2 size={14} />Wallet Clusters</button><button type="button" className={tab === 'watchlist' ? 'active' : ''} onClick={() => setTab('watchlist')}><Star size={14} />My Watchlist</button></div>
    {tab === 'watchlist' ? <WatchlistDashboard /> : <>
    <section className="reputation-lookup">
      <CreatorLookup chain={ecosystem.chainId} onScan={runScan} />
      {scan && <div ref={reportRef}>
        <CreatorProfileCard chain={ecosystem.chainId} variant="compact" {...scan} onClose={() => setScan(null)} />
        {scan.result && <Link className="rep-scan-full-link" to={`/terminal/reputation/${ecosystem.chainId}/${scan.address}`}>Open full profile page ↗</Link>}
      </div>}
    </section>
    {tab === 'clusters' ? <ClusterExplorer chain={ecosystem.chainId} onScan={runScan} /> : <section className="reputation-leaderboard">
      <div className="reputation-leaderboard-tabs">{VIEWS.map(([id, label]) => <button type="button" key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>)}</div>
      <p className="reputation-view-hint">{VIEWS.find(([id]) => id === view)?.[2]} · click a wallet to open its full profile</p>
      {error && <p className="reputation-lookup-error">{error}</p>}
      {!error && !data.rows.length && <div className="truth-empty" data-testid="reputation-leaderboard-empty">No {view === 'flagged' ? 'flagged' : 'scored'} creators recorded yet for {ecosystem.name}. Keep browsing — every token card you open feeds this graph.</div>}
      <div className="reputation-rank-list">{data.rows.map((row, i) => { const Icon = ICON[row.badge] || Shield; return <div className="reputation-rank-row" role="button" tabIndex={0} key={row.address} data-testid={`reputation-rank-${row.address}`} onClick={() => navigate(`/terminal/reputation/${ecosystem.chainId}/${row.address}`)} onKeyDown={e => e.key === 'Enter' && navigate(`/terminal/reputation/${ecosystem.chainId}/${row.address}`)}>
        <span className="reputation-rank-number">{String(i + 1).padStart(2, '0')}</span>
        <span onClick={e => e.stopPropagation()}><AddressPill address={row.address} /></span>
        <span className={`reputation-badge badge-${row.badge}`}><Icon size={11} />{BADGE_LABEL[row.badge]}</span>
        <span><small>TOKENS</small><b>{row.tokenCount}</b></span>
        <span><small>FLAGGED</small><b className={row.ruggedCount ? 'negative' : ''}>{row.ruggedCount}</b></span>
        <strong className="reputation-score">{row.score}</strong>
      </div>; })}</div>
    </section>}
    </>}
  </div>;
}
