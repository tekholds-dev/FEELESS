import React, { useEffect, useMemo, useRef, useState } from 'react';
import '../styles/familyMap.css';

// 🗺 THE CITY (owner, 2026-10-21: "a simple 3D map like the Godfather game on PSP"): nine districts, each held by a family in the order of
// the weekly board (verified trades) — the block's height is how strong that family is this week, its colour is the family's badge, a beacon
// marks YOUR turf and ⚔ marks districts whose families are at war right now. CSS 3D (perspective + preserve-3d), transform / opacity only.
export const DISTRICTS = [
  ['casino', '🎰 Casino Row'], ['docks', '⚓ The Docks'], ['italy', '🍝 Little Italy'],
  ['pump', '💊 Pump Street'], ['trench', '🪖 The Trenches'], ['bonk', '🐕 Bonk Bay'],
  ['heights', '🏙 Raydium Heights'], ['hills', '🪐 Jupiter Hills'], ['market', '☄ Meteora Market'],
];
const PALETTE = ['#d4af37', '#b3122e', '#5fd4ff', '#b79bff', '#45e486', '#ff9f45', '#ff4d6d', '#9fd8ff', '#f1d27a'];

export function strength(r) {
  const pct = Number(r?.pct) || 0;
  return Math.max(0, (r?.members || 0) * 4 + (r?.active || 0) * 6 + Math.max(-30, Math.min(60, pct)) + ((r?.warW || 0) - (r?.warL || 0)) * 5 + Math.min(80, (r?.city || 0) / 5));
}

// pure: who holds which district. Board order = the city's order (ranked families first); the rest of the map is unclaimed.
export function territories(rows, mineId, wars) {
  const fams = (rows || []).slice(0, DISTRICTS.length);
  const top = Math.max(1, ...fams.map(strength));
  const atWar = new Set();
  for (const w of wars || []) if (w.state === 'live') { atWar.add(w.a?.id); atWar.add(w.b?.id); }
  return DISTRICTS.map(([key, name], i) => {
    const r = fams[i];
    if (!r) return { key, name, owner: null, h: 0.08, color: '#2a2433' };
    return { key, name, owner: r, h: 0.25 + 0.75 * (strength(r) / top), color: r.badge?.c1 || PALETTE[i % PALETTE.length], mine: r.id === mineId, war: atWar.has(r.id) };
  });
}

export function FamilyMap({ rows, mineId, wars, onOpen, onEnter }) {
  const t = useMemo(() => territories(rows, mineId, wars), [rows, mineId, wars]);
  const [hover, setHover] = useState(null);
  const sel = hover != null ? t[hover] : t.find(d => d.mine) || t[0];
  const stage = useRef(null); const rz = useRef(-38); const drag = useRef(null); const [orbit, setOrbit] = useState(true);
  const setRz = z => { rz.current = z; stage.current?.style.setProperty('--rz', `${z}deg`); };
  useEffect(() => { if (!orbit) return undefined; let raf; let last = performance.now();
    const go = tm => { if (!document.hidden) setRz(rz.current + (tm - last) * 0.006); last = tm; raf = requestAnimationFrame(go); }; raf = requestAnimationFrame(go); return () => cancelAnimationFrame(raf); }, [orbit]);   // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <section className="fmap" data-testid="family-map">
      <header><span className="fmap-h">🗺 THE CITY</span><small>nine districts · held in the order of this week's board · height = strength · ⚔ = at war now</small></header>
      <div className="fmap-wrap">
        <div className="fmap-stage" ref={stage} style={{ '--rz': `${rz.current}deg` }} onPointerDown={e => { drag.current = { x: e.clientX, z: rz.current }; setOrbit(false); }}
          onPointerMove={e => { if (drag.current) setRz(drag.current.z + (e.clientX - drag.current.x) * 0.5); }} onPointerUp={() => { drag.current = null; }} onPointerLeave={() => { drag.current = null; }}>
          <button type="button" className={`fmap-orbit ${orbit ? 'active' : ''}`} onClick={() => setOrbit(o => !o)} aria-pressed={orbit} data-testid="fmap-orbit">{orbit ? '⏸ Hold' : '🔄 360°'}</button>
          <div className="fmap-sweep" />
          <div className="fmap-plane">
            {t.map((d, i) => (
              <div key={d.key} className={`fmap-tile ${d.owner ? 'is-held' : 'is-free'} ${d.mine ? 'is-mine' : ''} ${d.war ? 'is-war' : ''} ${hover === i ? 'is-hover' : ''}`}
                style={{ '--c': d.color, '--h': d.h, '--i': i }} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
                <div className="fmap-block"><i className="fmap-top" /><i className="fmap-s1" /><i className="fmap-s2" /></div>
                {d.mine ? <i className="fmap-beacon" /> : null}
                {d.war ? <i className="fmap-war">⚔</i> : null}
              </div>
            ))}
          </div>
        </div>
        <ol className="fmap-legend">
          {t.map((d, i) => (
            <li key={d.key} className={`${d.mine ? 'is-mine' : ''} ${hover === i ? 'is-hover' : ''}`} style={{ '--c': d.color }} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <button type="button" disabled={!d.owner} onClick={() => d.owner && (onEnter ? onEnter(d.mine ? null : d.owner.id) : onOpen?.(d.owner))} data-testid={`fmap-${d.key}`}>
                <i aria-hidden /><b>{d.name}</b><span>{d.owner ? `[${d.owner.tag}] ${d.owner.name}${d.owner.city ? ` · 🏙 ${d.owner.city}` : ''}` : 'unclaimed'}</span>{d.war ? <em>⚔</em> : null}
                {d.owner ? <em className="fmap-go">{d.mine ? '🏙 Enter' : '👁 Visit'}</em> : null}
              </button>
            </li>
          ))}
        </ol>
      </div>
      {sel ? <p className="fmap-sel">{sel.owner ? <><b>{sel.name}</b> — held by <b>[{sel.owner.tag}] {sel.owner.name}</b> · {sel.owner.members} members · {sel.owner.pct == null ? 'unranked' : `${sel.owner.pct >= 0 ? '+' : ''}${sel.owner.pct}% this week`}{sel.war ? ' · at war right now' : ''}</>
        : <><b>{sel.name}</b> is unclaimed — the next family on the board takes it.</>}</p> : null}
    </section>
  );
}
