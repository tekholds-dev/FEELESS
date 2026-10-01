import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../../lib/api';

// Command Center › Fuse builder: search live pools (with their meta), weight them, name the Fuse, set the creator's cut
// of FEELESS fees on its buys, and track volume / earned / owed per Fuse. Every save is signed and audit-logged.
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${(v || 0).toFixed(2)}`);
const EMPTY = { name: '', emoji: '⚛️', tagline: '', creatorBps: 1000, legs: [] };

export function FuseBuilder({ call }) {
  const [d, setD] = useState(null);
  const [draft, setDraft] = useState(EMPTY);
  const [q, setQ] = useState(''); const [found, setFound] = useState([]);
  const load = () => call('/admin/fuses').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (q.trim().length < 2) { setFound([]); return undefined; }
    const t = setTimeout(() => fetch(apiUrl(`/api/reputation/fuses/search?q=${encodeURIComponent(q.trim())}`)).then(r => r.json()).then(x => setFound(x.pools || [])).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [q]);
  const add = p => setDraft(x => (x.legs.some(l => l.pairAddress === p.pairAddress) || x.legs.length >= (d?.maxLegs || 6) ? x : { ...x, legs: [...x.legs, { chainId: p.chainId, pairAddress: p.pairAddress, symbol: p.symbol, weight: 25, meta: p }] }));
  const save = async body => { try { await call('/admin/fuses', { method: 'POST', body: JSON.stringify(body) }); toast.success('Saved'); setDraft(EMPTY); load(); } catch (e) { toast.error(e.message); } };
  return <div className="cc-block fz-builder" data-testid="fuse-builder">
    <div className="m-row"><h4>⚛️ Fuse builder</h4><span className="m-dim">Fuse popular pools into one basket. Buyers fuse in leg by leg (their wallet signs each swap); the creator earns a cut of the FEELESS fee.</span></div>
    <div className="fz-admin-list">{(d?.fuses || []).map(f => <div key={f.id} className={`qe-row ${f.enabled === false ? 'is-off' : ''}`}><span className="fz-emoji">{f.emoji}</span>
      <div><b>{f.name}</b> <span className="m-chip">{f.score.grade}</span> <small className="m-dim">index {f.index} · {usd(f.tvlUsd)} depth · {f.stats.buys} buys · {usd(f.stats.volumeUsd)} volume</small>
        <div className="m-dim">Creator {String(f.creator).slice(0, 4)}…{String(f.creator).slice(-4)} · {f.creatorBps / 100}% of fees · earned {usd(f.stats.creatorEarnedUsd)} · owed {usd(f.stats.creatorOwedUsd)}</div></div>
      <div className="m-row"><button type="button" className="m-btn" onClick={() => setDraft({ id: f.id, name: f.name, emoji: f.emoji, tagline: f.tagline || '', creatorBps: f.creatorBps, legs: f.legs.map(l => ({ chainId: l.chainId, pairAddress: l.pairAddress, symbol: l.symbol, weight: l.weight, meta: l })) })}>Edit</button>
        {f.stats.creatorOwedUsd > 0 && <button type="button" className="m-btn" onClick={() => save({ id: f.id, paidUsd: f.stats.creatorOwedUsd })}>Mark {usd(f.stats.creatorOwedUsd)} paid</button>}
        <button type="button" className="m-btn" onClick={() => save({ id: f.id, name: f.name, emoji: f.emoji, tagline: f.tagline, creatorBps: f.creatorBps, legs: f.legs, enabled: f.enabled === false })}>{f.enabled === false ? 'Turn on' : 'Turn off'}</button>
        <button type="button" className="m-btn danger" onClick={() => window.confirm(`Delete ${f.name}?`) && save({ id: f.id, delete: true })}>Delete</button></div></div>)}
      {d && !d.fuses.length && <p className="m-dim">No Fuses yet — build the first one below.</p>}</div>
    <div className="m-card fz-draft"><div className="m-row"><input className="m-input fz-emoji-in" value={draft.emoji} onChange={e => setDraft({ ...draft, emoji: e.target.value })} aria-label="Emoji" />
      <input className="m-input" placeholder="Fuse name (e.g. FEE Core)" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} aria-label="Name" />
      <input className="m-input" placeholder="Tagline" value={draft.tagline} onChange={e => setDraft({ ...draft, tagline: e.target.value })} aria-label="Tagline" />
      <label className="m-field"><span>Creator cut of fees %</span><input className="m-input" type="number" min="0" max={(d?.maxCreatorBps || 5000) / 100} value={draft.creatorBps / 100} onChange={e => setDraft({ ...draft, creatorBps: Math.round(Number(e.target.value) * 100) })} /></label></div>
      {draft.legs.map((l, i) => <div key={l.pairAddress} className="m-row fz-draft-leg"><b>{l.symbol}</b><small className="m-dim">{l.meta ? `${usd(l.meta.liquidityUsd)} liq · ${usd(l.meta.volume24h)} vol · ${l.meta.aprEst}% APR est.` : ''}</small>
        <label className="m-field"><span>Weight</span><input className="m-input" type="number" min="1" value={l.weight} onChange={e => setDraft({ ...draft, legs: draft.legs.map((x, j) => (j === i ? { ...x, weight: Number(e.target.value) } : x)) })} /></label>
        <button type="button" className="m-btn danger" onClick={() => setDraft({ ...draft, legs: draft.legs.filter((_, j) => j !== i) })} aria-label="Remove pool">✕</button></div>)}
      <input className="m-input" placeholder="Search pools: SOL USDC, FEE, a ticker or address…" value={q} onChange={e => setQ(e.target.value)} aria-label="Search pools" data-testid="fuse-search" />
      {found.length > 0 && <div className="fz-found">{found.map(p => <button type="button" key={p.pairAddress} className="qb-tile" onClick={() => add(p)}><span><b>{p.symbol}/{p.quote} · {p.chainId}</b><small>{usd(p.liquidityUsd)} liq · {usd(p.volume24h)} vol · {p.aprEst}% APR est. · {p.turnover}× turnover · {p.dex}</small></span></button>)}</div>}
      <div className="m-row"><button type="button" className="m-btn primary" disabled={!draft.name || draft.legs.length < 2} onClick={() => save({ ...draft, legs: draft.legs.map(({ meta, ...l }) => l) })}>{draft.id ? 'Save Fuse' : 'Launch Fuse'}</button>
        {draft.id && <button type="button" className="m-btn" onClick={() => setDraft(EMPTY)}>Cancel</button>}<small className="m-dim">2–{d?.maxLegs || 6} pools · weights are normalised to 100%</small></div></div>
  </div>;
}
