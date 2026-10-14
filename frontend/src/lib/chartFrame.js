// ⚡ ONE FRAME LOOP FOR EVERY CHART OVERLAY (owner, 2026-10-14: "site / agents tab still lags horribly"). ChartLive, ChartLevels and
// CandleFx each ran their own 30fps rAF loop on every chart, reading layout + the chart's scale 90 times a second while nothing moved.
// Now PriceChart BUMPS its chart when something really changed (a real tick, new data, a scroll / zoom, a resize) and one shared rAF
// runs each overlay's job only for the chart that changed — plus a once-a-second refresh (axis width, a missed bump). No frame work in a
// hidden tab. Pure DOM, no React render.
const ver = new WeakMap();    // chart container element → change counter
const jobs = new Set();       // { box: ref, fn, seen, at }
export const SAFETY_MS = 1000;
let raf = 0;
let beat = 0;

const hidden = () => typeof document !== 'undefined' && document.hidden;

function run(t) {
  raf = 0;
  if (hidden()) return;
  jobs.forEach(j => {
    const el = j.box && j.box.current;
    if (!el) return;
    const v = ver.get(el) || 0;
    if (v === j.seen && t - j.at < SAFETY_MS) return;
    j.seen = v; j.at = t;
    try { j.fn(t); } catch { /* a chart torn down mid-frame */ }
  });
}

function wake() {
  if (raf || typeof requestAnimationFrame !== 'function') return;
  raf = requestAnimationFrame(run);
}

function heartbeat(on) {
  if (on && !beat && typeof setInterval === 'function') beat = setInterval(wake, SAFETY_MS);
  if (!on && beat) { clearInterval(beat); beat = 0; }
}

/** The chart changed (tick · data · range · size): its overlays redraw on the next frame. */
export function bumpChart(el) {
  if (!el) return;
  ver.set(el, (ver.get(el) || 0) + 1);
  wake();
}

/** Run `fn(t)` on the shared frame whenever the chart in `box` (a ref) changed, else once a second. → stop(). */
export function addChartJob(box, fn) {
  const j = { box, fn, seen: -1, at: 0 };
  jobs.add(j);
  heartbeat(true);
  wake();
  return () => { jobs.delete(j); if (!jobs.size) heartbeat(false); };
}

export const chartJobCount = () => jobs.size;

if (typeof document !== 'undefined') document.addEventListener('visibilitychange', () => { if (!document.hidden) wake(); });
