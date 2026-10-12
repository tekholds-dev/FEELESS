import { useEffect, useRef, useState } from 'react';
import { tweenClose } from './tween';

// 🎞 DISPLAY-ONLY EASING for a live number (a seat's MC, its % since entry, the card's P&L): when a REAL new value lands (the shared
// live-price poller, a delta), the number on screen glides to it at ≤ 30 frames a second over ~450ms and STOPS exactly on it. It never
// runs ahead of the data, never overshoots and never feeds a calculation — it is what the eye sees between two real reads.
// Off (the value jumps) in fx-lite, under prefers-reduced-motion, while the tab is hidden, and in tests.
export const FRAME_MS = 1000 / 30;
export const EASE_MS = 450;
// the value to draw `elapsed` ms after the real value moved from `from` to `to` (ease-out cubic; ≥ dur = exactly `to`)
export const easedAt = (from, to, elapsed, dur = EASE_MS) => (from == null || to == null || !Number.isFinite(from) || !Number.isFinite(to) ? to : tweenClose(from, to, elapsed / dur));
const still = () => typeof window === 'undefined' || typeof requestAnimationFrame !== 'function' || process.env.NODE_ENV === 'test'
  || (typeof document !== 'undefined' && (document.hidden || document.body.classList.contains('fx-lite')))
  || !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

export function useEasedNumber(target, dur = EASE_MS) {
  const to = target == null || !Number.isFinite(Number(target)) ? null : Number(target);
  const [shown, setShown] = useState(to);
  const cur = useRef(to);
  useEffect(() => {
    const from = cur.current;
    if (to == null || from == null || from === to || still()) { cur.current = to; setShown(to); return undefined; }
    let raf = 0; let last = 0; const t0 = performance.now();
    const step = now => {
      const el = now - t0;
      if (el >= dur) { cur.current = to; setShown(to); return; }
      if (now - last >= FRAME_MS) { last = now; const v = easedAt(from, to, el, dur); cur.current = v; setShown(v); }   // ≤ 30 paints a second
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);   // a newer real value glides on from what is on screen now
  }, [to, dur]);
  return shown;
}
