import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FamilyCity3D, Vitals, vitalsOf } from './FamilyCity3D';
import { feePlan, outerPlan, spotOf, PLACES, usd } from '../lib/cityPlan';
import { sharedJson } from '../lib/sharedJson';
import '../styles/feeCity3d.css';

// 🌃 FEE CITY IN REAL 3D (owner, 2026-10-22: "way better design and animations … find free model sites and use the best"): the capital + its
// three market islands (MARKET ROW · VAULT DISTRICT · NEW MONEY) and the four outer cities, drawn by three.js with Kenney's CC0 city kits —
// lit windows, cars that hold at red lights, a roof light per market pulsing at its volume, places you walk into (the old lens tabs).
// Tap anything → the camera flies there + its vitals stand on the stage. No WebGL (or a test) → the CSS city, same props, same game.
export const webglOk = () => {
  if (typeof window === 'undefined' || /jsdom/i.test(window.navigator?.userAgent || '')) return false;
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
};
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
const still = () => typeof window !== 'undefined' && (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('reduced-motion-setting'));

// 🏦 the live Solana markets + today's top coins (one shared read a minute, every viewer)
export function useMarkets() {
  const [mk, setMk] = useState(null);
  useEffect(() => { let on = true; const go = () => sharedJson('/api/reputation/familia-markets', { maxAge: 55000 }).then(d => on && d && setMk(d)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, []);
  return mk;
}

// pure: a market's / place's vitals for the stage panel (WHAT · LIVE)
export function marketVitals(m, plan) {
  if (!m) return null;
  if (m.place) { const p = (plan?.places || []).find(x => x.key === m.place) || PLACES.find(x => x.key === m.place);
    return p ? { title: p.name, tone: 'lm', groups: [['PLACE', [['WHAT', p.sub], ['OPEN', 'tap again or use the panel']]]] } : null; }
  const x = (plan?.markets || []).find(k => k.key === m.mk); if (!x) return null; const mm = x.m || {};
  const live = x.kind === 'coin' ? [['MARKET CAP', usd(x.tvl)], ...(x.move != null ? [['24H', `${x.move >= 0 ? '+' : ''}${Number(x.move).toFixed(1)}%`]] : []), ...(mm.vol ? [['24H VOL', usd(mm.vol)]] : [])]
    : [['TVL', usd(x.tvl), Math.min(1, Math.log10(1 + (x.tvl || 0)) / 10)], ...(mm.pool ? [['BUSIEST POOL', `${mm.pool.base}/${mm.pool.quote}${mm.pool.labels?.length ? ` · ${mm.pool.labels[0]}` : ''}`], ['POOL LIQ', usd(mm.pool.liq)], ['POOL 24H VOL', usd(mm.pool.vol)]] : [])];
  return { title: x.name, tone: 'mk', groups: [['WHAT', [['KIND', String(x.kind).toUpperCase()], ...(mm.offer ? [['OFFERS', mm.offer]] : [])]], ['LIVE', live], ['ACTIVITY', [['ROOF LIGHT', `${x.hz} Hz pulse = its volume`]]]] };
}

// 📍 every place in Fee City (the old lens tabs) as one signpost menu — fly there and walk in. Lives in the stage controls of BOTH cities.
export function PlacesMenu({ onGo }) {
  const [open, setOpen] = useState(false); const ref = useRef(null);
  useEffect(() => { if (!open) return undefined; const out = e => { if (!ref.current?.contains(e.target)) setOpen(false); }; const esc = e => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', out); document.addEventListener('keydown', esc); return () => { document.removeEventListener('pointerdown', out); document.removeEventListener('keydown', esc); }; }, [open]);
  return <span className="fc3-places" ref={ref}><button type="button" className={open ? 'active' : ''} onClick={() => setOpen(o => !o)} aria-expanded={open} data-tip="Every place in Fee City — fly there and walk in" data-testid="city-places">📍 Places</button>
    {open ? <ul className="fc3-menu" role="menu">{PLACES.map((p, i) => <li key={p.key} style={{ '--i': i, '--pc': p.color }}><button type="button" role="menuitem" onClick={() => { setOpen(false); onGo(p); }} data-testid={`place-${p.key}`}>
      <b>{p.name}</b><small>{p.sub}</small></button></li>)}</ul> : null}</span>;
}

export function FeeCity3D({ v, sel, setSel, city, setCity, tour, overlay, onPlace, markets }) {
  const [gl] = useState(webglOk);
  const host = useRef(null); const eng = useRef(null); const [ready, setReady] = useState(false); const [tip, setTip] = useState(null); const [spin, setSpin] = useState(false);
  const isFee = city === 'fee' || !v.cities?.length;
  const plan = useMemo(() => (isFee ? feePlan(v, markets) : outerPlan(v, city)), [v, markets, city, isFee]);
  const live = useMemo(() => ({ raided: new Set((v.raids || []).filter(r => r.status === 'live').map(r => r.b?.id).filter(Boolean)),
    fight: (v.ffuse?.fights || []).find(f => f.status === 'live') || null, marks: Object.fromEntries((v.landmarks || []).map(m => [m.key, m.live || {}])) }), [v]);
  const pickRef = useRef(null);
  pickRef.current = pk => {
    if (pk?.gate) { setSel(null); setCity(pk.gate); return; }
    if (pk?.place) { const p = PLACES.find(x => x.key === pk.place); setSel(pk); if (p) onPlace?.(p.lens); return; }
    setSel(pk);
  };
  useEffect(() => {   // mount the engine once (WebGL only)
    if (!gl || !host.current) return undefined; let alive = true;
    import('../lib/cityEngine').then(async m => { if (!alive) return; await m.preload();
      if (!alive || !host.current) return;
      eng.current = m.createCity(host.current, { onPick: pk => pickRef.current(pk), onHover: setTip, lite: lite(), still: still() }); setReady(true); });
    return () => { alive = false; eng.current?.dispose(); eng.current = null; };
  }, [gl]);
  useEffect(() => { if (!ready || !eng.current || !plan) return; eng.current.setPlan(plan, live).then(first => { if (first && sel) eng.current?.flyTo(spotOf(plan, sel)); }); }, [ready, plan, live]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!ready || !eng.current || !plan) return; const s = spotOf(plan, sel); eng.current.flyTo(s, sel?.mk || sel?.place ? 19 : sel?.lm ? 17 : 15); }, [ready, sel?.id, sel?.lm, sel?.mk, sel?.place, plan?.kind, plan?.key]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { eng.current?.spin(spin); }, [spin, ready]);

  if (!gl) return <FamilyCity3D v={v} sel={sel} setSel={setSel} city={city} setCity={setCity} tour={tour} overlay={overlay} />;
  const vit = sel?.place ? null : sel?.mk ? marketVitals(sel, plan) : vitalsOf(sel, v);   // a place's own room pops out instead
  return <div className={`fc3 ${ready ? 'is-ready' : ''}`} data-testid="world-map">
    <div className="fc3-host" ref={host} aria-label={isFee ? 'Fee City in 3D — drag to turn, scroll to zoom, tap a building' : `${plan?.name || 'The city'} in 3D`} role="img" />
    {!ready ? <div className="fc3-load" aria-live="polite"><i className="fc3-sky" /><span className="fc3-skyline">{Array.from({ length: 14 }, (_, i) => <b key={i} style={{ '--i': i, '--h': `${30 + ((i * 37) % 60)}px` }} />)}</span><small>drawing the city…</small></div> : null}
    {tip ? <span className="fc3-tip" style={{ transform: `translate(${tip.x + 14}px, ${tip.y + 12}px)` }}>{tip.label}</span> : null}
    <Vitals vit={vit} onClose={() => setSel(sel)} />
    {overlay}
    <div className="fcy-ctl fc3-ctl">
      <button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(s => !s)} aria-pressed={spin} data-tip="Slowly turn the whole city" data-testid="city-spin">{spin ? '⏸ Stop' : '⟲ 360°'}</button>
      <button type="button" onClick={() => eng.current?.zoom(1.25)} data-tip="Zoom in" aria-label="Zoom in">＋</button>
      <button type="button" onClick={() => eng.current?.zoom(0.8)} data-tip="Zoom out" aria-label="Zoom out">－</button>
      <button type="button" onClick={() => { setSel(null); eng.current?.frameAll(); }} data-tip="See the whole city" aria-label="Whole city" data-testid="city-home">⌂</button>
      {tour.ctl}
      <small>drag to turn · right-drag to pan · scroll to zoom · tap a building</small></div>
    <ul className="fcy-key fc3-key"><li className="t-mine">yours</li><li className="t-family">families</li><li className="t-cpu">CPU towns</li><li className="t-cartel">cartels</li>{isFee ? <><li className="t-mk">markets</li><li className="t-place">places</li></> : null}</ul>
  </div>;
}
