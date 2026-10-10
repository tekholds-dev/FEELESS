import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { AG, candleGeom } from './OfficeRoom';

// 🏢 THE CONTROL ROOM in real 3D (three.js, own lazy chunk — the same renderer set-up as the first office, rebuilt dark and for TEN desks).
// It draws ONLY the room model (`roomModel(o)` in OfficeRoom.jsx): ten stations in chain order, each with its bot, a monitor showing
// that desk's action word + its line for this pass, a floor ring in the colour of its state; the chain as a lit floor line with the
// candidate travelling up to the desk it stands at; and the WALL MONITOR — the current coin, its stage, structure, decision, Warden,
// Devil, next review and the SAME candles the agents read with their levels. Nothing in here invents a value: no model → nothing drawn.
const STATE_HEX = { 'is-pass': 0x45e486, 'is-wait': 0x4d6a5c, 'is-work': 0x6cc7ff, 'is-obj': 0xf5c451, 'is-veto': 0xff4466 };
const STATE_CSS = { 'is-pass': '#45e486', 'is-wait': '#7d998b', 'is-work': '#6cc7ff', 'is-obj': '#f5c451', 'is-veto': '#ff6b86' };
const XS = [-6.4, -3.2, 0, 3.2, 6.4];
export const DESK_AT = i => [XS[i % 5], i < 5 ? -1.7 : 2.3];
const mono = (px, w = 700) => `${w} ${px}px "JetBrains Mono", ui-monospace, monospace`;
const cut = (s, n) => { const t = String(s ?? ''); return t.length > n ? `${t.slice(0, n - 1)}…` : t; };
const mmss = s => { const v = Math.max(0, Math.round(s)); return `${String(Math.floor(v / 60)).padStart(2, '0')}:${String(v % 60).padStart(2, '0')}`; };

function tex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  t.userData.redraw = (...a) => { const g = c.getContext('2d'); g.clearRect(0, 0, w, h); draw(g, w, h, ...a); t.needsUpdate = true; }; return t;
}
function drawDesk(g, w, h, s) {
  g.fillStyle = '#04100b'; g.fillRect(0, 0, w, h); const c = STATE_CSS[s.cls] || '#7d998b';
  g.fillStyle = c; g.fillRect(0, 0, w, 10); g.font = mono(46, 800); g.fillText(cut(s.tag, 11), 14, 66);
  g.fillStyle = '#cfe9db'; g.font = mono(24, 600); const words = cut(s.line, 54).split(' '); let line = ''; let y = 106;
  words.forEach(wd => { if ((`${line} ${wd}`).length > 19 && line) { g.fillText(line, 14, y); y += 30; line = wd; } else line = line ? `${line} ${wd}` : wd; }); if (y < h - 4) g.fillText(line, 14, y);
}
function drawSign(g, w, h) {
  g.fillStyle = '#04140d'; g.fillRect(0, 0, w, h); g.strokeStyle = '#15d16a'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#45e486'; g.shadowColor = '#45e486'; g.shadowBlur = 18; g.font = mono(78, 800); g.fillText('FEELESS HQ', 28, 110); g.shadowBlur = 0; g.fillStyle = '#b6f5d0'; g.font = mono(36, 700); g.fillText('AGENT OFFICE', 30, 170);
}
function drawStatus(g, w, h, st) {
  g.fillStyle = '#03101a'; g.fillRect(0, 0, w, h); g.strokeStyle = '#4fd8ff'; g.lineWidth = 5; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#8fb9c9'; g.font = mono(26, 700); g.fillText('PIPELINE STATUS', 22, 44);
  (st || []).forEach(([n, l, c], i) => { g.fillStyle = c; g.beginPath(); g.arc(34, 82 + i * 40, 8, 0, 7); g.fill(); g.fillStyle = '#e6fff0'; g.font = mono(30, 800); g.fillText(String(n), 56, 93 + i * 40); g.fillStyle = '#8fb9c9'; g.font = mono(22, 600); g.fillText(l, 130, 91 + i * 40); });
}
// the wall monitor: every word is a field of the room model; the chart is `candleGeom` of the SAME rows the agents read
function drawWall(g, w, h, wall, now) {
  g.fillStyle = '#020b10'; g.fillRect(0, 0, w, h); g.strokeStyle = '#4fd8ff'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  if (!wall) { g.fillStyle = '#7d998b'; g.font = mono(34, 700); g.fillText('NO CANDIDATE AND NO OPEN POSITION THIS PASS', 40, h / 2); return; }
  g.fillStyle = '#8fb9c9'; g.font = mono(22, 700); g.fillText(wall.kind === 'position' ? 'OPEN POSITION' : 'CURRENT CANDIDATE', 28, 40);
  g.fillStyle = '#ffffff'; g.font = mono(64, 800); g.fillText(`$${cut(wall.symbol, 9)}`, 26, 104);
  if (wall.move != null) { g.fillStyle = wall.move >= 0 ? '#45e486' : '#ff6b86'; g.font = mono(34, 800); g.fillText(`${wall.move >= 0 ? '+' : ''}${wall.move.toFixed(1)}%`, 28, 146); g.fillStyle = '#7d998b'; g.font = mono(18, 600); g.fillText(wall.kind === 'position' ? 'since entry' : 'in 5 min', 170, 144); }
  const rows = [['CURRENT STAGE', wall.stage], ['STRUCTURE', wall.structure], ['DECISION', wall.decision], ['WARDEN', wall.warden], ['DEVIL', wall.devil], ['NEXT REVIEW', wall.reviewAt != null ? mmss(wall.reviewAt - now) : '—']];
  rows.forEach(([k, v], i) => { const y = 190 + i * 50; g.fillStyle = '#7d998b'; g.font = mono(17, 700); g.fillText(k, 28, y); g.fillStyle = k === 'DEVIL' && v === 'OBJECT' ? '#ff6b86' : k === 'DECISION' ? '#f5c451' : '#e6fff0'; g.font = mono(26, 800); g.fillText(cut(v || '—', 21), 28, y + 26); });
  const X = 380, Y = 28, CW = w - X - 26, CH = h - 84; g.fillStyle = '#01060a'; g.fillRect(X, Y, CW, CH);
  const geo = candleGeom(wall.bars?.rows, wall.levels, CW, CH, 10);
  if (!geo) { g.fillStyle = '#7d998b'; g.font = mono(26, 700); g.fillText('NO CANDLE DATA FOR THIS COIN THIS PASS', X + 30, Y + CH / 2); }
  else {
    geo.lines.forEach(l => { const c = l.cls === 'is-take' ? '#45e486' : l.cls === 'is-stop' ? '#ff6b86' : l.cls === 'is-sup' ? '#4fd8ff' : '#ffffff'; g.strokeStyle = c; g.setLineDash([10, 7]); g.lineWidth = 2; g.beginPath(); g.moveTo(X, Y + l.y); g.lineTo(X + CW - 54, Y + l.y); g.stroke();
      g.setLineDash([]); g.fillStyle = c; g.font = mono(17, 700); g.fillText(l.label.toUpperCase(), X + CW - 150, Y + l.y - 5); });
    if (wall.bars.src === 'tape') { g.strokeStyle = '#45e486'; g.lineWidth = 3; g.beginPath(); geo.bars.forEach((b, i) => (i ? g.lineTo(X + b.x, Y + b.c) : g.moveTo(X + b.x, Y + b.c))); g.stroke(); }
    else geo.bars.forEach(b => { g.strokeStyle = g.fillStyle = b.up ? '#45e486' : '#ff6b86'; g.lineWidth = 2; g.beginPath(); g.moveTo(X + b.x, Y + b.h); g.lineTo(X + b.x, Y + b.l); g.stroke(); g.fillRect(X + b.x - b.bw / 2, Y + Math.min(b.o, b.c), b.bw, Math.max(2, Math.abs(b.c - b.o))); });
    geo.off.forEach((l, i) => { g.fillStyle = l.cls === 'is-take' ? '#45e486' : l.cls === 'is-stop' ? '#ff6b86' : '#8fb9c9'; g.font = mono(16, 700); g.fillText(`${l.up ? '↑' : '↓'} ${l.label.toUpperCase()}`, X + 8 + geo.off.filter((x, j) => j < i && x.up === l.up).length * 190, l.up ? Y + 20 : Y + CH - 8); });
    const ly = Y + geo.y(geo.last); g.strokeStyle = '#f5c451'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X, ly); g.lineTo(X + CW - 54, ly); g.stroke(); g.fillStyle = '#f5c451'; g.font = mono(17, 800); g.fillText('NOW', X + CW - 50, ly + 6);
  }
  g.fillStyle = '#7d998b'; g.font = mono(18, 600); g.fillText(cut(wall.caption, 78), X, h - 22);
}

function makeBot(k) {
  const g = new THREE.Group(); const white = new THREE.MeshPhysicalMaterial({ color: 0xf2f6f8, roughness: 0.32, clearcoat: 0.7, clearcoatRoughness: 0.25 });
  const band = new THREE.MeshStandardMaterial({ color: AG[k], roughness: 0.4, emissive: AG[k], emissiveIntensity: 0.35 }); const dark = new THREE.MeshPhysicalMaterial({ color: 0x0b1118, roughness: 0.1, clearcoat: 1 });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0, emissive: AG[k], emissiveIntensity: 2.4 });
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const body = new THREE.Group(); g.add(body);
  add(new THREE.CapsuleGeometry(0.26, 0.22, 8, 20), white, 0, 0.42, 0, body);
  add(new THREE.TorusGeometry(0.265, 0.035, 8, 32), band, 0, 0.44, 0, body).rotation.x = Math.PI / 2;
  const head = new THREE.Group(); head.position.y = 0.92; body.add(head);
  add(new THREE.SphereGeometry(0.24, 28, 20), white, 0, 0, 0, head).scale.set(1.15, 0.9, 1);
  add(new THREE.SphereGeometry(0.22, 28, 14, -Math.PI * 0.4, Math.PI * 0.8, Math.PI * 0.3, Math.PI * 0.38), dark, 0, 0.01, 0.04, head).scale.set(1.18, 1, 1);
  const eyes = [-0.08, 0.08].map(x => add(new THREE.SphereGeometry(0.035, 10, 10), eyeM, x, 0.02, 0.25, head));
  add(new THREE.CylinderGeometry(0.012, 0.012, 0.16, 6), dark, 0, 0.26, 0, head); add(new THREE.SphereGeometry(0.045, 10, 10), eyeM, 0, 0.36, 0, head);
  if (k === 'sherlock') add(new THREE.CylinderGeometry(0.3, 0.3, 0.025, 28), band, 0, 0.16, 0, head);
  if (k === 'devil') [-0.15, 0.15].forEach(x => { add(new THREE.ConeGeometry(0.04, 0.16, 10), band, x, 0.22, 0, head).rotation.z = -x * 2; });
  if (k === 'trigger' || k === 'courier') add(new THREE.TorusGeometry(0.28, 0.018, 8, 28, Math.PI), band, 0, 0.02, 0, head);
  if (k === 'judge') add(new THREE.ConeGeometry(0.13, 0.16, 5), band, 0, 0.3, 0, head);
  if (k === 'warden') add(new THREE.BoxGeometry(0.34, 0.3, 0.04), band, 0, 0.5, 0.27, body);
  if (k === 'reaper') add(new THREE.ConeGeometry(0.27, 0.3, 20, 1, true), band, 0, 0.2, -0.02, head);
  const arms = [-1, 1].map(sd => { const p = new THREE.Group(); p.position.set(sd * 0.3, 0.6, 0); body.add(p); add(new THREE.CapsuleGeometry(0.05, 0.22, 4, 10), white, 0, -0.15, 0, p); return p; });
  add(new THREE.SphereGeometry(0.16, 16, 12), dark, 0, 0.12, 0).scale.y = 0.7;
  g.traverse(o => { o.userData.k = k; });
  return { g, body, head, eyes, arms, white };
}

export default function OfficeRoom3D({ model, onSel, cam: camMode = 'main', rotate = false }) {
  const box = useRef(null); const api = useRef(null); const mRef = useRef(model); const camRef = useRef(camMode); const rotRef = useRef(rotate);
  mRef.current = model; camRef.current = camMode; rotRef.current = rotate;
  const onSelRef = useRef(onSel); onSelRef.current = onSel;

  useEffect(() => {
    const host = box.current; if (!host) return undefined;
    const W = () => host.clientWidth || 900, H = () => host.clientHeight || 480;
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); renderer.setSize(W(), H());
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.95;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.prepend(renderer.domElement); renderer.domElement.className = 'or3-canvas';
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0x04100c); scene.fog = new THREE.Fog(0x04100c, 22, 40);
    const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.22;
    const fovFor = a => Math.max(26, Math.min(52, (2 * Math.atan(Math.tan((59 * Math.PI) / 360) / a) * 180) / Math.PI));   // the whole wall + all five columns stay in frame at any width
    const cam = new THREE.PerspectiveCamera(fovFor(W() / H()), W() / H(), 0.1, 80); const pos = new THREE.Vector3(0, 7.9, 13.6); const look = new THREE.Vector3(0, 2.0, -1.4); cam.position.copy(pos); cam.lookAt(look);
    scene.add(new THREE.HemisphereLight(0xbfffe0, 0x08140f, 0.55));
    const key = new THREE.DirectionalLight(0xffffff, 1.5); key.position.set(-4, 11, 8); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
    Object.assign(key.shadow.camera, { left: -9, right: 9, top: 7, bottom: -7, near: 1, far: 30 }); key.shadow.normalBias = 0.03; scene.add(key);
    const M = (c, r = 0.5, m = 0) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
    const E = (c, i = 1.4) => new THREE.MeshStandardMaterial({ color: 0, emissive: c, emissiveIntensity: i });
    const box3 = (w, h, dd, mat, x, y, z, cast = true) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, dd), mat); o.position.set(x, y, z); o.castShadow = cast; o.receiveShadow = true; scene.add(o); return o; };
    const plane = (w, h, t, x, y, z) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: t, toneMapped: false })); m.position.set(x, y, z); scene.add(m); return m; };
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(34, 22), new THREE.MeshStandardMaterial({ color: 0x07140f, roughness: 0.22, metalness: 0.35 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    const grid = new THREE.GridHelper(34, 34, 0x15d16a, 0x0f3a27); grid.position.y = 0.004; grid.material.transparent = true; grid.material.opacity = 0.45; scene.add(grid);
    box3(22, 5.9, 0.2, M(0x0a1a14, 0.8), 0, 2.95, -4.2); box3(22, 0.07, 0.05, E(0x15d16a, 1.6), 0, 0.2, -4.08, false); box3(22, 0.07, 0.05, E(0x4fd8ff, 1.2), 0, 5.75, -4.08, false);
    [-10.9, 10.9].forEach(x => { box3(0.2, 5.9, 12, M(0x081711, 0.85), x, 2.95, 1.6); });
    // wall: sign · the monitor · status
    const sign = tex(640, 220, drawSign); sign.userData.redraw(); plane(3.4, 1.17, sign, -8.1, 3.6, -4.07);
    const wallT = tex(1024, 512, drawWall); box3(10.2, 5.1, 0.1, M(0x0b1118, 0.3, 0.4), 0, 2.95, -4.1); plane(10.0, 5.0, wallT, 0, 2.95, -4.03);
    const statT = tex(512, 256, drawStatus); plane(3.4, 1.7, statT, 8.1, 3.4, -4.07);

    const deskM = M(0x14241d, 0.35, 0.3); const legM = M(0x2a3d34, 0.3, 0.7);
    const st = (mRef.current?.stations || []).map((s0, i) => { const [x, z] = DESK_AT(i); const k = s0.key;
      box3(1.7, 0.06, 0.8, deskM, x, 0.78, z); box3(1.7, 0.02, 0.04, E(AG[k], 1.2), x, 0.76, z + 0.4, false);
      [[-0.76, -0.32], [0.76, -0.32], [-0.76, 0.32], [0.76, 0.32]].forEach(([a, b]) => box3(0.05, 0.76, 0.05, legM, x + a, 0.38, z + b));
      const scr = tex(256, 160, drawDesk); box3(0.92, 0.6, 0.04, M(0x0b1118, 0.4), x, 1.17, z - 0.25); plane(0.86, 0.54, scr, x, 1.17, z - 0.226); box3(0.06, 0.3, 0.06, legM, x, 0.92, z - 0.25);
      const b = makeBot(k); b.g.position.set(x, 0, z + 0.78); b.g.rotation.y = Math.PI; scene.add(b.g);
      const ringM = E(0x4d6a5c, 1.6); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.035, 8, 48), ringM); ring.rotation.x = -Math.PI / 2; ring.position.set(x, 0.02, z + 0.78); scene.add(ring);
      const selR = new THREE.Mesh(new THREE.TorusGeometry(0.86, 0.022, 8, 56), E(0xffffff, 2.2)); selR.rotation.x = -Math.PI / 2; selR.position.set(x, 0.03, z + 0.78); selR.visible = false; scene.add(selR);
      return { k, i, x, z, b, scr, ringM, ring, selR, cls: 'is-wait', lab: null }; });
    // the chain on the floor: one segment per hand-over, lit up to the desk the candidate stands at; a pulse travels that far
    const P = i => new THREE.Vector3(DESK_AT(i)[0], 0.03, DESK_AT(i)[1] + 0.78);
    const segs = Array.from({ length: 9 }, (_, i) => { const a = P(i), b = P(i + 1); const len = a.distanceTo(b); const m = E(0x15d16a, 0.5); const o = new THREE.Mesh(new THREE.BoxGeometry(len - 1.5, 0.02, 0.07), m);
      o.position.copy(a).lerp(b, 0.5); o.rotation.y = -Math.atan2(b.z - a.z, b.x - a.x); scene.add(o); return m; });
    const pulse = new THREE.Mesh(new THREE.SphereGeometry(0.11, 14, 14), E(0xffffff, 3)); pulse.visible = false; scene.add(pulse);

    let focusI = -1; let wall = null; let baseAt = Date.now() / 1000;
    const apply = () => { const m = mRef.current; if (!m) return; wall = m.wall; baseAt = Date.now() / 1000; focusI = m.stations.findIndex(s => s.focus);
      st.forEach(s => { const d = m.stations[s.i]; s.cls = d.cls; s.sel = d.selected; s.focus = d.focus; s.scr.userData.redraw(d); s.ringM.emissive.setHex(STATE_HEX[d.cls] || STATE_HEX['is-wait']); s.selR.visible = !!d.selected; });
      segs.forEach((mm, i) => { mm.emissive.setHex(i < focusI ? 0x45e486 : 0x15d16a); mm.emissiveIntensity = i < focusI ? 2.2 : 0.35; });
      statT.userData.redraw(m.status); wallT.userData.redraw(wall, 0); };
    apply();

    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let hover = null;
    const pick = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam); const hit = ray.intersectObjects(st.map(s => s.b.g), true)[0]; return hit ? hit.object.userData.k : null; };
    const onMove = e => { hover = pick(e); renderer.domElement.style.cursor = hover ? 'pointer' : 'default'; };
    const onClick = e => { const k = pick(e); if (k) onSelRef.current(k); };
    renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('click', onClick);
    const labs = host.querySelector('.or3-labels'); st.forEach(s => { s.lab = labs?.children[s.i]; });

    const still = () => document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let seen = true; const io = new IntersectionObserver(es => { seen = es[0]?.isIntersecting ?? true; }); io.observe(host);
    const v = new THREE.Vector3(); const wantP = new THREE.Vector3(); const wantL = new THREE.Vector3(); const clock = new THREE.Clock(); let raf = 0, last = 0, wallAt = 0, ang = 0, prevT = 0;
    const frame = moving => {
      const t = clock.getElapsedTime(); const dt = Math.min(0.1, t - prevT); prevT = t; const mode = camRef.current; const selS = st.find(s => s.sel);
      if (mode === 'top') { wantP.set(0, 17.5, 5.2); wantL.set(0, 0, 0.4); }
      else if (mode === 'focus' && selS) { wantP.set(selS.x * 0.72, 3.5, selS.z + 5.6); wantL.set(selS.x, 1.0, selS.z); }
      else { if (rotRef.current && moving) ang += dt * 0.16; const a = rotRef.current ? Math.sin(ang) * 0.55 : 0;   // auto-rotate = a slow sweep across the room (a full orbit would go behind the wall)
        wantP.set(Math.sin(a) * 13.6, 7.9, Math.cos(a) * 13.6); wantL.set(0, 2.0, -1.4); }
      pos.lerp(wantP, moving ? 0.06 : 1); look.lerp(wantL, moving ? 0.08 : 1); cam.position.copy(pos); cam.lookAt(look);
      if (wall?.reviewAt != null && t - wallAt > 1) { wallAt = t; wallT.userData.redraw(wall, Date.now() / 1000 - baseAt); }   // the review clock on the wall ticks
      if (focusI > 0 && moving) { const u = (t * 0.7) % focusI; const i = Math.floor(u); pulse.visible = true; pulse.position.copy(P(i)).lerp(P(i + 1), u - i); pulse.position.y = 0.12; } else pulse.visible = false;
      st.forEach(s => { const { b } = s; const busy = s.cls === 'is-work' || s.focus; const sp = busy ? 9 : s.cls === 'is-wait' ? 1.2 : 4;
        if (moving) { b.body.position.y = Math.abs(Math.sin(t * (busy ? 3.2 : 1.6) + s.i)) * 0.022; b.arms[0].rotation.x = -0.6 + Math.sin(t * sp + s.i) * 0.32; b.arms[1].rotation.x = -0.6 + Math.sin(t * sp + s.i + Math.PI) * 0.32;
          b.head.rotation.y = Math.sin(t * 0.6 + s.i) * (s.cls === 'is-veto' || s.cls === 'is-obj' ? 0.5 : 0.22); const blink = ((t + s.i * 0.7) % 4) < 0.12 ? 0.1 : 1; b.eyes.forEach(e => { e.scale.y = blink; });
          s.ringM.emissiveIntensity = s.focus ? 1.6 + Math.sin(t * 5) * 1.2 : s.cls === 'is-wait' ? 0.8 : 1.7; s.ring.scale.setScalar(s.focus ? 1 + Math.sin(t * 5) * 0.06 : 1); s.selR.rotation.z = t * 0.6; }
        b.white.emissive.setHex(hover === s.k ? 0x16351f : 0);
        if (s.lab) { v.set(s.x, 2.02, s.z + 0.5); v.project(cam); const out = v.z > 1; s.lab.style.transform = `translate(${(v.x * 0.5 + 0.5) * renderer.domElement.clientWidth}px, ${(-v.y * 0.5 + 0.5) * renderer.domElement.clientHeight}px) translate(-50%, -100%)`; s.lab.style.visibility = out ? 'hidden' : 'visible'; } });
      renderer.render(scene, cam);
    };
    const loop = now => { raf = requestAnimationFrame(loop); if (!seen) return;
      if (document.hidden || still()) { if (now - last > (document.hidden ? 2000 : 1000)) { last = now; frame(false); } return; }   // a still frame — never a blank room
      frame(true); };
    raf = requestAnimationFrame(loop); frame(false);
    const ro = new ResizeObserver(() => { renderer.setSize(W(), H()); cam.aspect = W() / H(); cam.fov = fovFor(cam.aspect); cam.updateProjectionMatrix(); }); ro.observe(host);
    api.current = { apply };
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('click', onClick);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); const m = o.material; (Array.isArray(m) ? m : m ? [m] : []).forEach(mm => { if (mm.map) mm.map.dispose(); mm.dispose(); }); });
      pm.dispose(); renderer.dispose(); renderer.domElement.remove(); api.current = null; };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { api.current?.apply(); }, [model]);   // a new pass / another selection → monitors, rings, the wall, the chain
  return <div className="or3" ref={box} data-testid="ofr-3d">
    <div className="or3-labels">{(model?.stations || []).map(s => <button key={s.key} type="button" className={`or3-lab ${s.cls} ${s.selected ? 'is-on' : ''} ${s.focus ? 'is-focus' : ''}`} style={{ '--ag': AG[s.key] }}
      onClick={() => onSel(s.key)} aria-pressed={!!s.selected} data-tip={`${s.name}: ${s.line}`} data-testid={`desk-${s.key}`}><b>{s.name}</b><em>{s.tag}</em></button>)}</div>
  </div>;
}
