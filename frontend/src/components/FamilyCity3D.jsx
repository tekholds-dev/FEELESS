import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Bridge, Car, CAR_COLORS, hash, Plot } from './cityParts';
import { FeeCapital, FEE_W, FEE_H, feeSpot } from './FeeCapital';
import '../styles/familyCity3d.css';
import '../styles/feeCity.css';

// 🌃 THE CITIES IN 3D (owner, 2026-10-21: "the city is dope, but needs different areas to go to … click any plot and it zooms in and shows
// vitals on top of the plot"). One camera stage, one city drawn at a time (less to paint = no lag): FEE CITY, the capital, or one of the four
// outer cities (their boroughs as islands, joined by suspension bridges, a bridge back to Fee City). Tap a plot or a landmark → the camera
// flies to it and its live vitals stand over it. Drag to turn, scroll to zoom. transform / opacity only; still in fx-lite / reduced motion.
export const ISLAND = 300;
export const GAP = 84;
const SEA = 120;
const LOT = (ISLAND - 14 * 5) / 4;          // 57.5 — four lots a row, 14px streets
export const lotPos = i => ({ x: 14 + (i % 4) * (LOT + 14), y: 14 + Math.floor(i / 4) * (LOT + 14) });

// pure: a city's boroughs laid out on their own sea → { pos: { key: {x, y} }, W, H }
export function cityLayout(bors) {
  if (!bors.length) return { pos: {}, W: 2 * SEA + ISLAND, H: 2 * SEA + ISLAND };
  const c0 = Math.min(...bors.map(b => b.col)); const r0 = Math.min(...bors.map(b => b.row));
  const cols = Math.max(...bors.map(b => b.col)) - c0 + 1; const rows = Math.max(...bors.map(b => b.row)) - r0 + 1;
  const pos = Object.fromEntries(bors.map(b => [b.key, { x: SEA + (b.col - c0) * (ISLAND + GAP), y: SEA + (b.row - r0) * (ISLAND + GAP) }]));
  return { pos, W: 2 * SEA + cols * ISLAND + (cols - 1) * GAP, H: 2 * SEA + rows * ISLAND + (rows - 1) * GAP };
}
// pure: the deck between two neighbouring islands
export function bridgeRect(pa, pb) {
  if (pa.y === pb.y) { const l = Math.min(pa.x, pb.x) + ISLAND; return { x: l - 6, y: pa.y + ISLAND / 2 - 13, w: GAP + 12, h: 26, horiz: true }; }
  const t = Math.min(pa.y, pb.y) + ISLAND; return { x: pa.x + ISLAND / 2 - 13, y: t - 6, w: 26, h: GAP + 12, horiz: false };
}

function Island({ b, p, blocks, boom, sel, onPick, reach, hot }) {
  return <div className={`fcy-isl ${boom === b.key ? 'is-boom' : ''} ${reach === false ? 'is-far' : ''} k-${b.key}`} style={{ transform: `translate(${p.x}px, ${p.y}px)` }} data-testid={`borough-${b.key}`}>
    <i className="fcy-lanes" aria-hidden="true" />
    {[0, 1, 2, 3, 4].flatMap(k => [<i key={`l${k}`} className="fcy-lamp" style={{ transform: `translate(${k * (LOT + 14) + 5}px, 3px) translateZ(14px)` }} />,
      <i key={`r${k}`} className="fcy-lamp" style={{ transform: `translate(${k * (LOT + 14) + 5}px, ${ISLAND - 7}px) translateZ(14px)` }} />])}
    {blocks.map(x => <Plot key={x.id} x={x} r={{ ...lotPos(x.i), w: LOT, h: LOT }} sel={sel === x.id} onPick={onPick} raid={hot?.has(x.owner)} />)}
    {['a', 'b', 'c'].map((r, i) => <Car key={r} route={r} i={i + b.col * 3 + b.row} color={CAR_COLORS[(hash(b.key) + i) % CAR_COLORS.length]} />)}
    {[0, 1, 2, 3].map(i => <i key={`p${i}`} className={`fcy-ped w-${i}`} style={{ '--i': i + b.col }} />)}
    <div className="fcy-sign"><b>{b.name}</b><small>×{b.tier}{boom === b.key ? ' · 🔥 BOOM' : ''}</small></div>
  </div>;
}

// pure: the vitals that stand over a picked plot / landmark
// pure: the vitals of a picked plot / landmark, in categories (WHO · STRENGTH · MONEY, a landmark's LIVE numbers, a fight's SCORE + STAKES)
export function vitalsOf(x, v) {
  if (!x || x.place || x.mk || x.gate) return null;
  const n = k => Math.round(Number(k) || 0).toLocaleString('en-US');
  const ff = x.lm === 'arena' && (v.ffuse?.fights || []).find(f => f.status === 'live');
  if (ff) return { title: `⚔ [${ff.a.tag}] vs [${ff.b.tag}]`, tone: 'lm', groups: [['SCORE', [['SPARKS', ff.duel ? `${ff.duel.a} ⚡ ${ff.duel.b}` : '0 ⚡ 0'], ['CLOCK', `${Math.floor(ff.left / 60)}m left`, ff.left / (ff.mins * 60)]]],
    ['STAKES', [['POT', ff.stake === 'mp' ? `${n(2 * ff.mp)} MP` : 'paper'], ['CROWD', `${n(ff.crowd.total)} pts · ${ff.crowd.bidders} bidders`]]]] };
  if (x.lm) { const m = (v.landmarks || []).find(l => l.key === x.lm);
    return { title: m?.name || x.lm, tone: 'lm', groups: [['LIVE', Object.entries(m?.live || {}).filter(([, val]) => typeof val === 'number').map(([k, val]) => [k.toUpperCase(), n(val)])]] }; }
  const bor = (v.boroughs || []).find(b => b.key === x.b); const top = Math.max(1, ...(v.blocks || []).map(b => b.power || 0));
  const rk = (v.ranked || []).find(r => r.id === x.owner); const reach = v.me?.reach?.[x.b];
  const who = [['DISTRICT', bor?.name || x.b], ['STATUS', !x.owner ? 'FOR SALE' : x.home ? 'HOME BLOCK' : x.kind === 'cpu' ? 'CPU TOWN' : x.kind === 'cartel' ? 'CARTEL' : 'TURF']];
  const strength = x.owner ? [['POWER', n(x.power), (x.power || 0) / top], ...(rk ? [['RANK', `${rk.rank.name} ${rk.rank.div} · #${rk.place}`]] : [])] : [];
  if (x.launch?.symbol) who.push(['LAUNCH', `$${x.launch.symbol}`]);
  const money = [['TIER', `×${bor?.tier ?? 1} production`], ...(!x.owner ? [['PRICE', v.me?.prices?.[x.id] != null ? `${n(v.me.prices[x.id])} MP` : 'sign in']] : []),
    ...(x.state ? [['UPKEEP', x.state === 'shut' ? 'SHUT · unfunded' : x.fundH == null ? 'home · never shuts' : `ACTIVE · ${x.fundH}h`, x.fundH == null ? null : Math.min(1, x.fundH / 336)]] : []),
    ...(x.owner && !x.mine && reach != null ? [['REACH', reach ? 'in raid range' : 'out of range']] : [])];
  return { title: x.owner ? `[${x.tag}] ${x.name}` : `PLOT ${x.id.toUpperCase()}`, tone: x.mine ? 'mine' : x.kind || (x.owner ? 'family' : 'free'),
    groups: [['WHO', who], ['STRENGTH', strength], ['MONEY', money]].filter(g => g[1].length) };
}

// the vitals panel sits ON the stage (never inside the 3D scene, where towers cut through it), grouped, with a close
export function Vitals({ vit, onClose }) {
  if (!vit) return null;
  return <aside className={`fc-vpanel t-${vit.tone}`} data-testid="city-vitals"><header><b>{vit.title}</b><button type="button" onClick={onClose} aria-label="Close and zoom out" data-tip="Zoom back out">✕</button></header>
    {vit.groups.map(([g, rows]) => <section key={g}><em>{g}</em><dl>{rows.map(([k, val, pct]) => <React.Fragment key={k}><dt>{k}</dt><dd key={val}>{val}
      {pct != null ? <u><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, pct))})` }} /></u> : null}</dd></React.Fragment>)}</dl></section>)}</aside>;
}

// 🎥 the camera: drag turns, wheel zooms, `focus` flies the camera to a world point and back
function CityStage({ W, H, focus, wx, ctl, hud, children }) {
  const stage = useRef(null); const rz = useRef(-28); const rx = useRef(54); const moved = useRef(false); const drag = useRef(null);
  const base = Math.max(0.42, Math.min(1.05, 760 / Math.max(W, H))); const zoom = useRef(base); const pan = useRef([0, 0]);
  const [spin, setSpin] = useState(false); const [fly, setFly] = useState(false);
  const apply = () => { const s = stage.current; if (!s) return; s.style.setProperty('--rz', `${rz.current}deg`); s.style.setProperty('--rx', `${rx.current}deg`);
    s.style.setProperty('--zoom', zoom.current); s.style.setProperty('--px', `${pan.current[0]}px`); s.style.setProperty('--py', `${pan.current[1]}px`); s.style.setProperty('--dy', focus ? '110px' : '0px'); };
  useEffect(() => {
    pan.current = focus ? [W / 2 - focus.x, H / 2 - focus.y] : [0, 0]; zoom.current = focus ? Math.max(base * 1.8, 0.95) : base;
    setFly(true); apply(); const t = setTimeout(() => setFly(false), 850); return () => clearTimeout(t);
  }, [focus?.x, focus?.y, W, H]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { apply(); if (!spin) return undefined; let raf; let last = performance.now();
    const go = t => { rz.current += (t - last) * 0.006; last = t; apply(); raf = requestAnimationFrame(go); }; raf = requestAnimationFrame(go); return () => cancelAnimationFrame(raf); }, [spin]);   // eslint-disable-line react-hooks/exhaustive-deps
  const down = e => { drag.current = { x: e.clientX, y: e.clientY, rz: rz.current, rx: rx.current }; moved.current = false; };
  const move = e => { const d = drag.current; if (!d) return; const dx = e.clientX - d.x; const dy = e.clientY - d.y; if (Math.abs(dx) + Math.abs(dy) > 6) moved.current = true;
    rz.current = d.rz + dx * 0.35; rx.current = Math.max(30, Math.min(68, d.rx - dy * 0.15)); apply(); };
  const up = () => { drag.current = null; };
  const wheel = e => { zoom.current = Math.max(0.38, Math.min(2.2, zoom.current * (e.deltaY > 0 ? 0.92 : 1.08))); apply(); };
  const zoomBy = f => { zoom.current = Math.max(0.38, Math.min(2.2, zoom.current * f)); apply(); };
  return <div className={`fcy wx-${wx} ${fly ? 'is-fly' : ''} ${focus ? 'is-focus' : ''}`} ref={stage} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerLeave={up} onWheel={wheel}
    onClickCapture={e => { if (moved.current) { e.stopPropagation(); e.preventDefault(); moved.current = false; } }} data-testid="world-map">
    <div className="fcy-sky" aria-hidden="true"><i className="fcy-moon" />{Array.from({ length: 22 }, (_, i) => <i key={i} className="fcy-star" style={{ '--i': i }} />)}</div>
    <div className="fcy-skyline" aria-hidden="true">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ '--i': i, '--h': `${40 + ((i * 37) % 70)}px` }} />)}</div>
    <div className="fcy-world" style={{ width: W, height: H }}><i className="fcy-water" aria-hidden="true" />{children}</div>{hud}
    {wx !== 'clear' ? <div className="fcy-wx" aria-hidden="true">{Array.from({ length: wx === 'fog' ? 4 : 30 }, (_, i) => <i key={i} style={{ '--i': i, '--x': `${(i * 37) % 100}%` }} />)}</div> : null}
    <div className="fcy-ctl"><button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(s => !s)} aria-pressed={spin} data-tip="Slowly turn the whole city" data-testid="city-spin">{spin ? '⏸ Stop' : '⟲ 360°'}</button>
      <button type="button" onClick={() => zoomBy(1.2)} data-tip="Zoom in" aria-label="Zoom in">＋</button>
      <button type="button" onClick={() => zoomBy(1 / 1.2)} data-tip="Zoom out" aria-label="Zoom out">－</button>{ctl}
      <small>drag to turn · scroll to zoom · tap a plot</small></div>
    <ul className="fcy-key"><li className="t-mine">yours</li><li className="t-family">families</li><li className="t-cpu">CPU towns</li><li className="t-cartel">cartels</li><li className="t-free">for sale</li></ul>
  </div>;
}

export function FamilyCity3D({ v, sel, setSel, city, setCity, tour, overlay }) {
  const cities = v.cities?.length ? v.cities : [{ key: 'all', name: 'The city', boroughs: (v.boroughs || []).map(b => b.key) }];
  const cur = cities.find(c => c.key === city) || cities[0];
  const isFee = cur.key === 'fee';
  const bors = useMemo(() => (v.boroughs || []).filter(b => cur.boroughs.includes(b.key)), [v.boroughs, cur]);
  const byB = useMemo(() => { const m = {}; (v.blocks || []).forEach(x => { (m[x.b] = m[x.b] || []).push(x); }); return m; }, [v.blocks]);
  const lay = useMemo(() => cityLayout(bors), [bors]);
  const W = isFee ? FEE_W : lay.W; const H = isFee ? FEE_H : lay.H;
  const spot = !sel || sel.place || sel.mk ? null : isFee ? feeSpot(sel) : sel.b && lay.pos[sel.b] ? { x: lay.pos[sel.b].x + lotPos(sel.i).x + LOT / 2, y: lay.pos[sel.b].y + lotPos(sel.i).y + LOT / 2 } : null;
  const inner = (v.bridges || []).filter(br => lay.pos[br.a] && lay.pos[br.b]);
  const home = (v.bridges || []).find(br => [br.a, br.b].includes('fee') && bors.some(b => [br.a, br.b].includes(b.key)));
  const homeP = home ? lay.pos[home.a === 'fee' ? home.b : home.a] : null;
  const fee = cities.find(c => c.key === 'fee');
  const hot = new Set((v.raids || []).filter(r => r.status === 'live').map(r => r.b.id));
  return <CityStage W={W} H={H} focus={spot} wx={v.season?.weather || 'clear'} ctl={tour.ctl} hud={<><Vitals vit={vitalsOf(sel, v)} onClose={() => setSel(sel)} />{overlay}</>}>
    {isFee ? <FeeCapital v={v} sel={sel} onPick={setSel} onGo={k => { setSel(null); setCity(k); }} tour={tour.on} hot={hot} />
      : <>{inner.map(br => <Bridge key={br.name} r={bridgeRect(lay.pos[br.a], lay.pos[br.b])} name={br.name} />)}
        {homeP && fee ? <Bridge r={{ x: 0, y: homeP.y + ISLAND / 2 - 13, w: homeP.x + 6, h: 26, horiz: true }} name={home.name}
          gate={{ key: 'fee', at: 'w', name: 'FEE CITY', sub: `${fee.held}/${fee.plots} held`, go: () => { setSel(null); setCity('fee'); } }} /> : null}
        {bors.map(b => <Island key={b.key} b={b} p={lay.pos[b.key]} blocks={byB[b.key] || []} boom={v.boom?.borough} sel={sel?.id} onPick={setSel} reach={v.me?.reach?.[b.key]} hot={hot} />)}</>}
  </CityStage>;
}
