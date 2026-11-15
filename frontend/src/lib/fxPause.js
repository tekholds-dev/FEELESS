import { useEffect, useState } from 'react';
// Off-screen FX pause: the Arena had ~400 animations running at once and 4 in 5 were on cards nobody could see.
// ONE IntersectionObserver marks animated surfaces that are off-screen with `fx-off` (CSS pauses every animation inside);
// they resume the moment they scroll back in. One MutationObserver (batched per frame) picks up cards as they mount.
export const FX_SURFACES = '.chat-fx, .mc-stage, .prime-card, .ar-card, .bf-arena, .sc3-card, .th-stage, .cfx, .cbg, .swap-desk, .clv, .spx-banner, .fcd-legs, .wsky, .st-scene, .lv-stage, .br-scene, .pw-field, .ltk-field, .fd-sky, .fd-wire, .gp-rails, .agd, .crt-stage, .col-flow, .cfl';
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
// Effects off, for lite mode or a viewer who asked for less motion. One rule, read everywhere.
export const isCalm = () => document.body.classList.contains('fx-lite') || !!window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
const mine = new WeakSet();
// 🎮 GAME RULES (owner 2026-11-14: "just like a game, shit should load when a user is there … stop peoples phone and pc from burning up … while
// still keeping all live animations", "no less than 25 fps"): (1) AWAY — no touch, key, wheel or pointer for AWAY_MS → every endless animation
// rests; the first input brings them all back. (2) LAYERS — an animated SVG part can't move on the GPU, so each one repainted the page under it:
// its outer <svg> gets its own layer once (capped), so a blinking panther repaints 60 px, not the page. (3) PRESSURE (< 25 fps) also rests the
// SVG-part animations, the ones that still cost paint.
export const AWAY_MS = 90000;
const LAYER_CAP = 80;
let away = false; let layered = 0; const lifted = new WeakSet();
export const isAway = () => away;
// 📣 'fxchange' on window whenever away or the quality level moves: video and canvas loops (not CSS, so the governor can't pause them) listen.
const told = () => { try { window.dispatchEvent(new Event('fxchange')); } catch { /* not in a page */ } };
export function setAway(v) { const n = !!v; if (n === away) return; away = n; try { document.body.classList.toggle('fx-away', n); govern(); } catch { /* not in a page */ } told(); }
// 🎮 The frame budget a canvas loop should keep: 0 = draw nothing (away / hidden / calm). Level 0 → 30 fps, level 1 → 15, level 2 → 8 (still alive).
export const fxFrameMs = () => (away || (typeof document !== 'undefined' && document.hidden) || isCalm() ? 0 : [33, 66, 125][fxLevel()]);
const TINY_PX = 24 * 24;   // level 2 keeps the live dots, carets and blinks (≤ 24×24): they say "it's working" and cost next to nothing
const svgRoot = t => (typeof SVGElement !== 'undefined' && t instanceof SVGElement ? (t.ownerSVGElement ? (t.closest?.('svg:not(svg svg)') || t.ownerSVGElement) : t) : null);
let pressure = 0; let holds = 0;   // `holds`: a surface doing heavy work for the user right now (the Brain while the model answers) asks the big layers to rest
export const fxPressure = () => (pressure || holds ? 1 : 0);
// 🎮 quality level like a game's dynamic settings: 0 full · 1 big layers + SVG parts + background video rest · 2 every endless effect bigger
// than a live dot rests too (only when level 1 still sat under 25 fps). The lag catcher steps it up and back down.
export const fxLevel = () => Math.max(pressure, holds ? 1 : 0);
export const fxStats = { running: 0, paused: 0, shed: 0, at: 0 };

export function govern(doc = document, win = window) {
  if (!doc || typeof doc.getAnimations !== 'function') return null;
  const vw = win.innerWidth; const vh = win.innerHeight; const hid = !!doc.hidden;
  const list = doc.getAnimations().filter(a => a?.effect?.target && a.effect.getComputedTiming?.().iterations === Infinity);
  const rects = list.map(a => a.effect.target.getBoundingClientRect());
  let running = 0; let paused = 0; let shed = 0;
  list.forEach((a, i) => {
    const r = rects[i];
    const off = hid || away || (r.width === 0 && r.height === 0) || r.bottom < -200 || r.top > vh + 200 || r.right < -200 || r.left > vw + 200;
    const svg = svgRoot(a.effect.target);
    const area = r.width * r.height; const lvl = fxLevel();
    const big = !off && lvl > 0 && (area >= BIG_PX || !!svg || (lvl > 1 && area > TINY_PX));
    if (!off && !big && svg && !lifted.has(svg) && layered < LAYER_CAP) { lifted.add(svg); layered += 1; try { svg.style.willChange = 'transform'; svg.style.contain = 'paint'; } catch { /* read-only node */ } }
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

export function setFxPressure(n) { pressure = Math.max(0, Math.min(2, Math.round(Number(n) || 0))); try { document.body.classList.toggle('fx-shed', pressure > 0 || holds > 0); govern(); } catch { /* not in a page */ } told(); }
// 🧠 holdFx(true) while a local model answers in the Brain (it shares the GPU Chrome draws with): big endless layers pause, then come back.
// Counted, so two holders never release each other; independent of the lag catcher's own pressure.
export function holdFx(on) { holds = Math.max(0, holds + (on ? 1 : -1)); try { document.body.classList.toggle('fx-shed', pressure > 0 || holds > 0); govern(); } catch { /* not in a page */ } told(); }

function startGovernor() {
  if (typeof document === 'undefined' || typeof document.getAnimations !== 'function') return () => {};
  let last = 0; let timer = null;
  const run = () => { timer = null; last = Date.now(); govern(); };
  const soon = () => { if (timer) return; timer = setTimeout(run, Math.max(0, 250 - (Date.now() - last))); };
  const every = setInterval(() => { if (!away && Date.now() - seenAt > AWAY_MS) setAway(true); run(); }, 1500);
  let seenAt = Date.now(); let lastMark = 0;   // 🎮 someone is here: any input marks it (at most 4 times a second) and wakes a resting page at once
  const here = () => { const now = Date.now(); if (now - lastMark < 250) return; lastMark = now; seenAt = now; if (away) setAway(false); };
  const HERE = ['pointermove', 'pointerdown', 'keydown', 'wheel', 'touchstart'];
  HERE.forEach(k => window.addEventListener(k, here, { passive: true, capture: true }));   // also while hidden: surfaces that mount in a background tab are paused too (a pass with nothing to do costs ~nothing)
  window.addEventListener('scroll', soon, { passive: true, capture: true });
  window.addEventListener('resize', soon, { passive: true });
  document.addEventListener('visibilitychange', run);
  setTimeout(run, 800);
  return () => { HERE.forEach(k => window.removeEventListener(k, here, { capture: true })); clearInterval(every); clearTimeout(timer); window.removeEventListener('scroll', soon, { capture: true }); window.removeEventListener('resize', soon); document.removeEventListener('visibilitychange', run); };
}

// 👁 One hook for "is this on screen?" (was copied into CatWorkbench and HiveBoard): pause polls and art while scrolled away. No observer → on.
export function useOnScreen(ref) {
  const [on, setOn] = useState(true);
  useEffect(() => { const el = ref.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { threshold: 0.05 }); io.observe(el); return () => io.disconnect(); }, [ref]);
  return on;
}
