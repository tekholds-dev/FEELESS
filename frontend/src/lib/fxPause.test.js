import { startFxPause, FX_SURFACES } from './fxPause';

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
