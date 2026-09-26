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

// Any external image that fails (e.g. host forbids cross-site embedding) retries once via the FEELESS image proxy.
export function installImageFallback() {
  if (typeof document === 'undefined' || window.__feelessImg) return;
  window.__feelessImg = true;
  document.addEventListener('error', e => {
    const img = e.target;
    if (!(img instanceof HTMLImageElement) || img.dataset.proxied || !/^https:\/\//.test(img.src) || img.src.startsWith(window.location.origin)) return;
    img.dataset.proxied = '1';
    img.src = `/api/reputation/img?u=${encodeURIComponent(img.src)}`;
  }, true);
}
