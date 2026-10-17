import { apiUrl } from './api';
import { fxPressure, setFxPressure, fxStats } from './fxPause';

// Lag catcher: measures what this browser actually feels (API latency, long tasks, FPS), reports once a
// minute, and flips the site into lite effects when the device is struggling. Cheap by design: one fetch
// wrapper, one PerformanceObserver, and a 1-second FPS sample every 30 seconds while the tab is visible.
const LITE_KEY = 'feeless:fx-lite';
let started = false;
let origFetch = null;
const state = { api: {}, longTasks: 0, longMs: 0, fps: [], errors: 0, errRoutes: {}, slowStreak: 0 };

export const liteMode = () => { try { return localStorage.getItem(LITE_KEY) || ''; } catch { return ''; } };
// An old auto lite stamp ('auto@<ms>') may still sit in storage; a lite mode the user picked ('on') is never touched.
export const isAutoLite = m => String(m || '').startsWith('auto');
export function setLite(mode) {
  try { if (mode) localStorage.setItem(LITE_KEY, mode); else localStorage.removeItem(LITE_KEY); } catch { /* private mode */ }
  document.body.classList.toggle('fx-lite', !!mode);
}

// Pure: should this minute's numbers switch the device to lite effects?
// 🔋 Chrome caps pages at 30 fps on battery / low-power mode — a steady 30 is the browser saving power, NOT lag. Going lite at
// < 38 froze every animation on laptops that were fine. Real jank = under 24 fps, or > 1.5s of blocked main thread a minute.
export function shouldGoLite({ fps, longMs }) {
  return (fps != null && fps < 24) || longMs > 1500;
}

function sampleFps() {
  if (document.hidden) return;
  let frames = 0; const t0 = performance.now();
  const tick = now => { frames += 1; if (now - t0 < 1000) requestAnimationFrame(tick); else state.fps.push(Math.round((frames * 1000) / (now - t0))); };
  requestAnimationFrame(tick);
}

function flush() {
  const fps = state.fps.length ? Math.round(state.fps.reduce((a, b) => a + b, 0) / state.fps.length) : null;
  const report = { page: window.location.pathname.replace(/\/[1-9A-HJ-NP-Za-km-z]{32,44}|\/0x[0-9a-fA-F]{40}/g, '/:id'), api: state.api, longTasks: state.longTasks, longMs: state.longMs, fps, lite: document.body.classList.contains('fx-lite'), errors: state.errors, errRoutes: state.errRoutes };
  // 🩺 A FIX, NOT A LITE MODE (owner, 2026-10-13): two bad minutes → the FX governor pauses only the BIG animated layers (the ones that
  // cost frames); every small effect, colour and layout stays. Three healthy minutes → they come back. The whole-site lite look is
  // only ever the user's own switch now.
  const bad = shouldGoLite(report);
  if (!liteMode()) {
    if (bad) { state.okStreak = 0; state.slowStreak += 1; if (state.slowStreak >= 2 && !fxPressure()) setFxPressure(1); }
    else if (fps != null) { state.slowStreak = 0; if (fxPressure()) { state.okStreak = (state.okStreak || 0) + 1; if (state.okStreak >= 3) { state.okStreak = 0; setFxPressure(0); } } }
  }
  report.fx = { ...fxStats, pressure: fxPressure() };
  const has = Object.keys(report.api).length || report.longTasks || fps != null;
  Object.assign(state, { api: {}, longTasks: 0, longMs: 0, fps: [], errors: 0, errRoutes: {} });
  if (!has) return;
  // keepalive fetch, not sendBeacon: Chrome refuses beacons with a JSON content type, so reports never arrived.
  try { (origFetch || fetch)(apiUrl('/api/reputation/perf'), { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) }).catch(() => {}); } catch { /* best effort */ }
}

export function startPerfWatch() {
  if (started || typeof window === 'undefined' || !window.performance) return;
  started = true;
  if (isAutoLite(liteMode())) setLite('');   // auto lite never carries over a reload: every visit is measured fresh (a user-picked lite stays)
  if (liteMode()) document.body.classList.add('fx-lite');
  fetch(apiUrl('/api/reputation/perf/config')).then(r => r.json()).then(c => { if (c.forceLite) document.body.classList.add('fx-lite'); }).catch(() => {});
  const orig = window.fetch.bind(window);
  origFetch = orig;
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!url.includes('/api/') || url.includes('/api/reputation/perf')) return orig(input, init);
    const t0 = performance.now();
    const key = url.replace(/^https?:\/\/[^/]+/, '').split('?')[0];
    try { return await orig(input, init); } catch (e) {
      if (e?.name !== 'AbortError') {   // a deliberate abort (unmount / timeout we set) is not an error; anything else names its route + kind
        state.errors += 1;
        const k = `${key.replace(/[1-9A-HJ-NP-Za-km-z]{32,44}/g, ':id').slice(0, 80)} · ${String(e?.name || 'Error').slice(0, 20)}`;
        if (Object.keys(state.errRoutes).length < 20 || state.errRoutes[k]) state.errRoutes[k] = (state.errRoutes[k] || 0) + 1;
      }
      throw e;
    } finally {
      const list = state.api[key] || (state.api[key] = []);
      if (list.length < 50) list.push(Math.round(performance.now() - t0));
    }
  };
  try {
    new PerformanceObserver(list => list.getEntries().forEach(e => { state.longTasks += 1; state.longMs += Math.round(e.duration); })).observe({ type: 'longtask', buffered: false });
  } catch { /* longtask unsupported (Safari) */ }
  setInterval(sampleFps, 30000); setTimeout(sampleFps, 5000);
  setInterval(flush, 60000);
  let hidAt = 0;   // a tab flicking hidden / visible must not post a report each time (≤ one hidden-flush per 10s)
  document.addEventListener('visibilitychange', () => { if (document.hidden && Date.now() - hidAt > 10000) { hidAt = Date.now(); flush(); } });
}
