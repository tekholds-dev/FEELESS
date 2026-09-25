import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShieldAlert, Rocket, BookOpen, Radio, ThumbsUp, Database, Trash2, CheckCircle2 } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { useWallet } from '../../hooks/useWallet';
import { AddressPill, CreatorProfileCard, timeAgo } from './CreatorProfile';
import { fetchCreator, BADGE_LABEL } from '../../lib/reputation';

async function getJson(path) {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error('Unavailable right now.');
  return res.json();
}

function usePolled(path, ms) {
  const [state, setState] = useState({ data: null, error: '' });
  useEffect(() => {
    let alive = true;
    const load = () => getJson(path).then(data => alive && setState({ data, error: '' })).catch(err => alive && setState(s => ({ ...s, error: err.message })));
    load();
    const t = ms ? setInterval(load, ms) : null;
    return () => { alive = false; if (t) clearInterval(t); };
  }, [path, ms]);
  return state;
}

// Inline scan: clicking a wallet opens its report in place, no navigation.
function InlineScan({ chain, address, onClose }) {
  const [state, setState] = useState({ loading: true, error: '', result: null });
  useEffect(() => {
    let alive = true;
    fetchCreator(chain, address).then(result => alive && setState({ loading: false, error: '', result }))
      .catch(err => alive && setState({ loading: false, error: err.message, result: null }));
    return () => { alive = false; };
  }, [chain, address]);
  return <div className="inline-scan"><CreatorProfileCard chain={chain} address={address} variant="compact" onClose={onClose} {...state} /></div>;
}

export function TrustSignals() {
  const { data, error } = usePolled('/api/reputation/feed?limit=30', 20000);
  const [open, setOpen] = useState(null);
  const events = data?.events || [];
  return <section className="live-trust-panel" data-testid="trust-signals">
    <div className="live-trust-head"><Radio size={15} /><h2>Trust signals</h2><small>Live · creator launches and rug flags across everything FEELESS observes</small></div>
    {error && !events.length && <p className="reputation-lookup-error">{error}</p>}
    {!error && !events.length && <div className="truth-empty">No trust events yet. They appear when a known creator launches again or a token gets flagged.</div>}
    <div className="trust-signal-list">{events.map(ev => {
      const Icon = ev.type === 'flagged' ? ShieldAlert : Rocket;
      const isOpen = open === ev.id;
      return <div key={ev.id} className={`trust-signal type-${ev.type} ${isOpen ? 'is-open' : ''}`}>
        <button type="button" className="trust-signal-row" onClick={() => setOpen(isOpen ? null : ev.id)}>
          <Icon size={14} /><span><b>{shortAddress(ev.address)}</b><small>{ev.detail}</small></span>
          {ev.badge && <span className={`reputation-badge badge-${ev.badge}`}>{BADGE_LABEL[ev.badge]} · {ev.score}</span>}
          {ev.cloneCount >= 2 && <span className="clone-chip">{ev.cloneCount} clones</span>}
          <time>{timeAgo(ev.ts)}</time>
        </button>
        {isOpen && <InlineScan chain={ev.chain} address={ev.address} onClose={() => setOpen(null)} />}
      </div>;
    })}</div>
  </section>;
}

export function CaseStudies() {
  const { data, error } = usePolled('/api/reputation/case-studies?limit=6', 0);
  const [open, setOpen] = useState(null);
  const cases = data?.cases || [];
  return <section className="live-trust-panel" data-testid="case-studies">
    <div className="live-trust-head"><BookOpen size={15} /><h2>Live case studies</h2><small>Real wallets from the reputation graph — what bad behavior actually looks like on-chain</small></div>
    {error && <p className="reputation-lookup-error">{error}</p>}
    {!error && data && !cases.length && <div className="truth-empty">No flagged or clone-farming wallets on record yet.</div>}
    <div className="case-grid">{cases.map(c => <article key={c.address} className={`case-card case-${c.kind}`}>
      <span className="eyebrow">{c.kind === 'rug' ? 'CONFIRMED LIQUIDITY COLLAPSE' : 'CLONE FARM'}</span>
      <div className="case-card-id"><AddressPill address={c.address} /><span className={`reputation-badge badge-${c.badge}`}>{BADGE_LABEL[c.badge]} · {c.score}</span></div>
      {c.kind === 'rug'
        ? <p>{c.rugged.length} token{c.rugged.length === 1 ? '' : 's'} lost 80%+ of peak liquidity after launch ({c.rugged.map(r => r.symbol || '?').join(', ')}). Every other launch from this wallet now carries the flag.</p>
        : <p>Launched <b>{c.tokenCount}</b> tokens using only <b>{c.distinctTickers}</b> distinct ticker{c.distinctTickers === 1 ? '' : 's'} ({c.tickers.slice(0, 3).join(', ')}). Re-launching the same name repeatedly is how clone spam fishes for buyers searching a trending ticker.</p>}
      <p className="case-lesson"><b>Lesson:</b> {c.kind === 'rug' ? 'check the creator before the chart — past behavior is the best predictor.' : 'when several contracts share one ticker, verify the exact contract address, not the name.'}</p>
      <button type="button" className="btn-outline" onClick={() => setOpen(open === c.address ? null : c.address)}>{open === c.address ? 'Hide report' : 'Open full scan here'}</button>
      {open === c.address && <InlineScan chain={c.chain} address={c.address} onClose={() => setOpen(null)} />}
    </article>)}</div>
  </section>;
}

export function LiveProof() {
  const rep = usePolled('/api/reputation/health', 30000).data;
  const candles = usePolled('/api/candles/health', 30000).data;
  const cases = usePolled('/api/reputation/case-studies?limit=1', 60000).data;
  const claims = [
    ['Creators earn trust — every launch remembers', rep ? `${rep.creators} creator wallets tracked · ${rep.mints} tokens observed` : '…', rep?.creators > 0],
    ['Clone spam and rugs get caught, not just charted', cases ? `${cases.total} wallets currently flagged for rugs or clone farming` : '…', cases?.total > 0],
    ['Charts never depend on one provider', candles ? `${candles.totalTicks} self-recorded price ticks across ${candles.pairsTracked} pools` : '…', candles?.totalTicks > 0],
    ['On-chain identity, not guesswork', rep ? (rep.usingDedicatedRpc ? 'Dedicated Solana RPC connected, public pool as fallback' : 'Running on public RPC pool') : '…', Boolean(rep)],
  ];
  return <section className="live-trust-panel live-proof" data-testid="live-proof">
    <div className="live-trust-head"><CheckCircle2 size={15} /><h2>Living proof</h2><small>Each claim below, measured live from the running system</small></div>
    <div className="proof-grid">{claims.map(([claim, value, ok]) => <div key={claim} className={`proof-row ${ok ? 'is-ok' : ''}`}><i /><span><b>{claim}</b><small>{value}</small></span></div>)}</div>
  </section>;
}

const VOTE_ITEMS = [
  ['globe-live', 'Richer live globe (per-network chat + launches)'],
  ['clusters-graph', 'Visual wallet-cluster graph'],
  ['locked-launch', 'On-chain Locked Launch program (audited)'],
  ['feeback', 'Fee-Back settlement'],
  ['multichain-rep', 'Reputation on EVM chains'],
  ['mobile', 'Mobile app'],
];

export function RoadmapVoting() {
  const { wallet, connect } = useWallet();
  const [state, setState] = useState({ counts: {}, mine: [] });
  const [busy, setBusy] = useState('');
  const load = useCallback(() => getJson(`/api/reputation/roadmap/votes${wallet?.address ? `?wallet=${encodeURIComponent(wallet.address)}` : ''}`).then(setState).catch(() => {}), [wallet?.address]);
  useEffect(() => { load(); }, [load]);
  const vote = async id => {
    if (!wallet?.address) { try { await connect?.('solana'); } catch { toast.error('Connect a wallet to vote.'); } return; }
    setBusy(id);
    try {
      const res = await fetch(apiUrl('/api/reputation/roadmap/vote'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ wallet: wallet.address, itemId: id }) });
      if (!res.ok) throw new Error('Vote failed.');
      await load();
    } catch (err) { toast.error(err.message); } finally { setBusy(''); }
  };
  const max = Math.max(1, ...Object.values(state.counts));
  const sorted = [...VOTE_ITEMS].sort((a, b) => (state.counts[b[0]] || 0) - (state.counts[a[0]] || 0));
  return <section className="live-trust-panel" data-testid="roadmap-voting">
    <div className="live-trust-head"><ThumbsUp size={15} /><h2>What should ship next?</h2><small>One vote per wallet per item · tap again to remove</small></div>
    <div className="vote-list">{sorted.map(([id, label]) => {
      const count = state.counts[id] || 0; const mine = state.mine.includes(id);
      return <button type="button" key={id} className={`vote-row ${mine ? 'is-mine' : ''}`} disabled={busy === id} onClick={() => vote(id)}>
        <span className="vote-bar" style={{ width: `${(count / max) * 100}%` }} /><b>{label}</b><strong>{count}</strong><ThumbsUp size={13} fill={mine ? 'currentColor' : 'none'} />
      </button>;
    })}</div>
    {!wallet?.address && <p className="reputation-view-hint">Connect a wallet to vote — it's how votes stay one-per-person.</p>}
  </section>;
}

export function DataSovereignty() {
  const [keys, setKeys] = useState([]);
  const scan = () => {
    try {
      const out = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (/feeless|price-trail|pending-swap/i.test(k)) out.push({ k, size: (localStorage.getItem(k) || '').length });
      }
      setKeys(out.sort((a, b) => b.size - a.size));
    } catch { setKeys([]); }
  };
  useEffect(scan, []);
  const clear = k => { try { localStorage.removeItem(k); } catch {} scan(); toast.success('Removed from this browser'); };
  const total = keys.reduce((s, x) => s + x.size, 0);
  return <section className="live-trust-panel" data-testid="data-sovereignty">
    <div className="live-trust-head"><Database size={15} /><h2>Your data, on this device</h2><small>Everything FEELESS keeps in this browser — inspect it or delete it</small></div>
    <p className="reputation-view-hint">{keys.length} item{keys.length === 1 ? '' : 's'} · {(total / 1024).toFixed(1)} KB. Nothing here leaves your browser. Server-side, FEELESS only stores public on-chain observations and anything you explicitly save with a connected wallet (watchlist, votes).</p>
    <div className="sovereignty-list">{keys.map(({ k, size }) => <div key={k} className="sovereignty-row"><code>{k}</code><small>{(size / 1024).toFixed(1)} KB</small><button type="button" className="icon-btn small-icon" title="Delete from this browser" onClick={() => clear(k)}><Trash2 size={13} /></button></div>)}</div>
    {keys.length > 1 && <button type="button" className="btn-outline" onClick={() => { keys.forEach(({ k }) => { try { localStorage.removeItem(k); } catch {} }); scan(); toast.success('All FEELESS browser data cleared'); }}><Trash2 size={13} />Clear all FEELESS data</button>}
  </section>;
}

