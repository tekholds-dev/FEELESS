// 🌃 THE CITY ENGINE (three.js) — draws a plan from lib/cityPlan.js as a real 3D night city (owner, 2026-10-22: "way better design … find
// free model sites and use the best"). Models: Kenney City Kit Commercial / Car Kit / City Kit Roads (CC0, public/assets/city, licences
// beside them). Windows are lit from the kit's own colour map; cars drive the avenues and HOLD at red lights; every market wears a billboard
// and a roof light whose pulse follows its volume; the pick ring glows on the ground (never a beam). Loaded only where WebGL exists
// (components/FeeCity3D.jsx falls back to the CSS city). Pauses off-screen / hidden tab; fx-lite = no bloom, fewer cars; reduced motion = still.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { centerOf, usd } from './cityPlan';

const BASE = `${process.env.PUBLIC_URL || ''}/assets/city`;
const B = n => `${BASE}/commercial/building-${n}.glb`;
export const MODELS = {
  shop: ['a', 'b', 'c', 'd', 'h'].map(B), mid: ['e', 'f', 'g', 'i', 'k'].map(B), big: ['j', 'l', 'm', 'n'].map(B),
  sky: ['a', 'b', 'c', 'd', 'e'].map(k => `${BASE}/commercial/building-skyscraper-${k}.glb`),
  cars: ['sedan', 'taxi', 'police', 'suv', 'sedan-sports', 'hatchback-sports', 'delivery', 'suv-luxury'].map(k => `${BASE}/cars/${k}.glb`),
  lamp: [`${BASE}/roads/light-square.glb`], signal: [`${BASE}/roads/traffic-light.glb`],
};
const KIND = { mine: '#ffcc4d', family: '#b388ff', cpu: '#ff5d73', cartel: '#3ddc84', free: '#5b6577' };
const MKT = { dex: '#45e486', lend: '#f5c451', perps: '#ff5dbb', stake: '#6ad7ff', coin: '#ff8fa3' };

// ── models: one load per file, clones share geometry + the lit-window material ─────────────────────────────────────────────────────
const cache = new Map(); let loader = null; const glowMats = new Map();
const load = url => { if (!cache.has(url)) { loader = loader || new GLTFLoader(); cache.set(url, loader.loadAsync(url).then(g => g.scene).catch(() => null)); } return cache.get(url); };
export const preload = () => Promise.all(Object.values(MODELS).flat().map(load));
// the kit's colour map holds its window glass in a few blue cells — those texels become a warm emissive map (lit windows at night)
function litWindows(mat) {
  if (!mat?.map?.image || glowMats.has(mat.uuid)) return glowMats.get(mat?.uuid) || mat;
  const img = mat.map.image; const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0); const px = g.getImageData(0, 0, c.width, c.height); const d = px.data;
  for (let i = 0; i < d.length; i += 4) { const r = d[i]; const gg = d[i + 1]; const b = d[i + 2]; const glass = b > 120 && b > r + 25 && gg > r - 10;
    d[i] = glass ? 255 : 0; d[i + 1] = glass ? 196 : 0; d[i + 2] = glass ? 112 : 0; }
  g.putImageData(px, 0, 0); const em = new THREE.CanvasTexture(c); em.colorSpace = THREE.SRGBColorSpace; em.flipY = mat.map.flipY;
  const m = mat.clone(); m.emissive = new THREE.Color('#ffffff'); m.emissiveMap = em; m.emissiveIntensity = 0.62; glowMats.set(mat.uuid, m); return m;
}
async function make(url, { lit = false } = {}) {
  const src = await load(url); if (!src) return new THREE.Group();
  const o = src.clone(true);
  o.traverse(n => { if (n.isMesh) { n.castShadow = false; n.receiveShadow = false; if (lit) n.material = litWindows(n.material); } });
  return o;
}
const sizeOf = o => new THREE.Box3().setFromObject(o).getSize(new THREE.Vector3());
// fit a model into w × d tiles (keeps its proportions), lift it to `h` tiles tall when given
function fit(o, w, d, h = null) {
  const s = sizeOf(o); const k = Math.min(w / Math.max(s.x, 0.01), d / Math.max(s.z, 0.01));
  o.scale.setScalar(k); if (h) o.scale.y = h / Math.max(s.y, 0.01); return o;
}

// ── canvas textures: signs, sky, water ripples, distant windows ─────────────────────────────────────────────────────────────────────
function sign(lines, { color = '#d4af37', w = 512, glow = true } = {}) {
  const c = document.createElement('canvas'); const big = lines[0] || ''; const small = lines.slice(1).filter(Boolean);
  c.width = w; c.height = 96 + small.length * 44; const g = c.getContext('2d');
  g.fillStyle = 'rgba(6,8,14,.86)'; const r = 18; const W = c.width; const H = c.height;
  g.beginPath(); g.moveTo(r, 0); g.arcTo(W, 0, W, H, r); g.arcTo(W, H, 0, H, r); g.arcTo(0, H, 0, 0, r); g.arcTo(0, 0, W, 0, r); g.closePath(); g.fill();
  g.lineWidth = 5; g.strokeStyle = color; if (glow) { g.shadowColor = color; g.shadowBlur = 18; } g.stroke(); g.shadowBlur = 0;
  g.fillStyle = color; g.font = '800 46px "JetBrains Mono", ui-monospace, Menlo, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(big.slice(0, 18), W / 2, 50);
  g.fillStyle = '#e9e4d6'; g.font = '600 32px "JetBrains Mono", ui-monospace, Menlo, monospace';
  small.forEach((t, i) => g.fillText(String(t).slice(0, 26), W / 2, 100 + i * 44));
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true, toneMapped: false }));
  sp.renderOrder = 20; const k = 0.0074; sp.scale.set(W * k, H * k, 1); sp.userData.sign = true; sp.userData.dispose = () => { tex.dispose(); sp.material.dispose(); }; return sp;
}
function skyTexture() {
  const c = document.createElement('canvas'); c.width = 4; c.height = 512; const g = c.getContext('2d'); const gr = g.createLinearGradient(0, 0, 0, 512);
  gr.addColorStop(0, '#03040c'); gr.addColorStop(0.45, '#0b1230'); gr.addColorStop(0.72, '#261a3c'); gr.addColorStop(0.86, '#5a3a2e'); gr.addColorStop(1, '#0a0b12');
  g.fillStyle = gr; g.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function noiseTexture(n = 128) {
  const c = document.createElement('canvas'); c.width = n; c.height = n; const g = c.getContext('2d'); const d = g.createImageData(n, n);
  for (let i = 0; i < n * n; i += 1) { const v = 110 + Math.random() * 40 + 30 * Math.sin(i * 0.07) * Math.cos(i * 0.013); d.data.set([v, v, v, 255], i * 4); }
  g.putImageData(d, 0, 0); const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping; return t;
}
function windowsTexture() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 64, 128);
  for (let y = 4; y < 124; y += 8) for (let x = 4; x < 60; x += 8) if (Math.random() < 0.38) { g.fillStyle = Math.random() < 0.8 ? '#ffcf7a' : '#7fd3ff'; g.fillRect(x, y, 4, 4); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function radial(color = '#ffd27a') {
  const c = document.createElement('canvas'); c.width = 64; c.height = 64; const g = c.getContext('2d'); const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, color); gr.addColorStop(0.35, `${color}88`); gr.addColorStop(1, `${color}00`); g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const neon = (hex, k = 2.2) => new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(k), toneMapped: false });

// ── the engine ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
export function createCity(host, { onPick, onHover, lite = false, still = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: !lite, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lite ? 1 : 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  host.appendChild(renderer.domElement); renderer.domElement.className = 'fc3-canvas';
  const scene = new THREE.Scene(); scene.background = skyTexture(); scene.fog = new THREE.Fog('#0a1022', 70, 230);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.4, 700);
  const controls = new OrbitControls(camera, renderer.domElement);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, minPolarAngle: 0.32, maxPolarAngle: 1.22, minDistance: 7, maxDistance: 170, screenSpacePanning: false, zoomSpeed: 0.9 });
  scene.add(new THREE.HemisphereLight('#4a5a95', '#0b0b14', 1.25));
  const moon = new THREE.DirectionalLight('#a9bcff', 1.35); moon.position.set(-60, 90, -40); scene.add(moon);
  const dusk = new THREE.DirectionalLight('#ffb35a', 0.55); dusk.position.set(80, 14, 70); scene.add(dusk);
  let composer = null;
  if (!lite) { composer = new EffectComposer(renderer); composer.addPass(new RenderPass(scene, camera));
    composer.addPass(new UnrealBloomPass(new THREE.Vector2(256, 256), 0.85, 0.5, 0.82)); composer.addPass(new OutputPass()); }

  const world = new THREE.Group(); let content = new THREE.Group(); scene.add(world, content); let sig = null;
  const pickables = []; const anim = []; let cars = []; let lights = null; let lightNodes = []; let planKey = null; let plan = null;
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.25, 1.55, 48), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd76a').multiplyScalar(2.4), toneMapped: false, transparent: true, side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2; ring.visible = false; scene.add(ring);
  const hoverFrame = new THREE.Mesh(new THREE.RingGeometry(1.0, 1.12, 4, 1), new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.85, toneMapped: false, side: THREE.DoubleSide }));
  hoverFrame.rotation.set(-Math.PI / 2, 0, Math.PI / 4); hoverFrame.visible = false; scene.add(hoverFrame);

  const clear = g => { while (g.children.length) { const c = g.children.pop(); c.traverse(n => { n.userData?.dispose?.(); if (n.isInstancedMesh) n.dispose(); }); } };
  const box = (w, h, d, color, x, y, z, parent = world, mat = null) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat || new THREE.MeshStandardMaterial({ color, roughness: 0.92 })); m.position.set(x, y, z); parent.add(m); return m; };
  const worldPicks = [];   // the gates live with the world (they survive a content swap)
  const proxy = (r, h, pick, label, inWorld = false) => { const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, h, r.d), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false }));
    const c = centerOf(r); m.position.set(c.x, h / 2, c.z); m.userData = { pick, label, rect: r }; (inWorld ? world : content).add(m); (inWorld ? worldPicks : pickables).push(m); return m; };
  const frame = (r, color, parent = content, y = 0.1) => { const g = new THREE.Group(); const t = 0.07; const mat = neon(color, 1.6);
    [[r.w, t, r.x + r.w / 2, r.z], [r.w, t, r.x + r.w / 2, r.z + r.d], [t, r.d, r.x, r.z + r.d / 2], [t, r.d, r.x + r.w, r.z + r.d / 2]].forEach(([w, d, x, z]) => box(w, 0.05, d, null, x, y, z, g, mat));
    parent.add(g); return g; };

  // ── the static world: water, sky dressing, islands, roads, bridges, lamps, stoplights ──
  async function buildWorld(p) {
    clear(world); cars = []; lightNodes = []; lights = null; worldPicks.length = 0;
    const bx = p.bounds; const W = bx.x1 - bx.x0; const D = bx.z1 - bx.z0; const cx = (bx.x0 + bx.x1) / 2; const cz = (bx.z0 + bx.z1) / 2;
    const ripple = noiseTexture(); ripple.repeat.set(W / 6, D / 6);
    const water = new THREE.Mesh(new THREE.PlaneGeometry(W + 260, D + 260), new THREE.MeshStandardMaterial({ color: '#071528', roughness: 0.28, metalness: 0.55, bumpMap: ripple, bumpScale: 0.6, emissive: '#02060f' }));
    water.rotation.x = -Math.PI / 2; water.position.set(cx, -0.55, cz); world.add(water); anim.push(t => { ripple.offset.set(t * 0.012, t * 0.007); });
    const glint = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial('#bcd0ff'), transparent: true, opacity: 0.35, depthWrite: false })); glint.scale.set(40, 6, 1); glint.position.set(cx - 30, -0.45, bx.z0 - 20); world.add(glint);
    // stars + moon + a far skyline ring
    const sg = new THREE.BufferGeometry(); const sp = []; for (let i = 0; i < 700; i += 1) { const a = Math.random() * Math.PI * 2; const e = 0.15 + Math.random() * 1.2; sp.push(Math.cos(a) * 380 * Math.cos(e), 380 * Math.sin(e), Math.sin(a) * 380 * Math.cos(e)); }
    sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
    const stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: '#dfe6ff', size: 1.4, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85 })); stars.position.set(cx, 0, cz); world.add(stars);
    const moonS = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial('#fff4d6'), fog: false, transparent: true, depthWrite: false })); moonS.scale.set(46, 46, 1); moonS.position.set(cx - 120, 95, cz - 210); world.add(moonS);
    const far = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: '#0b0f1c', emissive: '#ffffff', emissiveMap: windowsTexture(), emissiveIntensity: 0.55, roughness: 1 }), 90);
    const m4 = new THREE.Matrix4(); const R = Math.max(W, D) / 2 + 70;
    for (let i = 0; i < 90; i += 1) { const a = (i / 90) * Math.PI * 2; const h = 8 + ((i * 37) % 31); const w = 4 + ((i * 13) % 5);
      m4.compose(new THREE.Vector3(cx + Math.cos(a) * R, h / 2 - 0.6, cz + Math.sin(a) * R), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -a, 0)), new THREE.Vector3(w, h, w)); far.setMatrixAt(i, m4); }
    world.add(far);
    // islands: asphalt slab + quay wall + a gold trim on the capital; raised sidewalks per cell come with the content
    for (const i of p.islands) {
      box(i.w + 0.6, 1.1, i.d + 0.6, '#262a33', i.x + i.w / 2, -0.56, i.z + i.d / 2);
      box(i.w, 0.06, i.d, '#15171d', i.x + i.w / 2, 0.0, i.z + i.d / 2);
      if (i.capital || i.color) frame({ x: i.x - 0.3, z: i.z - 0.3, w: i.w + 0.6, d: i.d + 0.6 }, i.color || '#d4af37', world, 0.02);
      const s = sign([i.name, i.sub], { color: i.color || '#d4af37', w: 560 }); s.position.set(i.x + i.w / 2, 1.2, i.z + i.d + 1.4); s.scale.multiplyScalar(1.2); world.add(s);
    }
    // lane dashes (one instanced mesh) + crosswalks at the lights
    const dashes = []; for (const r of p.roads) for (const s of r.segs) {
      if (s.axis === 'x') for (let x = s.x0 + 0.4; x < s.x1 - 0.3; x += 0.7) dashes.push([x, s.z, 0]);
      else for (let z = s.z0 + 0.4; z < s.z1 - 0.3; z += 0.7) dashes.push([s.x, z, Math.PI / 2]); }
    const dm = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.32, 0.045), new THREE.MeshBasicMaterial({ color: '#c9b26a' }), Math.max(1, dashes.length));
    dashes.forEach(([x, z, a], k) => { m4.compose(new THREE.Vector3(x, 0.035, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, a)), new THREE.Vector3(1, 1, 1)); dm.setMatrixAt(k, m4); });
    world.add(dm);
    // bridges + gates: a deck on pillars, rails, two pylons with lit tips, cables
    const deck = (b, gate) => { const len = Math.abs(b.b - b.a); const mid = (b.a + b.b) / 2; const along = b.axis === 'x';
      const g = new THREE.Group(); world.add(g);
      const dk = box(along ? len : 1.4, 0.22, along ? 1.4 : len, '#1d2029', along ? mid : b.x, 0.02, along ? b.z : mid, g);
      dk.material = new THREE.MeshStandardMaterial({ color: '#1d2029', roughness: 0.8 });
      [-0.72, 0.72].forEach(o => box(along ? len : 0.06, 0.25, along ? 0.06 : len, '#8a7a4a', along ? mid : b.x + o, 0.25, along ? b.z + o : mid, g));
      [0.25, 0.75].forEach(f => { const at = b.a + (b.b - b.a) * f; [-0.8, 0.8].forEach(o => { box(0.18, 3.2, 0.18, '#3a3020', along ? at : b.x + o, 1.6, along ? b.z + o : at, g);
        const tip = box(0.22, 0.22, 0.22, null, along ? at : b.x + o, 3.25, along ? b.z + o : at, g, neon(gate ? '#ff8fa3' : '#ffd76a', 2.5)); tip.userData.blink = true; }); });
      for (let k = 1; k < 4; k += 1) { const at = b.a + ((b.b - b.a) * k) / 4; box(0.3, 0.6, 0.3, '#2b2e36', along ? at : b.x, -0.35, along ? b.z : at, g); }
      return g; };
    p.bridges.forEach(b => deck(b, false));
    p.gates.forEach(gt => { deck(gt, true); const end = gt.at === 'n' || gt.at === 'w' ? gt.a : gt.b;
      const s = sign([gt.name, gt.held ? `▸ ${gt.held}` : '▸ cross'], { color: '#ff8fa3', w: 440 });
      const pos = gt.axis === 'x' ? [end, 2.4, gt.z] : [gt.x, 2.4, end]; s.position.set(...pos); world.add(s);
      proxy({ x: pos[0] - 1.5, z: pos[2] - 1.5, w: 3, d: 3 }, 3, { gate: gt.key }, `Cross to ${gt.name}`, true); });
    // street lamps on every corner of the island grids (instanced) + their glow bulbs
    const lampAt = []; for (const r of p.roads) r.nodes.forEach((n, k) => { if (k % 2 === 0) lampAt.push([n.x + 0.42, n.z + 0.42]); });
    const lampSrc = await load(MODELS.lamp[0]);
    if (lampSrc) lampSrc.traverse(n => { if (!n.isMesh) return; const im = new THREE.InstancedMesh(n.geometry, n.material, lampAt.length);
      lampAt.forEach(([x, z], k) => { m4.compose(new THREE.Vector3(x, 0.03, z), new THREE.Quaternion(), new THREE.Vector3(1.6, 1.6, 1.6)); im.setMatrixAt(k, m4); }); world.add(im); });
    const bulbs = new THREE.InstancedMesh(new THREE.SphereGeometry(0.06, 8, 6), neon('#ffd27a', 1.7), lampAt.length);
    lampAt.forEach(([x, z], k) => { m4.makeTranslation(x, 0.98, z - 0.3); bulbs.setMatrixAt(k, m4); }); world.add(bulbs);
    const pools = new THREE.InstancedMesh(new THREE.PlaneGeometry(1.6, 1.6), new THREE.MeshBasicMaterial({ map: radial('#ffc46b'), transparent: true, opacity: 0.2, depthWrite: false, toneMapped: false }), lampAt.length);
    lampAt.forEach(([x, z], k) => { m4.compose(new THREE.Vector3(x, 0.045, z - 0.3), new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0)), new THREE.Vector3(1, 1, 1)); pools.setMatrixAt(k, m4); }); world.add(pools);
    // 🚦 stoplights: the kit's pole + a lamp per direction whose colour follows the phase
    lightNodes = p.lights.map(n => ({ x: n.x, z: n.z }));
    const sigSrc = await load(MODELS.signal[0]);
    if (sigSrc) sigSrc.traverse(n => { if (!n.isMesh) return; const im = new THREE.InstancedMesh(n.geometry, n.material, Math.max(1, lightNodes.length));
      lightNodes.forEach((l, k) => { m4.compose(new THREE.Vector3(l.x - 0.55, 0.03, l.z - 0.55), new THREE.Quaternion(), new THREE.Vector3(1.9, 1.9, 1.9)); im.setMatrixAt(k, m4); }); world.add(im); });
    lights = new THREE.InstancedMesh(new THREE.SphereGeometry(0.11, 10, 8), new THREE.MeshBasicMaterial({ toneMapped: false }), Math.max(2, lightNodes.length * 2));
    lightNodes.forEach((l, k) => { m4.makeTranslation(l.x - 0.55, 1.02, l.z - 0.42); lights.setMatrixAt(k * 2, m4); m4.makeTranslation(l.x - 0.42, 1.02, l.z - 0.55); lights.setMatrixAt(k * 2 + 1, m4); });
    world.add(lights);
    // 🚗 traffic on every loop + both lanes of every bridge
    const loops = [...p.loops, ...p.bridges.map(b => (b.axis === 'x' ? [[b.a - 0.5, b.z], [b.b + 0.5, b.z], [b.b + 0.5, b.z], [b.a - 0.5, b.z]] : [[b.x, b.a - 0.5], [b.x, b.b + 0.5], [b.x, b.b + 0.5], [b.x, b.a - 0.5]]))];
    const perLoop = lite ? 1 : 3; const headTex = radial('#fff1c4');
    for (let li = 0; li < loops.length; li += 1) {
      const pts = loops[li]; const segs = pts.map((a, k) => { const b = pts[(k + 1) % pts.length]; return { a, b, len: Math.hypot(b[0] - a[0], b[1] - a[1]) }; });
      const total = segs.reduce((s, x) => s + x.len, 0); if (total < 2) continue;
      segs.forEach(s => { s.stops = lightNodes.filter(n => (Math.abs(s.a[1] - s.b[1]) < 0.01 ? Math.abs(n.z - s.a[1]) < 0.05 && n.x > Math.min(s.a[0], s.b[0]) && n.x < Math.max(s.a[0], s.b[0])
        : Math.abs(n.x - s.a[0]) < 0.05 && n.z > Math.min(s.a[1], s.b[1]) && n.z < Math.max(s.a[1], s.b[1]))).map(n => Math.hypot(n.x - s.a[0], n.z - s.a[1])).sort((x, y) => x - y); });
      const n = li < p.loops.length ? perLoop + (li === 0 ? 2 : 0) : (lite ? 0 : 1);
      for (let k = 0; k < n; k += 1) {
        const o = await make(MODELS.cars[(li * 3 + k) % MODELS.cars.length]); fit(o, 0.42, 0.8);
        const car = new THREE.Group(); car.add(o);
        const hl = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1.6), new THREE.MeshBasicMaterial({ map: headTex, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false }));
        hl.rotation.x = -Math.PI / 2; hl.position.set(0, 0.04, 1.1); car.add(hl);
        [-0.12, 0.12].forEach(x => { const tl = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.05, 0.02), neon('#ff2a3d', 2.6)); tl.position.set(x, 0.17, -0.41); car.add(tl); });
        world.add(car); cars.push({ obj: car, segs, total, s: (total / n) * k + li * 1.7, v: 0, vmax: 1.6 + ((li + k) % 3) * 0.35, loop: li });
      }
    }
  }

  // ── content: plots, landmarks, markets, places (rebuilt on every data refresh) ──
  async function buildContent(p, live = {}) {   // built OFF-screen, then swapped in — a data refresh never blinks a building out
    const old = content; content = new THREE.Group(); const keep = anim.slice(0, 1); const was = pickables.splice(0); anim.length = 0; anim.push(...keep);
    const side = (r, color = '#30333c') => box(r.w, 0.12, r.d, color, r.x + r.w / 2, 0.06, r.z + r.d / 2, content);
    const tops = [];
    // family plots
    for (const l of p.lots) {
      side(l.rect, '#2d3038'); const c = centerOf(l.rect);
      if (l.kind === 'free') {
        if (l.seed % 3 === 2) { const o = await make(MODELS.mid[l.seed % MODELS.mid.length], { lit: true }); fit(o, l.rect.w - 0.5, l.rect.d - 0.5); o.position.set(c.x, 0.12, c.z); o.rotation.y = (l.seed % 4) * (Math.PI / 2);
          o.traverse(n => { if (n.isMesh) { n.material = n.material.clone(); n.material.color.multiplyScalar(0.6); n.material.emissiveIntensity = 0.16; } }); content.add(o);   // vacant: a few lights still on
          const fs = sign(['FOR SALE'], { color: '#c9b38a', w: 300, glow: false }); fs.position.set(c.x, sizeOf(o).y + 0.5, c.z); fs.scale.multiplyScalar(0.55); fs.userData.small = true; content.add(fs); }
        else if (l.seed % 3 === 1) { box(l.rect.w - 0.3, 0.04, l.rect.d - 0.3, '#163a22', c.x, 0.14, c.z, content);
          for (let t = 0; t < 3; t += 1) { const tr = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.7, 7), new THREE.MeshStandardMaterial({ color: '#1f6b3a', roughness: 1 })); tr.position.set(c.x - 0.5 + t * 0.5, 0.52, c.z + ((t * 37 + l.seed) % 5) / 10 - 0.2); content.add(tr); } }
        else { box(l.rect.w - 0.3, 0.03, l.rect.d - 0.3, '#1b1d24', c.x, 0.13, c.z, content);
          for (let k = 0; k < 2; k += 1) { const o = await make(MODELS.cars[(l.seed + k) % MODELS.cars.length]); fit(o, 0.36, 0.7); o.position.set(c.x - 0.35 + k * 0.7, 0.13, c.z); content.add(o); } }
        proxy(l.rect, 0.6, l.pick, 'For sale');
        continue;
      }
      const lvl = Math.max(1, Math.min(6, Math.round(Math.log10(1 + l.power) * 1.6)));
      const set = l.home || lvl >= 5 ? MODELS.sky : lvl >= 3 ? MODELS.big : MODELS.mid;
      const o = await make(set[l.seed % set.length], { lit: true }); fit(o, l.rect.w - 0.35, l.rect.d - 0.35, set === MODELS.sky ? 2.2 + lvl * 0.45 : null);
      o.position.set(c.x, 0.12, c.z); o.rotation.y = (l.seed % 4) * (Math.PI / 2); content.add(o);
      const h = sizeOf(o).y; frame(l.rect, KIND[l.kind] || KIND.family);
      if (l.tag) { const s = sign([`[${l.tag}]`], { color: KIND[l.kind], w: 260, glow: l.kind === 'mine' }); s.position.set(c.x, h + 0.7, c.z); s.scale.multiplyScalar(0.7); s.userData.small = true; content.add(s); }
      const roof = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), neon(KIND[l.kind], 3)); roof.position.set(c.x, h + 0.22, c.z); content.add(roof);
      if (l.owner && live.raided?.has(l.owner)) { const rf = frame(l.rect, '#ff2a3d', content, 0.16); anim.push(t => { rf.visible = Math.sin(t * 9) > -0.2; }); }
      proxy(l.rect, h + 0.3, l.pick, l.tag ? `[${l.tag}]` : 'Plot'); tops.push(h);
    }
    // landmarks
    for (const m of p.marks) { side(m.rect, '#33302a'); await landmark(m, live); }
    if (p.plaza) { const r = p.plaza; box(r.w, 0.12, r.d, '#4a4235', r.x + r.w / 2, 0.06, r.z + r.d / 2, content);
      const c = centerOf({ ...r, w: r.w - 4 });
      const f1 = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1, 0.25, 24), new THREE.MeshStandardMaterial({ color: '#6b5a3a', roughness: 0.6 })); f1.position.set(c.x, 0.25, c.z); content.add(f1);
      const jet = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.16, 1.1, 10), new THREE.MeshBasicMaterial({ color: new THREE.Color('#9fe3ff').multiplyScalar(1.8), toneMapped: false, transparent: true, opacity: 0.7 }));
      jet.position.set(c.x, 0.9, c.z); content.add(jet); anim.push(t => { jet.scale.y = 0.85 + Math.sin(t * 3) * 0.15; });
      for (let k = 0; k < 6; k += 1) { const tr = new THREE.Mesh(new THREE.ConeGeometry(0.3, 0.8, 7), new THREE.MeshStandardMaterial({ color: '#1f6b3a' })); tr.position.set(r.x + 1 + k * 2.2, 0.55, r.z + (k % 2 ? r.d - 0.4 : 0.4)); content.add(tr); }
      const sg = sign(['FEE PLAZA'], { color: '#d4af37', w: 360 }); sg.position.set(c.x, 2.2, c.z); content.add(sg); }
    // markets: a tower per market, a billboard, a roof light pulsing at its volume
    for (const m of p.markets) {
      side(m.rect, '#2a2e2a'); const c = centerOf(m.rect); const col = MKT[m.kind] || '#45e486';
      const set = m.kind === 'coin' ? (m.h > 2.6 ? MODELS.big : MODELS.mid) : m.h > 2.2 ? MODELS.sky : MODELS.big;
      const o = await make(set[(m.key.length + (m.name || '').length) % set.length], { lit: true }); fit(o, m.rect.w - 0.3, m.rect.d - 0.3, Math.max(1.4, m.h * 1.25));
      o.position.set(c.x, 0.12, c.z); content.add(o); const h = sizeOf(o).y;
      const tone = m.kind === 'coin' && m.move != null ? (m.move >= 0 ? '#45e486' : '#ff5d73') : col;
      const beacon = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.06, 8, 28), neon(tone, 2.8)); beacon.rotation.x = Math.PI / 2; beacon.position.set(c.x, h + 0.25, c.z); content.add(beacon);
      const hz = m.hz || 1; anim.push(t => { const k = 0.5 + 0.5 * Math.sin(t * hz * Math.PI * 2); beacon.scale.setScalar(0.85 + k * 0.35); beacon.material.color.set(tone).multiplyScalar(1.4 + k * 1.8); });
      frame(m.rect, col);
      const sub = m.kind === 'coin' ? `${usd(m.tvl)} MC${m.move != null ? ` · ${m.move >= 0 ? '+' : ''}${Number(m.move).toFixed(1)}%` : ''}` : `TVL ${usd(m.tvl)}`;
      const s = sign([m.name, sub], { color: tone, w: 420 }); s.position.set(c.x, h + 1.25, c.z); content.add(s);
      proxy(m.rect, h + 0.4, m.pick, m.name);
    }
    for (const x of p.spare) { side(x.rect, '#25272d'); const c = centerOf(x.rect); const all = [...MODELS.shop, ...MODELS.mid]; const o = await make(all[(x.rect.x * 7 + x.rect.z * 3) % all.length], { lit: true }); fit(o, x.rect.w - 0.5, x.rect.d - 0.5); o.position.set(c.x, 0.12, c.z); content.add(o); }
    for (const pl of p.places) await place(pl);
    scene.add(content); scene.remove(old); clear(old); was.length = 0;
    return tops;
  }

  async function landmark(m, live) {
    const r = m.rect; const c = centerOf(r); const lv = live.marks?.[m.key] || m.live || {};
    if (m.key === 'arena') {   // ⚔ the stadium: a lathe bowl, crowd, a lit pitch, four floodlight masts
      const g = new THREE.Group(); g.position.set(c.x, 0.12, c.z); content.add(g);
      const prof = [[2.3, 0], [2.4, 0.15], [3.1, 1.25], [3.25, 1.35], [3.25, 0]].map(([x, y]) => new THREE.Vector2(x, y));
      const bowl = new THREE.Mesh(new THREE.LatheGeometry(prof, 48), new THREE.MeshStandardMaterial({ color: '#3a3d48', roughness: 0.7, side: THREE.DoubleSide }));
      bowl.scale.set(r.w / 6.6, 1, r.d / 6.6); g.add(bowl);
      const pc = document.createElement('canvas'); pc.width = 256; pc.height = 160; const pg = pc.getContext('2d');
      for (let i = 0; i < 8; i += 1) { pg.fillStyle = i % 2 ? '#1e7a3c' : '#22883f'; pg.fillRect(i * 32, 0, 32, 160); }
      pg.strokeStyle = '#e8f5e8'; pg.lineWidth = 3; pg.strokeRect(8, 8, 240, 144); pg.beginPath(); pg.moveTo(128, 8); pg.lineTo(128, 152); pg.stroke(); pg.beginPath(); pg.arc(128, 80, 22, 0, Math.PI * 2); pg.stroke();
      const pt = new THREE.CanvasTexture(pc); pt.colorSpace = THREE.SRGBColorSpace;
      const pitch = new THREE.Mesh(new THREE.PlaneGeometry(r.w * 0.62, r.d * 0.6), new THREE.MeshStandardMaterial({ map: pt, roughness: 0.9, emissive: '#0a3a18', emissiveIntensity: 0.6 }));
      pitch.rotation.x = -Math.PI / 2; pitch.position.y = 0.05; g.add(pitch);
      const crowd = new THREE.InstancedMesh(new THREE.BoxGeometry(0.12, 0.16, 0.12), new THREE.MeshStandardMaterial({ roughness: 1 }), 260); const m4 = new THREE.Matrix4(); const col = new THREE.Color();
      for (let k = 0; k < 260; k += 1) { const a = (k / 260) * Math.PI * 2 * 3; const t = (k % 3) / 3; const rr = 2.55 + t * 0.55; m4.makeTranslation(Math.cos(a) * rr * r.w / 6.6, 0.35 + t * 0.85, Math.sin(a) * rr * r.d / 6.6);
        crowd.setMatrixAt(k, m4); crowd.setColorAt(k, col.set(['#d4af37', '#45e486', '#ff8fa3', '#e8e3d6', '#b388ff'][k % 5])); }
      g.add(crowd);
      [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sz]) => { box(0.12, 3.6, 0.12, '#55585f', sx * r.w * 0.47, 1.8, sz * r.d * 0.45, g);
        const head = box(0.5, 0.22, 0.2, null, sx * r.w * 0.47, 3.6, sz * r.d * 0.45, g, neon('#fff6d8', 3)); head.lookAt(0, 0, 0); });
      const hot = (lv.raids || 0) > 0 || live.fight;
      if (live.fight) ['a', 'b'].forEach((sd, k) => { const s = sign([`[${live.fight[sd].tag}]`, live.fight[sd].pct == null ? '' : `${live.fight[sd].pct >= 0 ? '+' : ''}${live.fight[sd].pct.toFixed(2)}%`], { color: live.fight[sd].color || (sd === 'a' ? '#45e486' : '#ff8fa3'), w: 300 });
        s.position.set(c.x + (k ? 1 : -1) * r.w * 0.18, 1.4, c.z); s.scale.multiplyScalar(0.8); content.add(s); });
      if (hot) anim.push(t => { crowd.position.y = Math.abs(Math.sin(t * 6)) * 0.05; });
      const s = sign([m.name || 'FUSE ARENA', live.fight ? 'FAMILY FUSE LIVE' : `${Math.round(lv.raids || 0)} raids live`], { color: '#d4af37', w: 460 }); s.position.set(c.x, 4.6, c.z); content.add(s);
      proxy(r, 1.6, m.pick, m.name); return;
    }
    if (m.key === 'launch') {   // 🚀 a rocket on its pad, exhaust breathing
      box(r.w - 0.4, 0.2, r.d - 0.4, '#3a3a40', c.x, 0.2, c.z, content);
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.32, 2.1, 16), new THREE.MeshStandardMaterial({ color: '#e8e3d6', metalness: 0.3, roughness: 0.4 })); body.position.set(c.x, 1.35, c.z); content.add(body);
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.6, 16), neon('#ffb35a', 1.4)); nose.position.set(c.x, 2.7, c.z); content.add(nose);
      const fire = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial('#ff9a3d'), transparent: true, depthWrite: false, toneMapped: false })); fire.position.set(c.x, 0.35, c.z); fire.scale.set(1.2, 1.4, 1); content.add(fire);
      anim.push(t => { const k = 0.8 + Math.sin(t * 13) * 0.12 + Math.sin(t * 7) * 0.08; fire.scale.set(1.2 * k, 1.5 * k, 1); });
      const s = sign([m.name || 'LAUNCH PAD', `${Math.round(lv.coins || 0)} coins launched`], { color: '#ffb35a', w: 420 }); s.position.set(c.x, 3.7, c.z); content.add(s);
      proxy(r, 3, m.pick, m.name); return;
    }
    const pickModel = { house: MODELS.sky[3], mansion: MODELS.big[3], shield: MODELS.sky[1] }[m.key];
    const o = await make(pickModel, { lit: true }); fit(o, r.w - 0.4, r.d - 0.4, m.key === 'house' ? 6.2 : m.key === 'shield' ? 4.6 : null);
    o.position.set(c.x, 0.12, c.z); content.add(o); const h = sizeOf(o).y;
    if (m.key === 'house') { const crown = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.08, 8, 30), neon('#ffd76a', 2.8)); crown.rotation.x = Math.PI / 2; crown.position.set(c.x, h + 0.2, c.z); content.add(crown);
      anim.push(t => { crown.rotation.z = t * 0.6; }); }
    if (m.key === 'mansion') { box(r.w - 0.2, 0.05, r.d - 0.2, '#2f5a2a', c.x, 0.15, c.z, content); const gate = box(r.w - 0.3, 0.3, 0.06, null, c.x, 0.3, r.z + r.d - 0.15, content, neon('#d4af37', 1.6)); gate.userData.gold = true; }
    if (m.key === 'shield') {   // 🛡 a searchlight sweeping the sky — its speed follows the flagged wallets it watches
      const cone = new THREE.Mesh(new THREE.ConeGeometry(1.6, 9, 24, 1, true), new THREE.MeshBasicMaterial({ color: '#9fe3ff', transparent: true, opacity: 0.08, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }));
      cone.geometry.translate(0, -4.5, 0); const piv = new THREE.Group(); piv.position.set(c.x, h + 0.1, c.z); piv.add(cone); cone.rotation.x = Math.PI * 0.82; content.add(piv);
      const sp = 0.25 + Math.min(1.2, Math.log10(1 + (lv.flagged || 0)) / 4); anim.push(t => { piv.rotation.y = t * sp; }); }
    const lines = { house: `${Math.round(lv.mp || 0).toLocaleString('en-US')} MP vault`, mansion: lv.tag ? `[${lv.tag}] ${lv.name || ''}` : 'the creator family', shield: `${Math.round(lv.flagged || 0)} flagged` }[m.key];
    const s = sign([m.name || m.key, lines], { color: '#d4af37', w: 440 }); s.position.set(c.x, h + 1.3, c.z); content.add(s);
    proxy(r, h + 0.3, m.pick, m.name);
  }

  async function place(pl) {   // 📍 a lens you walk into: its own building + a neon sign
    const r = pl.rect; const c = centerOf(r);
    box(r.w, 0.12, r.d, '#2c2a33', c.x, 0.06, c.z, content);
    const url = { tower: MODELS.sky[2], precinct: MODELS.mid[4], pawn: MODELS.mid[0], board: MODELS.shop[2], gym: MODELS.big[0], casino: MODELS.big[3], warehouse: MODELS.mid[4] }[pl.art] || MODELS.mid[0];
    const o = await make(url, { lit: true }); fit(o, r.w - 0.4, r.d - 0.4, pl.art === 'tower' ? 4.8 : null); o.position.set(c.x, 0.12, c.z); content.add(o); const h = sizeOf(o).y;
    frame(r, pl.color);
    if (pl.art === 'precinct') { const a = box(0.3, 0.12, 0.12, null, c.x - 0.18, h + 0.1, c.z, content, neon('#ff2a3d', 3)); const b2 = box(0.3, 0.12, 0.12, null, c.x + 0.18, h + 0.1, c.z, content, neon('#2a6bff', 3));
      anim.push(t => { const on = Math.sin(t * 10) > 0; a.visible = on; b2.visible = !on; }); }
    else { const n = new THREE.Mesh(new THREE.TorusGeometry(0.34, 0.05, 8, 24), neon(pl.color, 2.6)); n.position.set(c.x, h + 0.35, c.z); content.add(n); anim.push(t => { n.rotation.y = t * 1.4; }); }
    const s = sign([pl.name, pl.sub], { color: pl.color, w: 460 }); s.position.set(c.x, h + 1.3, c.z); content.add(s);
    proxy(r, h + 0.3, pl.pick, pl.name);
  }

  // ── camera ──
  let fly = null;
  const frameAll = () => { const bx = plan.bounds; const span = Math.max(bx.x1 - bx.x0, bx.z1 - bx.z0); return { x: plan.center.x, z: plan.center.z, dist: span * 0.6 }; };
  function flyTo(spot, dist = 12, ms = 900) {
    if (!plan) return;
    const to = spot || frameAll(); const d = spot ? dist : to.dist;
    const cine = new THREE.Vector3(0.5, 0.5, 0.75).normalize();   // the whole city = the cinematic angle; a pick keeps the angle you turned to
    let dir = camera.position.clone().sub(controls.target); dir = !spot || dir.lengthSq() < 1e-6 ? cine : dir.normalize(); if (dir.y < 0.38) { dir.y = 0.5; dir.normalize(); }
    fly = { t0: performance.now(), ms: still ? 1 : ms, fromT: controls.target.clone(), toT: new THREE.Vector3(to.x, 0, to.z), fromP: camera.position.clone(), toP: new THREE.Vector3(to.x, 0, to.z).add(dir.multiplyScalar(d)) };
    ring.visible = !!spot; if (spot) ring.position.set(spot.x, 0.16, spot.z);
  }

  // ── picking + hover ──
  const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let down = null; let hover = null; let hoverAt = null;
  const hit = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
    ray.setFromCamera(ptr, camera); return ray.intersectObjects([...pickables, ...worldPicks], false)[0]?.object || null; };
  const onDown = e => { down = { x: e.clientX, y: e.clientY }; };
  const onUp = e => { if (!down) return; const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y); down = null; if (moved > 6) return; const o = hit(e); if (o) onPick?.(o.userData.pick); };
  const onMove = e => { hoverAt = e; };
  const el = renderer.domElement; el.addEventListener('pointerdown', onDown); el.addEventListener('pointerup', onUp); el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerleave', () => { hoverAt = null; if (hover) { hover = null; hoverFrame.visible = false; el.style.cursor = ''; onHover?.(null); } });

  // ── the loop ──
  let raf = 0; let visible = true; let last = performance.now(); let t = 0; let phaseWas = -1; let dirty = true;
  const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(([en]) => { visible = en.isIntersecting; }, { threshold: 0.01 }) : null; io?.observe(host);
  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => size()) : null; ro?.observe(host);
  controls.addEventListener('change', () => { dirty = true; });
  function size() { const w = host.clientWidth || 800; const h = host.clientHeight || 520; renderer.setSize(w, h, false); composer?.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true; }
  const green = new THREE.Color('#2dff7a').multiplyScalar(2.2); const amber = new THREE.Color('#ffb020').multiplyScalar(2.2); const red = new THREE.Color('#ff2a3d').multiplyScalar(2.2);
  const phaseOf = tt => { const c = tt % 10; return c < 4.2 ? 0 : c < 5 ? 1 : c < 9.2 ? 2 : 3; };   // 0 x-green · 1 x-amber · 2 z-green · 3 z-amber
  const goFor = (ph, axis) => (axis === 'x' ? ph === 0 : ph === 2);
  function stepCars(dt, ph) {
    const byLoop = {}; cars.forEach(c => { (byLoop[c.loop] = byLoop[c.loop] || []).push(c); });
    Object.values(byLoop).forEach(list => list.sort((a, b) => a.s - b.s));
    for (const c of cars) {
      let s = ((c.s % c.total) + c.total) % c.total; let k = 0; while (k < c.segs.length - 1 && s > c.segs[k].len) { s -= c.segs[k].len; k += 1; }
      const sg = c.segs[k]; const axis = Math.abs(sg.a[1] - sg.b[1]) < 0.01 ? 'x' : 'z'; let want = c.vmax;
      const stop = sg.stops.find(d => d - s > 0.25 && d - s < 1.25); if (stop != null && !goFor(ph, axis)) want = Math.max(0, (stop - s - 0.45) * 1.8);
      const list = byLoop[c.loop]; const i = list.indexOf(c); const ahead = list[(i + 1) % list.length];
      if (ahead && ahead !== c) { const gap = ((ahead.s - c.s) % c.total + c.total) % c.total; if (gap < 1.1) want = Math.min(want, Math.max(0, (gap - 0.75) * 2)); }
      c.v += (want - c.v) * Math.min(1, dt * 3); c.s += c.v * dt;
      const f = sg.len ? s / sg.len : 0; const dx = sg.b[0] - sg.a[0]; const dz = sg.b[1] - sg.a[1]; const L = Math.hypot(dx, dz) || 1;
      const nx = -dz / L; const nz = dx / L;   // keep right: the lane sits off the centre line
      c.obj.position.set(sg.a[0] + dx * f - nx * 0.22, 0.07, sg.a[1] + dz * f - nz * 0.22); if (L > 0.01) c.obj.rotation.y = Math.atan2(dx, dz);
    }
  }
  function frameLoop(now) {
    raf = requestAnimationFrame(frameLoop);
    if (!visible || document.hidden) { last = now; return; }
    const dt = Math.min(0.05, (now - last) / 1000); last = now; t += still ? 0 : dt;
    if (fly) { const k = Math.min(1, (now - fly.t0) / fly.ms); const e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      controls.target.lerpVectors(fly.fromT, fly.toT, e); camera.position.lerpVectors(fly.fromP, fly.toP, e); if (k >= 1) fly = null; dirty = true; }
    controls.update();
    if (hoverAt) { const o = hit(hoverAt); const pk = o?.userData || null;
      if ((pk?.pick && JSON.stringify(pk.pick)) !== (hover && JSON.stringify(hover.pick))) { hover = pk?.pick ? pk : null; el.style.cursor = hover ? 'pointer' : '';
        if (hover?.rect) { const c = centerOf(hover.rect); const s = Math.max(hover.rect.w, hover.rect.d) * 0.78; hoverFrame.position.set(c.x, 0.2, c.z); hoverFrame.scale.set(s, s, 1); hoverFrame.visible = true; } else hoverFrame.visible = false;
        onHover?.(hover ? { label: hover.label, x: hoverAt.clientX, y: hoverAt.clientY } : null); }
      else if (hover) onHover?.({ label: hover.label, x: hoverAt.clientX, y: hoverAt.clientY });
      hoverAt = null; dirty = true; }
    if (!still) {
      const ph = phaseOf(t); stepCars(dt, ph); anim.forEach(fn => fn(t));
      if (lights && ph !== phaseWas) { phaseWas = ph; lightNodes.forEach((_, k) => { lights.setColorAt(k * 2, ph === 0 ? green : ph === 1 ? amber : red); lights.setColorAt(k * 2 + 1, ph === 2 ? green : ph === 3 ? amber : red); });
        if (lights.instanceColor) lights.instanceColor.needsUpdate = true; }
      if (ring.visible) { const k = 1 + Math.sin(t * 3) * 0.08; ring.scale.set(k, k, 1); ring.material.opacity = 0.65 + Math.sin(t * 3) * 0.3; }
      dirty = true;
    }
    const far = camera.position.distanceTo(controls.target) > 46;
    if (dirty) for (const g of [content, world]) for (const n of g.children) { if (!n.userData?.sign) continue;   // 🪧 a sign never fills the screen: it shrinks as you get close
      if (!n.userData.base) n.userData.base = n.scale.clone(); const f = Math.max(0.28, Math.min(1, camera.position.distanceTo(n.position) / 30)); n.scale.copy(n.userData.base).multiplyScalar(f);
      if (n.userData.small) n.visible = !far; }
    if (!dirty) return; dirty = false;
    if (composer) composer.render(); else renderer.render(scene, camera);
  }

  size(); raf = requestAnimationFrame(frameLoop);
  return {
    async setPlan(p, live = {}) {
      const key = `${p.kind}:${p.key || ''}:${p.islands.map(i => i.key).join(',')}`; const first = planKey !== key; plan = p;
      if (first) { planKey = key; await buildWorld(p); const f = frameAll(); camera.position.set(f.x + f.dist * 0.5, f.dist * 0.5, f.z + f.dist * 0.75); controls.target.set(f.x, 0, f.z); }   // a low, cinematic first look (≈ 30° up), not a map from above
      const nextSig = JSON.stringify([p.kind, p.key, p.lots.map(l => [l.id, l.kind, l.tag, Math.round(Math.log10(1 + l.power) * 1.6)]), p.markets.map(m => [m.key, usd(m.tvl), m.move == null ? null : Math.round(m.move)]),
        [...(live.raided || [])], live.fight ? [live.fight.id, live.fight.a?.pct, live.fight.b?.pct] : null, Object.values(live.marks || {}).map(x => JSON.stringify(x))]);
      if (first || nextSig !== sig) { sig = nextSig; await buildContent(p, live); }
      if (lights) { phaseWas = -1; lightNodes.forEach((_, k) => { lights.setColorAt(k * 2, green); lights.setColorAt(k * 2 + 1, red); }); if (lights.instanceColor) lights.instanceColor.needsUpdate = true; }
      dirty = true; return first;
    },
    flyTo, frameAll: () => flyTo(null),
    zoom(f) { const off = camera.position.clone().sub(controls.target); off.multiplyScalar(1 / f); const L = off.length(); if (L > controls.minDistance && L < controls.maxDistance) camera.position.copy(controls.target).add(off); dirty = true; },
    spin(on) { controls.autoRotate = !!on && !still; controls.autoRotateSpeed = 0.6; },
    dispose() { cancelAnimationFrame(raf); io?.disconnect(); ro?.disconnect(); controls.dispose(); clear(world); clear(content); composer?.dispose?.(); renderer.dispose(); renderer.domElement.remove(); },
  };
}
