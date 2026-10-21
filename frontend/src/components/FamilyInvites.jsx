import React, { useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';

// ✉ Family invites: any member invites a wallet, the invited wallet accepts or declines; the creator / HQ wallet may add a wallet straight in.
const post = (body) => fetch(apiUrl('/api/reputation/crews/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Refused.'); return b; });
export const inviteAgo = (at, now = Date.now() / 1000) => { const s = Math.max(0, now - at); return s < 3600 ? `${Math.round(s / 60)}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago` : `${Math.round(s / 86400)}d ago`; };
export const validWallet = w => /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test((w || '').trim());

export function InviteInbox({ invites, inFamily, addr, sess, onDone }) {
  const [busy, setBusy] = useState('');
  if (!invites?.length) return null;
  const go = async (act, cid, ok) => { setBusy(cid + act); try { await post({ address: addr, session: sess, act, id: cid }); toast.success(ok); onDone?.(); } catch (e) { toast.error(e.message); } setBusy(''); };
  return (
    <section className="fiv-inbox" data-testid="family-invites">
      <span className="fiv-h">✉ YOU'VE BEEN SUMMONED</span>
      {invites.map((v, i) => (
        <div key={v.cid} className="fiv-card" style={{ '--i': i }}>
          <span className="fiv-seal" aria-hidden>🌹</span>
          <div><b>[{v.tag}] {v.name}</b><small>{v.members}/{v.seats} seats · invited by {v.by} · {inviteAgo(v.at)}</small></div>
          <div className="fiv-acts">
            <button type="button" className="m-btn primary" disabled={!!busy || inFamily} data-tip={inFamily ? 'Leave your family first' : 'Take the seat'} onClick={() => go('accept', v.cid, `Welcome to ${v.name}`)} data-testid={`invite-accept-${v.cid}`}>Accept</button>
            <button type="button" className="m-btn" disabled={!!busy} onClick={() => go('decline', v.cid, 'Invite declined')} data-testid={`invite-decline-${v.cid}`}>Decline</button>
          </div>
        </div>
      ))}
    </section>
  );
}

export function InviteBox({ addr, sess, sent, canAdd, onDone }) {
  const [to, setTo] = useState(''); const [busy, setBusy] = useState('');
  const ok = validWallet(to);
  const go = async (act, word) => { setBusy(act); try { await post({ address: addr, session: sess, act, to: to.trim() }); toast.success(word); setTo(''); onDone?.(); } catch (e) { toast.error(e.message); } setBusy(''); };
  return (
    <div className="fiv-box" data-testid="family-invite-box">
      <span className="fiv-h">✉ BRING SOMEONE IN</span>
      <p className="fiv-sub">Paste their wallet. They see the invite in La Familia and accept it themselves{canAdd ? ' — or, as the creator wallet, add them now.' : '.'}</p>
      <form onSubmit={e => { e.preventDefault(); if (ok) go('invite', 'Invite sent'); }}>
        <input className="m-input" placeholder="Wallet address" value={to} maxLength={60} onChange={e => setTo(e.target.value)} aria-label="Wallet to invite" />
        <button type="submit" className="m-btn primary" disabled={!ok || !!busy} data-testid="invite-send">Send invite</button>
        {canAdd && <button type="button" className="m-btn fiv-add" disabled={!ok || !!busy} onClick={() => go('add', 'Added to the family')} data-testid="invite-add">👑 Add now</button>}
      </form>
      {to && !ok && <small className="fiv-bad">That doesn't look like a Solana wallet address.</small>}
      {!!sent?.length && <ul className="fiv-sent">{sent.map(s => <li key={s.to + s.at}><code>{s.to}</code><small>waiting · {inviteAgo(s.at)}</small></li>)}</ul>}
    </div>
  );
}
