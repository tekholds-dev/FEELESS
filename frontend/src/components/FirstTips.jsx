import React, { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import '../styles/firstTips.css';
import { Ic3 } from '../lib/icon3d';

// 💡 FIRST-TIME TIPS (owner 2026-10-30: "small, hover over spot, first time only, a skip option"). A pulsing spot sits on each control the
// first time you see a page; hover / focus it for one line on what it does, "Got it" retires that spot, "Skip all" retires the page.
// Remembered on this device (`feeless:tips:<id>`). tips = [[css selector, title, one line]]. Spots never cover a control (corner, 18 px).
const KEY = id => `feeless:tips:${id}`;
const ACCENT = { familia: 'gold', 'fee-landing': 'violet', 'agent-desk': 'violet' };   // each page's own palette (Familia noir gold, FeeCat violet night)
const readSeen = id => { try { const v = JSON.parse(localStorage.getItem(KEY(id)) || '[]'); return v === 'skip' ? 'skip' : Array.isArray(v) ? v : []; } catch { return 'skip'; } };
const save = (id, v) => { try { localStorage.setItem(KEY(id), JSON.stringify(v)); } catch { /* private window: this visit only */ } };

export function FirstTips({ id, tips }) {
  const [seen, setSeen] = useState(() => readSeen(id)); const [spots, setSpots] = useState([]); const [open, setOpen] = useState(null);
  const left = seen === 'skip' ? [] : tips.map((t, i) => [i, ...t]).filter(([i]) => !seen.includes(i));
  const place = useCallback(() => {
    setSpots(left.map(([i, sel]) => { const el = document.querySelector(sel); const r = el?.getBoundingClientRect();
      if (!r || !r.width || r.bottom <= 0 || r.top >= window.innerHeight) return null;
      const hit = document.elementFromPoint?.(r.left + r.width / 2, r.top + Math.min(r.height / 2, 12));   // scrolled out of its box / covered → no spot
      return !hit || el.contains(hit) || hit.closest?.('.ft') ? { i, x: Math.round(r.right - 9), y: Math.round(r.top - 9) } : null; }).filter(Boolean));
  }, [left.map(x => x[0]).join(',')]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!left.length) return undefined; let raf = 0; const go = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(place); };
    go(); const t = setInterval(go, 1200); window.addEventListener('scroll', go, { passive: true, capture: true }); window.addEventListener('resize', go);
    return () => { cancelAnimationFrame(raf); clearInterval(t); window.removeEventListener('scroll', go, { capture: true }); window.removeEventListener('resize', go); }; }, [place, left.length]);
  if (!left.length || typeof document === 'undefined') return null;
  const done = i => { const next = [...(seen === 'skip' ? [] : seen), i]; setSeen(next); save(id, next); setOpen(null); };
  const next = i => { const n = spots.find(s => s.i > i) || spots.find(s => s.i !== i); done(i); if (n) setOpen(n.i); };
  const skip = () => { setSeen('skip'); save(id, 'skip'); };
  const total = tips.length; const read = total - left.length;
  return createPortal(<div className={`ft is-${ACCENT[id] || 'green'}`} data-testid={`tips-${id}`}>
    {spots.map(({ i, x, y }) => { const [, , title, text] = left.find(t => t[0] === i) || []; const on = open === i; const more = spots.some(s => s.i !== i);
      return <span key={i} className={`ft-spot${on ? ' is-open' : ''}`} style={{ left: x, top: y }} onMouseEnter={() => setOpen(i)} onMouseLeave={() => setOpen(o => (o === i ? null : o))}>
        <button type="button" className="ft-dot" aria-label={`Tip: ${title}`} aria-expanded={on} onFocus={() => setOpen(i)} onClick={() => setOpen(o => (o === i ? null : i))} data-testid={`tip-${id}-${i}`}><i aria-hidden="true" /></button>
        {on ? <span className="ft-card" role="tooltip"><em>TIP {i + 1} OF {total}</em><i className="ft-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(i + 1) / total})` }} /></i>
          <b>{title}</b><small>{text}</small><span>{more ? <button type="button" className="m-btn m-go" onClick={() => next(i)} data-testid={`tip-next-${id}-${i}`}>Next tip →</button> : null}
          <button type="button" className={`m-btn${more ? '' : ' m-go'}`} onClick={() => done(i)} data-testid={`tip-ok-${id}-${i}`}>Got it</button>
          <button type="button" className="m-btn ft-skipall" onClick={skip}>Skip all</button></span></span> : null}</span>; })}
    <button type="button" className="ft-skip" onClick={skip} data-tip="Hide every first-time tip on this page" data-testid={`tips-skip-${id}`}><i className="ft-ring" style={{ '--p': read / total }} aria-hidden="true" /><Ic3 e="💡" /> {left.length} tip{left.length > 1 ? 's' : ''} · skip</button>
  </div>, document.body);
}
