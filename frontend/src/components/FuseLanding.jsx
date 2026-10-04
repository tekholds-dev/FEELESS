import React, { useEffect, useState } from 'react';
import { usePrime } from './ArenaPrime';
import { useLivePrices } from '../lib/livePrices';
import { TokenAvatar } from './terminal/MarketPrimitives';
import '../styles/fuseLanding.css';

// ⚡ Fuse landing: a dark stage, the spotlight comes on, ONE live card spins up to full size. Front = the card, back = its live book
// (tap to flip). Every number is the card's real state right now — it shows what a Fuse IS, it never promises a result.
const pct = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;
const usd = v => `$${(v || 0) >= 1000 ? (v / 1000).toFixed(1) + 'K' : (v || 0).toFixed(2)}`;
const px = v => (!v ? '—' : v >= 1 ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : `$${Number(v).toPrecision(3)}`);
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
  const [flip, setFlip] = useState(false);
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setTimeout(() => setLit(true), 350); const i = setInterval(() => setNow(Date.now() / 1000), 1000); return () => { clearTimeout(t); clearInterval(i); }; }, []);
  const live = useLivePrices((d?.cards || []).flatMap(c => (c.legs || []).map(l => l.pairAddress)));
  const c = heroCard(d?.cards, live);
  const cards = d?.cards || [];
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
        <div className={`fld-card ${flip ? 'is-flip' : ''}`} role="button" tabIndex={0} aria-pressed={flip} aria-label={flip ? 'Show the card front' : 'Show live card data'} onClick={() => setFlip(f => !f)}
          onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setFlip(f => !f))} data-testid="fld-card">
          <div className="fld-inner">
            <div className="fld-face fld-front">
              <span className="fld-tag">{c ? (c.real ? '💵 REAL MONEY' : '📄 PAPER · TRUE FILLS') : 'FUSE'}</span>
              <div className="fld-ring">{(c?.legs || []).slice(0, 4).map((l, i) => <i key={l.pairAddress} style={{ '--i': i, '--n': Math.min(4, c.legs.length) }}><TokenAvatar pair={{ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } }} size={54} /></i>)}</div>
              <b className="fld-name">{c ? c.label : 'Dealing a live card…'}</b>
              <span className="fld-coins">{(c?.legs || []).map(l => `$${l.symbol}`).join(' · ')}</span>
              {c && <em key={pct(c.pnlPct)} className={`fld-pct m-num fl-tick ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(c.pnlPct)}</em>}
              <small className="fld-hint">this run · tap for the live book ⟲</small></div>
            <div className="fld-face fld-back">
              <span className="fld-tag">LIVE BOOK · {c ? c.label : ''}</span>
              <ul className="fld-book">{(c?.legs || []).map(l => <li key={l.pairAddress}><b>${l.symbol}</b><small>{l.role}</small><span className="m-num">{px(l.entry)} → {px(l.livePx)}</span><em className={`m-num ${l.livePct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(l.livePct)}</em></li>)}</ul>
              {c && <div className="fld-kv"><span><small>IN CARD</small><b className="m-num">{usd(c.valueUsd)}</b></span><span><small>STARTED</small><b className="m-num">{usd(c.startUsd)}</b></span><span><small>ROUNDS</small><b className="m-num">{c.rounds || 0}</b></span></div>}
              <small className="fld-hint">entry → now per coin · fees are shown apart, never inside P&L</small></div>
          </div>
        </div>
        <ul className="fld-notes is-r">{NOTES.slice(2).map((n, i) => note(n, i + 2))}</ul>
      </div>
    </div>
    <ol className="fld-how" data-testid="fld-how">{HOW.map(([e, t, s], i) => <li key={t} style={{ '--i': i }}><span aria-hidden="true">{e}</span><b>{i + 1} · {t}</b><p>{s}</p></li>)}</ol>
    <small className="m-dim fld-fine">Cards show what happened, never what will. Coins can go to zero; FEELESS never holds your keys and never signs for you.</small>
  </section>;
}
