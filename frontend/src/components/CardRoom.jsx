import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FamEmpty } from './FamEmpty';
import '../styles/cardRoom.css';

// 🃏 THE CARD ROOM (owner 2026-10-27: "card room is corny and not live"): the family's recruits as a hand dealt on a noir felt table — each card
// has a DRAWN face for its job (hitter = fedora + tommy gun, guard = shield, earner = money bag, spy = mask), its level as the card value, an XP
// bar that fills, a live state (READY pulses · HURT counts down to the second · KING = level 10 foil). Tap a card: what it does + the move that
// uses it right now (raid · cartel justice · errands · the gym). Every number is the server's (family_world); the clock ticks here.
const SUIT = { hitter: ['♠', 'HITTER', 'Leads raids — its level is your raid power (top 3 hitters count)'], guard: ['♣', 'GUARD', 'Stands on your richest lots when you are raided (+def each level)'],
  earner: ['♥', 'EARNER', 'Runs errands — more MP per run as it levels'], spy: ['♦', 'SPY', 'Scouts boards before a hit — and hunts the rep cartels']};
const FACE = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10'];
export const cardFace = r => (r.lvl >= 10 ? 'K' : FACE[Math.max(0, Math.min(9, (r.lvl || 1) - 1))]);
const mmss = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
// pure: the table's vitals from the crew (hurt seconds already ticked down by `gone` seconds)
export function deckVitals(crew, gone = 0) {
  const cs = crew || []; const hurt = cs.map(r => Math.max(0, (Number(r.hurt) || 0) - gone)).filter(s => s > 0);
  return { n: cs.length, ready: cs.length - hurt.length, hurt: hurt.length, next: hurt.length ? Math.min(...hurt) : 0, kings: cs.filter(r => (r.lvl || 0) >= 10).length,
    power: cs.reduce((a, r) => a + (Number(r.lvl) || 0), 0) };
}

function Art({ k }) {   // the drawn face (viewBox 60 × 70), currentColor
  if (k === 'hitter') return <svg viewBox="0 0 60 70" aria-hidden="true"><path d="M14 30 Q30 22 46 30 L42 34 Q30 30 18 34 Z" /><path d="M20 30 Q21 14 30 14 Q39 14 40 30 Z" /><circle cx="30" cy="40" r="8" />
    <path d="M14 70 Q15 52 30 50 Q45 52 46 70 Z" /><path className="crd-gun" d="M8 58 L40 52 L42 55 L30 58 L28 64 L24 64 L25 59 L9 62 Z" /></svg>;
  if (k === 'earner') return <svg viewBox="0 0 60 70" aria-hidden="true"><path d="M24 16 L36 16 L33 24 L27 24 Z" /><path d="M27 24 Q10 34 14 54 Q18 66 30 66 Q42 66 46 54 Q50 34 33 24 Z" />
    <text x="30" y="56" textAnchor="middle">$</text></svg>;
  if (k === 'spy') return <svg viewBox="0 0 60 70" aria-hidden="true"><path d="M12 26 Q30 18 48 26 L44 30 Q30 26 16 30 Z" /><path d="M19 26 Q20 12 30 12 Q40 12 41 26 Z" />
    <path className="crd-mask" d="M14 38 Q22 33 30 38 Q38 33 46 38 Q44 46 37 45 Q33 44 30 41 Q27 44 23 45 Q16 46 14 38 Z" /><path d="M16 70 Q17 54 30 52 Q43 54 44 70 Z" /></svg>;
  return <svg viewBox="0 0 60 70" aria-hidden="true"><path d="M30 10 L50 18 Q50 46 30 62 Q10 46 10 18 Z" /><path className="crd-star" d="M30 24 L33 32 L41 32 L35 37 L37 45 L30 40 L23 45 L25 37 L19 32 L27 32 Z" /></svg>;
}

const MOVES = { hitter: [['raids', '⚔ Pick a raid'], ['cartels', '⚖ Hit a cartel ×1.5']], spy: [['cartels', '🕵 Hunt a cartel'], ['raids', '⚔ Scout a raid']],
  earner: [['jobs', '🧰 Run errands']], guard: [['raids', '🛡 Watch your raids']] };

export function CardRoom({ crew, onGo }) {
  const [pick, setPick] = useState(null); const seen = useRef(Date.now()); const [now, setNow] = useState(Date.now());
  useEffect(() => { seen.current = Date.now(); }, [crew]);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, 1000); return () => clearInterval(t); }, []);
  const gone = Math.max(0, (now - seen.current) / 1000);
  const v = useMemo(() => deckVitals(crew, gone), [crew, gone]);
  if (!crew?.length) return <FamEmpty art="crew" title="NO RECRUITS YET" note="Hire them on your block or win them in 🎖 Challenges." />;
  const hand = crew.slice().sort((a, b) => (b.lvl || 0) - (a.lvl || 0));
  const sel = hand.find(r => r.id === pick); const n = hand.length;
  return <div className="crd" data-testid="card-room">
    <div className="crd-vitals">
      <span style={{ '--i': 0 }}><em>CREW</em><b className="m-num">{v.n}</b></span>
      <span style={{ '--i': 1 }} className="is-up"><em>READY</em><b className="m-num">{v.ready}</b></span>
      <span style={{ '--i': 2 }} className={v.hurt ? 'is-dn' : ''} data-tip="Hurt recruits sit out raids until they heal"><em>HURT</em><b className="m-num">{v.hurt}</b><small className="m-num">{v.hurt ? `next back ${mmss(v.next)}` : 'all on their feet'}</small></span>
      <span style={{ '--i': 3 }} data-tip="Level-10 recruits — the Kings of the street"><em>KINGS</em><b className="m-num">{v.kings}</b></span>
      <span style={{ '--i': 4 }} data-tip="Every recruit's level added up"><em>DECK POWER</em><b className="m-num">{v.power}</b></span>
    </div>
    <div className="crd-table">
      <i className="crd-lamp" aria-hidden="true" />
      <div className="crd-hand" style={{ '--n': n }}>{hand.map((r, i) => { const s = SUIT[r.k] || SUIT.guard; const hurt = Math.max(0, (Number(r.hurt) || 0) - gone); const red = r.k === 'earner' || r.k === 'spy';
        const xp = r.next ? Math.min(1, (r.xp || 0) / r.next) : 1; const f = cardFace(r);
        return <button key={r.id} type="button" className={`fwd-card crd-card k-${r.k || 'guard'} ${red ? 'red' : ''} ${hurt ? 'is-hurt' : 'is-ready'} ${r.special ? 'is-special' : ''} ${(r.lvl || 0) >= 10 ? 'is-king' : ''} ${pick === r.id ? 'is-picked' : ''}`}
          style={{ '--i': i, '--a': `${(i - (n - 1) / 2) * Math.min(7, 40 / Math.max(1, n))}deg` }} aria-pressed={pick === r.id} onClick={() => setPick(p => (p === r.id ? null : r.id))}
          data-tip={`${s[1]} · level ${r.lvl}${r.next ? ` · ${r.xp}/${r.next} XP` : ''}${hurt ? ` · hurt, back in ${mmss(hurt)}` : ' · ready'}`} data-testid={`crd-${r.id}`}>
          <span className="tl">{f}<i>{s[0]}</i></span><b>{s[0]}</b><span className="crd-art"><Art k={r.k} /></span><small>{s[1]}</small><span className="br">{f}<i>{s[0]}</i></span>
          <u className="crd-xp" aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, xp)})` }} /></u>
          {hurt ? <em className="crd-hurt m-num">🩹 {mmss(hurt)}</em> : <em className="crd-ready" aria-hidden="true" />}
        </button>; })}</div>
    </div>
    {sel ? (() => { const s = SUIT[sel.k] || SUIT.guard; const hurt = Math.max(0, (Number(sel.hurt) || 0) - gone);
      return <div className="crd-pick" data-testid="crd-pick"><b>{s[0]} {s[1]} · LEVEL {sel.lvl}{(sel.lvl || 0) >= 10 ? ' · KING' : ''}</b><p>{s[2]}</p>
        <span className="crd-pxp"><em>XP</em><i aria-hidden="true"><s style={{ transform: `scaleX(${sel.next ? Math.min(1, (sel.xp || 0) / sel.next) : 1})` }} /></i><small className="m-num">{sel.next ? `${sel.xp}/${sel.next} to level ${sel.lvl + 1}` : 'max level'}</small></span>
        <div className="crd-acts">{hurt ? <button type="button" className="m-btn" onClick={() => onGo?.('rc')} data-tip="Challenges win fresh recruits while this one heals" data-testid="crd-go-rc">🎖 The gym · back in {mmss(hurt)}</button>
          : (MOVES[sel.k] || MOVES.guard).map(([k, l]) => <button key={k} type="button" className="m-btn m-go" onClick={() => onGo?.(k)} data-testid={`crd-go-${k}`}>{l}</button>)}</div></div>; })() : <p className="crd-hint">Tap a card — what it does, and the move that uses it right now.</p>}
  </div>;
}
