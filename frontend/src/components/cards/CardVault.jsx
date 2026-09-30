import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { MetaCard } from './MetaCard';

// Profile › Vault: every card this wallet holds (badges, season + weekly drops). Tap one to hold it:
// drag to turn it, click to flip for the lore and what it has earned.
export function CardVault({ address }) {
  const [cards, setCards] = useState(null);
  const [open, setOpen] = useState(null);
  const [flipped, setFlipped] = useState(false);
  useEffect(() => {
    let alive = true; setCards(null);
    if (address) fetch(apiUrl(`/api/reputation/cards/${address}`)).then(r => r.json()).then(d => alive && setCards(d.cards || [])).catch(() => alive && setCards([]));
    return () => { alive = false; };
  }, [address]);
  useEffect(() => {
    if (!open) return undefined;
    const k = e => e.key === 'Escape' && setOpen(null);
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [open]);
  const earned = (cards || []).reduce((a, c) => a + (c.earnedMine || 0), 0);
  return <section className="wp-card card-vault" data-testid="card-vault">
    <h3>Card vault <small>{cards ? `${cards.length} card${cards.length === 1 ? '' : 's'}${earned ? ` · earned ${earned.toFixed(4)} SOL` : ''}` : ''}</small></h3>
    {cards == null ? <p className="wp-bio">Opening the vault…</p> : !cards.length ? <p className="wp-bio">No cards yet. Badges and season drops land here as collectible cards.</p>
      : <div className="cv-grid m-scroll">{cards.map(c => <button key={c.key} type="button" className="mc-pick" onClick={() => { setOpen(c); setFlipped(false); }} title={c.title}><MetaCard card={c} size="sm" /></button>)}</div>}
    {open && <div className="cv-overlay" role="dialog" aria-modal="true" aria-label={open.title} onClick={e => e.target === e.currentTarget && setOpen(null)}>
      <div className="cv-hold m-pop"><MetaCard card={open} size="lg" interactive flipped={flipped} onFlip={setFlipped} />
        <div className="m-row"><button type="button" className="m-btn" onClick={() => setFlipped(f => !f)}>{flipped ? '↺ Front' : '↻ Lore & earnings'}</button><button type="button" className="m-btn" onClick={() => setOpen(null)}>Close</button></div></div>
    </div>}
  </section>;
}
