import { useEffect, useRef, useState } from 'react';

// pure: a number that glides to its new value (the card's week % counts up instead of jumping) — one short rAF tween per change
export function useGlide(v, ms = 650) {
  const [n, setN] = useState(v); const from = useRef(v);
  useEffect(() => { if (v == null || typeof v !== 'number') { setN(v); from.current = v; return undefined; }
    const a = typeof from.current === 'number' ? from.current : 0; if (a === v) { setN(v); return undefined; }
    let raf = 0; const t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / ms); const e = 1 - (1 - k) ** 3; setN(+(a + (v - a) * e).toFixed(1)); if (k < 1) raf = requestAnimationFrame(step); else from.current = v; };
    raf = requestAnimationFrame(step); return () => cancelAnimationFrame(raf); }, [v, ms]);
  return n;
}
