import React from 'react';
import { Countdown } from './RunnersPanel';
import '../styles/stageBattles.css';

const sg = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(1)}%`;
const short = (s, n = 26) => (String(s || '').length > n ? `${String(s).slice(0, n - 1)}…` : String(s || ''));

// one fight read from the numbers: each corner's move since the bell, sparks (seat duels won), who leads and by how much
export function fightRead(p) {
  const move = x => (Number(x?.now) || 0) - (Number(x?.start) || 0); const a = move(p.a); const b = move(p.b);
  const seats = p.duels?.seats || []; const sa = seats.filter(s => s.win === 'a').length; const sb = seats.filter(s => s.win === 'b').length;
  const lead = sa !== sb ? (sa > sb ? 'a' : 'b') : a !== b ? (a > b ? 'a' : 'b') : '';
  const gap = Math.abs(a - b); const pull = Math.max(-1, Math.min(1, ((sa - sb) / Math.max(1, seats.length)) * 0.7 + Math.max(-0.3, Math.min(0.3, (a - b) / 20))));
  const who = lead ? short(p[lead].name, 18) : ''; const close = Math.abs(sa - sb) <= 1 && gap < 2;
  const call = !lead ? 'Dead level — anyone\'s bell.' : close ? `Neck and neck — ${who} by a hair.` : sa + sb && Math.abs(sa - sb) >= 3 ? `${who} is running away with it, ${Math.max(sa, sb)}–${Math.min(sa, sb)} on sparks.` : `${who} leads ${Math.max(sa, sb)}–${Math.min(sa, sb)}.`;
  return { a, b, sa, sb, lead, pull, call, seats };
}

// ⚔ THE TWO LIVE FIGHTS on the Main Stage, as a show you can read at a glance: two corners squaring up, a rope pulled by who is
// winning, one spark pip per seat duel, the bell clock and a one-line call. Points only — never a bet. The full fight (reel, duel
// board, table) opens underneath.
export function StageBattles({ b, onFull, full }) {
  const pairs = (b?.pairs || []).slice(0, 2);
  if (!pairs.length) return null;
  return <section className="sbt" data-testid="stage-battles">
    <header className="sbt-head"><span className="m-label">⚔ LIVE NOW · {pairs.length} {pairs.length === 1 ? 'FIGHT' : 'FIGHTS'}</span>{b.endsAt ? <span className="sbt-bell">🔔 bell in <Countdown at={b.endsAt} /></span> : null}
      <button type="button" className="m-btn sbt-full" onClick={onFull} aria-expanded={!!full} data-testid="stage-battles-full">{full ? 'Hide the full fight' : 'Full fight, table & throne'}</button></header>
    <div className="sbt-row">{pairs.map((p, i) => { const r = fightRead(p);
      const corner = k => <div className={`sbt-corner is-${k} ${r.lead === k ? 'is-lead' : r.lead ? 'is-behind' : ''}`}><i className="sbt-emoji" aria-hidden>{p[k].emoji || '🃏'}</i>{r.lead === k && <u className="sbt-crown" aria-label="leading">👑</u>}
        <b data-tip={p[k].name}>{short(p[k].name)}</b><em className={`m-num ${r[k] >= 0 ? 'm-pos' : 'm-neg'}`} key={sg(r[k])}>{sg(r[k])}</em><small>{k === 'a' ? r.sa : r.sb} ⚡ sparks</small></div>;
      return <article key={`${p.a.key}-${p.b.key}`} className="sbt-fight" style={{ '--i': i }} data-testid={`stage-fight-${i}`}>
        <i className="sbt-glow" aria-hidden /><span className="sbt-tag">FIGHT {i + 1}</span>
        <div className="sbt-ring">{corner('a')}<span className="sbt-vs" aria-hidden><i>💥</i><b>VS</b></span>{corner('b')}</div>
        <div className="sbt-rope" aria-label={`Rope: ${r.lead ? `${p[r.lead].name} is pulling` : 'level'}`}><i className="sbt-knot" style={{ transform: `translateX(${(-r.pull * 46).toFixed(1)}%)` }} /></div>
        {r.seats.length > 0 && <ol className="sbt-pips" aria-label="Seat duels">{r.seats.map(s => <li key={s.seat} className={s.win === 'a' ? 'is-a' : s.win === 'b' ? 'is-b' : ''}
          data-tip={`Seat ${s.seat}: $${s.a?.symbol} ${sg(s.a?.pct)} vs $${s.b?.symbol} ${sg(s.b?.pct)}${s.win ? ` — spark to $${s[s.win]?.symbol}` : ' — level'}`}><i>⚡</i></li>)}</ol>}
        <p className="sbt-call" data-testid={`stage-call-${i}`}>🎙 {r.call}</p>
      </article>; })}</div>
  </section>;
}
