import React from 'react';

export default function AmbientBackground() {
  return (
    <div className="ambient-background" data-testid="ambient-background" aria-hidden="true">
      <div className="ambient-grid" />
      <div className="ambient-orb ambient-orb-one" />
      <div className="ambient-orb ambient-orb-two" />
      <div className="ambient-orbit ambient-orbit-one" />
      <div className="ambient-orbit ambient-orbit-two" />
      <div className="ambient-scanline" />
    </div>
  );
}