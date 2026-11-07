import { useEffect, useRef, useState } from 'react';

// A number that counts up to its value when it changes. Stills under fx-lite and reduced motion.
export function useCountUp(value, ms = 700) {
  const [shown, setShown] = useState(value || 0);
  useEffect(() => {
    const from = shown; const to = Number(value || 0); if (from === to) return undefined;
    if (document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setShown(to); return undefined; }
    const t0 = performance.now(); let raf = 0;
    const tick = now => { const p = Math.min(1, (now - t0) / ms); setShown(Math.round(from + (to - from) * (1 - (1 - p) ** 3))); if (p < 1) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps
  return shown;
}
