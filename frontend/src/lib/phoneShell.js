// 📱 THE PHONE SHELL (owner 2026-11-05): on any phone or fold, every tab is locked to the screen. The page itself never scrolls and never gets pushed around by Safari's bars or the keyboard; only the tab's own content moves inside it. Layout comes from the real usable size, never a device name.
export const isLockable = (w = window) => w.innerWidth <= 1024 && (w.matchMedia?.('(pointer: coarse)').matches || w.innerWidth <= 700);
const main = () => document.querySelector('.terminal-main');
// 🪟 On an unfolded fold, a tab's blocks sit either side of the crease. Finds the tab's own list of blocks (the first level with two or more) and marks it; the sheet does the rest. A tab with its own floor or cockpit is left alone.
export function markFoldSplit(w = window, d = document) {
  const lock = d.body.classList.contains('phone-lock'); const on = lock && w.innerWidth >= 620 && w.innerWidth > w.innerHeight;
  d.body.classList.toggle('fold-wide', on);
  const old = d.querySelector('.fold-split'); const root = d.querySelector('[data-testid^="terminal-page-"]') || main();
  if (!on || !root) { old?.classList.remove('fold-split'); return null; }
  let el = root;
  for (let depth = 0; depth < 8 && el; depth += 1) {   // go down while one child holds nearly all the height; the level where height is shared is the tab's list of blocks
    const kids = [...el.children].map(k => [k, k.getBoundingClientRect().height]).filter(x => x[1] > 0); const total = kids.reduce((n, x) => n + x[1], 0); const top = kids.reduce((b, x) => (x[1] > (b?.[1] || 0) ? x : b), null);
    if (!top) { el = null; break; }
    if (kids.length >= 2 && top[1] < total * 0.7 && !el.classList.contains('terminal-main')) break;
    el = top[0];
    if (depth === 7) el = null;
  }
  const skip = !el || el.children.length < 2 || el.closest('.dfl, canvas') || el.querySelector(':scope > .dfl');
  if (old && (skip || old !== el)) old.classList.remove('fold-split');
  if (skip) return null;
  el.classList.add('fold-split');
  return el;
}
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
  let foldT = 0; const foldSoon = () => { clearTimeout(foldT); foldT = setTimeout(() => markFoldSplit(w, d), 500); };
  const foldWatch = typeof MutationObserver !== 'undefined' ? new MutationObserver(foldSoon) : null; if (foldWatch && d.body) foldWatch.observe(d.body, { childList: true, subtree: true });
  w.addEventListener('resize', foldSoon); w.addEventListener('orientationchange', foldSoon); foldSoon();
  paint(); const late = setTimeout(paint, 1500); w.addEventListener('resize', soon); w.addEventListener('orientationchange', soon); vv?.addEventListener('resize', soon); vv?.addEventListener('scroll', soon); d.addEventListener('focusin', focus); d.addEventListener('scroll', relay, true);
  return () => { clearTimeout(foldT); foldWatch?.disconnect(); w.removeEventListener('resize', foldSoon); w.removeEventListener('orientationchange', foldSoon); clearTimeout(late); w.removeEventListener('resize', soon); w.removeEventListener('orientationchange', soon); vv?.removeEventListener('resize', soon); vv?.removeEventListener('scroll', soon); d.removeEventListener('focusin', focus); d.removeEventListener('scroll', relay, true); w.scrollTo = realTo; d.body.classList.remove('phone-lock', 'phone-kb'); };
}
