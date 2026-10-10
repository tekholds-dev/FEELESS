import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { AGENTS, screensOf, packetsOf, spinSec } from './AgentRoom';

// 🏢 THE AGENT OFFICE IN 3D (owner, 2026-10-09: "3D, no 2D kiddy look, a little realism"). A real WebGL room — PBR materials lit by a
// studio environment + a shadow-casting key light — with four glossy robots at their desks. Nothing on it is decoration-only data:
//   · each robot types at the speed of its REAL work this pass (spinSec of its ms), its antenna is its life (green · amber probation · red scrap)
//   · each monitor is a live canvas of its real output (Tally's 5-min bars · Sherlock's top reasons · Trigger's ENTER scope · Devil's docket)
//   · the glass tube carries this pass's real coins as stamped slips; the wall board = coins read · GO · market green %
//   · the speech bubbles over the robots are HTML (crisp text) = each one's live task, placed by projecting its head every frame
// Click a robot → AgentRoom shows its rules / rulings / record. Own chunk (lazy) — the app bundle never carries three.js.
// The loop stops off-screen, in a hidden tab, while `paused`, in fx-lite and under reduced motion (one still frame per pass there).
const COL = { tally: 0x1fd178, sherlock: 0x9a74ff, trigger: 0xf5b631, devil: 0xff5577 };
const XS = [-4.8, -1.6, 1.6, 4.8];
const LIFE = { alive: 0x45e486, probation: 0xf5c451, scrap: 0xff3355 };

function tex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; t.userData = { c, draw };
  const redraw = (...a) => { const g = c.getContext('2d'); g.clearRect(0, 0, w, h); draw(g, w, h, ...a); t.needsUpdate = true; };
  t.userData.redraw = redraw; return t;
}
const mono = (px, w = 700) => `${w} ${px}px "JetBrains Mono", ui-monospace, monospace`;
const cut = (s, n) => { const t = String(s || ''); return t.length > n ? `${t.slice(0, n - 1)}…` : t; };

function drawScreen(g, w, h, k, s) {
  g.fillStyle = '#03110a'; g.fillRect(0, 0, w, h);
  g.fillStyle = 'rgba(69,228,134,.06)'; for (let y = 0; y < h; y += 6) g.fillRect(0, y, w, 2);
  g.fillStyle = '#45e486'; g.font = mono(30, 800);
  if (k === 'tally') {
    g.fillText(`${s.n} READ`, 22, 46);
    s.bars.forEach((b, i) => { const bh = Math.max(6, Math.min(220, Math.abs(b.v) * 22)); g.fillStyle = b.v >= 0 ? '#45e486' : '#ff6b86'; g.fillRect(24 + i * 47, h - 24 - bh, 32, bh); });
  } else if (k === 'sherlock') {
    g.fillText('WHY IT MOVED', 22, 46); g.font = mono(28, 600); g.fillStyle = '#d8efe2';
    (s.tags.length ? s.tags : [['no clues this pass', '']]).forEach(([t, n], i) => g.fillText(`${cut(t, 20)}${n ? ` ×${n}` : ''}`, 22, 112 + i * 62));
  } else if (k === 'trigger') {
    g.strokeStyle = '#f5c451'; g.lineWidth = 5; g.beginPath(); g.arc(150, 170, 92, 0, Math.PI * 2); g.moveTo(150, 50); g.lineTo(150, 290); g.moveTo(30, 170); g.lineTo(270, 170); g.stroke();
    g.fillStyle = s.enters ? '#45e486' : '#2a3a32'; g.beginPath(); g.arc(150, 170, 16, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#f5c451'; g.font = mono(96, 800); g.fillText(String(s.enters), 310, 190); g.font = mono(28, 700); g.fillText('ENTER', 310, 236); g.fillStyle = '#8fb3a1'; g.fillText(`${s.waits} WAIT`, 310, 280);
  } else {
    g.fillText('DOCKET', 22, 46); g.font = mono(30, 700);
    (s.verdicts.length ? s.verdicts : [{ sym: '', none: true }]).forEach((v, i) => { g.fillStyle = v.none ? '#8fb3a1' : v.ok ? '#45e486' : '#ff8fa3';
      g.fillText(v.none ? 'nothing to argue' : `${v.ok ? (v.go ? '● GO ' : '✓  ') : '✕  '}$${cut(v.sym, 10)}`, 22, 112 + i * 62); });
  }
}
function drawBoard(g, w, h, s, at, rg) {
  const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, '#0a1b14'); grd.addColorStop(1, '#050d09'); g.fillStyle = grd; g.fillRect(0, 0, w, h);
  g.strokeStyle = '#15d16a'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#8fb3a1'; g.font = mono(30, 700); g.fillText(`THE AGENT DESK · ${at ? `pass ${Math.max(0, Math.round(Date.now() / 1000 - at))}s ago` : 'starting'}`, 36, 56);
  const cell = (x, v, l, c) => { g.fillStyle = c; g.font = mono(92, 800); g.fillText(v, x, 170); g.fillStyle = '#6d8d7d'; g.font = mono(24, 700); g.fillText(l, x, 214); };
  cell(40, String(s.n), 'COINS READ', '#e6fff1'); cell(380, String(s.go), 'GO', '#45e486');
  cell(620, rg?.green != null ? `${rg.green}%` : '—', `GREEN · ${String(rg?.word || 'unknown').toUpperCase()}`, rg?.word === 'cold' ? '#7cc7ff' : rg?.word === 'hot' ? '#ff8fa3' : '#e6fff1');
  g.fillStyle = '#ff4d6d'; g.beginPath(); g.arc(w - 40, 44, 12, 0, Math.PI * 2); g.fill();
}
function drawPlate(g, w, h, name, gen, st) {
  g.fillStyle = '#0b1a14'; g.fillRect(0, 0, w, h); g.strokeStyle = st === 'probation' ? '#f5c451' : st === 'scrap' ? '#ff4d6d' : 'rgba(69,228,134,.7)'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#d8efe2'; g.font = mono(40, 800); g.textAlign = 'center'; g.fillText(`${name.toUpperCase()} · GEN ${gen}${st === 'probation' ? ' ⚠' : st === 'scrap' ? ' ☠' : ''}`, w / 2, h / 2 + 14);
}
const SLIP = { go: ['#c9ffe0', '#0a7a3c', '🟢'], obj: ['#ffd9e0', '#a8263f', '✕'], wait: ['#fff1c9', '#8a6510', '⏳'], skip: ['#e6e6e6', '#555', '⛔'] };
function drawSlip(g, w, h, p) { const [bg, fg, ic] = SLIP[p.end] || SLIP.wait; g.fillStyle = bg; g.fillRect(0, 0, w, h); g.fillStyle = fg; g.font = mono(44, 800); g.textAlign = 'center'; g.fillText(`${ic} $${cut(p.sym, 8)}`, w / 2, h / 2 + 16); }
function drawCity(g, w, h) {
  const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, '#120d3a'); grd.addColorStop(.7, '#5a2c6e'); grd.addColorStop(1, '#ff8a5c'); g.fillStyle = grd; g.fillRect(0, 0, w, h);
  let x = 0; let seed = 7; const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  while (x < w) { const bw = 30 + rnd() * 60, bh = 80 + rnd() * 220; g.fillStyle = '#080a1c'; g.fillRect(x, h - bh, bw, bh);
    g.fillStyle = 'rgba(255,214,120,.8)'; for (let yy = h - bh + 10; yy < h - 10; yy += 18) for (let xx = x + 6; xx < x + bw - 8; xx += 14) if (rnd() > .62) g.fillRect(xx, yy, 5, 7); x += bw + 4; }
}

function makeRobot(k) {
  const g = new THREE.Group(); const col = new THREE.Color(COL[k]);
  const shell = new THREE.MeshPhysicalMaterial({ color: col, metalness: 0.45, roughness: 0.38, clearcoat: 0.8, clearcoatRoughness: 0.32 });
  const steel = new THREE.MeshStandardMaterial({ color: 0x9aa6b2, metalness: 0.9, roughness: 0.3 });
  const dark = new THREE.MeshPhysicalMaterial({ color: 0x05080c, metalness: 0.2, roughness: 0.08, clearcoat: 1 });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: new THREE.Color(k === 'devil' ? 0xffa0b4 : k === 'sherlock' ? 0xd6c4ff : 0x8dffc2), emissiveIntensity: 2.4 });
  const antM = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: new THREE.Color(LIFE.alive), emissiveIntensity: 2 });
  const add = (geo, m, x, y, z, cast = true) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = cast; o.receiveShadow = true; g.add(o); return o; };
  add(new THREE.CapsuleGeometry(0.42, 0.42, 8, 24), shell, 0, 1.28, 0);                                     // torso
  add(new THREE.CylinderGeometry(0.2, 0.2, 0.06, 32), dark, 0, 1.38, 0.41).rotation.x = Math.PI / 2;       // chest plate
  const chest = add(new THREE.SphereGeometry(0.06, 16, 16), antM.clone(), 0, 1.38, 0.45, false);
  add(new THREE.CylinderGeometry(0.12, 0.14, 0.18, 20), steel, 0, 1.86, 0);                                  // neck
  const head = new THREE.Group(); head.position.set(0, 2.2, 0); g.add(head);
  const hadd = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; head.add(o); return o; };
  const skull = hadd(new THREE.SphereGeometry(0.42, 40, 32), shell, 0, 0, 0); skull.scale.set(1.18, 0.92, 1);
  const visor = hadd(new THREE.SphereGeometry(0.4, 40, 24, -Math.PI * 0.42, Math.PI * 0.84, Math.PI * 0.3, Math.PI * 0.36), dark, 0, 0.02, 0.05); visor.scale.set(1.2, 1, 1);
  const eyes = [-0.15, 0.15].map(x => hadd(new THREE.SphereGeometry(0.07, 20, 16), eyeM, x, 0.03, 0.43));
  [-0.5, 0.5].map(x => hadd(new THREE.CylinderGeometry(0.1, 0.1, 0.08, 24), steel, x, 0, 0)).forEach(o => { o.rotation.z = Math.PI / 2; });   // ear bolts
  hadd(new THREE.CylinderGeometry(0.02, 0.02, 0.3, 8), steel, 0, 0.5, 0);
  const ant = hadd(new THREE.SphereGeometry(0.07, 20, 16), antM, 0, 0.68, 0);
  if (k === 'sherlock') { const hm = new THREE.MeshStandardMaterial({ color: 0x6b4f2a, roughness: 0.85 });
    hadd(new THREE.CylinderGeometry(0.62, 0.62, 0.04, 40), hm, 0, 0.3, 0); hadd(new THREE.SphereGeometry(0.42, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), hm, 0, 0.3, 0).scale.set(1.15, 0.7, 1); }
  if (k === 'devil') { const hm = new THREE.MeshPhysicalMaterial({ color: 0xffd2db, roughness: 0.3, clearcoat: 1 });
    [-0.3, 0.3].forEach(x => { const c = hadd(new THREE.ConeGeometry(0.08, 0.32, 20), hm, x, 0.42, 0); c.rotation.z = -x * 0.9; }); }
  if (k === 'trigger') { const t = hadd(new THREE.TorusGeometry(0.5, 0.035, 12, 40, Math.PI), new THREE.MeshStandardMaterial({ color: 0x1b1b1b, roughness: 0.4, metalness: 0.5 }), 0, 0.05, 0); t.scale.set(1.04, 1, 1);
    hadd(new THREE.SphereGeometry(0.05, 12, 12), eyeM, 0.42, -0.2, 0.28); }
  if (k === 'tally') { const gm = new THREE.MeshStandardMaterial({ color: 0xe6fff1, metalness: 0.9, roughness: 0.2 });
    [-0.15, 0.15].forEach(x => hadd(new THREE.TorusGeometry(0.11, 0.015, 8, 28), gm, x, 0.03, 0.46)); }
  const arm = side => { const p = new THREE.Group(); p.position.set(side * 0.55, 1.58, 0); g.add(p);
    const a = new THREE.Mesh(new THREE.CapsuleGeometry(0.11, 0.5, 6, 16), shell); a.position.y = -0.33; a.castShadow = true; p.add(a);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), steel); hand.position.y = -0.68; hand.castShadow = true; p.add(hand);
    if (k === 'sherlock' && side > 0) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.13, 0.025, 8, 28), new THREE.MeshStandardMaterial({ color: 0x3d2b14 })); r.position.set(0, -0.86, 0.1); p.add(r); }
    if (k === 'devil' && side > 0) { const gv = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.14, 0.14), new THREE.MeshStandardMaterial({ color: 0x6b4f2a, roughness: 0.6 })); gv.position.set(0, -0.84, 0.05); p.add(gv); }
    return p; };
  const armL = arm(-1), armR = arm(1);
  g.traverse(o => { o.userData.k = k; });
  return { g, head, eyes, ant, antM, chest, armL, armR, shell, eyeM };
}

export default function AgentOffice3D({ d, sel, setSel, paused }) {
  const box = useRef(null); const api = useRef(null); const dRef = useRef(d); const selRef = useRef(sel); const pausedRef = useRef(paused);
  dRef.current = d; selRef.current = sel; pausedRef.current = paused;

  useEffect(() => {
    const host = box.current; if (!host) return undefined;
    const W = () => host.clientWidth || 1000, H = () => host.clientHeight || Math.round((host.clientWidth || 1000) * 0.46);   // the box decides (inline 1000:460, pop-out taller)
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); renderer.setSize(W(), H());
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.prepend(renderer.domElement); renderer.domElement.className = 'agr3-canvas';
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0x070d14); scene.fog = new THREE.Fog(0x070d14, 18, 34);
    const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.45;
    const cam = new THREE.PerspectiveCamera(30, W() / H(), 0.1, 80); cam.position.set(0, 3.9, 11.4); const look = new THREE.Vector3(0, 2.05, 0); cam.lookAt(look);

    scene.add(new THREE.HemisphereLight(0x9fd8ff, 0x0b1520, 0.35));
    const key = new THREE.DirectionalLight(0xfff2e0, 2.2); key.position.set(5, 9, 7); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
    Object.assign(key.shadow.camera, { left: -9, right: 9, top: 7, bottom: -3, near: 1, far: 30 }); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.03; key.shadow.radius = 4; scene.add(key);
    const rim = new THREE.DirectionalLight(0x6fd8ff, 0.9); rim.position.set(-6, 5, -6); scene.add(rim);

    const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 20), new THREE.MeshStandardMaterial({ color: 0x0f1c26, roughness: 0.22, metalness: 0.5 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    const grid = new THREE.GridHelper(40, 40, 0x1d3a48, 0x13262f); grid.position.y = 0.002; grid.material.transparent = true; grid.material.opacity = 0.35; scene.add(grid);
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(40, 12), new THREE.MeshStandardMaterial({ color: 0x122431, roughness: 0.85 })); wall.position.set(0, 6, -3.2); wall.receiveShadow = true; scene.add(wall);
    const trim = new THREE.Mesh(new THREE.BoxGeometry(40, 0.08, 0.1), new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0x15d16a, emissiveIntensity: 1.6 })); trim.position.set(0, 0.3, -3.12); scene.add(trim);
    const city = tex(1024, 512, drawCity); city.userData.redraw();
    [-6.2, 6.2].forEach(x => { const w = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 2.6), new THREE.MeshBasicMaterial({ map: city, toneMapped: false })); w.position.set(x, 3.9, -3.18); scene.add(w);
      const fr = new THREE.Mesh(new THREE.BoxGeometry(4.4, 2.8, 0.06), new THREE.MeshStandardMaterial({ color: 0x2b4256, metalness: 0.7, roughness: 0.35 })); fr.position.set(x, 3.9, -3.22); scene.add(fr);
      [[0, 0, 0.06, 2.6], [0, 0, 4.2, 0.06]].forEach(([, , bw, bh]) => { const b = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, 0.05), fr.material); b.position.set(x, 3.9, -3.14); scene.add(b); }); });
    const board = tex(1024, 256, drawBoard);
    const boardM = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 1.3), new THREE.MeshStandardMaterial({ map: board, emissiveMap: board, emissive: 0xffffff, emissiveIntensity: 0.9, roughness: 0.4 })); boardM.position.set(0, 4.55, -3.15); scene.add(boardM);
    // plant
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.25, 0.6, 24), new THREE.MeshStandardMaterial({ color: 0x7a4a2a, roughness: 0.7 })); pot.position.set(-7.2, 0.3, -1.6); pot.castShadow = true; scene.add(pot);
    const leafM = new THREE.MeshStandardMaterial({ color: 0x2fa865, roughness: 0.6 });
    for (let i = 0; i < 7; i++) { const l = new THREE.Mesh(new THREE.ConeGeometry(0.12, 1.2, 8), leafM); l.position.set(-7.2, 1.1, -1.6); l.rotation.set(Math.sin(i * 2.1) * 0.5, i, Math.cos(i * 1.7) * 0.5); l.castShadow = true; scene.add(l); }
    // the tube
    const glass = new THREE.MeshPhysicalMaterial({ color: 0xbfe8ff, metalness: 0, roughness: 0.05, transparent: true, opacity: 0.18, clearcoat: 1, depthWrite: false });
    const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 15, 32, 1, true), glass); tube.rotation.z = Math.PI / 2; tube.position.set(0, 3.25, -1.4); scene.add(tube);
    const ringM = new THREE.MeshStandardMaterial({ color: 0x9aa6b2, metalness: 0.9, roughness: 0.3 });
    for (let x = -7; x <= 7; x += 1.75) { const r = new THREE.Mesh(new THREE.TorusGeometry(0.27, 0.035, 8, 24), ringM); r.rotation.y = Math.PI / 2; r.position.set(x, 3.25, -1.4); scene.add(r); }
    const tray = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.35, 0.6), new THREE.MeshStandardMaterial({ color: 0x15d16a, emissive: 0x15d16a, emissiveIntensity: 0.4, metalness: 0.3, roughness: 0.4 })); tray.position.set(7.6, 2.9, -1.4); scene.add(tray);

    // desks + robots
    const wood = new THREE.MeshStandardMaterial({ color: 0x6e4426, roughness: 0.55, metalness: 0.05 });
    const darkM = new THREE.MeshStandardMaterial({ color: 0x1c2632, roughness: 0.5, metalness: 0.6 });
    const bots = AGENTS.map(([k, , name], i) => {
      const x = XS[i];
      const top = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.1, 1.2), wood); top.position.set(x, 1.0, 0.6); top.castShadow = top.receiveShadow = true; scene.add(top);
      const front = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.9, 0.06), wood); front.position.set(x, 0.5, 1.17); front.castShadow = true; scene.add(front);
      [-1.15, 1.15].forEach(dx => { const s = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.95, 1.1), wood); s.position.set(x + dx, 0.48, 0.6); s.castShadow = true; scene.add(s); });
      const plate = tex(512, 96, drawPlate); const pl = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.28), new THREE.MeshStandardMaterial({ map: plate, emissiveMap: plate, emissive: 0xffffff, emissiveIntensity: 0.6 })); pl.position.set(x, 0.6, 1.21); scene.add(pl);
      const kb = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.04, 0.28), darkM); kb.position.set(x - 0.1, 1.07, 0.75); scene.add(kb);
      const mon = new THREE.Group(); mon.position.set(x + 0.75, 1.05, 0.45); mon.rotation.y = -0.35; scene.add(mon);
      const bez = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.66, 0.06), darkM); bez.position.y = 0.62; bez.castShadow = true; mon.add(bez);
      const scr = tex(512, 320, drawScreen); const sm = new THREE.Mesh(new THREE.PlaneGeometry(0.92, 0.58), new THREE.MeshBasicMaterial({ map: scr, toneMapped: false })); sm.position.set(0, 0.62, 0.032); mon.add(sm);
      const st = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.3, 12), darkM); st.position.y = 0.15; mon.add(st);
      const glow = new THREE.PointLight(COL[k], 1.4, 3.2, 2); glow.position.set(x + 0.6, 1.7, 0.9); scene.add(glow);
      const chair = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.4, 0.16), new THREE.MeshStandardMaterial({ color: 0x22303d, roughness: 0.7 })); chair.position.set(x, 1.3, -0.55); chair.castShadow = true; scene.add(chair);
      const r = makeRobot(k); r.g.position.set(x - 0.15, 0, -0.15); scene.add(r.g);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.85, 0.03, 8, 64), new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0x45e486, emissiveIntensity: 2 }));
      ring.rotation.x = -Math.PI / 2; ring.position.set(x - 0.15, 0.02, -0.15); ring.visible = false; scene.add(ring);
      return { k, name, i, r, scr, plate, ring, bub: null };
    });

    // slips (one canvas each, rebuilt per pass)
    const slipGeo = new THREE.PlaneGeometry(0.7, 0.22); let slips = [];
    const buildSlips = pk => { slips.forEach(s => { scene.remove(s.m); s.t.dispose(); s.m.material.dispose(); });
      slips = pk.map((p, i) => { const t = tex(256, 80, drawSlip); t.userData.redraw(p); const m = new THREE.Mesh(slipGeo, new THREE.MeshBasicMaterial({ map: t, transparent: true, side: THREE.DoubleSide }));
        m.position.set(-7, 3.25, -1.4); scene.add(m); return { m, t, i, end: p.end }; }); };

    // speech bubbles (HTML over the canvas; text stays sharp)
    const bubWrap = host.querySelector('.agr3-bubs'); bots.forEach(b => { b.bub = bubWrap?.children[b.i]; });

    const apply = () => {
      const dd = dRef.current; const s = screensOf(dd);
      board.userData.redraw(s, dd?.perf?.at || 0, dd?.perf?.regime);
      bots.forEach(b => { const l = dd?.life?.[b.k] || {}; const st = l.status || 'alive';
        b.scr.userData.redraw(b.k, s); b.plate.userData.redraw(b.name, l.gen || 1, st);
        b.r.antM.emissive.setHex(LIFE[st] || LIFE.alive); b.st = st; b.spin = spinSec(dd?.perf?.[b.k]); });
      buildSlips(packetsOf(dd?.table));
    };
    apply();

    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let hover = null; const par = { x: 0, y: 0 };
    const pick = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam); const hit = ray.intersectObjects(bots.map(b => b.r.g), true)[0]; return hit ? hit.object.userData.k : null; };
    const onMove = e => { hover = pick(e); renderer.domElement.style.cursor = hover ? 'pointer' : 'default';
      const rc = renderer.domElement.getBoundingClientRect(); par.x = ((e.clientX - rc.left) / rc.width - 0.5); par.y = ((e.clientY - rc.top) / rc.height - 0.5); };
    const onClick = e => { const k = pick(e); if (k) setSel(k); };
    renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('click', onClick);

    const still = () => document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let seen = true; const io = new IntersectionObserver(es => { seen = es[0]?.isIntersecting ?? true; }); io.observe(host);
    const v = new THREE.Vector3(); const clock = new THREE.Clock(); let raf = 0; let last = 0;
    const frame = (moving) => {
      const t = clock.getElapsedTime();
      cam.position.x += ((moving ? par.x * 1.4 : 0) - cam.position.x) * 0.05; cam.position.y += ((moving ? 3.9 - par.y * 0.5 : 3.9) - cam.position.y) * 0.05; cam.lookAt(look);
      bots.forEach(b => { const { r } = b; const sp = (Math.PI * 2) / (b.spin || 3);
        if (moving) {
          r.g.position.y = Math.sin(t * 1.6 + b.i) * 0.025;
          r.head.rotation.y = 0.32 + Math.sin(t * 0.45 + b.i * 1.3) * 0.28; r.head.rotation.x = -0.12 + Math.sin(t * 0.7 + b.i) * 0.05;
          r.armL.rotation.x = -1.05 + Math.sin(t * sp * 2) * 0.16; r.armR.rotation.x = -1.05 + Math.sin(t * sp * 2 + Math.PI) * 0.16;
          const blink = ((t + b.i * 1.1) % 4.3) < 0.13 ? 0.12 : 1; r.eyes.forEach(e => { e.scale.y = blink; });
          r.antM.emissiveIntensity = 1.4 + Math.sin(t * (b.st === 'scrap' ? 14 : 3)) * 0.9;
          r.eyeM.emissiveIntensity = b.st === 'scrap' ? (Math.sin(t * 23) > 0 ? 2.4 : 0.2) : 2.4;
        } else { r.armL.rotation.x = r.armR.rotation.x = -1.05; r.head.rotation.y = 0.32; }
        const isSel = selRef.current === b.k; b.ring.visible = isSel; if (isSel) b.ring.material.emissiveIntensity = 1.4 + Math.sin(t * 3) * 0.8;
        r.shell.emissive.setHex(hover === b.k ? 0x123322 : 0x000000);
        if (b.bub) { v.set(r.g.position.x, 3.25, r.g.position.z); v.project(cam); const W_ = renderer.domElement.clientWidth, H_ = renderer.domElement.clientHeight;
          b.bub.style.transform = `translate(${(v.x * 0.5 + 0.5) * W_}px, ${(-v.y * 0.5 + 0.5) * H_}px) translate(-50%, -100%)`; } });
      slips.forEach(s => { const span = 15, dur = 9; const p = moving ? (((t + s.i * (dur / Math.max(1, slips.length))) % dur) / dur) : (s.i + 0.5) / Math.max(1, slips.length);
        s.m.position.x = -7.4 + p * span; s.m.rotation.y = moving ? Math.sin(t * 2 + s.i) * 0.3 : 0; s.m.position.y = 3.25 + (moving ? Math.sin(t * 3 + s.i) * 0.04 : 0);
        s.m.material.opacity = p < 0.04 ? p / 0.04 : p > 0.95 ? (1 - p) / 0.05 : 1; s.m.visible = moving || s.end === 'go'; });
      renderer.render(scene, cam);
    };
    const loop = now => { raf = requestAnimationFrame(loop);
      if (!seen || pausedRef.current) return;
      if (document.hidden || still()) { if (now - last > (document.hidden ? 2000 : 1000)) { last = now; frame(false); } return; }   // a still frame — never a blank office
      frame(true); };
    raf = requestAnimationFrame(loop);
    const onResize = () => { renderer.setSize(W(), H()); cam.aspect = W() / H(); cam.updateProjectionMatrix(); };
    const ro = new ResizeObserver(onResize); ro.observe(host);
    api.current = { apply };
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('click', onClick);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); const m = o.material; (Array.isArray(m) ? m : m ? [m] : []).forEach(mm => { if (mm.map) mm.map.dispose(); mm.dispose(); }); });
      slips.forEach(s => s.t.dispose()); pm.dispose(); renderer.dispose(); renderer.domElement.remove(); api.current = null; };
  }, [setSel]);

  useEffect(() => { api.current?.apply(); }, [d]);   // a new pass → redraw monitors, board, plates, slips

  return <div className="agr3" ref={box} data-testid="agr-3d">
    <div className="agr3-bubs" aria-hidden>{AGENTS.map(([k]) => <span key={k} className={`agr3-bub is-${k}`}>{cut((d?.tasks?.[k] || 'waiting for the first pass').split(' · ')[0], 34)}</span>)}</div>
  </div>;
}
