import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/boosts.css';

// 🧊 THE STASH'S WEB (owner 2026-11-05): every dot is something it really holds, counted live. The middle is the Stash, the ring is what kind of thing, the outside is where it came from. No dot is drawn that the server did not count.
const CAT_COLOR = { Trades: '#3ee58a', Perps: '#a06bff', Picks: '#ffc24d', Content: '#ff8bd8', Code: '#7fd0ff', Snapshots: '#4fb8ff' };
const fmt = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n || 0));
export const bytes = n => (n >= 1e12 ? `${(n / 1e12).toFixed(1)} TB` : n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : n >= 1e3 ? `${Math.round(n / 1e3)} KB` : `${n || 0} B`);
// A browser without WebGL2 cannot load the map at all: the numbers below still stand, so it gets a line instead of a crash.
const StashMap = lazy(() => import('./StashMap').catch(() => ({ default: () => <p className="stw-none">Your browser could not draw the map. The numbers below are still right.</p> })));
export function layoutWeb(web) {
  const cats = web?.categories || []; const srcs = web?.sources || []; const links = web?.links || []; const nodes = [{ id: '__stash', kind: 'root', n: cats.reduce((a, c) => a + c.n, 0), label: 'The Stash', color: '#e6f6ff' }]; const at = {};
  cats.forEach(c => { const node = { id: c.id, kind: 'cat', n: c.n, label: c.id, color: CAT_COLOR[c.id] || '#9fb0d6' }; nodes.push(node); at[c.id] = node; });
  srcs.forEach(s => { const home = links.filter(l => l.to === s.id).sort((a, b) => b.n - a.n)[0]; const node = { id: `src:${s.id}`, kind: 'src', n: s.n, label: s.id, color: at[home?.from]?.color || '#9fb0d6', at: s.at }; nodes.push(node); at[`src:${s.id}`] = node; });
  const edges = [...cats.map(c => [nodes[0], at[c.id]]), ...links.filter(l => at[l.from] && at[`src:${l.to}`]).map(l => [at[l.from], at[`src:${l.to}`]])];
  (web?.dots || []).forEach(([cat, src, out], i) => { const home = at[`src:${src}`] || at[cat]; if (!home) return; const node = { id: `dot:${i}`, kind: 'dot', n: 1, label: '', color: out === 'won' ? '#3df08f' : out === 'lost' ? '#ff6f8e' : '#9dbcff' }; nodes.push(node); edges.push([home, node]); });
  return { nodes, edges };
}
export function StashWeb({ call = null, onClose = null, testid = 'stash-web' }) {
  const [d, setD] = useState(null); const [pick, setPick] = useState(null); const seen = useRef(0);
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; const p = call ? call('/admin/stash') : fetch(apiUrl('/api/cats/stash/web')).then(r => (r.ok ? r.json() : null)); Promise.resolve(p).then(j => { if (on && j) { setD(j); } }).catch(() => {}); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const { nodes, edges } = useMemo(() => layoutWeb(d?.web), [d]); const st = d?.stats; const grew = st ? st.items - seen.current : 0; useEffect(() => { if (st) seen.current = st.items; }, [st]);
  const on = pick && nodes.find(n => n.id === pick);
  return <section className="stw" data-testid={testid}><header><span><small>THE COLLECTIVE STASH</small><b className="m-num">{st ? `${fmt(st.items)} kept` : 'Reading…'}</b></span><p>Every proof, won or lost, kept for good. Nothing private: no emails, phones or signed-in pages.</p>{onClose ? <button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close (Esc)">✕</button> : null}</header>
    <div className="stw-map"><Suspense fallback={<div className="stw-sigma" />}><StashMap nodes={nodes} edges={edges} onPick={setPick} /></Suspense>
      {st && !st.items ? <p className="stw-none">Its first hourly pass fills this in. It only draws what it really holds.</p> : null}
      {on ? <div className="stw-card" data-testid="stw-card"><b>{on.label}</b><small className="m-num">{fmt(on.n)} kept</small></div> : null}</div>
    {st ? <div className="stw-tiles">{[['AGENTS', st.agents, 'Agents whose proofs are in it'], ['SOURCES', st.sources, 'Different sites its proofs read'], ['WON', st.outcomes?.won || 0, 'Kept'], ['LOST', st.outcomes?.lost || 0, 'Kept too. Losses teach as much as wins'], ['TODAY', st.lastDay, 'Added in the last 24 hours'], ...(st.storedBytes != null ? [['ON DISK', bytes(st.storedBytes), `From ${bytes(st.rawBytes)} before compressing`], ['ROOM LEFT', bytes(st.freeBytes), 'On this machine. It can mirror to free cloud storage once you add an account']] : [])].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div> : null}</section>;
}
