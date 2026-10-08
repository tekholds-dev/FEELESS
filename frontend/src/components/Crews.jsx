import React, { Suspense, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import '../styles/crews.css';

// 🛡 CREWS (Leaderboard › Crews): 2–8 wallets, an invite code, a members-only-post room, and a weekly board ranked by what members' VERIFIED FEELESS trades
// did over 7 days (price result, fees apart). A crew shares no money — everyone signs their own trades. GET /crews · /crews/mine · POST create / join / leave.
const EcosystemChat = React.lazy(() => import('./EcosystemChat'));
export const pctTxt = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
export const inviteLink = (origin, path, code) => `${origin}${path}?lens=crews&join=${encodeURIComponent(code)}`;
export const rankNote = r => (r.ranked ? `${r.trades} trades · ${r.wonPct}% won` : r.members < 2 ? 'needs 2+ members to rank' : `${r.trades}/5 trades to rank`);
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });

export function Crews() {
  const { wallet } = useWallet() || {}; const addr = wallet?.address || ''; const sess = addr ? readChatSession(addr) : '';
  const [board, setBoard] = useState(null); const [mine, setMine] = useState(undefined); const [busy, setBusy] = useState(false);
  const [name, setName] = useState(''); const [tag, setTag] = useState(''); const [code, setCode] = useState(() => { try { return new URLSearchParams(window.location.search).get('join') || ''; } catch { return ''; } });
  const loadBoard = fresh => sharedJson('/api/reputation/crews', { maxAge: 30000, fresh }).then(setBoard).catch(() => {});
  const loadMine = () => { if (!addr || !sess) { setMine(null); return Promise.resolve(); } return fetch(apiUrl(`/api/reputation/crews/mine?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : { crew: null })).then(d => setMine(d.crew || null)).catch(() => setMine(null)); };
  useEffect(() => { loadBoard(); loadMine(); }, [addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (path, body, ok) => {
    if (!sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(true);
    try { const r = await post(path, { address: addr, session: sess, ...body }); toast.success(ok); if (r.crew) setMine(r.crew); else setMine(null); sharedJson.freshAt = Date.now(); loadBoard(true); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const rows = board?.board || [];
  return <section className="crw" data-testid="crews">
    <div className="crw-mine m-card m-live">
      {mine ? <>
        <header><span className="m-label">🛡 YOUR CREW</span><b className="crw-name">[{mine.tag}] {mine.name}</b><small>{mine.members.length}/{mine.max} members</small>
          <button type="button" className="m-btn" disabled={busy} onClick={() => act('/api/reputation/crews/leave', {}, 'Left the crew')} data-testid="crew-leave">Leave</button></header>
        <ul className="crw-mem">{mine.members.map(m => <li key={m.address}><a href={`/terminal/profile/${m.address}`}>{m.name}{m.owner ? ' 👑' : ''}</a><em className={m.pct == null ? '' : m.pct >= 0 ? 'm-pos' : 'm-neg'}>{pctTxt(m.pct)}</em><small>{m.trades ? `${m.trades} trades · ${m.wonPct}% won` : 'no trades this week'}</small></li>)}</ul>
        <div className="crw-invite"><code>{inviteLink(window.location.origin, window.location.pathname, mine.code)}</code>
          <button type="button" className="m-btn" onClick={() => { (navigator.clipboard?.writeText(inviteLink(window.location.origin, window.location.pathname, mine.code)) || Promise.reject()).then(() => toast.success('Invite link copied')).catch(() => window.prompt('Copy the invite link:', inviteLink(window.location.origin, window.location.pathname, mine.code))); }} data-testid="crew-copy">⧉ Copy invite</button></div>
        <details className="crw-room"><summary>💬 Crew room · members post, anyone can read</summary>
          <Suspense fallback={<small className="m-dim">Opening the room…</small>}><div className="crw-chat"><EcosystemChat compact room={mine.room} ecosystem={{ id: `crew-${mine.id}`, name: mine.name }} /></div></Suspense></details>
      </> : <>
        <header><span className="m-label">🛡 CREWS</span><small>2–8 wallets · weekly board · a crew shares no money</small></header>
        {mine === undefined ? <small className="m-dim">Loading…</small> : !sess ? <p className="crw-hint m-dim">Connect your wallet and open chat once to start or join a crew.</p> : <div className="crw-forms">
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/create', { name, tag }, 'Crew created — share your invite link'); }} data-testid="crew-create-form">
            <input className="m-input" placeholder="Crew name" value={name} maxLength={20} onChange={e => setName(e.target.value)} aria-label="Crew name" />
            <input className="m-input crw-tag" placeholder="TAG" value={tag} maxLength={4} onChange={e => setTag(e.target.value.toUpperCase())} aria-label="Crew tag" />
            <button type="submit" className="m-btn primary" disabled={busy || name.trim().length < 3 || tag.length < 2}>Start a crew</button></form>
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/join', { code }, 'Joined the crew'); }} data-testid="crew-join-form">
            <input className="m-input" placeholder="Invite code" value={code} maxLength={32} onChange={e => setCode(e.target.value)} aria-label="Invite code" />
            <button type="submit" className="m-btn" disabled={busy || !code.trim()}>Join</button></form></div>}
      </>}
    </div>
    <div className="crw-board m-card">
      <header><span className="m-label">🏆 WEEKLY CREW BOARD</span><small data-tip={board?.rule}>{board ? `${board.total} crew${board.total === 1 ? '' : 's'} · verified trades, last 7 days` : ''}</small></header>
      {board && !rows.length && <p className="crw-hint m-dim">No crews yet. Start one, invite up to 7 friends, and trade — the board ranks verified results.</p>}
      <ol>{rows.map((r, i) => <li key={r.id} className={r.ranked ? '' : 'is-off'} style={{ '--i': i }} data-testid={`crew-row-${r.tag}`}>
        <b className="crw-rank">{r.ranked ? i + 1 : '·'}</b><span className="crw-tagc">{r.tag}</span><a href={`?lens=crews&crew=${r.id}`} className="crw-rname" onClick={e => e.preventDefault()}>{r.name}</a>
        <small>{r.members}/8 · {r.active} active</small><em className={`m-num ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pctTxt(r.pct)}</em><small className="crw-note">{rankNote(r)}</small></li>)}</ol>
      <small className="m-dim crw-rule">{board?.rule}</small>
    </div>
  </section>;
}
