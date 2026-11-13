import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import '../../styles/boosts.css';

// 🧊 THE STASH'S WEB (owner 2026-11-05): every dot is something it really holds, counted live. The middle is the Stash, the ring is what kind of thing, the outside is where it came from. No dot is drawn that the server did not count.
const CAT_COLOR = { Trades: '#3ee58a', Perps: '#a06bff', Picks: '#ffc24d', Content: '#ff8bd8', Code: '#7fd0ff', Snapshots: '#4fb8ff', Builds: '#19e68c' };   // 🧰 COL-10: every Claude build
const fmt = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n || 0));
export const bytes = n => (n >= 1e12 ? `${(n / 1e12).toFixed(1)} TB` : n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : n >= 1e3 ? `${Math.round(n / 1e3)} KB` : `${n || 0} B`);
// A browser without WebGL2 cannot load the map at all: the numbers below still stand, so it gets a line instead of a crash.
const StashMap = lazy(() => import('./StashMap').catch(() => ({ default: () => <p className="stw-none">Your browser could not draw the map. The numbers below are still right.</p> })));
export function layoutWeb(web) {
  const cats = web?.categories || []; const srcs = web?.sources || []; const links = web?.links || []; const nodes = [{ id: '__stash', kind: 'root', n: cats.reduce((a, c) => a + c.n, 0), label: 'The Stash', color: '#e6f6ff' }]; const at = {};
  cats.forEach(c => { const node = { id: c.id, kind: 'cat', n: c.n, label: c.id, color: CAT_COLOR[c.id] || '#9fb0d6' }; nodes.push(node); at[c.id] = node; });
  srcs.forEach(s => { const home = links.filter(l => l.to === s.id).sort((a, b) => b.n - a.n)[0]; const node = { id: `src:${s.id}`, kind: 'src', n: s.n, label: /^n\d+$/.test(s.id) ? '' : s.id, home: home?.from, color: at[home?.from]?.color || '#9fb0d6', at: s.at }; nodes.push(node); at[`src:${s.id}`] = node; });
  const edges = [...cats.map(c => [nodes[0], at[c.id]]), ...links.filter(l => at[l.from] && at[`src:${l.to}`]).map(l => [at[l.from], at[`src:${l.to}`]])];
  (web?.dots || []).forEach(([cat, src, out], i) => { const home = at[`src:${src}`] || at[cat]; if (!home) return; const node = { id: `dot:${i}`, kind: 'dot', n: 1, label: '', color: out === 'won' ? '#3df08f' : out === 'lost' ? '#ff6f8e' : '#9dbcff' }; nodes.push(node); edges.push([home, node]); });
  return { nodes, edges };
}
// 🔥 Who is on the webs now, one shared poll while a web is open. Only names agents and folders.
export function useWebLive() {
  const [d, setD] = useState({ live: [], stored: [] });
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; let q = ''; try { q = agentAuth()?.session ? `?session=${encodeURIComponent(agentAuth().session)}` : ''; } catch { q = ''; } fetch(apiUrl(`/api/cats/web/live${q}`)).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j) setD(j); }).catch(() => {}); }; go(); const t = setInterval(go, 8000); return () => { on = false; clearInterval(t); }; }, []);
  return d;
}
// The words beside a web: every agent working now, then what was just stored.
export function WebFeed({ d, empty = 'No agent is working right now.' }) {
  const rows = [...(d.live || []).map(r => ({ who: r.agent, what: r.does, where: r.feature ? r.feature.replace('/', ' › ') : r.folder, on: true })), ...(d.stored || []).map(r => ({ who: r.agent, what: `stored ${r.outcome === 'won' ? 'a win' : r.outcome === 'lost' ? 'a loss' : 'a proof'}`, where: r.folder }))].slice(0, 7);
  return <ul className="stw-feed" data-testid="web-feed" aria-live="polite">{rows.length ? rows.map((r, i) => <li key={`${r.who}-${i}`} className={r.on ? 'is-on' : ''}><i aria-hidden="true" /><b>{r.who}</b><span>{r.what}</span>{r.where ? <small className="m-num">{r.where}</small> : null}</li>) : <li className="is-empty">{empty}</li>}</ul>;
}
const firstBy = (rows, keyOf) => { const seen = {}; return rows.filter(r => { const k = keyOf(r); if (!k || seen[k]) return false; seen[k] = 1; return true; }); };
export function StashWeb({ call = null, onClose = null, testid = 'stash-web' }) {
  const [d, setD] = useState(null); const [pick, setPick] = useState(null); const seen = useRef(0);
  useEffect(() => { let on = true; const go = () => { if (document.hidden) return; const p = call ? call('/admin/stash') : fetch(apiUrl('/api/cats/stash/web')).then(r => (r.ok ? r.json() : null)); Promise.resolve(p).then(j => { if (on && j) { setD(j); } }).catch(() => {}); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const { nodes, edges } = useMemo(() => layoutWeb(d?.web), [d]); const st = d?.stats; const grew = st ? st.items - seen.current : 0; useEffect(() => { if (st) seen.current = st.items; }, [st]);
  const [over, setOver] = useState(null); const on = pick && nodes.find(n => n.id === pick); const shown = (over && nodes.find(n => n.id === over)) || on; const wl = useWebLive(); const ids = new Set(nodes.map(n => n.id));
  const live = firstBy([...(wl.live || []).map(r => ({ node: r.host && ids.has(`src:${r.host}`) ? `src:${r.host}` : r.folder || r.feature?.split('/')[0], label: r.agent })), ...(wl.stored || []).map(r => ({ node: ids.has(`src:${r.source}`) ? `src:${r.source}` : r.folder, label: r.agent, tone: r.outcome === 'lost' ? 'dn' : 'up' }))].filter(r => ids.has(r.node)), r => r.node);
  return <section className="stw" data-testid={testid}><header><span><small>THE COLLECTIVE STASH</small><b className="m-num">{st ? `${fmt(st.items)} kept` : 'Reading…'}</b></span><p>Every proof, won or lost, kept for good. Hover to see where it routes. The details stay in the Collective's private git.</p>{onClose ? <button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close (Esc)">✕</button> : null}</header>
    <div className="stw-map"><Suspense fallback={<div className="stw-sigma" />}><StashMap nodes={nodes} edges={edges} onPick={setPick} onHover={setOver} live={live} /></Suspense>
      {st && !st.items ? <p className="stw-none">Its first hourly pass fills this in. It only draws what it really holds.</p> : null}
      {shown ? <div className="stw-card" data-testid="stw-card"><b>{shown.label || (shown.kind === 'dot' ? 'One proof' : `A source in ${shown.home || 'the record'}`)}</b><small className="m-num">{fmt(shown.n)} kept{shown.kind === 'cat' ? ` · routes to ${edges.filter(([a, b]) => a.id === shown.id && b.kind === 'src').length} sources` : ''}</small></div> : null}</div><WebFeed d={wl} />
    {st ? <div className="stw-tiles">{[['AGENTS', st.agents, 'Agents whose proofs are in it'], ['SOURCES', st.sources, 'Different sites its proofs read'], ['WON', st.outcomes?.won || 0, 'Kept'], ['LOST', st.outcomes?.lost || 0, 'Kept too. Losses teach as much as wins'], ['TODAY', st.lastDay, 'Added in the last 24 hours'], ...(st.storedBytes != null ? [['ON DISK', bytes(st.storedBytes), `From ${bytes(st.rawBytes)} before compressing`], ['ROOM LEFT', bytes(st.freeBytes), 'On this machine. It can mirror to free cloud storage once you add an account']] : [])].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div> : null}</section>;
}

// 🕸 WHAT THE COLLECTIVE OFFERS (owner 2026-11-05): folders, and the kinds of feature in each. Every site is one unnamed dot, and nothing here can be clicked. When an agent codes or reads, its name rides on the feature it is using.
const FOLDER_COLOR = { ...CAT_COLOR, Picks: '#ffc24d', Research: '#9fe870' };
export function layoutSources(w) {
  const nodes = [{ id: '__root', kind: 'root', n: (w?.dots || []).length, label: 'The Collective', color: '#e6f6ff' }]; const edges = []; const at = {};
  (w?.folders || []).forEach(f => { const n = { id: f.id, kind: 'cat', n: f.n, label: f.id, color: FOLDER_COLOR[f.id] || '#9fb0d6' }; nodes.push(n); at[f.id] = n; edges.push([nodes[0], n]); });
  (w?.features || []).forEach(f => { const n = { id: f.id, kind: 'src', n: f.n, label: f.name, color: at[f.folder]?.color || '#9fb0d6' }; nodes.push(n); at[f.id] = n; if (at[f.folder]) edges.push([at[f.folder], n]); });
  (w?.dots || []).forEach((fid, i) => { if (!at[fid]) return; const n = { id: `dot:${i}`, kind: 'dot', n: 1, label: '', color: at[fid].color }; nodes.push(n); edges.push([at[fid], n]); });
  return { nodes, edges };
}
export function SourcesWeb() {
  const [w, setW] = useState(null); const wl = useWebLive();
  useEffect(() => { let on = true; fetch(apiUrl('/api/cats/sources/web')).then(r => (r.ok ? r.json() : null)).then(j => on && setW(j)).catch(() => {}); return () => { on = false; }; }, []);
  const { nodes, edges } = useMemo(() => layoutSources(w), [w]); const ids = new Set(nodes.map(n => n.id));
  const live = firstBy((wl.live || []).map(r => ({ node: r.feature && ids.has(r.feature) ? r.feature : r.folder || r.feature?.split('/')[0], label: r.agent })).filter(r => ids.has(r.node)), r => r.node);
  return <section className="stw stw-src" data-testid="sources-web"><header><span><small>WHAT THE COLLECTIVE OFFERS</small><b className="m-num">{w ? `${w.folders.length} folders · ${w.features.length} features` : 'Reading…'}</b></span><p>What your agent can draw on when it works. Its name lights up here on whatever it is using right now.</p></header>
    <div className="stw-map"><Suspense fallback={<div className="stw-sigma" />}><StashMap nodes={nodes} edges={edges} onPick={null} live={live} testid="src-sigma" allLabels /></Suspense></div><WebFeed d={wl} /></section>;
}
