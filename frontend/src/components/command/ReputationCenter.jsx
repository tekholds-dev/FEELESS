import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Shield, ShieldQuestion, Search, Layers, Star, HelpCircle, Link2 } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { fetchLeaderboard, fetchCreator, fetchClusters, BADGE_LABEL } from '../../lib/reputation';
import { CreatorProfileCard, AddressPill, WatchlistDashboard } from './CreatorProfile';
import { RepTools } from '../RepTools';
import { RepSection } from './RepStanding';
import { RepHero, RepNav, REP_SECTIONS } from './RepHero';
import { SupportButton } from '../SupportHub';
import { useRemembered } from '../../lib/remember';

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
  ['feeless', 'FEELESS launchers', 'Creators who launched on FEELESS — bangers vs dumps, verified on-chain'],
  ['trusted', 'Most trusted', 'Clean history, highest score'],
  ['serial', 'Serial launchers', 'Most tokens deployed by one wallet'],
  ['rising', 'Rising', 'New in the last 48h, clean so far'],
  ['active', 'Recently active', 'Most recent launch activity'],
  ['flagged', 'Flagged / rugged', 'At least one confirmed liquidity collapse'],
];

function BlocklistView() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch('/api/reputation/blocklist?limit=300').then(r => r.json()).then(setData).catch(() => setData({ wallets: [] })); }, []);
  const rows = data?.wallets || [];
  return <section className="reputation-blocklist" data-testid="reputation-blocklist">
    <p className="reputation-view-hint">Wallets proven by on-chain forensics to have bundled or sniped launches. Reported by the community with evidence, or caught automatically on {data?.autoThreshold || 3}+ launches. FEELESS launches can refuse them at open.</p>
    {!rows.length && <div className="truth-empty">No blocklisted wallets yet. Open any coin's Launch forensics to flag proven bundlers and snipers.</div>}
    <div className="reputation-rank-list">{rows.map((r, i) => <div key={r.wallet} className="reputation-rank-row blocklist-row">
      <span className="reputation-rank-number">{String(i + 1).padStart(2, '0')}</span>
      <span onClick={e => e.stopPropagation()}><AddressPill address={r.wallet} /></span>
      <span className="reputation-badge badge-flagged">⛔ {r.auto ? 'Serial offender' : 'Reported'}</span>
      <span><small>BUNDLES</small><b className={r.bundles ? 'negative' : ''}>{r.bundles}</b></span>
      <span><small>SNIPES</small><b>{r.snipes}</b></span>
      <strong className="reputation-score negative">{r.strikes}×</strong>
    </div>)}</div>
  </section>;
}

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
  const { clusters = [], creatorsScanned, pendingResolution } = state.data || {};
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

// 📊 a creator's record at a glance: what its launches became (sustained · dumped · dead · rugged) as one segmented bar, and its score as a ring
export function recordParts(row) {
  const n = Math.max(1, Number(row.tokenCount) || 0);
  const parts = [['sustained', row.sustainedCount, '#45e486'], ['dumped', row.dumpedCount, '#ffb347'], ['dead', row.deadCount, '#8a93a6'], ['rugged', row.ruggedCount, '#ff4d6d']]
    .map(([k, v, c]) => ({ k, v: Number(v) || 0, c, w: (Number(v) || 0) / n })).filter(p => p.v > 0);
  return { parts, other: Math.max(0, 1 - parts.reduce((a, p) => a + p.w, 0)), n };
}
function RecordBar({ row }) {
  const r = recordParts(row);
  return <span className="rep-rec" data-tip={`${r.n} launches: ${r.parts.map(p => `${p.v} ${p.k}`).join(' · ') || 'none judged yet'}`}><u>{r.parts.map(p => <i key={p.k} style={{ flexGrow: p.w, background: p.c }} />)}{r.other > 0 ? <i style={{ flexGrow: r.other }} className="is-open" /> : null}</u>
    <small>{r.parts.length ? r.parts.map(p => `${p.v} ${p.k}`).join(' · ') : `${r.n} launch${r.n === 1 ? '' : 'es'} · judging`}</small></span>;
}
function ScoreRing({ score, badge }) {
  const v = Math.max(0, Math.min(100, Number(score) || 0)); const c = { trusted: '#45e486', veteran: '#7ff0cf', building: '#6fd3ff', risky: '#ffb347', flagged: '#ff4d6d' }[badge] || '#b9c4bf';
  return <svg className="rep-ring" viewBox="0 0 44 44" role="img" aria-label={`score ${v}`} data-tip={`Score ${v} / 100`}><circle cx="22" cy="22" r="18" className="bg" />
    <circle cx="22" cy="22" r="18" className="fg" style={{ stroke: c, strokeDasharray: `${(v / 100) * 113.1} 113.1` }} transform="rotate(-90 22 22)" /><text x="22" y="26">{v}</text></svg>;
}

export function ReputationCenter() {
  const { ecosystem } = useWorkspace();
  const navigate = useNavigate();
  const [tab, setTab] = useState('leaderboard'); const [repSec, setRepSec] = useRemembered('feeless.rep.sec', 'investigate');
  const [view, setView] = useState('trusted');
  const [showAll, setShowAll] = useState(false);
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

  const sec = REP_SECTIONS.some(([k]) => k === repSec) ? repSec : 'investigate';
  return <div className="reputation-center" data-testid="reputation-center">
    <RepHero creators={data.totalCreators} tokens={data.totalTokensTracked} chain={ecosystem.name} rows={data.rows} />
    <div className="sup-row"><SupportButton /></div>
    <RepNav sec={sec} setSec={setRepSec} />
    <div className="rph-sec" key={sec}>
    {sec === 'investigate' && <><RepTools />
    <section className="reputation-lookup">
      <CreatorLookup chain={ecosystem.chainId} onScan={runScan} />
      {scan && <div ref={reportRef}>
        <CreatorProfileCard chain={ecosystem.chainId} variant="compact" {...scan} onClose={() => setScan(null)} />
        {scan.result && <Link className="rep-scan-full-link" to={`/terminal/reputation/${ecosystem.chainId}/${scan.address}`}>Open full profile page ↗</Link>}
      </div>}
    </section>
    </>}
    {['why', 'markets', 'standing', 'rugs', 'terms'].includes(sec) && <RepSection part={sec} />}
    {sec === 'how' && <>
    <section className="reputation-mechanics" data-testid="reputation-mechanics" >
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
    </>}
    {sec === 'board' && <>
    <div className="reputation-top-tabs"><button type="button" className={tab === 'leaderboard' ? 'active' : ''} onClick={() => setTab('leaderboard')}><Layers size={14} />Leaderboard</button><button type="button" className={tab === 'clusters' ? 'active' : ''} onClick={() => setTab('clusters')}><Link2 size={14} />Wallet Clusters</button><button type="button" className={tab === 'blocklist' ? 'active' : ''} onClick={() => setTab('blocklist')}>⛔ Blocklist</button><button type="button" className={tab === 'watchlist' ? 'active' : ''} onClick={() => setTab('watchlist')}><Star size={14} />My Watchlist</button></div>
    {tab === 'watchlist' ? <WatchlistDashboard /> : tab === 'blocklist' ? <BlocklistView /> : <>
    {tab === 'clusters' ? <ClusterExplorer chain={ecosystem.chainId} onScan={runScan} /> : <section className="reputation-leaderboard">
      <div className="reputation-leaderboard-tabs">{VIEWS.map(([id, label]) => <button type="button" key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>)}</div>
      <p className="reputation-view-hint">{VIEWS.find(([id]) => id === view)?.[2]} · click a wallet to open its full profile</p>
      {error && <p className="reputation-lookup-error">{error}</p>}
      {!error && !(data.rows || []).length && <div className="truth-empty" data-testid="reputation-leaderboard-empty">{view === 'feeless' ? 'No FEELESS launches yet. Every launch confirmed through the FEELESS launch studio is verified on-chain and scored here — bangers and rugs alike.' : `No ${view === 'flagged' ? 'flagged' : 'scored'} creators recorded yet for ${ecosystem.name}. Keep browsing — every token card you open feeds this graph.`}</div>}
      <div className="reputation-rank-list">{(data.rows || []).slice(0, showAll ? undefined : 12).map((row, i) => { const Icon = ICON[row.badge] || Shield; return <div className="reputation-rank-row" role="button" tabIndex={0} key={row.address} data-testid={`reputation-rank-${row.address}`} onClick={() => navigate(`/terminal/reputation/${ecosystem.chainId}/${row.address}`)} onKeyDown={e => e.key === 'Enter' && navigate(`/terminal/reputation/${ecosystem.chainId}/${row.address}`)}>
        <span className="reputation-rank-number">{String(i + 1).padStart(2, '0')}</span>
        <span onClick={e => e.stopPropagation()}><AddressPill address={row.address} /></span>
        <span className={`reputation-badge badge-${row.badge}`}><Icon size={11} />{BADGE_LABEL[row.badge]}</span>
        <span><small>TOKENS</small><b>{row.tokenCount}</b></span>
        {view === 'feeless' ? <span><small>BANGERS / DUMPS</small><b><span className="positive">{row.bigWinners}</span> / <span className={row.dumpedCount ? 'negative' : ''}>{row.dumpedCount}</span></b></span> : <span><small>DUMPED</small><b className={row.dumpedCount || row.ruggedCount ? 'negative' : ''}>{row.dumpedCount + row.ruggedCount}</b></span>}
        <RecordBar row={row} />
        <ScoreRing score={row.score} badge={row.badge} />
      </div>; })}</div>{(data.rows || []).length > 12 && <button type="button" className="pf-more" onClick={() => setShowAll(v => !v)}>{showAll ? 'Show top 12' : `Show all ${(data.rows || []).length}`}</button>}
    </section>}
    </>}
    </>}
    </div>
  </div>;
}
