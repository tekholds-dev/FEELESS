import React, { useEffect, useRef, useState } from 'react';

// Wraps a formatted value and flashes green/red for a beat whenever the underlying
// number actually changes on a poll — real data, just made visibly alive instead of
// silently swapping text. `raw` is the numeric value that drives the flash direction.
export const FlashValue = ({ raw, children, className = '' }) => {
  const prev = useRef(raw);
  const [flash, setFlash] = useState(null);
  useEffect(() => {
    if (raw == null || prev.current == null || Number.isNaN(Number(raw)) || Number.isNaN(Number(prev.current))) {
      prev.current = raw;
      return;
    }
    if (Number(raw) !== Number(prev.current)) {
      setFlash(Number(raw) > Number(prev.current) ? 'flash-up' : 'flash-down');
      prev.current = raw;
      const t = setTimeout(() => setFlash(null), 700);
      return () => clearTimeout(t);
    }
  }, [raw]);
  return <span className={`${className} flash-value ${flash || ''}`}>{children}</span>;
};
