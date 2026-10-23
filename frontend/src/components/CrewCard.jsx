import React, { useEffect, useRef, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { useGlide } from '../lib/useGlide';
import { FamilyBadge } from './FamilyBadge';
import { FamilyCardArt } from './FamilyCardArt';
import '../styles/crews.css';

// 🌹 THE LIGHT FAMILIA PIECES (2026-10-23, task D "Familia loads as its own app package"): the family card, the Top Families strip, the
// profile card + chip, the board read and the pure helpers. Home, Landing, profiles and the season ticker import THESE — so the full Familia app
// (Crews.jsx: the city, the block, the rooms, three.js) is its own lazy chunk, fetched only when you open Familia (or hover its link).
export const PRIZES = [150, 100, 60];
export const MEDAL = ['🥇', '🥈', '🥉'];
export const pctTxt = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v}%`);
export const inviteLink = (origin, path, code) => `${origin}${path}?lens=crews&join=${encodeURIComponent(code)}`;
export const rankNote = r => (r.ranked ? `${r.trades} trades · ${r.wonPct}% won` : r.members < 2 ? 'needs 2+ members to rank' : `${r.trades}/5 trades to rank`);
export const costText = (q, kind) => { const x = q?.[kind]; if (!x) return ''; return q.free ? 'free for FEELESS staff' : `$${x.usd.toFixed(x.usd % 1 ? 2 : 0)}${x.sol ? ` ≈ ${x.sol} SOL` : ''}`; };
export const seatsLine = c => `${c.members.length}/${c.seats} seats`;
export const podium = rows => { const r = (rows || []).filter(x => x.ranked); return (r.length ? r : [...(rows || [])].sort((a, b) => b.members - a.members || b.active - a.active)).slice(0, 3); };
export const heat = r => Math.max(0, Math.min(1, ((r?.active || 0) / Math.max(1, r?.members || 1)) * 0.5 + Math.min(1, Math.abs(Number(r?.pct) || 0) / 40) * 0.5));
export const CARD_STYLE = { noir: 'cd-noir', gold: 'cd-gold', blood: 'cd-blood', neon: 'cd-neon', ice: 'cd-ice', royal: 'cd-royal' };
export const CARD_FX = { smoke: 'cfx2-smoke', embers: 'cfx2-embers', rain: 'cfx2-rain', lightning: 'cfx2-lightning', stars: 'cfx2-stars' };
const PLACE = ['', 'is-p1', 'is-p2', 'is-p3'];
export const evAgo = t => { const s = Date.now() / 1000 - t; return s < 60 ? 'now' : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

export function useCrewBoard(every = 20000) {
  const [b, setB] = useState(null);
  useEffect(() => { let on = true; let t = null;
    const go = fresh => sharedJson('/api/reputation/crews', { maxAge: 15000, fresh }).then(d => { if (on) setB(d); }).catch(() => {}).finally(() => { if (on) t = setTimeout(() => go(), document.hidden ? every * 3 : every); });
    go(); return () => { on = false; clearTimeout(t); }; }, [every]);
  return b;
}

export function CrewCard3D({ r, place, small, onOpen }) {
  const el = useRef(null);
  const tilt = e => { const n = el.current; if (!n || small) return; const b = n.getBoundingClientRect(); n.style.setProperty('--rx', `${((e.clientY - b.top) / b.height - 0.5) * -14}deg`); n.style.setProperty('--ry', `${((e.clientX - b.left) / b.width - 0.5) * 16}deg`); };
  const flat = () => { el.current?.style.setProperty('--rx', '0deg'); el.current?.style.setProperty('--ry', '0deg'); };
  const h = heat(r);
  const cd = r.card || {};
  const pct = useGlide(r.pct == null ? null : Number(r.pct));
  const fill = Math.max(0.04, Math.min(1, (r.members || 0) / Math.max(1, r.seats || 5)));
  return <button type="button" ref={el} className={`crw-3d ${['', 'p1', 'p2', 'p3', 'p4'][place] || ''} ${small ? 'is-small' : ''} ${h > 0.6 ? 'is-hot' : ''} ${CARD_STYLE[cd.style] || 'cd-noir'}`} style={{ '--heat': h.toFixed(2), '--spin': `${(6 - h * 4.5).toFixed(1)}s` }}
    onPointerMove={tilt} onPointerLeave={flat} onClick={() => onOpen?.(r)} data-testid={`crew-3d-${r.tag}`} aria-label={`${r.name}: ${pctTxt(r.pct)} this week`} data-tip={`${r.name} — tap to open the family`}>
    <span className="crw-bolt" aria-hidden="true" />
    <span className="crw-face">
      <FamilyCardArt style={cd.style} />
      {CARD_FX[cd.fx] ? <span className={`crw-cfx ${CARD_FX[cd.fx]}`} aria-hidden="true"><i /><i /><i /><i /><i /></span> : null}
      <span className="fcc-top"><b className={`fcc-rank ${PLACE[place] || ''}`}>{place && place <= 3 ? `#${place}` : '—'}</b><span className="fcc-live"><i aria-hidden="true" />{r.active || 0} live</span></span>
      <span className="fcc-crest">{r.badge ? <FamilyBadge b={r.badge} size="md" px={small ? 44 : 64} chips={false} /> : <b className="crw-3tag">{r.tag}</b>}</span>
      <span className="crw-3name">{r.name}</span>
      {cd.line && !small ? <i className="crw-3line">“{cd.line}”</i> : null}
      <span className="fcc-vitals">
        <span className="fcc-v"><em className={`crw-3pct ${r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pctTxt(pct)}</em><small>WEEK</small></span>
        <span className="fcc-v"><b>{r.members}<s>/{r.seats}</s></b><small>SEATS</small><u aria-hidden="true"><i style={{ transform: `scaleX(${fill})` }} /></u></span>
        {!small ? <span className="fcc-v"><b>{r.bounties || 0}</b><small>BOUNTIES</small></span> : null}
      </span>
      {!small && <span className="crw-heat" aria-hidden="true" data-tip="Heat = how active + how big the week's move is"><i style={{ transform: `scaleX(${Math.max(0.05, h)})` }} /></span>}
      {r.launch && !small ? <span className="crw-3meta">🚀 ${r.launch}</span> : null}
    </span>
  </button>;
}

export function TopCrews({ title = '🌹 TOP FAMILIES' }) {
  const b = useCrewBoard(); const top = podium(b?.board);
  if (!top.length) return null;
  return <section className="crw-top" data-testid="top-crews"><header><span className="m-label">{title}</span><a href="/terminal/leaderboard?lens=crews">all families →</a></header>
    <div className="crw-top-row">{top.map((r, i) => <CrewCard3D key={r.id} r={r} place={i + 1} small onOpen={() => { window.location.href = '/terminal/leaderboard?lens=crews'; }} />)}</div></section>;
}

export function CrewProfile({ address }) {
  const [c, setC] = useState(null); const b = useCrewBoard(30000);
  useEffect(() => { let on = true; if (!address) return undefined; sharedJson(`/api/reputation/crews/of/${address}`, { maxAge: 120000 }).then(d => on && setC(d?.crew || null)).catch(() => {}); return () => { on = false; }; }, [address]);
  if (!c) return null;
  const rows = b?.board || []; const r = rows.find(x => x.id === c.id); const place = r && r.ranked ? rows.filter(x => x.ranked).indexOf(r) + 1 : 0;
  return <section className="crw-prof m-card" data-testid="crew-profile"><header><span className="m-label">🌹 LA FAMILIA</span><small>{place ? `#${place} this week` : 'unranked this week'}</small></header>
    {r ? <CrewCard3D r={r} place={place && place <= 3 ? place : 4} /> : <b>[{c.tag}] {c.name}</b>}</section>;
}

export function CrewChip({ address }) {
  const [c, setC] = useState(null);
  useEffect(() => { let alive = true; if (!address) return undefined; sharedJson(`/api/reputation/crews/of/${address}`, { maxAge: 120000 }).then(d => alive && setC(d?.crew || null)).catch(() => {}); return () => { alive = false; }; }, [address]);
  return c ? <a className="m-chip crw-chip" href="/terminal/leaderboard?lens=crews" data-tip={`La Familia: ${c.name}${c.badge?.motto ? ` — “${c.badge.motto}”` : ''}`} data-testid="crew-chip">{c.badge ? <FamilyBadge b={c.badge} size="sm" /> : '🌹'} {c.tag}</a> : null;
}
