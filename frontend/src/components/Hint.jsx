import React from 'react';

// Small "?" with an explanation on hover/focus/tap.
export function Hint({ text }) {
  return <span className="hint" tabIndex={0} role="note" aria-label={text} data-hint={text}>?</span>;
}

// Lightweight-charts (our chart library) has a known internal race: when a chart is torn
// down (switching coins fast, unmounting a room) its own ResizeObserver/paint loop can fire
// one more repaint against the just-disposed canvas, throwing "Object is disposed" from
// code we don't own and can't try/catch. It's harmless — the chart is already gone — but left
// unhandled it surfaces as an uncaught window error. Swallow only this exact signature.
export function installChartDisposalGuard() {
  if (typeof window === 'undefined' || window.__feelessChartGuard) return;
  window.__feelessChartGuard = true;
  const isBenign = (msg, stack) => /Object is disposed/i.test(msg || '') && /_internal_paint|CanvasRenderingTarget2D|TimeAxisWidget|PriceAxisWidget|ChartWidget|PaneWidget/i.test(stack || '');
  window.addEventListener('error', e => {
    if (isBenign(e.message, e.error?.stack)) e.preventDefault();
  });
  window.addEventListener('unhandledrejection', e => {
    if (isBenign(e.reason?.message, e.reason?.stack)) e.preventDefault();
  });
}

// Any truncated text (…) shows its full content on hover.
export function installOverflowTitles() {
  if (typeof document === 'undefined' || window.__feelessTitles) return;
  window.__feelessTitles = true;
  document.addEventListener('mouseover', e => {
    const el = e.target;
    if (!(el instanceof HTMLElement) || el.title || el.dataset.hint || el.children.length > 0 || /^(BODY|HTML|SCRIPT|STYLE|MAIN|SECTION)$/.test(el.tagName)) return;
    const text = el.textContent?.trim();
    if (!text || text.length > 400) return;
    const cs = getComputedStyle(el);
    const clipped = (cs.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 1) || (cs.webkitLineClamp && cs.webkitLineClamp !== 'none' && el.scrollHeight > el.clientHeight + 2);
    if (clipped) el.title = text;
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
