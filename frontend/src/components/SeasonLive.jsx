import React, { useEffect, useRef, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { evAgo } from './Crews';
import '../styles/seasonLive.css';

// 🏁 SEASON LIVE (owner, 2026-10-20: "finish the season tab — more versatile with every social event and cool vitals"): one hub on top of the
// Seasons page — a countdown that ticks, the race vitals (leader, the gap, players, families, Fuse cards racing) and ONE feed with lenses across
// every social event FEELESS records: player rank moves (seen live between reads), family events (/crews/live) and the Fuse season (cards
// opened, rank moves, past champions). Every line is a real event; nothing is made up to fill the feed.
export const LENSES = [['all', '⚡ All'], ['players', '🏆 Players'], ['families', '🌹 Families'], ['fuse', '⚛ Fuse']];
export const clock = s => { if (s == null || s < 0) return '—'; const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), x = Math.floor(s % 60);
  return d ? `${d}d ${String(h).padStart(2, '0')}h ${String(m).padStart(2, '0')}m` : `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}`; };
// rank moves between two board reads → events
export function rankMoves(prev, next, now) {
  if (!prev?.length) return [];
  const was = Object.fromEntries(prev.map(r => [r.address, r.rank]));
  return (next || []).filter(r => was[r.address] && was[r.address] !== r.rank).map(r => ({ lens: 'players', at: now, icon: r.rank < was[r.address] ? '🔼' : '🔽',
    text: `@${r.handle || r.name} ${r.rank < was[r.address] ? 'climbed' : 'slipped'} to #${r.rank} (${Number(r.score).toLocaleString()} pts)`, key: `rk-${r.address}-${r.rank}-${now}` }));
}
export function fuseEvents(fs, now) {
  const out = [];
  for (const m of fs?.moves || []) out.push({ lens: 'fuse', at: m.at || now, icon: m.up ? '🔼' : '🔽', text: m.text || `${m.name || 'a card'} → #${m.rank}`, key: `fm-${m.id || m.name}-${m.at}` });
  for (const c of (fs?.cards || []).slice(0, 5)) if (c.openedAt || c.at) out.push({ lens: 'fuse', at: c.openedAt || c.at, icon: '⚛', text: `${c.name || 'a card'} joined the Fuse race${c.pct != null ? ` · ${c.pct > 0 ? '+' : ''}${Number(c.pct).toFixed(1)}%` : ''}`, key: `fc-${c.id}` });
  for (const p of (fs?.past || []).slice(0, 3)) out.push({ lens: 'fuse', at: p.at || p.crownedAt || now - 86400, icon: '👑', text: `${p.name || p.card || 'a card'} won ${p.week || 'a Fuse week'}`, key: `fp-${p.week}-${p.name}` });
  return out;
}

export function SeasonLive({ d }) {
  const [lens, setLens] = useState('all'); const [fam, setFam] = useState(null); const [fs, setFs] = useState(null); const [moves, setMoves] = useState([]);
  const [t, setT] = useState(() => Date.now()); const prev = useRef(null); const base = useRef({ at: Date.now(), left: d?.endsIn });
  useEffect(() => { base.current = { at: Date.now(), left: d?.endsIn }; const top = d?.top || [];
    const mv = rankMoves(prev.current, top, Date.now() / 1000); if (mv.length) setMoves(x => [...mv, ...x].slice(0, 30)); prev.current = top; }, [d]);
  useEffect(() => { const i = setInterval(() => { if (!document.hidden) setT(Date.now()); }, 1000); return () => clearInterval(i); }, []);
  useEffect(() => { let on = true; const load = () => { sharedJson('/api/reputation/crews/live', { maxAge: 15000 }).then(x => on && x && setFam(x)).catch(() => {});
    sharedJson('/api/reputation/fuses/season', { maxAge: 30000 }).then(x => on && x && setFs(x)).catch(() => {}); };
    load(); const i = setInterval(() => { if (!document.hidden) load(); }, 30000); return () => { on = false; clearInterval(i); }; }, []);
  const top = d?.top || []; const left = base.current.left == null ? null : base.current.left - (t - base.current.at) / 1000;
  const gap = top.length > 1 ? top[0].score - top[1].score : null; const me = d?.me;
  const fusLeft = fs?.endsAt ? fs.endsAt - t / 1000 : null;
  const tiles = [['⏳ SEASON ENDS', clock(left), 'tick'], ['🥇 LEADER', top[0] ? `@${top[0].handle || top[0].name}` : '—', ''], ['📏 #1 LEAD', gap == null ? '—' : `${Math.round(gap).toLocaleString()} pts`, ''],
    ['🎯 YOU', me?.rank ? `#${me.rank} · ${me.tier}` : me ? me.tier : 'connect', ''], ['👥 PLAYERS', String(d?.players ?? '—'), ''], ['🌹 FAMILIES', String(fam?.vitals?.families ?? '—'), ''],
    ['⚛ FUSE WEEK', fusLeft != null ? clock(fusLeft) : '—', 'tick'], ['🃏 CARDS RACING', String((fs?.cards || []).length || 0), '']];
  const feed = [...moves, ...(fam?.events || []).map(e => ({ lens: 'families', at: e.at, icon: { founded: '🌹', joined: '🤝', badge: '🛡', bounty: '🎯', claimed: '✋', paid: '💰', launch: '🚀', crown: '👑' }[e.kind] || '•',
    text: `[${e.fam}] ${e.text}`, key: `fe-${e.kind}-${e.id}-${e.at}` })), ...fuseEvents(fs, t / 1000)]
    .filter(e => lens === 'all' || e.lens === lens).sort((a, b) => b.at - a.at).slice(0, 18);
  const counts = { players: moves.length, families: (fam?.events || []).length, fuse: fuseEvents(fs, 0).length };
  return <section className="sl m-card m-live" data-testid="season-live">
    <header><span className="sl-live"><i />LIVE</span><b>SEASON HUB</b><small>every event FEELESS records, as it happens</small></header>
    <div className="sl-tiles">{tiles.map(([k, v, c], i) => <span key={k} className={c ? `is-${c}` : ''} style={{ '--i': i }}><em>{k}</em><b key={c ? undefined : v}>{v}</b></span>)}</div>
    {top.length ? <div className="sl-race" aria-label="the top of the board">{top.slice(0, 5).map((r, i) => <div key={r.address} className="sl-lane" style={{ '--i': i }}>
      <span className="sl-pos">{['🥇', '🥈', '🥉'][i] || `#${i + 1}`}</span><b>@{r.handle || r.name}</b>
      <i className="sl-track"><u style={{ transform: `scaleX(${Math.max(0.03, r.score / Math.max(1, top[0].score))})` }} /></i><small>{Number(r.score).toLocaleString()}</small></div>)}</div> : null}
    <nav className="sl-lens m-seg" role="tablist">{LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`sl-lens-${k}`}>
      {l}{k !== 'all' && counts[k] ? <i>{counts[k]}</i> : null}</button>)}</nav>
    {feed.length ? <ol className="sl-feed">{feed.map((e, i) => <li key={e.key} className={`l-${e.lens}`} style={{ '--i': i }}><i>{e.icon}</i><span>{e.text}</span><small>{evAgo(e.at)}</small></li>)}</ol>
      : <p className="sl-empty">{lens === 'players' ? 'Rank moves show up here the moment they happen — keep this open.' : 'Nothing yet in this lens.'}</p>}
  </section>;
}
