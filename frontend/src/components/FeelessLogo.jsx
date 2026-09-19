import React from 'react';

export function FeelessMark({ size = 40, glow = true }) {
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 100 100" width={size} height={size} className={glow ? 'drop-shadow-[0_0_12px_rgba(20,241,149,0.7)]' : ''}>
        <defs>
          <linearGradient id="fLeaf" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00FFA3" />
            <stop offset="55%" stopColor="#14F195" />
            <stop offset="100%" stopColor="#0B8F5E" />
          </linearGradient>
          <radialGradient id="fShine" cx="40%" cy="35%" r="40%">
            <stop offset="0%" stopColor="#EAFFF3" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#EAFFF3" stopOpacity="0" />
          </radialGradient>
        </defs>
        <path d="M20 15 C55 5, 85 25, 82 55 C60 42, 40 48, 30 65 C22 50, 18 32, 20 15 Z" fill="url(#fLeaf)" />
        <path d="M28 45 C55 35, 80 50, 78 78 C58 68, 42 72, 34 88 C26 76, 24 60, 28 45 Z" fill="url(#fLeaf)" />
        <path d="M20 15 C55 5, 85 25, 82 55 C60 42, 40 48, 30 65 C22 50, 18 32, 20 15 Z" fill="url(#fShine)" />
      </svg>
    </div>
  );
}

export function FeelessWordmark({ size = 28 }) {
  return (
    <div className="flex items-center gap-3">
      <FeelessMark size={size + 12} />
      <div className="leading-none">
        <div className="font-black tracking-[0.14em] text-white" style={{ fontSize: size, letterSpacing: '0.14em' }}>FEELESS</div>
        <div className="text-[9px] tracking-[0.28em] text-[#14F195]/80 mt-0.5">SAME TX. ZERO FEES. MORE FOR YOU.</div>
      </div>
    </div>
  );
}
