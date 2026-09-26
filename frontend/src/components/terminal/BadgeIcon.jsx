import React from 'react';

// Hand-made SVG emblems — one per badge, gradient-filled by tone.
const TONES = { gold: ['#fff3c4', '#f5c542', '#a8740a'], mint: ['#c9fff0', '#00e9a0', '#00784f'], bad: ['#ffd0d8', '#fa708c', '#9b1c38'], plain: ['#ffffff', '#b9d4c6', '#5f7d6d'] };
const PATHS = {
  'feeless-hq': 'M3 17h18l-1.5-9-4.5 4-3-7-3 7-4.5-4zM4 19h16v2H4z', // crown
  'fee-holder': 'M12 2c5 3 8 7 8 11a8 8 0 0 1-16 0c0-4 3-8 8-11zm0 5c-2 3-3 5-3 7h2c0-2 1-4 3-6z', // leaf-drop
  'feecat-holder': 'M4 4l4 4h8l4-4v9a8 8 0 0 1-16 0zm5 8a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z', // cat head
  'rfee-holder': 'M12 2l9 6-9 14L3 8zm0 4L7 9l5 8 5-8z', // gem
  'fee-whale': 'M2 13c3-5 9-6 14-3l4-3v6l-4-1c-2 5-8 7-14 1zm13-1a1 1 0 1 0 0 .1z', // whale
  'rides-with-fee': 'M8 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm8 0a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM4 9a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm16 0a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm-8 3c3 0 5 3 5 5s-2 3-5 3-5-1-5-3 2-5 5-5z', // paw
  caller: 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4z', // target
  'sharp-caller': 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm9-4l-7 7 1 1 7-7z', // target + dart
  'feeless-launcher': 'M12 2c4 2 6 6 6 11l-2 3H8l-2-3c0-5 2-9 6-11zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM9 18h6l-3 4z', // rocket
  'trusted-creator': 'M12 2l8 3v6c0 5-3 9-8 11-5-2-8-6-8-11V5zm-1 13l6-6-1.5-1.5L11 12 8.5 9.5 7 11z', // shield check
  'flagged-creator': 'M12 2l10 18H2zm-1 6v6h2V8zm0 8v2h2v-2z', // warning
  blocklisted: 'M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zM6 11v2h12v-2z', // no-entry
  'airdrop-recipient': 'M12 2c5 0 9 3 9 7H3c0-4 4-7 9-7zM4 10l7 8h2l7-8h-2l-6 6-6-6zM10 19h4v3h-4z', // parachute
  custom: 'M12 2l3 7 7 .5-5.5 4.5 2 7L12 17l-6.5 4 2-7L2 9.5 9 9z', // star
};
export function BadgeIcon({ id, tone = 'gold', size = 16 }) {
  const key = String(id || '').startsWith('custom-') ? 'custom' : id;
  const d = PATHS[key] || PATHS.custom;
  const [a, b, c] = TONES[tone] || TONES.gold;
  const gid = `bg-${key}-${tone}`;
  return <svg className="badge-svg" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
    <defs><linearGradient id={gid} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={a} /><stop offset=".55" stopColor={b} /><stop offset="1" stopColor={c} /></linearGradient></defs>
    <path d={d} fill={`url(#${gid})`} fillRule="evenodd" stroke={c} strokeWidth=".6" />
  </svg>;
}
