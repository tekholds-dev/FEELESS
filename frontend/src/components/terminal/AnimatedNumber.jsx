import React, { useEffect, useRef, useState } from 'react';

const reduced = () => typeof window !== 'undefined' && (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('reduced-motion-setting'));
const ease = t => 1 - Math.pow(1 - t, 3);

// Live number: glides from the previous real reading to the new one (interpolated frames only
// in between — it always settles on the real value), and rolls each changed digit odometer-style.
export function AnimatedNumber({ value, format = v => String(v), duration = 2800, className = '' }) {
  const target = Number(value);
  const valid = Number.isFinite(target);
  const [shown, setShown] = useState(valid ? target : null);
  const [dir, setDir] = useState(null);
  const from = useRef(valid ? target : null);
  const raf = useRef(0);
  const prevText = useRef('');

  useEffect(() => {
    if (!valid) { setShown(null); return undefined; }
    const start = from.current;
    if (start == null || start === target || reduced()) { from.current = target; setShown(target); return undefined; }
    setDir(target > start ? 'up' : 'down');
    const t0 = performance.now();
    let lastPaint = 0;
    cancelAnimationFrame(raf.current);
    const step = now => {
      const p = Math.min(1, (now - t0) / duration);
      const v = start + (target - start) * ease(p);
      from.current = v;
      if (p >= 1 || now - lastPaint > 80) { lastPaint = now; setShown(p >= 1 ? target : v); }
      if (p < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [target, valid, duration]);

  if (shown == null) return <span className={className}>—</span>;
  const text = String(format(shown));
  const before = prevText.current;
  prevText.current = text;
  return <span className={`anim-num ${dir ? `anim-${dir}` : ''} ${className}`} aria-label={String(format(target))}>
    {text.split('').map((ch, i) => {
      const changed = before && before.length === text.length && before[i] !== ch && /\d/.test(ch);
      return <span key={`${i}-${changed ? ch : 'k'}`} className={changed ? `digit roll-${dir || 'up'}` : 'digit'} aria-hidden="true">{ch}</span>;
    })}
  </span>;
}
