import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { RACE, VEHICLES, cityOf, step, atCheckpoint, kmh, fmtMs, bearing, traffic } from '../lib/raceEngine';
import { tgInitData, tgHaptic } from '../lib/telegram';
import '../styles/streetRace.css';

// 🏁 THE RACEWAY (owner 2026-10-27: "family be a telegram game where people can drive vehicles / race this city"): drive Fee City at night — the
// families' own blocks are the buildings (their colour, their tag on the roof), traffic loops the avenues, street lamps at every crossing. Pick a
// vehicle, hit the server's checkpoints in order, beat par. The server deals the track and checks the time (backend/raceway.py); a wallet in a
// family earns MP (the day's first finish + under par), a Telegram player posts to the board, nobody signed in practises. Errand mode = a
// delivery run from your family's home that pays that errand's MP (×1.25 under par). three.js loads only when the Raceway opens.
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'The race office said no.'); return j; });
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');

function windowTexture(THREE) {   // lit office windows on the night towers (one canvas, shared)
  const c = document.createElement('canvas'); c.width = 64; c.height = 128; const g = c.getContext('2d');
  g.fillStyle = '#05070a'; g.fillRect(0, 0, 64, 128);
  for (let y = 4; y < 128; y += 8) for (let x = 4; x < 64; x += 8) { const on = Math.random(); g.fillStyle = on > 0.62 ? '#ffd889' : on > 0.5 ? '#7fd8ff' : '#0b1016'; g.fillRect(x, y, 4, 5); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1, 2); return t;
}
function signTexture(THREE, text, color) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 96; const g = c.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,.6)'; g.fillRect(0, 0, 256, 96); g.strokeStyle = color; g.lineWidth = 6; g.strokeRect(4, 4, 248, 88);
  g.font = '900 54px Unbounded, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.shadowColor = color; g.shadowBlur = 18; g.fillStyle = color; g.fillText(text, 128, 50);
  return new THREE.CanvasTexture(c);
}
function vehicleMesh(THREE, k) {
  const v = VEHICLES[k] || VEHICLES.car; const grp = new THREE.Group();
  const paint = new THREE.MeshStandardMaterial({ color: v.color, metalness: 0.6, roughness: 0.35, emissive: v.color, emissiveIntensity: 0.12 });
  const dark = new THREE.MeshStandardMaterial({ color: '#0b0d10', roughness: 0.6 }); const glass = new THREE.MeshStandardMaterial({ color: '#7fd8ff', emissive: '#0b2a3a', metalness: 0.2, roughness: 0.1 });
  const lamp = new THREE.MeshBasicMaterial({ color: '#fff6d0' }); const tail = new THREE.MeshBasicMaterial({ color: '#ff3355' });
  const box = (w, h, d, m, x, y, z) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(x, y, z); grp.add(b); return b; };
  if (k === 'bike') { box(0.5, 0.5, 1.8, paint, 0, 0.75, 0); box(0.42, 0.7, 0.5, dark, 0, 1.3, -0.3); box(0.3, 0.3, 0.3, lamp, 0, 0.95, 0.95); box(0.3, 0.2, 0.1, tail, 0, 0.9, -0.95); }
  else if (k === 'truck') { box(2.4, 2.6, 4.6, paint, 0, 1.75, -1.1); box(2.3, 1.7, 2, dark, 0, 1.3, 2.2); box(2.1, 0.7, 0.1, glass, 0, 1.65, 3.21); box(0.5, 0.3, 0.1, lamp, -0.8, 0.9, 3.22); box(0.5, 0.3, 0.1, lamp, 0.8, 0.9, 3.22); box(0.6, 0.25, 0.1, tail, -0.9, 0.8, -3.42); box(0.6, 0.25, 0.1, tail, 0.9, 0.8, -3.42); }
  else { box(2, 0.7, 4.4, paint, 0, 0.75, 0); box(1.7, 0.55, 2.1, glass, 0, 1.35, -0.3); box(0.45, 0.22, 0.1, lamp, -0.65, 0.8, 2.21); box(0.45, 0.22, 0.1, lamp, 0.65, 0.8, 2.21); box(0.5, 0.2, 0.1, tail, -0.65, 0.85, -2.21); box(0.5, 0.2, 0.1, tail, 0.65, 0.85, -2.21); }
  const wheelG = new THREE.CylinderGeometry(k === 'truck' ? 0.55 : 0.42, k === 'truck' ? 0.55 : 0.42, 0.35, 12); wheelG.rotateZ(Math.PI / 2); const wheels = [];
  const wz = k === 'bike' ? [[0, 0.75], [0, -0.75]] : k === 'truck' ? [[-1.15, 2.2], [1.15, 2.2], [-1.15, -2.4], [1.15, -2.4]] : [[-1, 1.4], [1, 1.4], [-1, -1.4], [1, -1.4]];
  for (const [x, z] of wz) { const w = new THREE.Mesh(wheelG, dark); w.position.set(x, k === 'truck' ? 0.55 : 0.42, z); grp.add(w); wheels.push(w); }
  const beam = new THREE.Mesh(new THREE.ConeGeometry(3.2, 16, 16, 1, true), new THREE.MeshBasicMaterial({ color: '#fff3c0', transparent: true, opacity: 0.07, depthWrite: false, side: THREE.DoubleSide }));
  beam.rotation.x = -Math.PI / 2; beam.position.set(0, 0.9, (v.len / 2) + 8); grp.add(beam);   // the headlight cone on the road ahead
  grp.userData.wheels = wheels; return grp;
}

export function StreetRace({ blocks, addr = '', sess = '', mode = 'race', store = '', onDone }) {
  const mount = useRef(null); const three = useRef(null);
  const g = useRef({ s: { x: 0, z: 0, yaw: 0, speed: 0 }, inp: { gas: 0, steer: 0, brake: false }, track: null, token: '', t0: 0, splits: [], cp: 0, running: false, veh: 'car' });
  const [phase, setPhase] = useState('pick'); const [count, setCount] = useState(3);
  const [veh, setVeh] = useState(() => { try { return VEHICLES[localStorage.getItem('feeless.race.veh')] ? localStorage.getItem('feeless.race.veh') : 'car'; } catch { return 'car'; } });
  const [info, setInfo] = useState(null); const [hud, setHud] = useState({ t: 0, kmh: 0, cp: 0, n: 0, arrow: 0, x: 0, z: 0 }); const [res, setRes] = useState(null); const [err, setErr] = useState('');
  const city = useMemo(() => cityOf(blocks, 'feeless-race'), [blocks]);
  const who = useMemo(() => (addr && sess ? { address: addr, session: sess } : tgInitData() ? { tg: tgInitData() } : {}), [addr, sess]);
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/familia-race${addr && sess ? `?address=${addr}&session=${encodeURIComponent(sess)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setInfo(x)).catch(() => {}), [addr, sess]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { g.current.veh = veh; try { localStorage.setItem('feeless.race.veh', veh); } catch { /* private */ } three.current?.setVehicle?.(veh); }, [veh]);

  // 🌃 the night city, the car, the rings — built once; the loop reads `g` every frame
  useEffect(() => {
    let alive = true; let raf = 0; let ro = null; const el = mount.current;
    import('three').then(THREE => {
      if (!alive || !el) return;
      const L = RACE.grid * RACE.cell; const low = lite();
      const renderer = new THREE.WebGLRenderer({ antialias: !low, powerPreference: 'high-performance' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, low ? 1 : 1.6)); renderer.setSize(el.clientWidth || 600, el.clientHeight || 380); el.appendChild(renderer.domElement);
      const scene = new THREE.Scene(); scene.background = new THREE.Color('#04060a'); scene.fog = new THREE.Fog('#04060a', 50, 230);
      const camera = new THREE.PerspectiveCamera(62, (el.clientWidth || 600) / (el.clientHeight || 380), 0.5, 600);
      scene.add(new THREE.HemisphereLight('#5d6cff', '#0a120d', 0.6)); const moon = new THREE.DirectionalLight('#cfd8ff', 0.55); moon.position.set(-80, 140, -40); scene.add(moon);
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(L + 160, L + 160), new THREE.MeshStandardMaterial({ color: '#0a0e0c', roughness: 1 })); ground.rotation.x = -Math.PI / 2; ground.position.set(L / 2, 0, L / 2); scene.add(ground);
      const roadM = new THREE.MeshStandardMaterial({ color: '#16191b', roughness: 0.85 });
      for (let k = 0; k <= RACE.grid; k += 1) {
        const a = new THREE.Mesh(new THREE.PlaneGeometry(RACE.road, L + RACE.road), roadM); a.rotation.x = -Math.PI / 2; a.position.set(k * RACE.cell, 0.02, L / 2); scene.add(a);
        const b = new THREE.Mesh(new THREE.PlaneGeometry(L + RACE.road, RACE.road), roadM); b.rotation.x = -Math.PI / 2; b.position.set(L / 2, 0.03, k * RACE.cell); scene.add(b);
      }
      const m4 = new THREE.Matrix4(); const q = new THREE.Quaternion(); const v3 = new THREE.Vector3(); const sc = new THREE.Vector3();
      const per = Math.floor(L / 6); const dashes = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.28, 2.4), new THREE.MeshBasicMaterial({ color: '#f5c451' }), (RACE.grid + 1) * per * 2); let di = 0;
      const flat = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0)); const flatX = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, Math.PI / 2));
      for (let k = 0; k <= RACE.grid; k += 1) for (let s = 0; s < per; s += 1) {
        m4.compose(v3.set(k * RACE.cell, 0.05, s * 6 + 3), flat, sc.set(1, 1, 1)); dashes.setMatrixAt(di++, m4);
        m4.compose(v3.set(s * 6 + 3, 0.05, k * RACE.cell), flatX, sc.set(1, 1, 1)); dashes.setMatrixAt(di++, m4);
      }
      scene.add(dashes);
      const winT = windowTexture(THREE);
      const towers = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.75, metalness: 0.1, emissive: '#ffd27a', emissiveMap: winT, emissiveIntensity: 0.85 }), city.length);
      const col = new THREE.Color();
      city.forEach((b, i) => { m4.compose(v3.set(b.x, b.h / 2, b.z), q.identity(), sc.set(b.w, b.h, b.d)); towers.setMatrixAt(i, m4); towers.setColorAt(i, col.set(b.color)); });
      scene.add(towers);
      const signs = []; city.filter(b => b.tag).slice(0, 40).forEach(b => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: signTexture(THREE, b.tag, b.color), depthWrite: false })); sp.scale.set(9, 3.4, 1); sp.position.set(b.x, b.h + 3, b.z); scene.add(sp); signs.push(sp); });
      const lamps = new THREE.InstancedMesh(new THREE.SphereGeometry(0.5, 8, 6), new THREE.MeshBasicMaterial({ color: '#ffd27a' }), (RACE.grid + 1) ** 2); let li = 0;
      for (let i = 0; i <= RACE.grid; i += 1) for (let j = 0; j <= RACE.grid; j += 1) { m4.compose(v3.set(i * RACE.cell + RACE.road / 2, 6, j * RACE.cell + RACE.road / 2), q.identity(), sc.set(1, 1, 1)); lamps.setMatrixAt(li++, m4); }
      scene.add(lamps);
      const glowM = new THREE.MeshBasicMaterial({ color: '#ffd27a', transparent: true, opacity: 0.08, depthWrite: false });
      const pools = new THREE.InstancedMesh(new THREE.CircleGeometry(5, 18), glowM, (RACE.grid + 1) ** 2); li = 0;
      for (let i = 0; i <= RACE.grid; i += 1) for (let j = 0; j <= RACE.grid; j += 1) { m4.compose(v3.set(i * RACE.cell + RACE.road / 2 - 2, 0.06, j * RACE.cell + RACE.road / 2 - 2), flat, sc.set(1, 1, 1)); pools.setMatrixAt(li++, m4); }
      scene.add(pools);
      const traf = new THREE.InstancedMesh(new THREE.BoxGeometry(1.9, 1.2, 4), new THREE.MeshStandardMaterial({ color: '#8899aa', emissive: '#223', roughness: 0.5 }), 10); scene.add(traf);
      const trafL = new THREE.InstancedMesh(new THREE.BoxGeometry(1.6, 0.2, 0.1), new THREE.MeshBasicMaterial({ color: '#fff3c0' }), 10); scene.add(trafL);
      let car = vehicleMesh(THREE, g.current.veh); scene.add(car);
      const rings = []; const ringG = new THREE.TorusGeometry(6, 0.45, 10, 40); const beamG = new THREE.CylinderGeometry(5.6, 5.6, 60, 24, 1, true);
      const setTrack = tr => {
        rings.forEach(r => scene.remove(r)); rings.length = 0;
        (tr?.cps || []).forEach(([x, z], i) => { const grp = new THREE.Group();
          const ring = new THREE.Mesh(ringG, new THREE.MeshBasicMaterial({ color: i === 0 ? '#45e486' : '#2a6b4a', transparent: true, opacity: 0.95 })); ring.position.y = 6; grp.add(ring);
          const beam = new THREE.Mesh(beamG, new THREE.MeshBasicMaterial({ color: '#45e486', transparent: true, opacity: i === 0 ? 0.12 : 0.04, depthWrite: false, side: THREE.DoubleSide })); beam.position.y = 30; grp.add(beam);
          grp.position.set(x, 0, z); scene.add(grp); rings.push(grp); });
      };
      const setVehicle = k => { scene.remove(car); car = vehicleMesh(THREE, k); scene.add(car); };
      const lightRing = n => rings.forEach((r, i) => { r.visible = i >= n; const on = i === n; r.children[0].material.color.set(on ? '#45e486' : '#2a6b4a'); r.children[1].material.opacity = on ? 0.14 : 0.04; });
      three.current = { setTrack, setVehicle, lightRing };
      if (g.current.track) setTrack(g.current.track);
      ro = new ResizeObserver(() => { const w = el.clientWidth || 600; const h = el.clientHeight || 380; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); }); ro.observe(el);
      let last = performance.now(); let hudAt = 0; const camPos = new THREE.Vector3(-20, 30, -20); const look = new THREE.Vector3();
      const loop = now => {
        raf = requestAnimationFrame(loop);
        if (document.hidden) { last = now; return; }
        const dt = Math.min(0.05, (now - last) / 1000); last = now; const G = g.current;
        if (G.running) {
          const near = city.filter(b => Math.abs(b.x - G.s.x) < 34 && Math.abs(b.z - G.s.z) < 34);
          const n = step(G.s, G.inp, dt, G.veh, near); if (n.hit && !G.s.hitting) tgHaptic('heavy'); G.s = { ...n, hitting: n.hit };
          const cp = G.track?.cps?.[G.cp];
          if (cp && atCheckpoint(G.s, cp)) { G.splits.push(Math.round(now - G.t0)); G.cp += 1; three.current.lightRing(G.cp); tgHaptic(G.cp === G.track.cps.length ? 'success' : 'medium');
            if (G.cp >= G.track.cps.length) { G.running = false; G.finish?.(Math.round(now - G.t0)); } }
        }
        car.position.set(G.s.x, 0, G.s.z); car.rotation.y = G.s.yaw; (car.userData.wheels || []).forEach(w => { w.rotation.x += G.s.speed * dt / 0.45; });
        const back = G.running || G.s.speed ? 11 : 16; const up = G.running || G.s.speed ? 5 : 9;
        camPos.lerp(v3.set(G.s.x - Math.sin(G.s.yaw) * back, up, G.s.z - Math.cos(G.s.yaw) * back), Math.min(1, dt * 4)); camera.position.copy(camPos);
        camera.lookAt(look.set(G.s.x + Math.sin(G.s.yaw) * 7, 1.5, G.s.z + Math.cos(G.s.yaw) * 7));
        rings.forEach((r, i) => { r.children[0].rotation.y += dt * (i === G.cp ? 1.6 : 0.5); });
        traffic(now / 1000, 10).forEach((p, i) => { m4.compose(v3.set(p.x, 0.8, p.z), q.setFromEuler(new THREE.Euler(0, p.yaw, 0)), sc.set(1, 1, 1)); traf.setMatrixAt(i, m4);
          m4.compose(v3.set(p.x + Math.sin(p.yaw) * 2.05, 0.9, p.z + Math.cos(p.yaw) * 2.05), q, sc.set(1, 1, 1)); trafL.setMatrixAt(i, m4); });
        traf.instanceMatrix.needsUpdate = true; trafL.instanceMatrix.needsUpdate = true;
        renderer.render(scene, camera);
        if (now - hudAt > 100) { hudAt = now; const cp = G.track?.cps?.[G.cp];
          setHud({ t: G.running ? now - G.t0 : G.lastMs || 0, kmh: kmh(G.s.speed), cp: G.cp, n: G.track?.cps?.length || 0, arrow: cp ? bearing(G.s, cp) : 0, x: G.s.x, z: G.s.z }); }
      };
      raf = requestAnimationFrame(loop);
      three.current.dispose = () => { scene.traverse(o => { o.geometry?.dispose?.(); const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : []; ms.forEach(m => { m.map?.dispose?.(); m.emissiveMap?.dispose?.(); m.dispose?.(); }); }); renderer.dispose(); renderer.domElement.remove(); };
    }).catch(() => setErr('3D did not load on this device.'));
    return () => { alive = false; cancelAnimationFrame(raf); ro?.disconnect(); three.current?.dispose?.(); three.current = null; };
  }, [city]);

  // ⌨ arrows / WASD + space; 📱 the on-screen pedals (pointer events) write the same input
  useEffect(() => {
    const keys = new Set(); const sync = () => { const I = g.current.inp; I.gas = (keys.has('up') ? 1 : 0) - (keys.has('down') ? 1 : 0); I.steer = (keys.has('left') ? 1 : 0) - (keys.has('right') ? 1 : 0); I.brake = keys.has('brake'); };
    const map = e => ({ ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down', ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', Space: 'brake' }[e.code]);
    const dn = e => { const k = map(e); if (!k || !g.current.running) return; e.preventDefault(); keys.add(k); sync(); };
    const upk = e => { const k = map(e); if (!k) return; keys.delete(k); sync(); };
    window.addEventListener('keydown', dn); window.addEventListener('keyup', upk);
    return () => { window.removeEventListener('keydown', dn); window.removeEventListener('keyup', upk); };
  }, []);
  const pedal = (k, v) => ({ onPointerDown: e => { e.preventDefault(); e.currentTarget.setPointerCapture?.(e.pointerId); g.current.inp[k] = v; }, onPointerUp: () => { g.current.inp[k] = k === 'brake' ? false : 0; },
    onPointerCancel: () => { g.current.inp[k] = k === 'brake' ? false : 0; }, onContextMenu: e => e.preventDefault() });

  const go = async () => {
    setErr(''); setRes(null);
    try {
      const r = await post('/api/reputation/familia-race/start', { ...who, mode, store });
      const G = g.current; const [x, z] = r.track.start; const c0 = r.track.cps[0];
      Object.assign(G, { track: r.track, token: r.token, splits: [], cp: 0, running: false, practice: r.practice, s: { x, z, yaw: Math.atan2(c0[0] - x, c0[1] - z), speed: 0 }, inp: { gas: 0, steer: 0, brake: false } });
      three.current?.setTrack(r.track); three.current?.lightRing(0);
      G.finish = async ms => {
        G.lastMs = ms; setPhase('done');
        try { const f = await post('/api/reputation/familia-race/finish', { ...who, mode, store, token: G.token, ms, splits: G.splits, vehicle: G.veh }); setRes({ ...f, ms }); load(); onDone?.(f); }
        catch (e) { setRes({ ms, error: e.message }); }
      };
      setPhase('count'); setCount(3);
      let n = 3; const t = setInterval(() => { n -= 1; setCount(n); if (n <= 0) { clearInterval(t); G.t0 = performance.now(); G.running = true; setPhase('go'); } }, 800);
    } catch (e) { setErr(e.message); }
  };
  const par = info?.track?.par; const n = hud.n || info?.track?.cps?.length || 0; const L = RACE.grid * RACE.cell;
  const cps = g.current.track?.cps || info?.track?.cps || [];
  return <section className={`sr is-${phase}`} data-testid="street-race">
    <div className="sr-stage" ref={mount} aria-label="The Raceway — drive Fee City" />
    <div className="sr-hud" aria-live="off">
      <span className="sr-time"><em>{mode === 'errand' ? `DELIVERY · ${store.toUpperCase()}` : "TODAY'S RACE"}</em><b className="m-num">{fmtMs(hud.t)}</b><small className="m-num">par {fmtMs(g.current.track?.par || par)}</small></span>
      <span className="sr-cps" data-tip="Checkpoints — hit them in order">{Array.from({ length: n }, (_, i) => <i key={i} className={i < hud.cp ? 'is-done' : i === hud.cp ? 'is-next' : ''} />)}</span>
      <svg className="sr-map" viewBox={`-10 -10 ${L + 20} ${L + 20}`} aria-hidden="true">
        {Array.from({ length: RACE.grid + 1 }, (_, k) => <g key={k}><line x1={k * RACE.cell} y1="0" x2={k * RACE.cell} y2={L} /><line x1="0" y1={k * RACE.cell} x2={L} y2={k * RACE.cell} /></g>)}
        {cps.map(([x, z], i) => <circle key={i} cx={x} cy={z} r={i === hud.cp ? 9 : 6} className={i < hud.cp ? 'is-done' : i === hud.cp ? 'is-next' : ''} />)}
        <circle cx={hud.x} cy={hud.z} r="8" className="sr-me" />
      </svg>
      {phase === 'go' ? <span className="sr-arrow" style={{ transform: `rotate(${-hud.arrow}rad)` }} aria-hidden="true">▲</span> : null}
      <span className="sr-speed"><b className="m-num">{hud.kmh}</b><em>KM/H</em><i style={{ transform: `scaleX(${Math.min(1, hud.kmh / 190)})` }} /></span>
    </div>
    {phase === 'count' ? <div className="sr-count m-num" key={count}>{count || 'GO'}</div> : null}
    {phase === 'go' ? <div className="sr-pedals">
      <span><button type="button" className="sr-pad" aria-label="Steer left" {...pedal('steer', 1)} data-testid="sr-left">◀</button><button type="button" className="sr-pad" aria-label="Steer right" {...pedal('steer', -1)} data-testid="sr-right">▶</button></span>
      <span><button type="button" className="sr-pad is-brake" aria-label="Brake / reverse" {...pedal('gas', -1)} data-testid="sr-brake">BRAKE</button><button type="button" className="sr-pad is-gas" aria-label="Gas" {...pedal('gas', 1)} data-testid="sr-gas">GAS</button></span>
    </div> : null}
    {phase === 'pick' || phase === 'done' ? <div className="sr-panel" data-testid="sr-panel">
      {phase === 'done' && res ? <div className="sr-result" data-testid="sr-result"><em>{res.error ? 'NOT COUNTED' : res.practice ? 'PRACTICE RUN' : res.best ? '🏆 NEW BEST' : 'FINISHED'}</em><b className="m-num">{fmtMs(res.ms)}</b>
        <small>{res.error || (res.practice ? 'Sign in (wallet or Telegram) to post times — a family earns MP.' : `${res.place ? `#${res.place} today · ` : ''}${res.ms <= res.par ? 'under par' : `par ${fmtMs(res.par)}`}${res.mp ? ` · +${res.mp.toLocaleString('en-US')} MP to the family bank` : ''}`)}</small></div> : null}
      <span className="m-seg sr-vehs" role="radiogroup" aria-label="Vehicle">{Object.entries(VEHICLES).map(([k, x]) => <button key={k} type="button" role="radio" aria-checked={veh === k} className={veh === k ? 'active' : ''} onClick={() => setVeh(k)} data-tip={x.tip} data-testid={`sr-veh-${k}`}>{x.name}</button>)}</span>
      <button type="button" className="m-btn m-go sr-go" onClick={go} data-tip={mode === 'errand' ? 'Drive the delivery: pickup → drop. Under par pays the errand ×1.25' : 'Hit every checkpoint in order. Your first finish today + beating par pay MP to your family'} data-testid="sr-go">{phase === 'done' ? '🔁 RUN IT AGAIN' : mode === 'errand' ? '🚚 START THE DELIVERY' : '🏁 START'}</button>
      {err ? <p className="sr-err">⚠ {err}</p> : null}
      <ol className="sr-board" aria-label="Today's board">{(res?.board || info?.board || []).slice(0, 6).map(r => <li key={r.place} style={{ '--i': r.place }}><i>#{r.place}</i><b>{r.tag ? `[${r.tag}] ` : ''}{r.name || r.who}</b><small>{VEHICLES[r.vehicle]?.name || ''}</small><em className="m-num">{fmtMs(r.ms)}</em></li>)}
        {!(res?.board || info?.board || []).length ? <li className="sr-empty">No times today yet — set the first one.</li> : null}</ol>
      <small className="sr-keys">⌨ arrows / WASD · space brakes · 📱 the pedals · MP: first finish {info?.mp?.finish || 120} + under par {info?.mp?.par || 280}</small>
    </div> : null}
  </section>;
}
