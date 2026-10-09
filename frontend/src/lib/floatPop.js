import { useEffect, useLayoutEffect, useRef, useState } from 'react';

// 🎈 A small popover drawn on <body> at its button (portal + fixed position): rows that animate (transform) trap an absolutely positioned
// popover under the next row — the TP / SL panel did. Opens below the button, flips up when there is no room, stays inside the window.
// Outside click, Esc or a scroll closes it.
export function useFloatPop(width = 200) {
  const ref = useRef(null); const popRef = useRef(null);
  const [open, setOpen] = useState(false); const [pos, setPos] = useState(null);
  const place = () => { const r = ref.current?.getBoundingClientRect(); if (!r) return;
    const h = popRef.current?.offsetHeight || 220; const left = Math.max(8, Math.min(window.innerWidth - width - 8, r.right - width));
    const below = r.bottom + 6 + h < window.innerHeight; setPos({ left, top: below ? r.bottom + 6 : Math.max(8, r.top - 6 - h), width }); };
  useLayoutEffect(() => { if (open) place(); }, [open]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open) return undefined;
    const out = e => { if (!ref.current?.contains(e.target) && !popRef.current?.contains(e.target)) setOpen(false); };
    const key = e => e.key === 'Escape' && setOpen(false); const close = () => setOpen(false);
    document.addEventListener('mousedown', out); window.addEventListener('keydown', key); window.addEventListener('scroll', close, true); window.addEventListener('resize', close);
    return () => { document.removeEventListener('mousedown', out); window.removeEventListener('keydown', key); window.removeEventListener('scroll', close, true); window.removeEventListener('resize', close); };
  }, [open]);
  return { ref, popRef, open, setOpen, style: pos ? { position: 'fixed', left: pos.left, top: pos.top, width: pos.width, zIndex: 1300 } : { position: 'fixed', visibility: 'hidden' } };
}
