import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import '../../styles/stashBrain.css';

// 🧠 Proofs › Stash brain (Slice 10, owner 2026-11-18: "the stash grows boastfully"). Every page a mind loads is kept sealed (scrape, static page,
// screenshot) and sorted by everything on it; brains ask it first. This panel shows how it grows and what it saves, by category. Counts, categories and
// freshness only: no page, address or number from a page ever reaches it (the API sends none).
const API = '/api/cats/proofs/stash-brain';
const CAT = { nba: 'NBA', nfl: 'NFL', nhl: 'NHL', mlb: 'MLB', ncaa: 'NCAA', soccer: 'Soccer', ufc: 'UFC', coins: 'Coins', markets: 'Markets', search: 'Searches', web: 'Web' };
const KIND = { pob: 'PoB', pow: 'PoW', pop: 'PoP', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const usd = v => (v > 0 ? `$${v < 0.01 ? v.toFixed(4) : v.toFixed(2)}` : '$0');
const secs = v => (!v ? '0 s' : v >= 5400 ? `${(v / 3600).toFixed(1)} h` : v >= 90 ? `${Math.round(v / 60)} min` : `${Math.round(v)} s`);
const size = b => (b >= 1e9 ? `${(b / 1e9).toFixed(1)} GB` : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : b >= 1e3 ? `${Math.round(b / 1e3)} KB` : `${b || 0} B`);
const ago = at => { const s = Math.max(0, Date.now() / 1000 - at); return !at ? '—' : s < 90 ? 'just now' : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 129600 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`; };
const pct = v => `${Math.round((v || 0) * 100)}%`;
const tipStyle = { background: 'var(--m-surface)', border: '1px solid var(--m-line)', borderRadius: 10, fontSize: 11, fontFamily: 'var(--f-mono)' };

export function stashVerdict(d) {
  if (!d?.pages) return 'Empty so far. The first page a mind reads starts it.';
  const reads = (d.hits || 0) + (d.browsed || 0);
  if (!d.hits) return `${d.pages.toLocaleString()} pages kept, sealed. No brain has reused one yet: the next run on a related topic will.`;
  return `The stash answered ${pct(d.hits / Math.max(1, reads))} of ${reads.toLocaleString()} page reads, and saved ${secs(d.savedSecs)} and ${usd(d.paidEqUsd)} a paid mind would have spent.`;
}

function Meter({ v, label, tip, tone }) {
  return <span className={`sbr-meter${tone ? ` is-${tone}` : ''}`} data-tip={tip}><small>{label}</small><i><b style={{ transform: `scaleX(${Math.max(0, Math.min(1, v || 0))})` }} /></i></span>;
}

export function StashBrain() {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [lens, setLens] = useState('cats');
  const load = useCallback(() => fetch(API).then(r => (r.ok ? r.json() : Promise.reject(new Error(`The stash did not answer (${r.status}).`)))).then(j => { setD(j); setErr(''); }).catch(e => setErr(e.message || 'Could not read the stash.')), []);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => clearInterval(t); }, [load]);
  const grow = useMemo(() => (d?.days || []).map(x => ({ day: x.day.slice(5), total: x.total, added: x.added })), [d]);
  if (err && !d) return <p className="sbr-none" data-testid="sbr-err">{err}</p>;
  if (!d) return <p className="sbr-none">Reading the stash…</p>;
  const C = 2 * Math.PI * 22; const top = Math.max(1, ...(d.cats || []).map(c => c.pages));
  return <section className="sbr m-card m-live" data-testid="sbr">
    <header className="sbr-top">
      <svg className="sbr-ring" viewBox="0 0 56 56" aria-hidden="true"><circle cx="28" cy="28" r="22" /><circle cx="28" cy="28" r="22" className="is-fg" strokeDasharray={`${C * (d.hitRate || 0)} ${C}`} transform="rotate(-90 28 28)" /><text x="28" y="32" textAnchor="middle">{pct(d.hitRate)}</text></svg>
      <div className="sbr-sum"><span className="m-label">STASH BRAIN · SEALED BY CATEGORY · BRAINS ONLY</span>
        <p className="sbr-say" data-testid="sbr-say">{stashVerdict(d)}</p>
        <div className="sbr-stats">{[['Pages', d.pages.toLocaleString(), 'Every public page a mind loaded, kept as scrape + static page + screenshot'], ['Hits', d.hits, 'Pages a brain took from the stash instead of browsing', 'up'], ['Browsed', d.browsed, 'Pages that were missing or stale, so they were browsed (and kept)'], ['Saved', secs(d.savedSecs), 'Browser and step time the hits did not spend', 'up'], ['Paid-eq', usd(d.paidEqUsd), 'What a paid mind would have spent on the steps it skipped. Real $ saved: ' + usd(d.savedUsd)], ['Size', size(d.bytes), 'Sealed on disk']].map(([k, v, tip, t]) => <span key={k} className={t ? `is-${t}` : ''} data-tip={tip}><small>{k}</small><b className="m-num">{v}</b></span>)}</div></div>
    </header>
    <div className="sbr-grow" data-tip="Pages kept, total, over the last 14 days"><ResponsiveContainer width="100%" height={120}>
      <AreaChart data={grow} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
        <defs><linearGradient id="sbrFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--m-accent)" stopOpacity={0.45} /><stop offset="100%" stopColor="var(--m-accent)" stopOpacity={0} /></linearGradient></defs>
        <XAxis dataKey="day" tick={{ fontSize: 9, fill: 'var(--m-dim)' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 9, fill: 'var(--m-dim)' }} tickLine={false} axisLine={false} width={34} allowDecimals={false} />
        <Tooltip contentStyle={tipStyle} formatter={(v, k) => [v, k === 'total' ? 'pages kept' : 'added']} />
        <Area type="monotone" dataKey="total" stroke="var(--m-accent)" strokeWidth={2} fill="url(#sbrFill)" isAnimationActive={false} />
      </AreaChart></ResponsiveContainer></div>
    <div className="m-seg sbr-lens" role="tablist" aria-label="Show">{[['cats', 'By category'], ['runs', 'Last runs']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-tip={k === 'cats' ? 'Growth, hit rate and $ saved per category' : 'Hits vs pages browsed, per run'}>{l}</button>)}</div>
    {lens === 'cats' ? (d.cats?.length ? <ol className="sbr-list" data-testid="sbr-cats">{d.cats.map((c, i) => <li key={c.cat} className="sbr-cat" style={{ '--i': i }} data-testid={`sbr-cat-${c.cat}`}>
      <div className="sbr-cat-head"><b>{CAT[c.cat] || c.cat}</b><span className="m-num">{c.pages.toLocaleString()} pages · {size(c.bytes)}</span><small>last read {ago(c.lastAt)}</small></div>
      <Meter v={c.pages / top} label={`share ${pct(c.pages / Math.max(1, d.pages))}`} tip="Its share of everything kept" />
      <Meter v={c.hitRate} label={`hit rate ${pct(c.hitRate)} · ${c.hits} hits / ${c.browsed} browsed`} tip="How often a brain's read came from the stash" tone="up" />
      <Meter v={c.fresh / Math.max(1, c.pages)} label={`fresh now ${c.fresh}`} tip="Pages still fresh enough to serve (live odds age in minutes, a roster in hours)" />
      <div className="sbr-cat-foot"><span data-tip="Every number on its pages, kept beside the words that name it">{c.numbers.toLocaleString()} numbers</span><span data-tip="Screenshots / static pages kept">{c.shots} shots · {c.statics} static</span><span className="is-up" data-tip={`Real $ saved ${usd(c.savedUsd)}`}>saved {secs(c.savedSecs)} · {usd(c.paidEqUsd)} paid-eq</span></div>
    </li>)}</ol> : <p className="sbr-none">Nothing kept yet.</p>)
      : (d.runs?.length ? <ol className="sbr-list" data-testid="sbr-runs">{d.runs.map((r, i) => { const n = Math.max(1, r.hits + r.browsed); return <li key={`${r.at}${i}`} className="sbr-run" style={{ '--i': i }}>
        <span className="sbr-kind">{KIND[r.kind] || (r.proof ? 'Proof' : 'Task')}</span>
        <span className="sbr-split" data-tip={`${r.hits} from the stash, ${r.browsed} browsed`}><b className="is-hit" style={{ flexGrow: r.hits }} /><b className="is-br" style={{ flexGrow: r.browsed || (r.hits ? 0 : 1) }} /></span>
        <span className="m-num sbr-run-n">{r.hits}/{n}</span><small>{secs(r.savedSecs)} · {ago(r.at)}</small></li>; })}</ol> : <p className="sbr-none">No run has used the stash yet.</p>)}
    <p className="sbr-seal">🔒 Each category has its own key. Only a brain inside a run can open a page; people see these counts, never what was read.</p>
  </section>;
}
