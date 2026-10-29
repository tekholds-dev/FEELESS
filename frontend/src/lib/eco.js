import '../styles/eco.css';

// 🔋 PHONE ECO (owner, 2026-10-29: "iPhone Duo / mobile overheats viewing FEELESS in Safari — that can't happen"). A phone held for minutes
// at 120 Hz with a WebGL globe, full-screen blur layers and dozens of infinite animations is a hand warmer. On touch phones / the Duo
// (coarse pointer + iOS, or a short side ≤ 900 px) the site starts in eco: lite effects, no backdrop blur, the globe draws only while
// you touch it, live prices poll half as often. The trader can switch FULL effects back on in Settings › Look (`feeless:fx-full`).
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
  document.body.classList.add('fx-eco', 'fx-lite');
  return true;
}
export function setFullFx(on) {
  try { if (on) localStorage.setItem(FULL_KEY, '1'); else localStorage.removeItem(FULL_KEY); } catch { /* private */ }
  if (on) document.body.classList.remove('fx-eco', 'fx-lite'); else startEco();
}
