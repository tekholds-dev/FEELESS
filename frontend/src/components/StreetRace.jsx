import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { RACE, VEHICLES, cityOf, step, atCheckpoint, kmh, fmtMs, bearing, lightPhase, axisOf, crossingAt, trafficInit, trafficStep, trafficPose, RED_PENALTY_MS } from '../lib/raceEngine';
import { tgInitData, tgHaptic } from '../lib/telegram';
import '../styles/streetRace.css';

// 🏁 THE RACEWAY (owner 2026-10-27: "family be a telegram game where people can drive vehicles / race this city" · "true stop and go, daytime,
// real checkpoints"): drive Fee City by day — the families' own blocks are the buildings (their colour, their tag on the roof), a traffic light on
// every crossing (traffic stops at red and goes on green; you running a red = +2 s), real checkpoint gates across the road. Pick a vehicle, hit
// the server's gates in order, beat par. The server deals the track and checks the time (backend/raceway.py); a wallet in a
// family earns MP (the day's first finish + under par), a Telegram player posts to the board, nobody signed in practises. Errand mode = a
// delivery run from your family's home that pays that errand's MP (×1.25 under par). three.js loads only when the Raceway opens.
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw Object.assign(new Error(j.detail || 'The race office said no.'), { status: r.status }); return j; });
const lite = () => typeof document !== 'undefined' && document.body.classList.contains('fx-lite');

function windowTexture(THREE) {   // daytime glass on the towers: blue-grey panes, some catching the sun (white wall = the building's own colour shows)
  const c = document.createElement('canvas'); c.width = 64; c.height = 128; const g = c.getContext('2d');
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, 64, 128);
  for (let y = 4; y < 128; y += 8) for (let x = 4; x < 64; x += 8) { const r = Math.random(); g.fillStyle = r > 0.8 ? '#cfe6f7' : r > 0.4 ? '#5d7c99' : '#46627d'; g.fillRect(x, y, 4, 5); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 5); return t;
}
function gateTexture(THREE, text, finish) {   // the banner across a checkpoint gate
  const c = document.createElement('canvas'); c.width = 512; c.height = 96; const g = c.getContext('2d');
  if (finish) { for (let i = 0; i < 32; i += 1) for (let j = 0; j < 6; j += 1) { g.fillStyle = (i + j) % 2 ? '#111' : '#fff'; g.fillRect(i * 16, j * 16, 16, 16); } }
  else { g.fillStyle = '#0b3d22'; g.fillRect(0, 0, 512, 96); g.fillStyle = '#15d16a'; g.fillRect(0, 0, 512, 10); g.fillRect(0, 86, 512, 10); }
  g.font = '900 56px Unbounded, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineWidth = 8; g.strokeStyle = '#000'; g.strokeText(text, 256, 50); g.fillStyle = finish ? '#f5c451' : '#ffffff'; g.fillText(text, 256, 50);
  return new THREE.CanvasTexture(c);
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
  // before START: today's rings are up and the car waits on the line, nose to the first checkpoint
  useEffect(() => { const tr = info?.track; const G = g.current; if (!tr?.cps?.length || G.running || G.token) return;
    const [x, z] = tr.start; const c0 = tr.cps[0]; Object.assign(G, { track: tr, s: { x, z, yaw: Math.atan2(c0[0] - x, c0[1] - z), speed: 0 } }); three.current?.setTrack(tr); three.current?.lightRing(0); }, [info]);
  useEffect(() => { g.current.veh = veh; try { localStorage.setItem('feeless.race.veh', veh); } catch { /* private */ } three.current?.setVehicle?.(veh); }, [veh]);

  // 🌃 the night city, the car, the rings — built once; the loop reads `g` every frame
  useEffect(() => {
    let alive = true; let raf = 0; let ro = null; const el = mount.current;
    import('three').then(THREE => {
      if (!alive || !el) return;
      const L = RACE.grid * RACE.cell; const low = lite();
      const renderer = new THREE.WebGLRenderer({ antialias: !low, powerPreference: 'high-performance' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, low ? 1 : 1.6)); renderer.setSize(el.clientWidth || 600, el.clientHeight || 380); el.appendChild(renderer.domElement);
      const scene = new THREE.Scene(); scene.background = new THREE.Color('#9fd0f5'); scene.fog = new THREE.Fog('#cfe6f7', 90, 330);
      const camera = new THREE.PerspectiveCamera(62, (el.clientWidth || 600) / (el.clientHeight || 380), 0.5, 600);
      scene.add(new THREE.HemisphereLight('#e4f3ff', '#6b7a5e', 1.0)); const sun = new THREE.DirectionalLight('#fff3dc', 1.25); sun.position.set(140, 200, 70); scene.add(sun);
      const grass = new THREE.Mesh(new THREE.PlaneGeometry(L + 900, L + 900), new THREE.MeshStandardMaterial({ color: '#6f9a55', roughness: 1 })); grass.rotation.x = -Math.PI / 2; grass.position.set(L / 2, -0.02, L / 2); scene.add(grass);
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(L + 30, L + 30), new THREE.MeshStandardMaterial({ color: '#a7ae9f', roughness: 1 })); ground.rotation.x = -Math.PI / 2; ground.position.set(L / 2, 0, L / 2); scene.add(ground);
      const railM = new THREE.MeshStandardMaterial({ color: '#d9dde2', metalness: 0.5, roughness: 0.4 }); const stripeM = new THREE.MeshStandardMaterial({ color: '#e0463c' });
      [[L / 2, -9, L + 18, 0], [L / 2, L + 9, L + 18, 0], [-9, L / 2, L + 18, 1], [L + 9, L / 2, L + 18, 1]].forEach(([x, z, len, rot]) => {   // the guard rail round the city
        const r = new THREE.Mesh(new THREE.BoxGeometry(len, 1.1, 0.5), railM); r.position.set(x, 0.55, z); r.rotation.y = rot ? Math.PI / 2 : 0; scene.add(r);
        const st = new THREE.Mesh(new THREE.BoxGeometry(len, 0.25, 0.55), stripeM); st.position.set(x, 0.9, z); st.rotation.y = rot ? Math.PI / 2 : 0; scene.add(st); });
      const roadM = new THREE.MeshStandardMaterial({ color: '#3b4046', roughness: 0.9 });
      for (let k = 0; k <= RACE.grid; k += 1) {
        const a = new THREE.Mesh(new THREE.PlaneGeometry(RACE.road, L + RACE.road), roadM); a.rotation.x = -Math.PI / 2; a.position.set(k * RACE.cell, 0.02, L / 2); scene.add(a);
        const b = new THREE.Mesh(new THREE.PlaneGeometry(L + RACE.road, RACE.road), roadM); b.rotation.x = -Math.PI / 2; b.position.set(L / 2, 0.03, k * RACE.cell); scene.add(b);
      }
      const m4 = new THREE.Matrix4(); const q = new THREE.Quaternion(); const v3 = new THREE.Vector3(); const sc = new THREE.Vector3();
      const per = Math.floor(L / 6); const dashes = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.28, 2.4), new THREE.MeshBasicMaterial({ color: '#f4f2ea' }), (RACE.grid + 1) * per * 2); let di = 0;
      const flat = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0)); const flatX = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, Math.PI / 2));
      for (let k = 0; k <= RACE.grid; k += 1) for (let s = 0; s < per; s += 1) {
        m4.compose(v3.set(k * RACE.cell, 0.05, s * 6 + 3), flat, sc.set(1, 1, 1)); dashes.setMatrixAt(di++, m4);
        m4.compose(v3.set(s * 6 + 3, 0.05, k * RACE.cell), flatX, sc.set(1, 1, 1)); dashes.setMatrixAt(di++, m4);
      }
      scene.add(dashes);
      const winT = windowTexture(THREE);
      const towers = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: '#ffffff', map: winT, roughness: 0.6, metalness: 0.15 }), city.length);
      const col = new THREE.Color();
      city.forEach((b, i) => { m4.compose(v3.set(b.x, b.h / 2, b.z), q.identity(), sc.set(b.w, b.h, b.d)); towers.setMatrixAt(i, m4); towers.setColorAt(i, col.set(b.color)); });
      scene.add(towers);
      const signs = []; city.filter(b => b.tag).slice(0, 40).forEach(b => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: signTexture(THREE, b.tag, b.color), depthWrite: false })); sp.scale.set(9, 3.4, 1); sp.position.set(b.x, b.h + 3, b.z); scene.add(sp); signs.push(sp); });
      const NX = (RACE.grid + 1) ** 2; const corner = (i, j) => [i * RACE.cell + RACE.road / 2 + 0.6, j * RACE.cell + RACE.road / 2 + 0.6];
      const poles = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.18, 0.18, 6, 6), new THREE.MeshStandardMaterial({ color: '#2b3036', roughness: 0.6 }), NX);
      const heads = new THREE.InstancedMesh(new THREE.BoxGeometry(0.9, 2.2, 0.9), new THREE.MeshStandardMaterial({ color: '#15181c', roughness: 0.5 }), NX);
      const lampNS = new THREE.InstancedMesh(new THREE.SphereGeometry(0.34, 8, 6), new THREE.MeshBasicMaterial({ color: '#ffffff' }), NX);
      const lampEW = new THREE.InstancedMesh(new THREE.SphereGeometry(0.34, 8, 6), new THREE.MeshBasicMaterial({ color: '#ffffff' }), NX); let li = 0;
      for (let i = 0; i <= RACE.grid; i += 1) for (let j = 0; j <= RACE.grid; j += 1) { const [cx, cz] = corner(i, j);
        m4.compose(v3.set(cx, 3, cz), q.identity(), sc.set(1, 1, 1)); poles.setMatrixAt(li, m4); m4.compose(v3.set(cx, 6.6, cz), q.identity(), sc.set(1, 1, 1)); heads.setMatrixAt(li, m4);
        m4.compose(v3.set(cx, 6.6, cz - 0.5), q.identity(), sc.set(1, 1, 1)); lampNS.setMatrixAt(li, m4); m4.compose(v3.set(cx - 0.5, 6.6, cz), q.identity(), sc.set(1, 1, 1)); lampEW.setMatrixAt(li, m4); li += 1; }
      scene.add(poles, heads, lampNS, lampEW);
      const LC = { g: new THREE.Color('#2bff7a'), y: new THREE.Color('#ffc832'), r: new THREE.Color('#ff3b3b') }; let shown = '';
      const paintLights = t => { const ph = lightPhase(t); const key = ph.ns + ph.ew; if (key === shown) return; shown = key;
        for (let k = 0; k < NX; k += 1) { lampNS.setColorAt(k, LC[ph.ns]); lampEW.setColorAt(k, LC[ph.ew]); } lampNS.instanceColor.needsUpdate = true; lampEW.instanceColor.needsUpdate = true; };
      paintLights(0);
      const traf = new THREE.InstancedMesh(new THREE.BoxGeometry(1.9, 1.3, 4.2), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.4, metalness: 0.3 }), 10); scene.add(traf);
      ['#e8e8e8', '#2b5d9c', '#b8322f', '#2f2f33', '#d8b23a', '#4b8f5a', '#e8e8e8', '#7a8794', '#2b5d9c', '#b8322f'].forEach((c, i) => traf.setColorAt(i, col.set(c)));
      const trafL = new THREE.InstancedMesh(new THREE.BoxGeometry(1.6, 0.25, 0.1), new THREE.MeshBasicMaterial({ color: '#ff3355' }), 10); scene.add(trafL);   // brake lights
      let car = vehicleMesh(THREE, g.current.veh); scene.add(car);
      const rings = []; const pillarG = new THREE.BoxGeometry(1, 8, 1); const bannerG = new THREE.BoxGeometry(RACE.road + 3, 2, 0.4);
      const setTrack = tr => {   // a real gate across the road at each checkpoint, turned to face the way you arrive
        rings.forEach(r => scene.remove(r)); rings.length = 0; let px = tr?.start?.[0] || 0; let pz = tr?.start?.[1] || 0; const n = (tr?.cps || []).length;
        (tr?.cps || []).forEach(([x, z], i) => { const grp = new THREE.Group(); const along = Math.abs(x - px) >= Math.abs(z - pz) ? 'x' : 'z'; const fin = i === n - 1;
          const pm = new THREE.MeshStandardMaterial({ color: fin ? '#f5c451' : '#15d16a', emissive: fin ? '#6b4f00' : '#0b5a2e', emissiveIntensity: 0.4 });
          const half = RACE.road / 2 + 1; const a1 = new THREE.Mesh(pillarG, pm); const a2 = new THREE.Mesh(pillarG, pm); a1.position.set(-half, 4, 0); a2.position.set(half, 4, 0);
          const ban = new THREE.Mesh(bannerG, new THREE.MeshStandardMaterial({ map: gateTexture(THREE, fin ? 'FINISH' : `CHECKPOINT ${i + 1}`, fin), emissive: '#ffffff', emissiveIntensity: 0.15 })); ban.position.set(0, 8, 0);
          grp.add(a1, a2, ban); grp.rotation.y = along === 'x' ? Math.PI / 2 : 0; grp.position.set(x, 0, z); scene.add(grp); rings.push(grp); px = x; pz = z; });
      };
      const setVehicle = k => { scene.remove(car); car = vehicleMesh(THREE, k); scene.add(car); };
      const lightRing = n => rings.forEach((r, i) => { r.visible = i >= n; r.scale.setScalar(i === n ? 1 : 0.85); r.children[0].material.emissiveIntensity = i === n ? 0.9 : 0.15; });
      three.current = { setTrack, setVehicle, lightRing };
      if (g.current.track) setTrack(g.current.track);
      ro = new ResizeObserver(() => { const w = el.clientWidth || 600; const h = el.clientHeight || 380; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); }); ro.observe(el);
      let last = performance.now(); let hudAt = 0; const camPos = new THREE.Vector3(-20, 30, -20); const look = new THREE.Vector3(); let cars = trafficInit(10);
      const loop = now => {
        raf = requestAnimationFrame(loop);
        if (document.hidden) { last = now; return; }
        const dt = Math.min(0.05, (now - last) / 1000); last = now; const G = g.current;
        if (G.running) {
          const near = city.filter(b => Math.abs(b.x - G.s.x) < 34 && Math.abs(b.z - G.s.z) < 34).concat(cars.map(trafficPose).filter(p => Math.abs(p.x - G.s.x) < 20 && Math.abs(p.z - G.s.z) < 20)
            .map(p => ({ x: p.x, z: p.z, w: p.yaw % Math.PI === 0 ? 2 : 4.4, d: p.yaw % Math.PI === 0 ? 4.4 : 2 })));
          const n = step(G.s, G.inp, dt, G.veh, near); if (n.hit && !G.s.hitting) tgHaptic('heavy'); G.s = { ...n, hitting: n.hit };
          const xi = crossingAt(G.s.x, G.s.z); const key = xi ? `${xi.i}:${xi.j}` : '';   // 🚦 running a red: +2 s, once per crossing
          if (key && key !== G.lastX && Math.abs(G.s.speed) > 3) { const ph = lightPhase((now - G.t0) / 1000 + G.lt); if (ph[axisOf(G.s.yaw)] === 'r') { G.pen += RED_PENALTY_MS; G.flash = now; tgHaptic('error'); } }
          G.lastX = key;
          const cp = G.track?.cps?.[G.cp];
          if (cp && atCheckpoint(G.s, cp)) { G.splits.push(Math.round(now - G.t0)); G.cp += 1; three.current.lightRing(G.cp); tgHaptic(G.cp === G.track.cps.length ? 'success' : 'medium');
            if (G.cp >= G.track.cps.length) { G.running = false; G.finish?.(Math.round(now - G.t0) + G.pen); } }
        }
        car.position.set(G.s.x, 0, G.s.z); car.rotation.y = G.s.yaw; (car.userData.wheels || []).forEach(w => { w.rotation.x += G.s.speed * dt / 0.45; });
        const idle = !G.running && Math.abs(G.s.speed) < 0.5; const back = idle ? 15 : 11; const up = idle ? 7 : 5; const yawC = idle ? G.s.yaw + Math.sin(now / 4000) * 0.9 : G.s.yaw;   // idle: the camera sways round the car
        camPos.lerp(v3.set(G.s.x - Math.sin(yawC) * back, up, G.s.z - Math.cos(yawC) * back), Math.min(1, dt * (idle ? 1.5 : 4))); camera.position.copy(camPos);
        camera.lookAt(look.set(G.s.x + Math.sin(G.s.yaw) * 7, 1.5, G.s.z + Math.cos(G.s.yaw) * 7));
        rings.forEach((r, i) => { r.children[0].rotation.y += dt * (i === G.cp ? 1.6 : 0.5); });
        const tl = G.running ? (now - G.t0) / 1000 + G.lt : now / 1000; paintLights(tl); cars = trafficStep(cars, tl, dt);
        cars.forEach((c, i) => { const p = trafficPose(c); m4.compose(v3.set(p.x, 0.85, p.z), q.setFromEuler(new THREE.Euler(0, p.yaw, 0)), sc.set(1, 1, 1)); traf.setMatrixAt(i, m4);
          m4.compose(v3.set(p.x - Math.sin(p.yaw) * 2.12, 0.9, p.z - Math.cos(p.yaw) * 2.12), q, sc.set(c.v < 3 ? 1.15 : 0.6, 1, 1)); trafL.setMatrixAt(i, m4); });   // brake lights grow when it stops
        traf.instanceMatrix.needsUpdate = true; trafL.instanceMatrix.needsUpdate = true;
        renderer.render(scene, camera);
        if (now - hudAt > 100) { hudAt = now; const cp = G.track?.cps?.[G.cp];
          setHud({ t: G.running ? now - G.t0 + G.pen : G.lastMs || 0, kmh: kmh(G.s.speed), cp: G.cp, n: G.track?.cps?.length || 0, arrow: cp ? bearing(G.s, cp) : 0, x: G.s.x, z: G.s.z, pen: G.pen || 0, red: G.flash && now - G.flash < 1200 }); }
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
      const r = await post('/api/reputation/familia-race/start', { ...who, mode, store }).catch(e => {   // a stale sign-in still races — as practice
        if (e.status === 401 && mode === 'race') { setErr('Your sign-in expired — this run is practice (sign in again to post times).'); return post('/api/reputation/familia-race/start', { mode }); } throw e; });
      const G = g.current; const [x, z] = r.track.start; const c0 = r.track.cps[0];
      Object.assign(G, { track: r.track, token: r.token, splits: [], cp: 0, running: false, practice: r.practice, pen: 0, lastX: (() => { const xi = crossingAt(x, z); return xi ? `${xi.i}:${xi.j}` : ''; })(), flash: 0, lt: (performance.now() / 1000) % 12, s: { x, z, yaw: Math.atan2(c0[0] - x, c0[1] - z), speed: 0 }, inp: { gas: 0, steer: 0, brake: false } });
      three.current?.setTrack(r.track); three.current?.lightRing(0);
      G.finish = async ms => {
        G.lastMs = ms; setPhase('done');
        try { const f = await post('/api/reputation/familia-race/finish', { ...who, mode, store, token: G.token, ms, pen: G.pen, splits: G.splits, vehicle: G.veh }); setRes({ ...f, ms, pen: G.pen }); load(); onDone?.(f); }
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
      {hud.pen ? <span className={`sr-pen ${hud.red ? 'is-flash' : ''}`} data-tip="Red lights you ran — 2 s each">🚦 +{(hud.pen / 1000).toFixed(0)}s</span> : null}
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
        <small>{res.error || (res.practice ? 'Sign in (wallet or Telegram) to post times — a family earns MP.' : `${res.place ? `#${res.place} today · ` : ''}${res.pen ? `incl. 🚦 +${res.pen / 1000}s · ` : ''}${res.ms <= res.par ? 'under par' : `par ${fmtMs(res.par)}`}${res.mp ? ` · +${res.mp.toLocaleString('en-US')} MP to the family bank` : ''}`)}</small></div> : null}
      <span className="m-seg sr-vehs" role="radiogroup" aria-label="Vehicle">{Object.entries(VEHICLES).map(([k, x]) => <button key={k} type="button" role="radio" aria-checked={veh === k} className={veh === k ? 'active' : ''} onClick={() => setVeh(k)} data-tip={x.tip} data-testid={`sr-veh-${k}`}>{x.name}</button>)}</span>
      <button type="button" className="m-btn m-go sr-go" onClick={go} data-tip={mode === 'errand' ? 'Drive the delivery: pickup → drop. Under par pays the errand ×1.25' : 'Hit every checkpoint in order. Your first finish today + beating par pay MP to your family'} data-testid="sr-go">{phase === 'done' ? '🔁 RUN IT AGAIN' : mode === 'errand' ? '🚚 START THE DELIVERY' : '🏁 START'}</button>
      {err ? <p className="sr-err">⚠ {err}</p> : null}
      <ol className="sr-board" aria-label="Today's board">{(res?.board || info?.board || []).slice(0, 6).map(r => <li key={r.place} style={{ '--i': r.place }}><i>#{r.place}</i><b>{r.tag ? `[${r.tag}] ` : ''}{r.name || r.who}</b><small>{VEHICLES[r.vehicle]?.name || ''}</small><em className="m-num">{fmtMs(r.ms)}</em></li>)}
        {!(res?.board || info?.board || []).length ? <li className="sr-empty">No times today yet — set the first one.</li> : null}</ol>
      <small className="sr-keys">⌨ arrows / WASD · space brakes · 📱 the pedals · 🚦 stop at red (+2 s if you run it) · MP: first finish {info?.mp?.finish || 120} + under par {info?.mp?.par || 280}</small>
    </div> : null}
  </section>;
}
