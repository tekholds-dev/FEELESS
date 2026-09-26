import React from 'react';

// Small "?" with an explanation on hover/focus/tap.
export function Hint({ text }) {
  return <span className="hint" tabIndex={0} role="note" aria-label={text} data-hint={text}>?</span>;
}

// Any truncated text (…) shows its full content on hover.
export function installOverflowTitles() {
  if (typeof document === 'undefined' || window.__feelessTitles) return;
  window.__feelessTitles = true;
  document.addEventListener('mouseover', e => {
    const el = e.target;
    if (!(el instanceof HTMLElement) || el.title || el.dataset.hint || !el.textContent?.trim()) return;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) el.title = el.textContent.trim().slice(0, 500);
  }, { passive: true });
}
