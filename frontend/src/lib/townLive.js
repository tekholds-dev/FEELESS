// 🏘 TOWN SIGNS — every town building's live number (backend/town_live.py via GET /api/reputation/familia-town/live): one shared read every
// 45 s for the whole page (the 3D block's signs, the drawn CSS block and the town picker all read it), paused while the tab is hidden.
import { useEffect, useState } from 'react';
import { sharedJson } from './sharedJson';

const EVERY = 45000;
let last = null; let timer = null; const subs = new Set();
const tick = () => {
  if (typeof document !== 'undefined' && document.hidden) { timer = setTimeout(tick, EVERY); return; }
  sharedJson('/api/reputation/familia-town/live', { maxAge: EVERY - 500 }).then(d => { if (d?.signs) { last = d.signs; subs.forEach(f => f(last)); } }).catch(() => {})
    .finally(() => { timer = subs.size ? setTimeout(tick, EVERY) : null; });
};
export function useTownLive(on = true) {
  const [s, setS] = useState(last);
  useEffect(() => {
    if (!on) return undefined;
    subs.add(setS); if (last) setS(last);
    if (!timer) tick();
    return () => { subs.delete(setS); if (!subs.size && timer) { clearTimeout(timer); timer = null; } };
  }, [on]);
  return s;
}
