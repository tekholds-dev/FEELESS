import '../styles/eco.css';

// 🔋 PHONE ECO (owner, 2026-10-29: "iPhone Duo / mobile overheats viewing FEELESS in Safari — that can't happen"). A phone held for minutes
// at 120 Hz with a WebGL globe, full-screen blur layers and JS-driven number glides is a hand warmer. Owner, same day: "cut the heat but
// don't stop the vital and cool effects". So eco cuts only the HIDDEN costs and keeps every transform/opacity animation (those run on the
// compositor and cost next to nothing): no backdrop blur / blur glow layers, the WebGL globe draws only while touched, 1× canvas pixels,
// live prices every 6s, numbers snap + flash instead of a 12 Hz React glide. Lite effects stay the user's own choice. Settings › Look turns
// FULL effects on (`feeless:fx-full`). On touch phones / the Duo only (coarse pointer + iOS, or a short side ≤ 900 px).
export const FULL_KEY = 'feeless:fx-full';
/** pure: is this a phone-like device? (desktop touchscreens and laptops are not) */
export function isPhoneLike({ coarse, ua = '', w = 0, h = 0 }) {
  const ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && coarse);   // iPadOS / Safari "desktop site" reports a Mac
  return !!coarse && (ios || Math.min(w, h) <= 900);
}
const device = () => (typeof window === 'undefined' ? false : isPhoneLike({ coarse: !!window.matchMedia?.('(pointer: coarse)')?.matches, ua: navigator.userAgent,
  w: window.screen?.width || window.innerWidth, h: window.screen?.height || window.innerHeight }));
export const fullFx = () => { try { return localStorage.getItem(FULL_KEY) === '1'; } catch { return false; } };
export const ecoDevice = device;
export const ecoOn = () => device() && !fullFx();
export const isEco = () => typeof document !== 'undefined' && document.body.classList.contains('fx-eco');
export function startEco() {
  if (typeof document === 'undefined' || !ecoOn()) return false;
  document.body.classList.add('fx-eco');
  return true;
}
export function setFullFx(on) {
  try { if (on) localStorage.setItem(FULL_KEY, '1'); else localStorage.removeItem(FULL_KEY); } catch { /* private */ }
  if (on) document.body.classList.remove('fx-eco'); else startEco();
}
