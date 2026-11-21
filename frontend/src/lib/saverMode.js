// 🔋 Battery + data saver (owner 2026-11-20, Slice 34: "so they can always work on the go … no battery burn or cell data burn"). On a phone or
// foldable (touch, ≤ 900 px), with Save-Data on, on low battery (< 20 %, not charging) or with reduced motion, the site wears `fx-lite` by itself:
// a still background (the smoke holds one frame), sparklines without animation, every heavy effect off (each sheet's body.fx-lite block).
// `body.fx-saver` names WHY it is on, so pollers can slow down too. It rides on top of phone eco (lib/eco.js); a user who picked FULL effects
// in Settings › Look (feeless:fx-full) keeps them, here too.
import { FULL_KEY } from './eco';
export function saverWhy(win = window, nav = typeof navigator !== 'undefined' ? navigator : {}, battery = null) {
  const mq = q => !!win.matchMedia?.(q)?.matches;
  if (mq('(pointer: coarse)') && win.innerWidth <= 900) return 'phone';
  if (nav.connection?.saveData) return 'save-data';
  if (mq('(prefers-reduced-motion: reduce)')) return 'reduced-motion';
  if (battery && !battery.charging && battery.level < 0.2) return 'low-battery';
  return '';
}
export const saverOn = () => typeof document !== 'undefined' && document.body.classList.contains('fx-saver');
/** A poll interval for this device: hidden tab = 4× slower, saver / phone eco on = 3× slower (cell data). */
export const pollMs = (ms, doc = typeof document !== 'undefined' ? document : null) => ms * (doc?.hidden ? 4 : 1) * (doc?.body?.classList.contains('fx-saver') || doc?.body?.classList.contains('fx-eco') ? 3 : 1);
export function applySaver(win = window, nav = navigator, battery = null) {
  let full = false; try { full = win.localStorage.getItem(FULL_KEY) === '1'; } catch { /* private window */ }
  const why = full ? '' : saverWhy(win, nav, battery); const b = win.document.body;
  b.classList.toggle('fx-saver', !!why); if (why) { b.classList.add('fx-lite'); b.dataset.saver = why; } else delete b.dataset.saver;
  return why;
}
export function startSaver(win = window, nav = navigator) {
  applySaver(win, nav);
  const again = () => applySaver(win, nav, battery_);
  let battery_ = null;
  win.addEventListener('resize', again, { passive: true });
  nav.connection?.addEventListener?.('change', again);
  nav.getBattery?.().then(bt => { battery_ = bt; again(); bt.addEventListener('levelchange', again); bt.addEventListener('chargingchange', again); }).catch(() => {});
}
