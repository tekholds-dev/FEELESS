import React from 'react';
import '../styles/cardFx.css';

// 🎇 ONE set of live card backdrops, sitewide: <CardFx kind="aurora|grid|beam|embers" /> as the FIRST child of a card that has
// the class `cfx-host`. Own DOM layers (never the card's ::before / ::after), transform + opacity only, hidden in fx-lite /
// reduced motion, paused off-screen (`.cfx` itself is in lib/fxPause FX_SURFACES — never the host: pausing a host froze its own fade-in half way). `tone` = up | down | gold recolours it.
export const CARD_FX = ['aurora', 'grid', 'beam', 'embers'];
const PARTS = { aurora: 3, grid: 2, beam: 2, embers: 7 };

export function CardFx({ kind = 'aurora', tone }) {
  const k = CARD_FX.includes(kind) ? kind : 'aurora';
  return <span className={`cfx cfx-${k}${tone ? ` is-${tone}` : ''}`} aria-hidden data-testid={`cfx-${k}`}>
    {Array.from({ length: PARTS[k] }, (_, i) => <i key={i} style={{ '--i': i }} />)}
  </span>;
}
