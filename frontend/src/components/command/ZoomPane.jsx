import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import '../../styles/zoomPane.css';

// 🔍 Scroll to zoom at the cursor, drag to move, double click to go in. Used by every picture a person marks and by the big print. Zooming back to 100% lets the page scroll again.
const MAX = 12;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const ZoomPane = forwardRef(function ZoomPane({ children, className = '', drag = true, testid = 'zoom-pane' }, ref) {
  const box = useRef(null); const inner = useRef(null); const view = useRef({ s: 1, x: 0, y: 0 }); const hold = useRef(null); const moved = useRef(false); const [pct, setPct] = useState(100);
  const paint = useCallback(() => { const { s, x, y } = view.current; if (inner.current) inner.current.style.transform = `translate(${x}px, ${y}px) scale(${s})`; setPct(Math.round(s * 100)); window.dispatchEvent(new Event('zoom-moved')); }, []);
  const place = useCallback((s, x, y) => { const r = box.current.getBoundingClientRect(); const S = clamp(s, 1, MAX); view.current = { s: S, x: clamp(x, r.width * (1 - S), 0), y: clamp(y, r.height * (1 - S), 0) }; paint(); }, [paint]);
  const zoomAt = useCallback((k, cx, cy) => { const { s, x, y } = view.current; const S = clamp(s * k, 1, MAX); const q = S / s; place(S, cx - (cx - x) * q, cy - (cy - y) * q); }, [place]);
  const glide = useCallback(fn => { const el = inner.current; el?.classList.add('is-glide'); fn(); const t0 = performance.now(); const tick = () => { window.dispatchEvent(new Event('zoom-moved')); if (performance.now() - t0 < 380) requestAnimationFrame(tick); else el?.classList.remove('is-glide'); }; requestAnimationFrame(tick); }, []);
  const middle = k => { const r = box.current.getBoundingClientRect(); glide(() => zoomAt(k, r.width / 2, r.height / 2)); };
  useImperativeHandle(ref, () => ({
    reset: () => glide(() => place(1, 0, 0)),
    // Brings one spot, given in screen pixels, to the middle at a size you can read.
    focus: (rect, most = 5) => { const r = box.current.getBoundingClientRect(); const { s, x, y } = view.current; const cx = (rect.left + rect.width / 2 - r.left - x) / s; const cy = (rect.top + rect.height / 2 - r.top - y) / s; const S = clamp(Math.min(r.width / (Math.max(rect.width / s, 1) * 1.7), r.height / (Math.max(rect.height / s, 1) * 1.7)), 1.5, most); glide(() => place(S, r.width / 2 - cx * S, r.height / 2 - cy * S)); },
  }), [glide, place]);
  useEffect(() => { const el = box.current; if (!el) return undefined;
    const wheel = e => { if (view.current.s <= 1 && e.deltaY > 0) return; e.preventDefault(); const r = el.getBoundingClientRect(); zoomAt(Math.exp(-e.deltaY * 0.002), e.clientX - r.left, e.clientY - r.top); };
    el.addEventListener('wheel', wheel, { passive: false }); return () => el.removeEventListener('wheel', wheel); }, [zoomAt]);
  const down = e => { moved.current = false; if (!drag || view.current.s <= 1) return; hold.current = { px: e.clientX, py: e.clientY, x: view.current.x, y: view.current.y, id: e.pointerId }; };
  const move = e => { const h = hold.current; if (!h) return; const dx = e.clientX - h.px; const dy = e.clientY - h.py; if (!moved.current && Math.hypot(dx, dy) < 4) return; if (!moved.current) box.current.setPointerCapture?.(h.id); moved.current = true; place(view.current.s, h.x + dx, h.y + dy); };
  const up = () => { hold.current = null; };
  const dbl = e => { if (!drag) return; const r = box.current.getBoundingClientRect(); glide(() => zoomAt(2, e.clientX - r.left, e.clientY - r.top)); };
  return <div ref={box} className={`zmp ${pct > 100 ? 'is-in' : ''}${drag ? '' : ' is-still'} ${className}`} data-testid={testid} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onDoubleClick={dbl} onClickCapture={e => { if (moved.current) { e.stopPropagation(); moved.current = false; } }}>
    <div ref={inner} className="zmp-in" data-testid={`${testid}-in`}>{children}</div>
    <div className="zmp-ctl" onPointerDown={e => e.stopPropagation()} onDoubleClick={e => e.stopPropagation()}><button type="button" onClick={() => middle(0.66)} disabled={pct <= 100} aria-label="Zoom out" data-tip="Zoom out">−</button><button type="button" className="m-num" onClick={() => glide(() => place(1, 0, 0))} aria-label="Back to the whole picture" data-tip="Back to the whole picture" data-testid={`${testid}-pct`}>{pct}%</button><button type="button" onClick={() => middle(1.5)} disabled={pct >= MAX * 100} aria-label="Zoom in" data-tip="Zoom in. Or scroll on it">+</button></div></div>;
});
