import React, { useEffect, useState } from 'react';
import { usePrime, primeRow, TIER } from './ArenaPrime';
import { LiveFuseCard } from './FuseCard';
import { useLivePrices } from '../lib/livePrices';
import '../styles/fuseLanding.css';

// ⚡ Fuse landing: no box — the page's own dark backdrop, a spotlight comes on, ONE live tier card (its real design) spins up to
// stage size; ⟲ flips it to its live book. Every number is the card's real state right now — it shows what a Fuse IS, it never promises a result.
const pct = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;
const NOTES = [
  ['①', 'Pick coins — or copy a card', 'Pools, majors and gated runners. Up to 3 + 3 on one card.'],
  ['②', 'One approval buys it all', 'You sign once. Every coin lands in YOUR wallet.'],
  ['③', 'Rounds do the work', 'Each round the losers are swapped and the winners ride.'],
  ['④', 'You hold the keys', 'Take profit, switch a coin or withdraw any time.'],
];
const HOW = [
  ['🧪', 'Build', 'Open the Lab, pick your coins or load a proven card, choose Safe / Balanced / Degen.'],
  ['⚡', 'Fuse', 'Review every fee and the minimum you get, then approve once.'],
  ['🔔', 'Play rounds', 'A 10s bell opens each round. Stops, take-profits and swaps follow your card plan.'],
  ['🏟', 'Compete', 'Cards fight in The Pit for the Throne and climb the weekly Crown Race.'],
];

// the best card on the board right now, with each coin's LIVE move since the card bought it
export function heroCard(cards, live) {
  const pool = (cards || []).filter(c => (c.legs || []).length);
  if (!pool.length) return null;
  const c = pool.reduce((a, b) => ((b.pnlPct ?? -1e9) > (a.pnlPct ?? -1e9) ? b : a));
  const legs = c.legs.map(l => { const p = live?.get?.(l.pairAddress)?.price || l.now || l.entry; return { ...l, livePx: p, livePct: l.entry ? (p / l.entry - 1) * 100 : 0 }; });
  return { ...c, legs };
}

export function FuseLanding({ onGo }) {
  const d = usePrime(20000);
  const [lit, setLit] = useState(false);
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setTimeout(() => setLit(true), 350); const i = setInterval(() => setNow(Date.now() / 1000), 1000); return () => { clearTimeout(t); clearInterval(i); }; }, []);
  const live = useLivePrices((d?.cards || []).flatMap(c => (c.legs || []).map(l => l.pairAddress)));
  const c = heroCard(d?.cards, live);
  const cards = d?.cards || [];
  const tier = TIER[c?.tier] || TIER.gold;
  const rounds = cards.reduce((n, x) => n + (x.rounds || 0), 0);
  const bell = Math.max(0, Math.min(...cards.filter(x => x.nextRoundAt && !x.resting).map(x => x.nextRoundAt), now + 3600) - now);
  const note = ([n, t, s], i) => <li key={n} style={{ '--i': i }}><b>{n}</b><span><strong>{t}</strong>{s}</span></li>;
  return <section className="fld" data-testid="fuse-landing">
    <div className={`fld-stage ${lit ? 'is-lit' : ''}`}>
      <span className="fld-cone" aria-hidden="true" /><span className="fld-floor" aria-hidden="true" />
      <div className="fld-copy">
        <small className="m-label">FEELESS · FUSE</small>
        <h2 className="fld-h">MANY COINS.<br /><em>ONE CARD.</em></h2>
        <p>Fuse pools, majors and fresh runners into a single card you own. Rounds swap the losers, the winners ride, and you sign every move.</p>
        {c && <div className="fld-hero" data-testid="fld-hero"><span>{c.label} · {c.real ? '💵 real money' : '📄 paper at true fills'}</span>
          <b key={pct(c.pnlPct)} className={`m-num fl-tick ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pnlPct)}</b><small>this run, right now · {(c.legs || []).map(l => `$${l.symbol}`).join(' · ')}</small></div>}
        <div className="fld-live" data-testid="fld-live">
          <span><small>LIVE TIER CARDS</small><b className="m-num">{cards.length || '—'}</b></span>
          <span><small>ROUNDS PLAYED</small><b key={rounds} className="m-num fl-tick">{rounds ? rounds.toLocaleString() : '—'}</b></span>
          <span><small>NEXT BELL</small><b className="m-num">{cards.length ? `${Math.floor(bell / 60)}:${String(Math.floor(bell % 60)).padStart(2, '0')}` : '—'}</b></span>
          <span><small>ON REAL MONEY</small><b className="m-num">{cards.filter(x => x.real).length}</b></span></div>
        <div className="fld-cta"><button type="button" className="m-btn primary m-go" onClick={() => onGo?.('lab')} data-testid="fld-build">⚡ Build a card</button>
          <button type="button" className="m-btn" onClick={() => onGo?.('arena')} data-testid="fld-arena">🏟 Watch the Arena</button></div>
      </div>
      <div className="fld-rig">
        <ul className="fld-notes is-l">{NOTES.slice(0, 2).map(note)}</ul>
        {/* the REAL tier card, in its own design (look + aura), at stage size — ⟲ flips it to its live book */}
        <div className="fld-card" data-testid="fld-card">{c ? <LiveFuseCard r={primeRow(c)} aura={tier.aura} look={tier.look} label={c.real ? '💵 REAL · FUSE WALLET' : '📄 PAPER · TRUE FILLS'} serverOnly={!!c.real} />
          : <span className="fld-ghost">Dealing a live card…</span>}</div>
        <ul className="fld-notes is-r">{NOTES.slice(2).map((n, i) => note(n, i + 2))}</ul>
      </div>
    </div>
    <ol className="fld-how" data-testid="fld-how">{HOW.map(([e, t, s], i) => <li key={t} style={{ '--i': i }}><span aria-hidden="true">{e}</span><b>{i + 1} · {t}</b><p>{s}</p></li>)}</ol>
    <small className="m-dim fld-fine">Cards show what happened, never what will. Coins can go to zero; FEELESS never holds your keys and never signs for you.</small>
  </section>;
}
