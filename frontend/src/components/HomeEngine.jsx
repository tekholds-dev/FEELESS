// ⚛ FUSE FORGE (Home; owner, 2026-10-15: "that home look is still ass — a dope animation that shows a crazy cool FEELESS feature"). The feature
// nobody else has: MANY COINS → ONE FUSE CARD. The live coins of a real tier card orbit the forge, spiral into its core, flash, and the card
// is forged — a holographic card that tilts in 3D, every coin on it with its live %. Every 8s the next tier card is forged (Blaze carries
// the 💵 REAL MONEY badge). Data = the public `/fuses/prime` cards; a coin's % is its own leg reading, "—" when unknown. Hover holds.
import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import { TokenAvatar } from './terminal/MarketPrimitives';
import '../styles/homeEngine.css';

const POLL = 30000;
const FORGE_MS = 8000;
const TIER_LOOK = { degen: 'blaze', next: 'plasma', balanced: 'gold', safe: 'prism', ever: 'nebula' };
// pure: the cards the forge cycles through — real first, coins that really hold money, each coin with its live %
export function forgeCards(prime) {
  const cards = (prime?.cards || []).map(c => ({ id: c.id || c.tpl, tpl: c.tpl, label: String(c.label || c.tpl || 'Fuse'), real: !!c.real, look: TIER_LOOK[c.tpl] || 'blaze',
    coins: (c.legs || []).filter(l => l?.symbol && !l.placeholder).slice(0, 6).map(l => ({ mint: l.mint, sym: String(l.symbol).slice(0, 10), pair: l.pairAddress, pct: l.pnlPct == null ? null : Number(l.pnlPct), usd: Number(l.usd) || 0 })) }))
    .filter(c => c.coins.length);
  return cards.sort((a, b) => (b.real - a.real) || (b.coins.length - a.coins.length));
}
export const pctWord = p => (p == null || !Number.isFinite(p) ? '—' : Math.abs(p) >= 1000 ? `+${(p / 100 + 1).toFixed(1)}x` : `${p > 0 ? '+' : ''}${p.toFixed(1)}%`);
const pairOf = c => ({ chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.sym } });

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null); const [i, setI] = useState(0); const [hold, setHold] = useState(false);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      sharedJson('/api/reputation/fuses/prime', { maxAge: POLL - 2000 }).then(p => { if (on && p) setD(p); }).catch(() => {}); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  const cards = useMemo(() => forgeCards(d), [d]);
  useEffect(() => { if (hold || cards.length < 2) return undefined; const t = setInterval(() => setI(x => x + 1), FORGE_MS); return () => clearInterval(t); }, [hold, cards.length]);
  if (!cards.length) return null;
  const k = i % cards.length; const cur = cards[k]; const n = cur.coins.length;
  const go = (e, url) => { if (onOpen) { e.preventDefault(); onOpen(url); } };
  return <section className={`frg is-${cur.look}`} data-testid="home-engine" onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)}>
    <div className="frg-stage" key={cur.id + i} data-testid="frg-stage" aria-label={`${n} coins forging into ${cur.label}`}>
      <i className="frg-floor" aria-hidden="true" /><i className="frg-halo" aria-hidden="true" />
      <div className="frg-orbit" aria-hidden="true">{cur.coins.map((c, j) => <span key={`${c.mint}-${j}`} className="frg-coin" style={{ '--a': `${(360 / n) * j}deg`, '--j': j }}>
        <span className="frg-coin-in"><TokenAvatar pair={pairOf(c)} size={34} /></span></span>)}</div>
      <i className="frg-burst" aria-hidden="true" />{[0, 1, 2, 3, 4, 5, 6, 7].map(s => <i key={s} className="frg-shard" aria-hidden="true" style={{ '--s': `${s * 45}deg` }} />)}
      <div className="frg-card" data-testid="frg-card"><div className="frg-tilt">
        <i className="frg-holo" aria-hidden="true" /><i className="frg-sheen" aria-hidden="true" />
        <header><b>{cur.label}</b>{cur.real ? <em className="frg-real">💵 REAL MONEY</em> : <em>📄 PAPER</em>}</header>
        <ul>{cur.coins.map((c, j) => <li key={`${c.mint}-${j}`}><TokenAvatar pair={pairOf(c)} size={18} /><span>${c.sym}</span><b className={c.pct == null ? '' : c.pct >= 0 ? 'up' : 'dn'}>{pctWord(c.pct)}</b></li>)}</ul>
        <footer><span>{n} COIN{n === 1 ? '' : 'S'}</span><i>⚛</i><span>ONE FUSE</span></footer>
      </div></div>
    </div>
    <div className="frg-side">
      <span className="frg-kick">⚛ FUSE FORGE <i className="frg-live" aria-hidden="true">● LIVE</i></span>
      <h2>Many coins.<br /><b>One Fuse.</b></h2>
      <p>FEELESS fuses live coins into one card — the engine rotates, trails and banks each coin for you. These are the real cards running right now.</p>
      <div className="frg-tiers" role="tablist" aria-label="Fuse cards">{cards.map((c, j) => <button key={c.id} type="button" role="tab" aria-selected={j === k} className={j === k ? 'active' : ''}
        onClick={() => setI(j)} data-testid={`frg-t-${c.tpl}`}>{c.label.replace(/^Prime /, '')}{c.real ? ' 💵' : ''}</button>)}</div>
      <ol className="frg-legs" key={cur.id}>{cur.coins.map((c, j) => <li key={`${c.mint}-${j}`}><button type="button" onClick={() => openCoin({ mint: c.mint, symbol: c.sym, pairAddress: c.pair })}>
        <TokenAvatar pair={pairOf(c)} size={20} /><b>${c.sym}</b><span className={c.pct == null ? '' : c.pct >= 0 ? 'up' : 'dn'}>{pctWord(c.pct)}</span></button></li>)}</ol>
      <a className="frg-go m-btn m-go" href="/terminal/fuse?tab=lab" onClick={e => go(e, '/terminal/fuse?tab=lab')}>⚛ Forge your own Fuse</a>
    </div>
  </section>;
}
