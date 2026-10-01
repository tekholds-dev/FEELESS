import { apiUrl } from './api';

// Lag catcher: measures what this browser actually feels (API latency, long tasks, FPS), reports once a
// minute, and flips the site into lite effects when the device is struggling. Cheap by design: one fetch
// wrapper, one PerformanceObserver, and a 1-second FPS sample every 30 seconds while the tab is visible.
const LITE_KEY = 'feeless:fx-lite';
let started = false;
let origFetch = null;
const state = { api: {}, longTasks: 0, longMs: 0, fps: [], errors: 0, slowStreak: 0 };

export const liteMode = () => { try { return localStorage.getItem(LITE_KEY) || ''; } catch { return ''; } };
// Auto lite is temporary: it is stamped ('auto@<ms>') and expires after AUTO_LITE_MS, and 3 healthy minutes in a row
// switch it back off. A lite mode the user picked ('on') is never touched.
const AUTO_LITE_MS = 6 * 3600 * 1000;
export const isAutoLite = m => String(m || '').startsWith('auto');
export function autoLiteExpired(mode, now = Date.now()) {
  if (!isAutoLite(mode)) return false;
  const at = Number(String(mode).split('@')[1]);
  return !at || now - at > AUTO_LITE_MS;
}
export function setLite(mode) {
  try { if (mode) localStorage.setItem(LITE_KEY, mode); else localStorage.removeItem(LITE_KEY); } catch { /* private mode */ }
  document.body.classList.toggle('fx-lite', !!mode);
}

// Pure: should this minute's numbers switch the device to lite effects?
export function shouldGoLite({ fps, longMs }) {
  return (fps != null && fps < 38) || longMs > 1500;
}

function sampleFps() {
  if (document.hidden) return;
  let frames = 0; const t0 = performance.now();
  const tick = now => { frames += 1; if (now - t0 < 1000) requestAnimationFrame(tick); else state.fps.push(Math.round((frames * 1000) / (now - t0))); };
  requestAnimationFrame(tick);
}

function flush() {
  const fps = state.fps.length ? Math.round(state.fps.reduce((a, b) => a + b, 0) / state.fps.length) : null;
  const report = { page: window.location.pathname.replace(/\/[1-9A-HJ-NP-Za-km-z]{32,44}|\/0x[0-9a-fA-F]{40}/g, '/:id'), api: state.api, longTasks: state.longTasks, longMs: state.longMs, fps, lite: document.body.classList.contains('fx-lite'), errors: state.errors };
  if (!liteMode() && shouldGoLite(report)) { state.slowStreak += 1; if (state.slowStreak >= 2) setLite(`auto@${Date.now()}`); } else state.slowStreak = 0;
  if (isAutoLite(liteMode()) && fps != null) { state.okStreak = shouldGoLite(report) ? 0 : (state.okStreak || 0) + 1; if (state.okStreak >= 3) { state.okStreak = 0; setLite(''); } }
  const has = Object.keys(report.api).length || report.longTasks || fps != null;
  Object.assign(state, { api: {}, longTasks: 0, longMs: 0, fps: [], errors: 0 });
  if (!has) return;
  // keepalive fetch, not sendBeacon: Chrome refuses beacons with a JSON content type, so reports never arrived.
  try { (origFetch || fetch)(apiUrl('/api/reputation/perf'), { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(report) }).catch(() => {}); } catch { /* best effort */ }
}

export function startPerfWatch() {
  if (started || typeof window === 'undefined' || !window.performance) return;
  started = true;
  if (autoLiteExpired(liteMode())) setLite('');
  if (liteMode()) document.body.classList.add('fx-lite');
  fetch(apiUrl('/api/reputation/perf/config')).then(r => r.json()).then(c => { if (c.forceLite) document.body.classList.add('fx-lite'); }).catch(() => {});
  const orig = window.fetch.bind(window);
  origFetch = orig;
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!url.includes('/api/') || url.includes('/api/reputation/perf')) return orig(input, init);
    const t0 = performance.now();
    try { return await orig(input, init); } catch (e) { state.errors += 1; throw e; } finally {
      const key = url.replace(/^https?:\/\/[^/]+/, '').split('?')[0];
      const list = state.api[key] || (state.api[key] = []);
      if (list.length < 50) list.push(Math.round(performance.now() - t0));
    }
  };
  try {
    new PerformanceObserver(list => list.getEntries().forEach(e => { state.longTasks += 1; state.longMs += Math.round(e.duration); })).observe({ type: 'longtask', buffered: false });
  } catch { /* longtask unsupported (Safari) */ }
  setInterval(sampleFps, 30000); setTimeout(sampleFps, 5000);
  setInterval(flush, 60000);
  document.addEventListener('visibilitychange', () => { if (document.hidden) flush(); });
}
