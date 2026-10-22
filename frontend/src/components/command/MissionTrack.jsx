import React, { useMemo, useState } from 'react';
import '../../styles/missionTrack.css';

// 🛤 THE MISSION TRACK (owner P2: "roadmap / whitepaper as a real 3D view — text in a dropdown"): the roadmap as a road running into the
// distance (CSS 3D, transform / opacity only). Every milestone is a pylon standing on it, lit by its status (LIVE green · TESTING amber ·
// BUILDING violet · PLANNED dark), a rocket marks "you are here" between the last LIVE and the first one still in test, the lane dashes run.
// Tap a pylon → its text drops down under the track. The status filter dims the others. Targets are never guarantees.
export const STATE_TONE = { LIVE: 'live', TESTING: 'test', BUILDING: 'build', PLANNED: 'plan' };
// pure: where the rocket sits — just after the last LIVE milestone
export const hereIndex = missions => { let k = -1; (missions || []).forEach((m, i) => { if (m[2] === 'LIVE') k = i; }); return k; };

export function MissionTrack({ missions, filter = 'ALL' }) {
  const [open, setOpen] = useState(null);
  const here = useMemo(() => hereIndex(missions), [missions]);
  const n = (missions || []).length;
  const pick = open != null ? missions.find(m => m[0] === open) : null;
  return <section className="mt" data-testid="mission-track">
    <div className="mt-stage" aria-label="The roadmap as a track — tap a milestone">
      <div className="mt-sky" aria-hidden="true">{Array.from({ length: 22 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</div>
      <div className="mt-world">
        <div className="mt-road" aria-hidden="true"><span className="mt-lane" /><span className="mt-edge l" /><span className="mt-edge r" /></div>
        <div className="mt-pylons">{(missions || []).map(([id, title, state], i) => {
          const dim = filter !== 'ALL' && state !== filter; const z = i / Math.max(1, n - 1);
          return <button key={id} type="button" className={`mt-pylon t-${STATE_TONE[state] || 'plan'} ${i % 2 ? 'is-r' : 'is-l'} ${dim ? 'is-dim' : ''} ${open === id ? 'is-open' : ''}`}
            style={{ '--z': z, '--i': i }} onClick={() => setOpen(o => (o === id ? null : id))} aria-expanded={open === id} data-testid={`mission-${id}`}
            data-tip={`${id} · ${title} — ${state}`}>
            <span className="mt-sign"><b>{id}</b><em>{state}</em><small>{title}</small></span><i className="mt-post" /></button>; })}
          {here >= 0 ? <span className="mt-rocket" style={{ '--z': (here + 0.5) / Math.max(1, n - 1) }} aria-label="You are here"><b>🚀</b><small>YOU ARE HERE</small></span> : null}</div>
      </div>
    </div>
    {pick ? <div className={`mt-drop t-${STATE_TONE[pick[2]] || 'plan'}`} data-testid="mission-drop"><span className="mt-tag">{pick[0]} · {pick[2]}</span><h3>{pick[1]}</h3><p>{pick[3]}</p>
      <button type="button" className="m-btn" onClick={() => setOpen(null)} aria-label="Close">✕</button></div>
      : <p className="mt-hint">👆 Tap a milestone on the track for its details.</p>}
  </section>;
}
