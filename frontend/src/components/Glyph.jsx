import React from 'react';

// FEELESS glyph set — custom SVG icons (no emoji), gradient-filled, sized by `size`.
const P = {
  bull: 'M3 5c1 3 3 4 5 4h8c2 0 4-1 5-4-1 4-2 6-4 7v3c0 3-2 5-5 5s-5-2-5-5v-3C5 11 4 9 3 5zm6 8a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm-5 4h4c0 1-1 2-2 2s-2-1-2-2z',
  bear: 'M6 3a3 3 0 0 1 3 2h6a3 3 0 1 1 3 4c1 1 2 3 2 5 0 5-4 8-8 8s-8-3-8-8c0-2 1-4 2-5a3 3 0 0 1 0-6zm3 9a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm-3 3c-1.5 0-2.5 1-2.5 2s1 1.5 2.5 1.5 2.5-.5 2.5-1.5-1-2-2.5-2z',
  degen: 'M4 4h16v16H4zm4 3a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm8 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-4 3.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM8 14a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm8 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z',
  swords: 'M3 3l7 7-2 2-7-7V3zm18 0v2l-7 7-2-2 7-7zM6 14l4 4-2 2-1-1-2 2-2-2 2-2-1-1zm12 0l2 2-1 1 2 2-2 2-2-2-1 1-2-2z',
  trophy: 'M7 3h10v2h3v3a4 4 0 0 1-4 4h-.5A5 5 0 0 1 13 15v3h3v3H8v-3h3v-3a5 5 0 0 1-2.5-3H8a4 4 0 0 1-4-4V5h3zm-1 4v1a2 2 0 0 0 2 2V7zm12 0v3a2 2 0 0 0 2-2V7z',
  radar: 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm0 3a7 7 0 1 0 7 7h-2a5 5 0 1 1-5-5zm0 4a3 3 0 1 0 3 3h-3z',
  crown: 'M3 17h18l-1.5-9-4.5 4-3-7-3 7-4.5-4zM4 19h16v2H4z',
  target: 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4z',
  bundle: 'M3 7l9-4 9 4v10l-9 4-9-4zm9-1.8L6.5 7.5 12 10l5.5-2.5zM5 9.3v6.4l6 2.7v-6.4zm14 0-6 2.7v6.4l6-2.7z',
  shield: 'M12 2l8 3v6c0 5-3 9-8 11-5-2-8-6-8-11V5zm-1 13l6-6-1.5-1.5L11 12 8.5 9.5 7 11z',
  ban: 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm-6 9v2h12v-2z',
  scan: 'M3 3h6v2H5v4H3zm12 0h6v6h-2V5h-4zM3 15h2v4h4v2H3zm16 0h2v6h-6v-2h4zM7 11h10v2H7z',
  person: 'M12 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8zm0 10c5 0 8 3 8 6v2H4v-2c0-3 3-6 8-6z',
  bag: 'M7 7a5 5 0 0 1 10 0h3l-1 14H5L4 7zm2 0h6a3 3 0 0 0-6 0z',
  chart: 'M3 20h18v2H3zM5 12h3v7H5zm5-5h3v12h-3zm5 3h3v9h-3z',
  fire: 'M12 2c1 4 6 6 6 12a6 6 0 0 1-12 0c0-3 2-5 3-6 0 2 1 3 2 3 0-4-1-6 1-9z',
  cat: 'M4 4l4 4h8l4-4v9a8 8 0 0 1-16 0zm5 8a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z',
};
const TONES = { mint: ['#c9fff0', '#19f58f', '#00784f'], rose: ['#ffd0d8', '#fa708c', '#9b1c38'], violet: ['#eadcff', '#b388ff', '#5a2fb0'], gold: ['#fff3c4', '#f5c542', '#a8740a'], sky: ['#d6f1ff', '#5ec8ff', '#1b6fb3'], plain: ['#ffffff', '#cfe8da', '#5f7d6d'] };
export function Glyph({ name, tone = 'mint', size = 18, className = '' }) {
  const [a, b, c] = TONES[tone] || TONES.mint;
  const id = `g-${name}-${tone}`;
  return <svg className={`glyph ${className}`} width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
    <defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={a} /><stop offset=".55" stopColor={b} /><stop offset="1" stopColor={c} /></linearGradient></defs>
    <path d={P[name] || P.target} fill={`url(#${id})`} fillRule="evenodd" />
  </svg>;
}
