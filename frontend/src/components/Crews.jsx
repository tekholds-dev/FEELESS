import React, { Suspense, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { sharedJson } from '../lib/sharedJson';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import '../styles/crews.css';

// 🛡 CREWS (Leaderboard › Crews): $25 in SOL to the FEELESS fee wallet starts a crew with 5 seats including you; +5 seats cost $5 each time. One transfer you
// sign, re-read on-chain by the server (never reused; staff free). An invite link, a members-only-post room, and a weekly board ranked by what members' VERIFIED
// FEELESS trades did over 7 days — the top 3 pay their members season points. A crew shares no money: everyone signs their own trades.
// GET /crews · /crews/price · /crews/mine · POST create · seats · join · leave.
const EcosystemChat = React.lazy(() => import('./EcosystemChat'));
export const PRIZES = [150, 100, 60];
export const pctTxt = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
export const inviteLink = (origin, path, code) => `${origin}${path}?lens=crews&join=${encodeURIComponent(code)}`;
export const rankNote = r => (r.ranked ? `${r.trades} trades · ${r.wonPct}% won` : r.members < 2 ? 'needs 2+ members to rank' : `${r.trades}/5 trades to rank`);
export const costText = (q, kind) => { const x = q?.[kind]; if (!x) return ''; return q.free ? 'free for FEELESS staff' : `$${x.usd.toFixed(x.usd % 1 ? 2 : 0)}${x.sol ? ` ≈ ${x.sol} SOL` : ''}`; };
export const seatsLine = c => `${c.members.length}/${c.seats} seats`;
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });

export function Crews() {
  const { wallet, provider } = useWallet() || {}; const addr = wallet?.address || ''; const sess = addr ? readChatSession(addr) : '';
  const [board, setBoard] = useState(null); const [mine, setMine] = useState(undefined); const [busy, setBusy] = useState(''); const [q, setQ] = useState(null);
  const [name, setName] = useState(''); const [tag, setTag] = useState(''); const [code, setCode] = useState(() => { try { return new URLSearchParams(window.location.search).get('join') || ''; } catch { return ''; } });
  const loadBoard = fresh => sharedJson('/api/reputation/crews', { maxAge: 30000, fresh }).then(setBoard).catch(() => {});
  const loadMine = () => { if (!addr || !sess) { setMine(null); return Promise.resolve(); } return fetch(apiUrl(`/api/reputation/crews/mine?address=${addr}&session=${encodeURIComponent(sess)}`)).then(r => (r.ok ? r.json() : { crew: null })).then(d => setMine(d.crew || null)).catch(() => setMine(null)); };
  useEffect(() => { loadBoard(); loadMine(); }, [addr, sess]);   // eslint-disable-line react-hooks/exhaustive-deps
  // the quote (and whether the name + tag are free) is read BEFORE anything is paid; debounced while typing
  useEffect(() => { const t = setTimeout(() => fetch(apiUrl(`/api/reputation/crews/price?address=${addr}&name=${encodeURIComponent(name)}&tag=${encodeURIComponent(tag)}`)).then(r => (r.ok ? r.json() : null)).then(setQ).catch(() => {}), 300); return () => clearTimeout(t); }, [addr, name, tag, mine?.id]);
  const pay = async (kind) => {   // one SOL transfer YOU sign to the fee wallet → its signature goes with the request
    if (q?.free) return '';
    if (!q?.payTo || !q?.[kind]?.sol) throw new Error('The fee wallet or the SOL price is not available right now — try again in a minute.');
    const { batchSend } = await import('../lib/batchSend');
    const [sig] = await batchSend({ provider, owner: addr, recipients: [{ address: q.payTo, amount: Number(q[kind].sol.toFixed(9)) }], kind: `crew-${kind}` });
    return sig;
  };
  const act = async (path, body, ok, kind) => {
    if (!sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(path);
    try {
      const signature = kind ? await pay(kind) : undefined;
      const r = await post(path, { address: addr, session: sess, ...body, ...(kind ? { signature } : {}) }); toast.success(ok);
      if (r.crew) setMine(r.crew); else setMine(null); sharedJson.freshAt = Date.now(); loadBoard(true);
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  const rows = board?.board || []; const owner = mine?.members?.find(m => m.owner)?.address === addr;
  return <section className="crw" data-testid="crews">
    <div className="crw-mine m-card m-live">
      {mine ? <>
        <header><span className="m-label">🛡 YOUR CREW</span><b className="crw-name">[{mine.tag}] {mine.name}</b><small>{seatsLine(mine)}</small>
          {owner && <button type="button" className="m-btn primary" disabled={!!busy} onClick={() => act('/api/reputation/crews/seats', {}, `➕ +${mine.packSeats} seats`, 'seats')} data-testid="crew-seats" data-tip={`Add ${mine.packSeats} seats: one SOL transfer you sign to the FEELESS fee wallet.`}>{busy.endsWith('/seats') ? '…' : `➕ +${mine.packSeats} seats · ${costText(q, 'seats') || `$${mine.packUsd}`}`}</button>}
          <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('/api/reputation/crews/leave', {}, 'Left the crew')} data-testid="crew-leave">Leave</button></header>
        <ul className="crw-mem">{mine.members.map(m => <li key={m.address}><a href={`/terminal/profile/${m.address}`}>{m.name}{m.owner ? ' 👑' : ''}</a><em className={m.pct == null ? '' : m.pct >= 0 ? 'm-pos' : 'm-neg'}>{pctTxt(m.pct)}</em><small>{m.trades ? `${m.trades} trades · ${m.wonPct}% won` : 'no trades this week'}</small></li>)}</ul>
        <div className="crw-invite"><code>{inviteLink(window.location.origin, window.location.pathname, mine.code)}</code>
          <button type="button" className="m-btn" onClick={() => { (navigator.clipboard?.writeText(inviteLink(window.location.origin, window.location.pathname, mine.code)) || Promise.reject()).then(() => toast.success('Invite link copied')).catch(() => window.prompt('Copy the invite link:', inviteLink(window.location.origin, window.location.pathname, mine.code))); }} data-testid="crew-copy">⧉ Copy invite</button></div>
        <details className="crw-room"><summary>💬 Crew room · members post, anyone can read</summary>
          <Suspense fallback={<small className="m-dim">Opening the room…</small>}><div className="crw-chat"><EcosystemChat compact room={mine.room} ecosystem={{ id: `crew-${mine.id}`, name: mine.name }} /></div></Suspense></details>
      </> : <>
        <header><span className="m-label">🛡 CREWS</span><small>{q ? `${costText(q, 'create')} · ${q.baseSeats} seats incl. you · +${q.packSeats} seats ${costText(q, 'seats')}` : '5 seats incl. you'} · a crew shares no money</small></header>
        {mine === undefined ? <small className="m-dim">Loading…</small> : !sess ? <p className="crw-hint m-dim">Connect your wallet and open chat once to start or join a crew.</p> : <div className="crw-forms">
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/create', { name, tag }, 'Crew created — share your invite link', 'create'); }} data-testid="crew-create-form">
            <input className="m-input" placeholder="Crew name" value={name} maxLength={20} onChange={e => setName(e.target.value)} aria-label="Crew name" />
            <input className="m-input crw-tag" placeholder="TAG" value={tag} maxLength={4} onChange={e => setTag(e.target.value.toUpperCase())} aria-label="Crew tag" />
            <button type="submit" className="m-btn primary" disabled={!!busy || name.trim().length < 3 || tag.length < 2 || (q && q.ok === false)} data-tip="One SOL transfer you sign to the FEELESS fee wallet, checked on-chain. If anything fails after you pay, send the same payment again — it is kept.">{busy.endsWith('/create') ? 'Paying…' : `Start a crew · ${costText(q, 'create') || '$25'}`}</button>
            {q?.ok === false && (name || tag) && <small className="crw-why" data-testid="crew-why">{q.why}</small>}</form>
          <form onSubmit={e => { e.preventDefault(); act('/api/reputation/crews/join', { code }, 'Joined the crew'); }} data-testid="crew-join-form">
            <input className="m-input" placeholder="Invite code (free to join)" value={code} maxLength={32} onChange={e => setCode(e.target.value)} aria-label="Invite code" />
            <button type="submit" className="m-btn" disabled={!!busy || !code.trim()}>Join</button></form></div>}
      </>}
    </div>
    <div className="crw-board m-card">
      <header><span className="m-label">🏆 WEEKLY CREW BOARD</span><small data-tip={board?.rule}>{board ? `${board.total} crew${board.total === 1 ? '' : 's'} · verified trades, last 7 days` : ''}</small></header>
      <p className="crw-prize" data-testid="crew-prizes">Top 3 ranked crews pay every member season points each week: <b>🥇 +{PRIZES[0]}</b> · <b>🥈 +{PRIZES[1]}</b> · <b>🥉 +{PRIZES[2]}</b></p>
      {board && !rows.length && <p className="crw-hint m-dim">No crews yet. Start one, fill your seats and trade — the board ranks verified results.</p>}
      <ol>{rows.map((r, i) => <li key={r.id} className={r.ranked ? '' : 'is-off'} style={{ '--i': i }} data-testid={`crew-row-${r.tag}`}>
        <b className="crw-rank">{r.ranked ? i + 1 : '·'}</b><span className="crw-tagc">{r.tag}</span><span className="crw-rname">{r.name}</span>
        <small>{r.members}/{r.seats} seats · {r.active} active</small><em className={`m-num ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pctTxt(r.pct)}</em><small className="crw-note">{rankNote(r)}</small></li>)}</ol>
      <small className="m-dim crw-rule">{board?.rule}</small>
    </div>
  </section>;
}

// 🛡 the crew tag beside a name (profile header): [TAG] name of the crew the wallet is in — nothing if none
export function CrewChip({ address }) {
  const [c, setC] = useState(null);
  useEffect(() => { let alive = true; if (!address) return undefined; sharedJson(`/api/reputation/crews/of/${address}`, { maxAge: 120000 }).then(d => alive && setC(d?.crew || null)).catch(() => {}); return () => { alive = false; }; }, [address]);
  return c ? <a className="m-chip crw-chip" href="/terminal/leaderboard?lens=crews" data-tip={`Crew: ${c.name}`} data-testid="crew-chip">🛡 {c.tag}</a> : null;
}
