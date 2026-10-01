import React, { useState } from 'react';

// Animated badge art without the lag: a 35KB still poster everywhere; the GIF only plays while you hover/focus it,
// or when `live` (the one badge you're looking at). Locked badges stay dimmed — no CSS filters on animated layers.
export function BadgeArt({ art, name, live = false, locked = false, size = 'md' }) {
  const [hot, setHot] = useState(false);
  if (!art) return <span className={`badge-art ${size} is-empty`} aria-hidden="true">🏅</span>;
  return <span className={`badge-art ${size} ${locked ? 'is-locked' : ''}`} onMouseEnter={() => setHot(true)} onMouseLeave={() => setHot(false)} onFocus={() => setHot(true)} onBlur={() => setHot(false)}>
    <img src={`${art}.${live || hot ? 'gif' : 'jpg'}`} alt={name} loading="lazy" decoding="async" draggable="false" />
  </span>;
}
