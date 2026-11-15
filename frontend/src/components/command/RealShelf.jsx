import React, { useState } from 'react';
import { motion } from 'motion/react';
import { apiUrl } from '../../lib/api';
import '../../styles/realShelf.css';

// 🌍 REAL WORLD, NOW (owner 2026-11-15: "real world stuff should show first … i wona see a 3d iphone fold option"). Real products people use
// today, newest phones first (iPhone Duo, iPhone 18 Pro, Galaxy Z Fold 8, Pixel 11 Pro Fold). One tap drops in the closest free CC0 model and
// writes its creative brief into the agent's ask box: your agent remixes it into something new. The rest of the library stays below.
export function RealShelf({ cards = [], cats = [], busy = '', onTake }) {
  const [at, setAt] = useState('');
  if (!cards.length) return null;
  const shown = at ? cards.filter(c => c.cat === at) : cards;
  return <section className="rws" aria-label="Real world, now" data-testid="rws">
    <header><small className="m-label">REAL WORLD · NOW</small><em>{cards.length} real products</em></header>
    <span className="rws-cats" role="group" aria-label="Which kind">{[['', 'All'], ...cats].map(([k, l]) => <button key={k || 'all'} type="button" className={at === k ? 'is-on' : ''} aria-pressed={at === k} onClick={() => setAt(k)} data-testid={`rws-cat-${k || 'all'}`}>{l}</button>)}</span>
    <ul className="rws-list">{shown.map((c, i) => <motion.li key={c.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 12) * 0.03, duration: 0.25 }}>
      <button type="button" disabled={!!busy} onClick={() => onTake?.(c)} data-tip={`Adds ${c.model.name} and writes the brief for your agent: ${c.brief}`} data-testid={`rws-${c.id}`}>
        <img src={!c.model.thumb ? undefined : String(c.model.thumb).startsWith('/api/') ? apiUrl(c.model.thumb) : c.model.thumb} alt="" loading="lazy" onError={e => { e.currentTarget.removeAttribute('src'); }} />
        <span><b>{busy === c.model.id ? 'Getting…' : c.name}</b><small>{c.line}</small>{c.remix ? <small className="rws-from">from {c.model.name}</small> : null}</span>
      </button></motion.li>)}</ul>
  </section>;
}
