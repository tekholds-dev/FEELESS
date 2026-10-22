import React, { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';

// 🧭 The HUD around the Familia cities: the five-city rail (Fee City the widest), one chat per city where every line wears its family tag,
// Call-of-Duty style rank emblems (drawn: a shield, chevrons for the division, a crown for the Dons) and the ranked ladder.
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
const DIV = { III: 1, II: 2, I: 3 };

export function RankBadge({ rank, size = 'md' }) {
  if (!rank) return null;
  const don = String(rank.div || '').startsWith('#');
  return <span className={`fh-emb t-${rank.tier} s-${size} ${don ? 'is-don' : ''}`} data-tip={`${rank.name} ${rank.div}${rank.next ? ` · next division at ${n(rank.next)} power` : ''}`} data-testid="rank-badge">
    <i aria-hidden="true">{don ? <b className="fh-crown" /> : Array.from({ length: DIV[rank.div] || 1 }, (_, k) => <b key={k} className="fh-chev" />)}</i>
    {size !== 'sm' ? <span><em>{rank.name}</em><small>{rank.div}</small></span> : null}</span>;
}

export function CityRail({ cities, city, onGo }) {
  return <nav className="fh-rail" role="tablist" aria-label="Cities" data-testid="city-rail">{(cities || []).map((c, i) => <button key={c.key} type="button" role="tab" aria-selected={city === c.key}
    className={`fh-city k-${c.key} ${city === c.key ? 'active' : ''}`} style={{ '--i': i }} onClick={() => onGo(c.key)} data-testid={`city-${c.key}`} data-tip={`${c.name} — ${c.vibe}`}>
    <b>{c.name}</b><small>{c.vibe}</small><u><s style={{ transform: `scaleX(${c.plots ? Math.max(0.02, c.held / c.plots) : 0})` }} /></u><em key={c.held}>{c.held}/{c.plots} held</em></button>)}</nav>;
}

export function CityChat({ city, name, addr, sess }) {
  const room = `city-${city}`; const [msgs, setMsgs] = useState([]); const [t, setT] = useState(''); const [busy, setBusy] = useState(false); const end = useRef(null);
  useEffect(() => { let on = true;
    const go = () => fetch(apiUrl(`/api/reputation/chat/${room}`)).then(r => (r.ok ? r.json() : null)).then(d => { if (on && d) setMsgs((d.messages || []).slice(-40)); }).catch(() => {});
    go(); const p = setInterval(() => { if (!document.hidden) go(); }, 8000); return () => { on = false; clearInterval(p); }; }, [room]);
  useEffect(() => { const el = end.current; if (el?.parentNode) el.parentNode.scrollTop = el.parentNode.scrollHeight; }, [msgs]);
  const send = async e => {
    e.preventDefault(); if (!t.trim()) return;
    if (!addr || !sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(true);
    try { const r = await fetch(apiUrl('/api/reputation/chat'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ room, address: addr, text: t.trim(), ts: Math.floor(Date.now() / 1000), session: sess }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Could not post'); setT(''); setMsgs(m => [...m, j.message].slice(-40)); }
    catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  return <section className="fh-chat m-card" data-testid="city-chat">
    <header><b>💬 {name}</b><small>{msgs.length ? `${msgs.length} lines · live` : 'quiet streets'}</small></header>
    <ol>{msgs.map(m => <li key={m.id}>{m.fam ? <i style={{ '--fc': m.fam.color || '#d4af37' }}>{m.fam.tag}</i> : <i className="is-free">free</i>}<b>{m.username || m.handle || 'anon'}</b><span>{m.text}</span></li>)}
      {!msgs.length ? <li className="fh-nil">No one's talking in {name} yet. Say something — your family tag rides with you.</li> : null}<li ref={end} aria-hidden="true" className="fh-end" /></ol>
    <form onSubmit={send}><input className="m-input" value={t} maxLength={280} onChange={e => setT(e.target.value)} placeholder={`Talk in ${name}…`} aria-label={`Chat in ${name}`} />
      <button type="submit" className="m-btn" disabled={busy || !t.trim()} data-tip="Post to this city's street chat">Send</button></form>
  </section>;
}

export function RankLadder({ ranked, mine }) {
  const top = Math.max(1, ...(ranked || []).map(r => r.power || 0));
  return <section className="fh-ladder m-card" data-testid="rank-ladder">
    <header><span className="m-label">🎖 RANKED · FAMILY POWER</span><small>Street Rat → Kingpin in three divisions each · the top 25 Kingpins are Dons of Fee City</small></header>
    {(ranked || []).length ? <ol>{ranked.map((r, i) => <li key={r.id} className={r.id === mine ? 'is-mine' : ''} style={{ '--i': i }}>
      <b className="fh-place">{r.place}</b><RankBadge rank={r.rank} size="sm" /><span><em>[{r.tag}] {r.name}</em><small>{r.rank.name} {r.rank.div}</small></span>
      <u><s style={{ transform: `scaleX(${Math.max(0.02, (r.power || 0) / top)})` }} /></u><strong key={r.power}>{n(r.power)}</strong></li>)}</ol>
      : <p className="m-dim">No families ranked yet — the first Don takes the city.</p>}
  </section>;
}
