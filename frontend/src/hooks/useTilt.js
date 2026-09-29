import { useRef } from 'react';

// Lightweight 3D tilt-on-hover for cards. Measures the card once per hover and batches
// transform writes into animation frames, so a grid of cards never forces layout per mouse move.
// No-ops on touch devices and when the user prefers reduced motion.
export function useTilt(maxDeg = 8) {
  const ref = useRef(null);
  const rect = useRef(null);
  const frame = useRef(0);
  const point = useRef(null);

  const onMouseMove = event => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(pointer: coarse), (prefers-reduced-motion: reduce)').matches) return;
    if (!rect.current) rect.current = el.getBoundingClientRect();
    point.current = [event.clientX, event.clientY];
    if (frame.current) return;
    frame.current = requestAnimationFrame(() => {
      frame.current = 0;
      const r = rect.current;
      if (!r || !point.current) return;
      const px = (point.current[0] - r.left) / r.width;
      const py = (point.current[1] - r.top) / r.height;
      el.style.transform = `perspective(700px) rotateX(${(0.5 - py) * maxDeg * 2}deg) rotateY(${(px - 0.5) * maxDeg * 2}deg) translateZ(0)`;
    });
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (frame.current) cancelAnimationFrame(frame.current);
    frame.current = 0; rect.current = null; point.current = null;
    if (el) el.style.transform = 'perspective(700px) rotateX(0deg) rotateY(0deg)';
  };

  return { ref, onMouseMove, onMouseLeave };
}
