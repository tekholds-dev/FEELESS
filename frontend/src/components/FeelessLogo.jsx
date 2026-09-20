import React from 'react';

export function FeelessMark({ size = 40, glow = true }) {
  return <span className={`feeless-mark ${glow ? 'mark-glow' : ''}`} style={{ width: size, height: size }}>
    <img src="/assets/feeless-logo.png" alt="FEELESS" width={size} height={size} />
  </span>;
}

export function FeelessWordmark({ size = 28 }) {
  return <span className="feeless-wordmark">
    <FeelessMark size={size + 22} />
    <span><strong style={{ fontSize: size }}>FEELESS</strong><small>LESS NOISE. MORE ALPHA.</small></span>
  </span>;
}