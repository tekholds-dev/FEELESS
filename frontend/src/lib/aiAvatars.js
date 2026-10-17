// 🖼 the avatars on chat bubbles + chart pins (owner, 2026-10-16): OSSY + G4 = the owner's own pictures, the ten agents = the picked GIFs
const BASE = '/assets/ai-pfp/';
const AGENTS = ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge'];
export function avatarOf(who) {
  const k = String(who || '').toLowerCase();
  if (k === 'ossy' || k === 'local') return `${BASE}ossy.webp`;
  if (k === 'g4' || k === 'lan') return `${BASE}g4.webp`;
  return AGENTS.includes(k) ? `${BASE}${k}.gif` : null;
}
