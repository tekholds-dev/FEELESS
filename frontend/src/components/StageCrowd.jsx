import React, { useEffect, useRef, useState } from 'react';

// 🧍 The ringside crowd under one fight (lib/miniCrowd.js): small real rigged avatars that walk the foot of the ring, gather under the
// leading card and cheer. Loads lazily, draws only while on screen and the tab is visible, and is skipped in fx-lite / reduced motion.
// If the avatar files are not there (not deployed) it renders nothing — the stage never shows a broken box.
export default function StageCrowd({ lead = '', seed = 1, count = 3 }) {
  const ref = useRef(null); const crowd = useRef(null); const [off, setOff] = useState(false);
  useEffect(() => {
    const cv = ref.current; if (!cv) return undefined;
    if (document.body.classList.contains('fx-lite') || matchMedia('(prefers-reduced-motion: reduce)').matches) { setOff(true); return undefined; }
    let alive = true, io = null;
    import('../lib/miniCrowd').then(m => { if (!alive) return; const c = m.createCrowd(cv, { count, seed }); crowd.current = c;
      c.start().then(() => { if (alive) { c.setLead(lead); cv.dataset.ready = '1'; } }).catch(() => alive && setOff(true));
      if ('IntersectionObserver' in window) { io = new IntersectionObserver(([e]) => c.setActive(!!e?.isIntersecting), { threshold: 0.05 }); io.observe(cv); } }).catch(() => alive && setOff(true));
    return () => { alive = false; io && io.disconnect(); crowd.current && crowd.current.dispose(); crowd.current = null; };
  }, [seed, count]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { crowd.current && crowd.current.setLead(lead); }, [lead]);
  if (off) return null;
  return <div className="sbt-crowd" aria-hidden="true" data-testid="stage-crowd"><canvas ref={ref} /></div>;
}
