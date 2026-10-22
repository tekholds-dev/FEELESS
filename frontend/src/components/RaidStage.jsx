import React, { useEffect, useRef, useState } from 'react';
import { Building, heightOf } from './FamilyBlock';
import { BUILT } from './cityParts';
import '../styles/familyBlock.css';
import '../styles/raidStage.css';

// 🔫 A RAID, PLAYED ON THE TARGET'S BLOCK (owner, 2026-10-21: "raids and hits played inside the city — chess / card moves on the target's
// block in 3D, no 2D cards"). The target's real 5 × 5 block (the same CSS-3D buildings as its Familia page): every built store is a
// square you can strike, guards float over the lots as shield halos (their strength only once scouted), your hitters stand at the kerb.
// Moves are a game action bar (keys 1–4); the last move plays out ON the building it hit (muzzle flash + coins, a blocked ring, a blast
// + smoke, a radar sweep) with a banner. The engine is family_world.py (seeded dice, the house answers for a sleeping defender).
export const MOVE_ICON = { hit: '🔫', sabotage: '💣', scout: '🕵', retreat: '🏃', guard: '🛡', counter: '🔪', lockdown: '🔒' };
export const NEEDS_LOT = new Set(['hit', 'sabotage', 'scout', 'guard']);
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');

// pure: the attacker's odds on a lot — the engine's own formula (family_world.odds); unknown guards → null
export function raidOdds(r, lot) {
  if (!lot || lot.def == null) return null;
  const s = Math.max(1, (r.power || 1) * 2 + (r.hitters || []).slice(0, 3).reduce((a, b) => a + b, 0) - 2 * (r.hurt || 0));
  return Math.max(0.08, Math.min(0.88, s / (s + 1.4 * (lot.def + (lot.shield || 0)) + 1)));
}
// pure: the move that just happened, for the effects (a new key each move so the animation replays)
export function lastFx(r) {
  const m = (r.moves || []).at(-1);
  return m ? { kind: m.act, lot: m.lot, win: m.win !== false, side: m.side, word: m.word, n: r.moves.length } : null;
}

export function RaidStage({ r, act, busy }) {
  const mySide = r.actions?.hit ? 'a' : 'b'; const live = r.status === 'live'; const myTurn = live && r.turn === mySide;
  const moves = Object.entries(r.actions || {});
  const [pick, setPick] = useState(mySide === 'a' ? 'hit' : 'guard');
  const [left, setLeft] = useState(0); const [rz, setRz] = useState(-38); const drag = useRef(null); const moved = useRef(false);
  useEffect(() => { const f = () => setLeft(Math.max(0, Math.round(r.deadline - Date.now() / 1000))); f(); const t = setInterval(f, 1000); return () => clearInterval(t); }, [r.deadline]);
  const play = (kind, lot) => act({ act: mySide === 'a' ? 'attack' : 'defend', raid: r.id, kind, lot: lot ?? -1 }, `${MOVE_ICON[kind] || ''} ${kind}`);
  const choose = k => { if (NEEDS_LOT.has(k)) setPick(k); else play(k); };
  useEffect(() => {
    if (!myTurn) return undefined;
    const key = e => { const i = Number(e.key) - 1; if (e.target?.tagName === 'INPUT' || !(i >= 0 && i < moves.length)) return; choose(moves[i][0]); };
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key);
  });   // eslint-disable-line react-hooks/exhaustive-deps
  const fx = lastFx(r); const cap = Math.floor((r.stash || 0) * 0.35);
  const cells = Array.from({ length: 25 }, (_, i) => (r.board || []).find(l => l.lot === i));
  return <section className={`rds m-card s-${r.status} side-${mySide} ${myTurn ? 'is-turn' : ''}`} data-testid={`raid-${r.id}`}>
    <header className="rds-hud">
      <span className="rds-vs"><b className="a">{r.a.tag}</b><i>⚔</i><b className="b">{r.b.tag}</b>{r.kind !== 'family' ? <em>{r.kind === 'cartel' ? 'CARTEL · loot ×1.5' : 'CPU TOWN'}</em> : null}</span>
      <span className="rds-k"><em>ROUND</em><b>{Math.min(r.round, r.rounds)}/{r.rounds}</b></span>
      <span className={`rds-k rds-turn ${myTurn ? 'is-me' : ''}`}><em>{live ? (myTurn ? 'YOUR MOVE' : 'THEIR MOVE') : 'OVER'}</em><b>{live ? `${left}s` : r.end}</b>
        {live ? <u><s style={{ transform: `scaleX(${Math.min(1, left / 240)})` }} /></u> : null}</span>
      <span className="rds-k rds-loot" data-tip={`Loot so far — a raid takes at most 35 % of their stash (${n(cap)} MP)`}><em>LOOT</em><b key={r.loot}>{n(r.loot)} MP</b><u><s style={{ transform: `scaleX(${cap ? Math.min(1, r.loot / cap) : 0})` }} /></u></span>
      <span className="rds-k"><em>CREW</em><b>{(r.hitters || []).length - (r.hurt || 0)}/{(r.hitters || []).length}</b></span>
    </header>
    <div className="fbk-stage rds-stage" style={{ '--rz': `${rz}deg` }} onPointerDown={e => { drag.current = { x: e.clientX, rz }; moved.current = false; }}
      onPointerMove={e => { if (!drag.current) return; const dx = e.clientX - drag.current.x; if (Math.abs(dx) > 5) moved.current = true; setRz(drag.current.rz + dx * 0.5); }}
      onPointerUp={() => { drag.current = null; }} onPointerLeave={() => { drag.current = null; }}
      onClickCapture={e => { if (moved.current) { e.stopPropagation(); moved.current = false; } }}>
      <div className="fbk-sky" aria-hidden="true" />{live ? <><i className="rds-siren r" aria-hidden="true" /><i className="rds-siren b" aria-hidden="true" /><i className="rds-sweep" aria-hidden="true" /></> : null}
      <div className="fbk-plane rds-plane">
        <i className="fbk-road" aria-hidden="true" />
        {cells.map((l, i) => { const odds = l ? raidOdds(r, l) : null; const guard = l ? (l.def ?? 0) + (l.shield || 0) : 0;
          return <button key={i} type="button" className={`fbk-lot ${l ? 'has-b' : 'is-empty'} rds-lot ${l?.down ? 'is-down' : ''} ${myTurn && l && NEEDS_LOT.has(pick) ? `aim-${pick}` : ''}`}
            style={{ '--h': `${l ? heightOf(l.b, l.lvl) : 0}px` }} disabled={!l || !myTurn || !NEEDS_LOT.has(pick) || busy} onClick={() => play(pick, i)} data-testid={`rl-${i}`}
            data-tip={l ? `${l.b} L${l.lvl} · ${Math.round((l.share || 0) * 100)} % of the stash · guards ${l.def == null ? 'unknown — scout it' : guard}${odds != null ? ` · your odds ${Math.round(odds * 100)} %` : ''}` : 'empty lot'}>
            {l ? <><Building l={{ b: l.b, lvl: l.lvl, at: 0 }} nowS={BUILT} />{guard > 0 || l.shield ? <i className="rds-dome" style={{ '--g': Math.min(1, guard / 10) }} /> : null}
              <span className="rds-tag"><b>{l.def == null ? '🛡 ?' : `🛡 ${guard}`}</b>{odds != null && mySide === 'a' ? <small>{Math.round(odds * 100)}%</small> : null}</span>
              {l.down ? <i className="rds-smoke" aria-hidden="true"><b /><b /><b /></i> : null}</> : null}
            {fx && fx.lot === i ? <i key={fx.n} className={`rds-fx k-${fx.kind} ${fx.win ? 'is-win' : 'is-miss'}`} aria-hidden="true">{Array.from({ length: 6 }, (_, k) => <b key={k} style={{ '--k': k }} />)}</i> : null}
          </button>; })}
        {(r.hitters || []).map((lvl, i) => <i key={i} className={`rds-man ${i >= (r.hitters.length - (r.hurt || 0)) ? 'is-down' : ''}`} style={{ '--i': i }} data-tip={`hitter L${lvl}`}><b /></i>)}
      </div>
      {fx ? <p key={fx.n} className={`rds-banner k-${fx.kind} s-${fx.side} ${fx.win ? 'is-win' : 'is-miss'}`} role="status">{fx.word}</p> : null}
      {live ? <div className="rds-bar" role="toolbar" aria-label="Raid moves">{moves.map(([k, what], i) => <button key={k} type="button" className={`rds-move ${pick === k ? 'active' : ''}`} disabled={!myTurn || busy}
        onClick={() => choose(k)} data-tip={`${what}${NEEDS_LOT.has(k) ? ' — then tap a building' : ''}`} data-testid={`mv-${k}`}><kbd>{i + 1}</kbd><i>{MOVE_ICON[k]}</i><span>{k}</span></button>)}</div>
        : <p className="rds-over" data-testid="raid-over">RAID OVER · {r.end} · {n(r.paid)} MP{(r.downLots || []).length ? ` · ${r.downLots.length} store${r.downLots.length === 1 ? '' : 's'} down` : ''}</p>}
    </div>
    <ol className="rds-log">{(r.moves || []).slice().reverse().map((m, i) => <li key={i} className={`s-${m.side}`}>{m.word}</li>)}</ol>
  </section>;
}
