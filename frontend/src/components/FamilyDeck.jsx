import React, { Suspense, lazy, useEffect } from 'react';
import { useRemembered } from '../lib/remember';
// FamilyHQ is already in Crews' static graph — a lazy import of it split FamilyBadge into its own chunk and crashed Familia
// ("Cannot read properties of undefined (reading 'call')", 2026-10-22), so the Books come in statically
import { FamilyBooks as Books } from './FamilyHQ';
import { AvenueRoom as Avenue, TrenchList as Trench } from './CityAvenue';   // already in Familia's graph (FamilyWorld) — static, same reason
import { PoolHub, usePools } from './PoolHub';

// 🧰 THE FAMILY DECK (owner, 2026-10-22, on the block page: "img shows all requests never started" — the block had a 3D city over an empty void):
// every real tool runs right here under the family's own block — the desk's live P&L, the Trench Towers coins with one-tap trade, pools with the
// range tuner, the Night Vault, perps, the Pump board, cats, the rep market, the family Books and the members. One tab at a time, each loaded only
// when opened (no lag, nothing fetched for tabs you never open).
function Pools() { const p = usePools(); return p ? <PoolHub pools={p} /> : <p className="m-dim">Reading the pools…</p>; }
const Vault = lazy(() => import('./NightVault').then(m => ({ default: m.NightVault })));
const RepMarkets = lazy(() => import('./RepMarkets'));

export const DECK = [
  ['trades', '📈', 'Trade Center', 'the desk\'s real trades · live P&L'], ['tt', '🗼', 'Trench Towers', 'the intake list · trade it'],
  ['pools', '🏦', 'Pools', 'APY · 24h earned · range tuner'], ['vault', '💤', 'Night Vault', 'earn while you sleep'],
  ['perps', '📉', 'Perps', 'funding · leverage · venues'], ['radar', '📡', 'Pump board', 'hottest coins · one tap'],
  ['cats', '🐱', 'Cats', 'FeeCat live · your cats'], ['rep', '🎲', 'Rep market', 'call it → chips → points'],
  ['books', '📒', 'Books', 'the family\'s trades this week'], ['members', '👥', 'Members', 'seats · vitals · roles'],
];

export function FamilyDeck({ mine, tools }) {
  const [tab, setTab] = useRemembered('feeless.fam.deck', 'trades');
  useEffect(() => {   // 🏙 a block errand (e.g. "size JLP against your SOL") opens its tool here
    const go = e => { if (DECK.some(d => d[0] === e.detail)) setTab(e.detail); };
    window.addEventListener('feeless:deck', go); return () => window.removeEventListener('feeless:deck', go);
  }, [setTab]);
  const body = {
    trades: <Avenue lens="trades" />, tt: <Trench />, pools: <Pools />, vault: <Vault />, perps: <Avenue lens="perps" />, radar: <Avenue lens="pumpradar" />,
    cats: <Avenue lens="feecat" />, rep: <RepMarkets />,
    books: mine ? <Books book={mine.book} /> : <p className="m-dim">Join a family to see its Books.</p>,
    members: mine && tools ? tools('table') : <p className="m-dim">Your family's seats show here once you're in one.</p>,
  }[tab] || null;
  return <section className="fdk m-card" data-testid="family-deck">
    <header><b>🧰 FAMILY DECK</b><small>{DECK.length} tools · run the money from the block</small></header>
    <nav className="fdk-tabs" role="tablist" aria-label="Family tools">{DECK.map(([k, ic, name, how], i) => <button key={k} type="button" role="tab" aria-selected={tab === k}
      className={tab === k ? 'active' : ''} style={{ '--i': i }} onClick={() => setTab(k)} data-tip={`${name} — ${how}`} data-testid={`deck-${k}`}><i aria-hidden="true">{ic}</i><span><b>{name}</b><small>{how}</small></span></button>)}</nav>
    <div className="fdk-body" key={tab}><Suspense fallback={<p className="m-dim">Opening {DECK.find(d => d[0] === tab)?.[2]}…</p>}>{body}</Suspense></div>
  </section>;
}
