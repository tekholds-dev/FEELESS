import React, { useId } from 'react';

// The FEELESS lead-cat mark, alive: blinking eye, twitching ears, swaying tail.
// Variants recolor the same rig — 'mint' is the default leader, others mark different moods/tiers.
const VARIANTS = {
  mint: { a: '#7dfbd4', b: '#12c07a', glow: 'rgba(18,192,122,.55)' },
  gold: { a: '#fff3c4', b: '#f5c542', glow: 'rgba(245,197,66,.55)' },
  rose: { a: '#ffd0d8', b: '#fa708c', glow: 'rgba(250,112,140,.5)' },
  violet: { a: '#eadcff', b: '#b388ff', glow: 'rgba(179,136,255,.5)' },
  ghost: { a: '#e7f3ee', b: '#9fd3b6', glow: 'rgba(159,211,182,.35)' },
};

const HEAD = 'M40 22c9-8 20-10 28-4 3-9 10-14 17-13-2 6-1 11 3 15 9 9 12 21 8 33-3 9-10 16-20 19-13 4-27 0-35-10-9-11-9-27-1-40z';

// Fur markings for the cat family — clipped to the head so every variant keeps Fee's silhouette.
function Markings({ pattern, color }) {
  if (pattern === 'stripes') return <g stroke={color} strokeWidth="4.5" strokeLinecap="round" opacity=".85" fill="none"><path d="M50 26l4 12M60 22l3 12M70 24l1 11" /><path d="M36 50l10 2M34 60l11 0" /></g>;
  if (pattern === 'spots') return <g fill={color} opacity=".85"><circle cx="50" cy="34" r="5" /><circle cx="44" cy="56" r="4" /><circle cx="78" cy="30" r="3.5" /><circle cx="58" cy="64" r="3" /></g>;
  if (pattern === 'patch') return <path d="M30 40c6-14 22-18 30-10 4 5 1 16-7 22-9 6-20 3-23-12z" fill={color} opacity=".85" />;
  return null;
}

// `colors` ([fur, accent]) + `pattern` let any FeeCat wear Fee's animated rig in its own coat.
export function FeeCatMark({ size = 40, variant = 'mint', animate = true, className = '', colors, pattern, label }) {
  const c = colors ? { a: colors[0], b: colors[1], glow: `${colors[1]}88` } : (VARIANTS[variant] || VARIANTS.mint);
  // Unique per instance: a shared id would point every cat at the first gradient in the DOM — and if
  // that one sits in a hidden element (e.g. the desktop-hidden mobile tab bar), every cat renders blank.
  const id = `feecat-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  return (
    <svg
      className={`feecat-mark ${animate ? 'is-alive' : ''} ${className}`}
      width={size} height={size} viewBox="0 0 120 120"
      style={{ filter: `drop-shadow(0 0 ${size * 0.18}px ${c.glow})` }}
      aria-label={label || 'Fee, the FEELESS lead cat'}
      role="img"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={c.a} />
          <stop offset="1" stopColor={c.b} />
        </linearGradient>
        <clipPath id={`${id}-head`}><path d={HEAD} /></clipPath>
      </defs>
      <g className="fc-body">
        {/* tail / mane sweep */}
        <g className="fc-tail" style={{ transformOrigin: '46px 74px' }}>
          <path d="M46 70c-14 2-24 12-28 26-3 10-2 20 3 30 3-11 10-19 20-24 8-4 14-3 19 2-2-9-5-16-14-19 6-2 11-6 13-13-5 3-9 2-13-2z" fill={`url(#${id})`} opacity=".95" />
        </g>
        {/* head */}
        <path d={HEAD} fill={`url(#${id})`} />
        {pattern && <g clipPath={`url(#${id}-head)`}><Markings pattern={pattern} color={c.b} /></g>}
        {/* ear twitch group (left ear) */}
        <path className="fc-ear fc-ear-l" style={{ transformOrigin: '46px 26px' }} d="M40 22c2-10 8-17 16-19-1 8 1 15 6 20-8-2-16-2-22-1z" fill={`url(#${id})`} />
        {/* snout */}
        <path d="M84 46c6 2 10 6 11 12-4 1-8 0-11-3-3 3-6 4-10 3 3-4 6-8 10-12z" fill={`url(#${id})`} opacity=".9" />
        {/* eye */}
        <ellipse className="fc-eye" cx="66" cy="42" rx="7" ry="5" fill="#04120b" />
        <circle className="fc-eye-spark" cx="68" cy="40" r="1.6" fill="#fff" />
      </g>
    </svg>
  );
}
