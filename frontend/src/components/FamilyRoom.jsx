import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { FamilyBadge } from './FamilyBadge';
import { useFloatPop } from '../lib/floatPop';
import '../styles/familyRoom.css';

// 🎩 THE FAMILY ROOM (owner, 2026-10-20: "a REAL layout — family vitals, per-member activity, ranks and roles"): the family's hero with its
// live numbers, THE TABLE (every member by rank, with role, heat, streak, last trade) and THE WIRE (the family's newest closed trades).
// Every number is the members' verified FEELESS trades over 7 days (price result) — server-side in backend/family_room.py.
export const RANK_ORDER = ['don', 'underboss', 'consigliere', 'capo', 'soldier', 'associate'];
export const STATUS = { fire: ['🔥', 'on fire'], active: ['🟢', 'active'], quiet: ['💤', 'quiet'], new: ['🆕', 'new blood'] };
export const usdTxt = v => (v == null ? '—' : `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(Math.abs(v) >= 100 ? 0 : 2)}`);
export const agoTxt = (t, now = Date.now() / 1000) => { const s = Math.max(0, now - t); return s < 60 ? 'now' : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
export const byRank = ms => [...(ms || [])].sort((a, b) => RANK_ORDER.indexOf(a.rank) - RANK_ORDER.indexOf(b.rank) || (b.usd || 0) - (a.usd || 0));
export const initials = n => (n || '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '??';

function Gauge({ v, label }) {
  const p = Math.max(0, Math.min(100, Number(v) || 0));
  const c = 2 * Math.PI * 34;
  return (
    <span className="frm-gauge" data-tip="RESPECT: the week's verified result, who is actually working, the war record and the family's size — 0 to 100">
      <svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="34" className="frm-gtrack" /><circle cx="40" cy="40" r="34" className="frm-gfill" style={{ strokeDasharray: `${(c * p) / 100} ${c}` }} /></svg>
      <b key={p}>{Math.round(p)}</b><em>{label}</em>
    </span>
  );
}

export function FamilyHero({ mine, busy, onLeave }) {
  const v = mine.vitals || {};
  const war = mine.war || {};
  const tiles = [
    ['WEEK', usdTxt(v.usd), v.usd == null ? '' : v.usd >= 0 ? 'up' : 'dn'],
    ['WON', v.wonPct == null ? '—' : `${v.wonPct}%`, ''],
    ['TRADES', v.trades ?? '—', ''],
    ['WORKING 24H', `${v.active ?? 0}/${v.members ?? mine.members.length}`, ''],
    ['WARS', `${war.wins || 0}–${war.losses || 0}`, ''],
    ['WAR CHEST', war.chest == null ? '—' : `${Number(war.chest).toLocaleString('en-US')} pts`, 'gold'],
  ];
  return (
    <header className="frm-hero" data-testid="family-hero">
      <div className="frm-crest">{mine.badge ? <FamilyBadge b={mine.badge} size="md" /> : <span className="frm-rose">🌹</span>}</div>
      <div className="frm-id">
        <span className="frm-eyebrow">THE {String(mine.name).toUpperCase()} FAMILY · [{mine.tag}]</span>
        <h2>{mine.name}</h2>
        {mine.badge?.motto ? <i className="frm-motto">“{mine.badge.motto}”</i> : null}
        <div className="frm-heat" data-tip="How hard the family is trading right now (members' trades in the last 24h)"><em>HEAT</em><span><i style={{ transform: `scaleX(${Math.max(0.03, (v.heat || 0) / 100)})` }} /></span><b>{v.heat ?? 0}</b></div>
        <div className="frm-spot">
          {v.hot ? <span className="frm-chip is-hot">🔥 hot hand · {v.hot.name}</span> : null}
          {v.streak ? <span className="frm-chip">🎯 {v.streak.n} wins straight · {v.streak.name}</span> : null}
          <span className="frm-chip">{mine.members.length}/{mine.seats} seats</span>
        </div>
      </div>
      <Gauge v={v.respect} label="RESPECT" />
      <div className="frm-vit">{tiles.map(([k, n, tone], i) => <span key={k} style={{ '--i': i }} className={tone ? `t-${tone}` : ''}><em>{k}</em><b key={String(n)}>{n}</b></span>)}</div>
      <button type="button" className="m-btn frm-leave" disabled={!!busy} onClick={onLeave} data-testid="crew-leave">Leave</button>
    </header>
  );
}

function RoleMenu({ m, mine, addr, sess, onDone }) {
  const fp = useFloatPop(250); const { open, setOpen } = fp;
  const [busy, setBusy] = useState(false);
  const set = async (body, word) => {
    setBusy(true);
    try {
      const r = await fetch(apiUrl('/api/reputation/crews/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: addr, session: sess, act: 'role', to: m.address, ...body }) });
      const b = await r.json().catch(() => ({})); if (!r.ok) throw new Error(b.detail || 'Refused.');
      toast.success(word); setOpen(false); onDone?.(b.crew);
    } catch (e) { toast.error(e.message); }
    setBusy(false);
  };
  return (
    <>
      <button type="button" ref={fp.ref} aria-expanded={open} className="frm-set" onClick={() => setOpen(!open)} data-testid={`role-${m.address.slice(0, 6)}`} aria-label={`Set ${m.name}'s role and rank`}>⚙</button>
      {open && createPortal(
        <div ref={fp.popRef} style={fp.style} className="frm-pop" role="dialog" aria-label="Role and rank">
          <span className="frm-ph">ROLE · {m.name}</span>
          <div className="frm-opts">{Object.entries(mine.roles || {}).map(([k, [ic, word]]) => <button key={k} type="button" disabled={busy} className={m.role === k ? 'active' : ''} onClick={() => set({ role: m.role === k ? '' : k }, `${ic} ${m.name} is your ${word}`)}>{ic} {word}</button>)}</div>
          {!m.owner && <>
            <span className="frm-ph">RANK</span>
            <div className="frm-opts">{(mine.promote || []).map(k => <button key={k} type="button" disabled={busy} className={m.rank === k ? 'active' : ''} onClick={() => set({ rank: k }, `${m.name} promoted`)}>{k}</button>)}
              <button type="button" disabled={busy} onClick={() => set({ rank: '' }, `${m.name} ranks on results`)}>↺ by results</button></div>
          </>}
        </div>, document.body
      )}
    </>
  );
}

export function FamilyTable({ mine, owner, addr, sess, onChanged }) {
  const ms = byRank(mine.members);
  return (
    <section className="frm-table" data-testid="family-table">
      <header><span className="frm-h">🪑 THE TABLE</span><small>ranked by the Don, then by verified results this week</small></header>
      <ul>{ms.map((m, i) => {
        const st = STATUS[m.status] || STATUS.quiet;
        return (
          <li key={m.address} className={`frm-mem r-${m.rank} s-${m.status}`} style={{ '--i': i, '--heat': ((m.heat || 0) / 100).toFixed(2) }}>
            <span className="frm-av"><i>{initials(m.name)}</i><em title={st[1]}>{st[0]}</em></span>
            <div className="frm-who">
              <a href={`/terminal/profile/${m.address}`}><b>{m.name}</b>{m.owner ? ' 👑' : ''}</a>
              <span className="frm-tags"><span className={`fnr-rank r-${m.rank}`}>{m.rankLabel}</span>{m.roleLabel ? <span className="frm-role">{m.roleIcon} {m.roleLabel}</span> : null}</span>
              <span className="frm-mheat"><i style={{ transform: `scaleX(${Math.max(0.03, (m.heat || 0) / 100)})` }} /></span>
            </div>
            <div className="frm-num">
              <b className={m.usd > 0 ? 'up' : m.usd < 0 ? 'dn' : ''} key={m.usd}>{m.trades ? usdTxt(m.usd) : '—'}</b>
              <small>{m.trades ? `${m.trades} trades · ${m.wonPct}% won` : 'no trades this week'}</small>
              <small className="frm-last">{m.last ? <>last <b>${m.last.sym}</b> <span className={m.last.pct >= 0 ? 'up' : 'dn'}>{m.last.pct >= 0 ? '+' : ''}{m.last.pct}%</span> · {agoTxt(m.last.at)}</> : st[1]}{m.streak >= 2 ? ` · 🔥×${m.streak}` : ''}</small>
            </div>
            {owner && <RoleMenu m={m} mine={mine} addr={addr} sess={sess} onDone={onChanged} />}
          </li>
        );
      })}</ul>
    </section>
  );
}

export function FamilyWire({ mine }) {
  const rows = mine.wire || [];
  return (
    <section className="frm-wire" data-testid="family-wire">
      <header><span className="frm-h"><i className="frm-dot" /> THE WIRE</span><small>the family's closed trades, live</small></header>
      {rows.length ? <ol>{rows.map((r, i) => (
        <li key={`${r.w}-${r.at}-${r.sym}`} style={{ '--i': i }} className={r.pct >= 0 ? 'is-up' : 'is-dn'}>
          <span className="frm-wr">{r.rank.split(' ')[0]}</span>
          <span className="frm-wn"><b>{r.name}</b> {r.pct >= 0 ? 'cashed' : 'took a hit on'} <b>${r.sym}</b></span>
          <em>{r.pct >= 0 ? '+' : ''}{r.pct}%</em><small>{usdTxt(r.usd)} · {agoTxt(r.at)}</small>
        </li>))}</ol>
        : <p className="frm-empty">Quiet on the wire. The family's verified trades show up here the minute they close.</p>}
    </section>
  );
}
