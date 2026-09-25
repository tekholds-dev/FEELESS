import { useRef } from 'react';

// Lightweight 3D tilt-on-hover for cards. Applies a perspective transform that
// follows the pointer, and resets smoothly on leave. No-ops on touch devices
// and when the user prefers reduced motion.
export function useTilt(maxDeg = 8) {
  const ref = useRef(null);

  const onMouseMove = event => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(pointer: coarse), (prefers-reduced-motion: reduce)').matches) return;
    const rect = el.getBoundingClientRect();
    const px = (event.clientX - rect.left) / rect.width;
    const py = (event.clientY - rect.top) / rect.height;
    const rotateY = (px - 0.5) * maxDeg * 2;
    const rotateX = (0.5 - py) * maxDeg * 2;
    el.style.transform = `perspective(700px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(0)`;
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (el) el.style.transform = 'perspective(700px) rotateX(0deg) rotateY(0deg)';
  };

  return { ref, onMouseMove, onMouseLeave };
}
