// Off-screen FX pause: the Arena had ~400 animations running at once and 4 in 5 were on cards nobody could see.
// ONE IntersectionObserver marks animated surfaces that are off-screen with `fx-off` (CSS pauses every animation inside);
// they resume the moment they scroll back in. One MutationObserver (batched per frame) picks up cards as they mount.
export const FX_SURFACES = '.mc-stage, .prime-card, .ar-card, .bf-arena, .sc3-card, .th-stage, .cfx, .cbg, .swap-desk, .clv, .spx-banner, .fcd-legs';
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
  const stopGov = startGovernor();
  return () => { io.disconnect(); mo.disconnect(); stopGov(); started = false; };
}

// 🩺 THE FX GOVERNOR — the lag catcher's FIX (owner, 2026-10-13: "lag catcher actually fixes instead of a lite mode"). The surface list
// above only covers classes someone remembered to add. This needs no list: every ~1.5s (and on scroll) it reads EVERY endless
// animation on the page and
//   · pauses the ones whose element is off-screen, has no box, or whose tab is hidden — and resumes them the moment they are back;
//   · under real jank (`setFxPressure(1)` from the lag catcher: < 24 fps or > 1.5s blocked a minute) pauses only the BIG layers
//     (≥ BIG_PX² of screen: sweeps, auroras, drifting backdrops — the ones that cost a frame) and leaves every small effect running.
// It only ever resumes an animation it paused itself. Reads first, then writes: one layout per pass.
export const BIG_PX = 150000;
const mine = new WeakSet();
let pressure = 0; let holds = 0;   // `holds`: a surface doing heavy work for the user right now (the Brain while the model answers) asks the big layers to rest
export const fxPressure = () => (pressure || holds ? 1 : 0);
export const fxStats = { running: 0, paused: 0, shed: 0, at: 0 };

export function govern(doc = document, win = window) {
  if (!doc || typeof doc.getAnimations !== 'function') return null;
  const vw = win.innerWidth; const vh = win.innerHeight; const hid = !!doc.hidden;
  const list = doc.getAnimations().filter(a => a?.effect?.target && a.effect.getComputedTiming?.().iterations === Infinity);
  const rects = list.map(a => a.effect.target.getBoundingClientRect());
  let running = 0; let paused = 0; let shed = 0;
  list.forEach((a, i) => {
    const r = rects[i];
    const off = hid || (r.width === 0 && r.height === 0) || r.bottom < -200 || r.top > vh + 200 || r.right < -200 || r.left > vw + 200;
    const big = !off && (pressure > 0 || holds > 0) && r.width * r.height >= BIG_PX;
    if (off || big) {
      if (a.playState === 'running') { a.pause(); mine.add(a); }
      if (mine.has(a)) { paused += 1; if (big) shed += 1; }
    } else {
      if (mine.has(a) && a.playState === 'paused') { a.play(); mine.delete(a); }
      running += 1;
    }
  });
  Object.assign(fxStats, { running, paused, shed, at: Date.now() });
  return fxStats;
}

export function setFxPressure(n) { pressure = n > 0 ? 1 : 0; try { document.body.classList.toggle('fx-shed', pressure > 0 || holds > 0); govern(); } catch { /* not in a page */ } }
// 🧠 holdFx(true) while a local model answers in the Brain (it shares the GPU Chrome draws with): big endless layers pause, then come back.
// Counted, so two holders never release each other; independent of the lag catcher's own pressure.
export function holdFx(on) { holds = Math.max(0, holds + (on ? 1 : -1)); try { document.body.classList.toggle('fx-shed', pressure > 0 || holds > 0); govern(); } catch { /* not in a page */ } }

function startGovernor() {
  if (typeof document === 'undefined' || typeof document.getAnimations !== 'function') return () => {};
  let last = 0; let timer = null;
  const run = () => { timer = null; last = Date.now(); govern(); };
  const soon = () => { if (timer) return; timer = setTimeout(run, Math.max(0, 250 - (Date.now() - last))); };
  const every = setInterval(run, 1500);   // also while hidden: surfaces that mount in a background tab are paused too (a pass with nothing to do costs ~nothing)
  window.addEventListener('scroll', soon, { passive: true, capture: true });
  window.addEventListener('resize', soon, { passive: true });
  document.addEventListener('visibilitychange', run);
  setTimeout(run, 800);
  return () => { clearInterval(every); clearTimeout(timer); window.removeEventListener('scroll', soon, { capture: true }); window.removeEventListener('resize', soon); document.removeEventListener('visibilitychange', run); };
}
