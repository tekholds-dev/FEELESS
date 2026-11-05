// 📱 THE PHONE SHELL (owner 2026-11-05): on any phone or fold, every tab is locked to the screen. The page itself never scrolls and never gets pushed around by Safari's bars or the keyboard; only the tab's own content moves inside it. Layout comes from the real usable size, never a device name.
export const isLockable = (w = window) => w.innerWidth <= 1024 && (w.matchMedia?.('(pointer: coarse)').matches || w.innerWidth <= 700);
const main = () => document.querySelector('.terminal-main');
export function installPhoneShell(w = window, d = document) {
  if (!w.visualViewport && typeof w.innerHeight !== 'number') return () => {};
  const vv = w.visualViewport; let frame = 0;
  const paint = () => { frame = 0; const on = isLockable(w); d.body.classList.toggle('phone-lock', on); if (!on) { d.documentElement.style.removeProperty('--app-vh'); return; } const h = vv ? vv.height : w.innerHeight; const keyboard = vv ? w.innerHeight - vv.height > 120 : false; d.documentElement.style.setProperty('--app-vh', `${Math.round(h)}px`); d.documentElement.style.setProperty('--app-top', `${Math.round(vv ? vv.offsetTop : 0)}px`); d.body.classList.toggle('phone-kb', keyboard); const bar = d.querySelector('.mobile-tabbar'); const shown = bar && getComputedStyle(bar).display !== 'none' && !keyboard; d.documentElement.style.setProperty('--tabbar-h', shown ? `${Math.round(bar.getBoundingClientRect().height)}px` : '0px'); };
  const soon = () => { if (!frame) frame = requestAnimationFrame(paint); };
  // the input you are typing in stays above the keyboard
  const focus = e => { if (!d.body.classList.contains('phone-lock') || !e.target?.matches?.('input,textarea,[contenteditable]')) return; setTimeout(() => e.target.scrollIntoView?.({ block: 'center', behavior: 'smooth' }), 280); };
  // pages written for a scrolling window keep working: scrolling the tab counts as scrolling the page
  const realTo = w.scrollTo.bind(w);
  w.scrollTo = (...a) => { const m = d.body.classList.contains('phone-lock') ? main() : null; if (m) m.scrollTo(...a); else realTo(...a); };
  const relay = e => { if (e.target === main()) w.dispatchEvent(new Event('scroll')); };
  paint(); const late = setTimeout(paint, 1500); w.addEventListener('resize', soon); w.addEventListener('orientationchange', soon); vv?.addEventListener('resize', soon); vv?.addEventListener('scroll', soon); d.addEventListener('focusin', focus); d.addEventListener('scroll', relay, true);
  return () => { clearTimeout(late); w.removeEventListener('resize', soon); w.removeEventListener('orientationchange', soon); vv?.removeEventListener('resize', soon); vv?.removeEventListener('scroll', soon); d.removeEventListener('focusin', focus); d.removeEventListener('scroll', relay, true); w.scrollTo = realTo; d.body.classList.remove('phone-lock', 'phone-kb'); };
}
