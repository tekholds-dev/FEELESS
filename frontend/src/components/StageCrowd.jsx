import React, { useEffect, useRef, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { pickPeople, tagTop, spreadTags, DEMO_PEOPLE } from '../lib/crowdMath';

// 🧍 The ringside crowd under one fight (lib/miniCrowd.js): small real rigged avatars that walk the foot of the ring, gather under the
// leading card and cheer. Each walker can carry a REAL person: the last Fuse card they bought above their name, their earned
// FEELESS badges beside it (GET /fuses/crowd — holders and backers only, nobody invented; no one real → anonymous fans, no tags).
// Loads lazily, draws only while on screen and the tab is visible, skipped in fx-lite / reduced motion; no avatar files → renders nothing.
const N = 3;
const demo = () => { try { return new URLSearchParams(window.location.search).get('crowdDemo') === '1'; } catch { return false; } };

export default function StageCrowd({ lead = '', seed = 1, count = N }) {
  const ref = useRef(null); const crowd = useRef(null); const tags = useRef([]); const [off, setOff] = useState(false); const [people, setPeople] = useState([]);
  useEffect(() => {
    let alive = true;
    if (demo()) { setPeople(DEMO_PEOPLE); return undefined; }
    sharedJson('/api/reputation/fuses/crowd', { maxAge: 60000 }).then(d => alive && setPeople(d?.people || [])).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    const cv = ref.current; if (!cv) return undefined;
    // no WebGL / matchMedia (tests, very old browsers), fx-lite or reduced motion → no crowd, and three.js is never even loaded
    if (typeof window.matchMedia !== 'function' || !window.WebGLRenderingContext || document.body.classList.contains('fx-lite') || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setOff(true); return undefined; }
    let alive = true, io = null;
    const onFrame = pos => { const W = cv.clientWidth, xs = spreadTags(pos.map(p => p.x), W); pos.forEach((p, i) => { const el = tags.current[i]; if (el) el.style.transform = `translate(${xs[i].toFixed(1)}px, ${Math.max(0, p.y - 32).toFixed(1)}px) translateX(-50%)`; }); };
    import('../lib/miniCrowd').then(m => { if (!alive) return; const c = m.createCrowd(cv, { count, seed, onFrame }); crowd.current = c;
      c.start().then(() => { if (alive) { c.setLead(lead); cv.dataset.ready = '1'; } }).catch(() => alive && setOff(true));
      if ('IntersectionObserver' in window) { io = new IntersectionObserver(([e]) => c.setActive(!!e?.isIntersecting), { threshold: 0.05 }); io.observe(cv); } }).catch(() => alive && setOff(true));
    return () => { alive = false; io && io.disconnect(); crowd.current && crowd.current.dispose(); crowd.current = null; };
  }, [seed, count]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { crowd.current && crowd.current.setLead(lead); }, [lead]);
  if (off) return null;
  const slots = pickPeople(people, seed - 1, count);
  return <div className="sbt-crowd" data-testid="stage-crowd">
    <canvas ref={ref} aria-hidden="true" />
    {slots.map((p, i) => p && <div key={p.address} className="sbt-pt" ref={el => { tags.current[i] = el; }} data-testid={`crowd-tag-${i}`}>
      {tagTop(p) ? <small className="sbt-pt-top">{tagTop(p)}</small> : null}
      <span className="sbt-pt-name">{(p.badges || []).slice(0, 3).map(b => (b.art ? <img key={b.id} className="sbt-pt-badge" src={`${b.art}.jpg`} alt={b.label || ''} title={b.label || ''} loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} /> : b.icon ? <em key={b.id} className="sbt-pt-ico" title={b.label || ''}>{b.icon}</em> : null))}
        <b>{p.name}</b>{p.demo ? <u className="sbt-pt-demo">demo</u> : null}</span>
    </div>)}
  </div>;
}
