// Off-screen FX pause: the Arena had ~400 animations running at once and 4 in 5 were on cards nobody could see.
// ONE IntersectionObserver marks animated surfaces that are off-screen with `fx-off` (CSS pauses every animation inside);
// they resume the moment they scroll back in. One MutationObserver (batched per frame) picks up cards as they mount.
export const FX_SURFACES = '.mc-stage, .prime-card, .ar-card, .bf-arena, .sc3-card, .th-stage, .cfx, .cbg, .swap-desk';
let started = false;

export function startFxPause(root = document.body) {
  if (started || typeof IntersectionObserver === 'undefined' || typeof MutationObserver === 'undefined') return () => {};
  started = true;
  const seen = new WeakSet();
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => e.target.classList.toggle('fx-off', !e.isIntersecting));
  }, { rootMargin: '200px 0px' });
  const scan = () => { root.querySelectorAll(FX_SURFACES).forEach(el => { if (!seen.has(el)) { seen.add(el); io.observe(el); } }); };
  let queued = false;
  const mo = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; scan(); });
  });
  mo.observe(root, { childList: true, subtree: true });
  scan();
  return () => { io.disconnect(); mo.disconnect(); started = false; };
}
