// 🧈 BODY FLAGS (owner 2026-11-15 "still major lag site wide … clean butter browsing"): a rule like `body:has(.fuse-page) .mouse-glow`
// makes the browser re-check the WHOLE page for that selector on every DOM change anywhere — measured 45 ms of style work per inserted
// node (each price tick, each chat line) with ~80 such checks live. Same result, no cost: once per changed frame we look the few
// markers up ourselves and set a plain body class (`body.has-fuse-page`), and the CSS matches that instead.
export const BODY_FLAGS = [
  ['.fuse-page', 'has-fuse-page'],
  ['.legal-consent', 'has-legal-consent'],
  ['.hqp', 'has-hqp'],
  ['.pwr', 'has-pwr'],
  ['.fwd-place', 'has-fwd-place'],
  ['.terminal-main.page-feed', 'has-page-feed'],
];
export function syncBodyFlags(doc = document) {
  const b = doc?.body; if (!b) return;
  BODY_FLAGS.forEach(([sel, cls]) => { const on = !!doc.querySelector(sel); if (b.classList.contains(cls) !== on) b.classList.toggle(cls, on); });
}
