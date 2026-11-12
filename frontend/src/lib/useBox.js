import { useEffect } from 'react';

// 📐 An element's own width, read by a ResizeObserver instead of a CSS container query (2026-11-11: three @container boxes on
// HQ › Sicario's made every full style pass take 13–38 s in Chrome — measured 26 ms with them gone). `data-narrow` is set when the
// box is at most `narrowPx` wide (React never owns that attribute, so a className change cannot wipe it); `vars` also writes
// --box-w / --box-h in px for sizes that used cqw / cqh.
export function useBox(ref, narrowPx = 560, vars = false) {
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      if (width > 0 && width <= narrowPx) el.setAttribute('data-narrow', ''); else el.removeAttribute('data-narrow');
      if (vars) { el.style.setProperty('--box-w', `${Math.round(width)}px`); el.style.setProperty('--box-h', `${Math.round(height)}px`); }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, narrowPx, vars]);
}
