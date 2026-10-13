import { startFxPause, FX_SURFACES, govern, setFxPressure, BIG_PX } from './fxPause';

test('off-screen animated surfaces are paused and resume when they scroll back in', () => {
  let cb; const observed = [];
  global.IntersectionObserver = class { constructor(f) { cb = f; } observe(el) { observed.push(el); } disconnect() {} };
  document.body.innerHTML = '<div class="prime-card" id="a"></div><div class="mc-stage" id="b"></div><div class="plain"></div>';
  const stop = startFxPause();
  expect(observed.map(e => e.id)).toEqual(['a', 'b']);                       // only the animated surfaces are watched
  cb([{ target: observed[0], isIntersecting: false }, { target: observed[1], isIntersecting: true }]);
  expect(observed[0].classList.contains('fx-off')).toBe(true);
  expect(observed[1].classList.contains('fx-off')).toBe(false);
  cb([{ target: observed[0], isIntersecting: true }]);
  expect(observed[0].classList.contains('fx-off')).toBe(false);
  expect(FX_SURFACES).toContain('.bf-arena');
  stop();
});

test('🩺 the governor pauses endless animations that are off-screen or in a hidden tab, and under pressure only the big layers', () => {
  const mk = (rect, iterations = Infinity) => { const a = { playState: 'running', effect: { target: { getBoundingClientRect: () => rect }, getComputedTiming: () => ({ iterations }) } };
    a.pause = () => { a.playState = 'paused'; }; a.play = () => { a.playState = 'running'; }; return a; };
  const box = (top, w = 100, h = 100) => ({ top, bottom: top + h, left: 0, right: w, width: w, height: h });
  const onScreen = mk(box(100)); const below = mk(box(5000)); const once = mk(box(5000), 1); const big = mk(box(0, 800, 600)); const gone = mk({ top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 });
  const userPaused = mk(box(100)); userPaused.playState = 'paused';
  const doc = { hidden: false, getAnimations: () => [onScreen, below, once, big, gone, userPaused] }; const win = { innerWidth: 1000, innerHeight: 800 };
  expect(govern(doc, win)).toMatchObject({ running: 3, paused: 2, shed: 0 });
  expect([onScreen, below, once, big, gone].map(a => a.playState)).toEqual(['running', 'paused', 'running', 'running', 'paused']);   // a one-shot animation is never touched
  below.effect.target.getBoundingClientRect = () => box(300); govern(doc, win);
  expect(below.playState).toBe('running'); expect(userPaused.playState).toBe('paused');                 // back in view → resumes; what it did not pause it never resumes
  setFxPressure(1); govern(doc, win);
  expect(big.playState).toBe('paused'); expect(onScreen.playState).toBe('running'); expect(800 * 600).toBeGreaterThanOrEqual(BIG_PX);   // jank: only the big layer goes
  setFxPressure(0); govern(doc, win); expect(big.playState).toBe('running');
  doc.hidden = true; govern(doc, win); expect([onScreen, big].map(a => a.playState)).toEqual(['paused', 'paused']);                      // a hidden tab animates nothing
  doc.hidden = false; govern(doc, win); expect(onScreen.playState).toBe('running');
  expect(govern({}, win)).toBeNull();
});
