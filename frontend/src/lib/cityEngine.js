// 🌃 THE CITY ENGINE (three.js) — CALM MOTION RULE (owner, 2026-10-22: "better than shit blinking til seizure"): nothing here flashes; a light
// breathes (≤ 0.4 Hz, ≤ 25 % brightness) or TURNS — activity is how fast a halo spins, never a strobe.
// — draws a plan from lib/cityPlan.js as a real 3D city (owner, 2026-10-22: "way better design … find free model
// sites and use the best" · "hella glow on cities and a day / night theme" · "more land, pizza spots, buildings outside the heart big af").
// Models: Kenney City Kit Commercial / Car Kit / City Kit Roads (CC0, public/assets/city, licences beside them). NIGHT: windows lit from the
// kit's own colour map, neon edges on every market tower, bloom; DAY: a sun, blue sky, glass that reflects instead of glowing. Cars drive the
// avenues and HOLD at red lights; people walk the promenades; every island sits in a ring of open land (parks, food stalls). Every market
// wears a billboard and a roof light whose pulse follows its volume; a pick is a ring on the ground (never a beam). `onAnchors` hands the page
// screen positions of 3D points (the real Fuse cards stand over the stadium pitch as DOM). Loaded only where WebGL exists
// (components/FeeCity3D.jsx falls back to the CSS city). Pauses off-screen / hidden tab; fx-lite = no bloom, fewer cars; reduced motion = still.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { centerOf, usd, apyTxt, LAND, FOOT } from './cityPlan';

const BASE = `${process.env.PUBLIC_URL || ''}/assets/city`;
const B = n => `${BASE}/commercial/building-${n}.glb`;
export const MODELS = {
  shop: ['a', 'b', 'c', 'd', 'h'].map(B), mid: ['e', 'f', 'g', 'i', 'k'].map(B), big: ['j', 'l', 'm', 'n'].map(B),
  sky: ['a', 'b', 'c', 'd', 'e'].map(k => `${BASE}/commercial/building-skyscraper-${k}.glb`),
  cars: ['sedan', 'taxi', 'police', 'suv', 'sedan-sports', 'hatchback-sports', 'delivery', 'suv-luxury'].map(k => `${BASE}/cars/${k}.glb`),
  lamp: [`${BASE}/roads/light-square.glb`], signal: [`${BASE}/roads/traffic-light.glb`],
};
const KIND = { mine: '#ffcc4d', family: '#b388ff', cpu: '#ff5d73', cartel: '#3ddc84', free: '#5b6577' };
const MKT = { dex: '#45e486', lend: '#f5c451', perps: '#ff5dbb', stake: '#6ad7ff', coin: '#ff8fa3', v2: '#ff9f45', v3: '#6ad7ff', dlmm: '#ffd36b', vault: '#3ddc84', rwa: '#e8e3d6' };
const FOOD = [['PIZZA', '#ff6a3d'], ['TACOS', '#ffd36b'], ['COFFEE', '#c98a5a'], ['BOBA', '#ff8fd0'], ['WINGS', '#ff9f45'], ['NOODLES', '#6ad7ff']];

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
  const m = mat.clone(); m.emissive = new THREE.Color('#ffffff'); m.emissiveMap = em; m.emissiveIntensity = 0.42; glowMats.set(mat.uuid, m); return m;
}
async function make(url, { lit = false } = {}) {
  const src = await load(url); if (!src) return new THREE.Group();
  const o = src.clone(true);
  o.traverse(n => { if (n.isMesh) { n.castShadow = false; n.receiveShadow = false; if (lit) n.material = litWindows(n.material); } });
  return o;
}
const sizeOf = o => new THREE.Box3().setFromObject(o).getSize(new THREE.Vector3());
// fit a model into w × d tiles, KEEPING ITS SHAPE (owner, 2026-10-22: "why do the buildings look like ramps" — stretching a model tall turned
// its sloped roof into a ramp). `h` only nudges the height, never more than 12 % past the model's own proportions; tall = a taller model.
function fit(o, w, d, h = null) {
  const s = sizeOf(o); const k = Math.min(w / Math.max(s.x, 0.01), d / Math.max(s.z, 0.01));
  o.scale.setScalar(k); if (h) o.scale.y = k * Math.max(0.9, Math.min(1.12, h / Math.max(s.y * k, 0.01))); return o;
}
// the model whose own height (at this footprint) is closest to the height wanted — a $1B market gets a real skyscraper, not a stretched shop
async function tallest(urls, w, d, h) {
  let best = null; let bestErr = Infinity;
  for (const u of urls) { const src = await load(u); if (!src) continue; const s = sizeOf(src); const k = Math.min(w / Math.max(s.x, 0.01), d / Math.max(s.z, 0.01)); const err = Math.abs(s.y * k - h);
    if (err < bestErr) { bestErr = err; best = u; } }
  return best || urls[0];
}

// ── canvas textures: signs, skies, water ripples, distant windows, awnings ──────────────────────────────────────────────────────────
function sign(lines, { color = '#d4af37', w = 512, glow = true } = {}) {
  const c = document.createElement('canvas'); const big = lines[0] || ''; const small = lines.slice(1).filter(Boolean);
  c.width = w; c.height = 96 + small.length * 44; const g = c.getContext('2d');
  g.fillStyle = 'rgba(6,8,14,.86)'; const r = 18; const W = c.width; const H = c.height;
  g.beginPath(); g.moveTo(r, 0); g.arcTo(W, 0, W, H, r); g.arcTo(W, H, 0, H, r); g.arcTo(0, H, 0, 0, r); g.arcTo(0, 0, W, 0, r); g.closePath(); g.fill();
  g.lineWidth = 4; g.strokeStyle = color; if (glow) { g.shadowColor = color; g.shadowBlur = 10; } g.stroke(); g.shadowBlur = 0;
  g.fillStyle = color; g.font = '800 46px "JetBrains Mono", ui-monospace, Menlo, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
  if (glow) { g.shadowColor = color; g.shadowBlur = 6; } g.fillText(big.slice(0, 18), W / 2, 50); g.shadowBlur = 0;
  g.fillStyle = '#e9e4d6'; g.font = '600 32px "JetBrains Mono", ui-monospace, Menlo, monospace';
  small.forEach((t, i) => g.fillText(String(t).slice(0, 26), W / 2, 100 + i * 44));
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sp.renderOrder = 20; const k = 0.0084; sp.scale.set(W * k, H * k, 1); sp.userData.sign = true; sp.userData.dispose = () => { tex.dispose(); sp.material.dispose(); }; return sp;
}
function gradient(stops) {
  const c = document.createElement('canvas'); c.width = 4; c.height = 512; const g = c.getContext('2d'); const gr = g.createLinearGradient(0, 0, 0, 512);
  stops.forEach(([at, col]) => gr.addColorStop(at, col)); g.fillStyle = gr; g.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const NIGHT_SKY = [[0, '#03040c'], [0.45, '#0b1230'], [0.72, '#2a1a44'], [0.86, '#6a3a2e'], [1, '#0a0b12']];
const DAY_SKY = [[0, '#2f6fc0'], [0.5, '#7fb6ea'], [0.8, '#cfe3f4'], [0.92, '#f6dcb4'], [1, '#c9d6e0']];
function noiseTexture(n = 128) {
  const c = document.createElement('canvas'); c.width = n; c.height = n; const g = c.getContext('2d'); const d = g.createImageData(n, n);
  for (let i = 0; i < n * n; i += 1) { const v = 110 + Math.random() * 40 + 30 * Math.sin(i * 0.07) * Math.cos(i * 0.013); d.data.set([v, v, v, 255], i * 4); }
  g.putImageData(d, 0, 0); const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping; return t;
}
function windowsTexture() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 64, 128);
  for (let y = 4; y < 124; y += 8) for (let x = 4; x < 60; x += 8) if (Math.random() < 0.42) { g.fillStyle = Math.random() < 0.75 ? '#ffcf7a' : Math.random() < 0.5 ? '#7fd3ff' : '#ff8fd0'; g.fillRect(x, y, 4, 4); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function radial(color = '#ffd27a') {
  const c = document.createElement('canvas'); c.width = 64; c.height = 64; const g = c.getContext('2d'); const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, color); gr.addColorStop(0.35, `${color}88`); gr.addColorStop(1, `${color}00`); g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function stripes(a, b) {
  const c = document.createElement('canvas'); c.width = 64; c.height = 16; const g = c.getContext('2d');
  for (let i = 0; i < 8; i += 1) { g.fillStyle = i % 2 ? b : a; g.fillRect(i * 8, 0, 8, 16); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const neon = (hex, k = 1.2) => new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(Math.min(1.5, k * 0.6)), toneMapped: false });   // capped: a lit sign, not a sun

// ── the engine ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
export function createCity(host, { onPick, onHover, onAnchors, lite = false, still = false, day = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: !lite, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lite ? 1 : 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.08;
  host.appendChild(renderer.domElement); renderer.domElement.className = 'fc3-canvas';
  const scene = new THREE.Scene(); const skyN = gradient(NIGHT_SKY); const skyD = gradient(DAY_SKY); scene.background = skyN; scene.fog = new THREE.Fog('#0a1022', 90, 330);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.4, 900);
  const controls = new OrbitControls(camera, renderer.domElement);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, minPolarAngle: 0.3, maxPolarAngle: 1.24, minDistance: 8, maxDistance: 260, screenSpacePanning: false, zoomSpeed: 0.9 });
  const hemi = new THREE.HemisphereLight('#4a5a95', '#0b0b14', 1.25); scene.add(hemi);
  const key = new THREE.DirectionalLight('#a9bcff', 1.35); key.position.set(-60, 90, -40); scene.add(key);
  const dusk = new THREE.DirectionalLight('#ffb35a', 0.55); dusk.position.set(80, 14, 70); scene.add(dusk);
  let composer = null; let bloom = null;
  if (!lite) { composer = new EffectComposer(renderer); composer.addPass(new RenderPass(scene, camera));
    bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.42, 0.4, 0.86); composer.addPass(bloom); composer.addPass(new OutputPass()); }
  // materials the day / night switch retunes
  const M = { water: new THREE.MeshStandardMaterial({ color: '#071528', roughness: 0.28, metalness: 0.55, emissive: '#02060f' }),
    grass: new THREE.MeshStandardMaterial({ color: '#173a22', roughness: 1 }), walk: new THREE.MeshStandardMaterial({ color: '#3a352c', roughness: 0.9 }),
    asphalt: new THREE.MeshStandardMaterial({ color: '#15171d', roughness: 0.95 }), quay: new THREE.MeshStandardMaterial({ color: '#262a33', roughness: 0.9 }),
    leaf: new THREE.MeshStandardMaterial({ color: '#1f6b3a', roughness: 1 }), trunk: new THREE.MeshStandardMaterial({ color: '#4a3020', roughness: 1 }),
    far: new THREE.MeshStandardMaterial({ color: '#0b0f1c', emissive: '#ffffff', emissiveMap: windowsTexture(), emissiveIntensity: 0.32, roughness: 1 }) };
  let mode = day ? 'day' : 'night'; let sky = {};

  const world = new THREE.Group(); let content = new THREE.Group(); scene.add(world, content); let sig = null;
  const pickables = []; const anim = []; let cars = []; let walkers = null; let lights = null; let lightNodes = []; let planKey = null; let plan = null; let anchors = [];
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.6, 2.0, 56), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffd76a').multiplyScalar(1.4), toneMapped: false, transparent: true, side: THREE.DoubleSide }));
  ring.rotation.x = -Math.PI / 2; ring.visible = false; scene.add(ring);
  const hoverFrame = new THREE.Mesh(new THREE.RingGeometry(1.0, 1.1, 4, 1), new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.85, toneMapped: false, side: THREE.DoubleSide }));
  hoverFrame.rotation.set(-Math.PI / 2, 0, Math.PI / 4); hoverFrame.visible = false; scene.add(hoverFrame);

  const clear = g => { while (g.children.length) { const c = g.children.pop(); c.traverse(n => { n.userData?.dispose?.(); if (n.isInstancedMesh) n.dispose(); }); } };
  const box = (w, h, d, color, x, y, z, parent = world, mat = null) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat || new THREE.MeshStandardMaterial({ color, roughness: 0.92 })); m.position.set(x, y, z); parent.add(m); return m; };
  const worldPicks = [];   // the gates live with the world (they survive a content swap)
  const proxy = (r, h, pick, label, inWorld = false) => { const m = new THREE.Mesh(new THREE.BoxGeometry(r.w, h, r.d), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false }));
    const c = centerOf(r); m.position.set(c.x, h / 2, c.z); m.userData = { pick, label, rect: r }; (inWorld ? world : content).add(m); (inWorld ? worldPicks : pickables).push(m); return m; };
  const frame = (r, color, parent = content, y = 0.1, t = 0.06) => { const g = new THREE.Group(); const mat = neon(color, 1.05);
    [[r.w, t, r.x + r.w / 2, r.z], [r.w, t, r.x + r.w / 2, r.z + r.d], [t, r.d, r.x, r.z + r.d / 2], [t, r.d, r.x + r.w, r.z + r.d / 2]].forEach(([w, d, x, z]) => box(w, 0.05, d, null, x, y, z, g, mat));
    parent.add(g); return g; };
  // ✨ neon edges up a tower's four corners + a crown — the "hella glow" (night), a thin trim by day
  const edges = (o, c, color, parent = content) => { const s = sizeOf(o); const g = new THREE.Group(); const mat = neon(color, 0.9); const hx = s.x / 2 + 0.02; const hz = s.z / 2 + 0.02;
    [[-hx, -hz], [hx, -hz], [hx, hz], [-hx, hz]].forEach(([dx, dz]) => box(0.03, s.y, 0.03, null, c.x + dx, 0.12 + s.y / 2, c.z + dz, g, mat));
    frame({ x: c.x - hx, z: c.z - hz, w: hx * 2, d: hz * 2 }, color, g, 0.12 + s.y, 0.06); parent.add(g); return g; };

  // ── the static world: water, sky dressing, islands + their land, roads, bridges, lamps, stoplights, traffic, people ──
  async function buildWorld(p) {
    clear(world); cars = []; lightNodes = []; lights = null; worldPicks.length = 0; walkers = null;
    const bx = p.bounds; const W = bx.x1 - bx.x0; const D = bx.z1 - bx.z0; const cx = (bx.x0 + bx.x1) / 2; const cz = (bx.z0 + bx.z1) / 2;
    const ripple = noiseTexture(); ripple.repeat.set(W / 6, D / 6); M.water.bumpMap = ripple; M.water.bumpScale = 0.6; M.water.needsUpdate = true;
    const water = new THREE.Mesh(new THREE.PlaneGeometry(W + 400, D + 400), M.water);
    water.rotation.x = -Math.PI / 2; water.position.set(cx, -0.55, cz); world.add(water); anim.push(t => { ripple.offset.set(t * 0.012, t * 0.007); });
    // stars + moon / sun + a far skyline ring
    const sg = new THREE.BufferGeometry(); const sp = []; for (let i = 0; i < 800; i += 1) { const a = Math.random() * Math.PI * 2; const e = 0.15 + Math.random() * 1.2; sp.push(Math.cos(a) * 480 * Math.cos(e), 480 * Math.sin(e), Math.sin(a) * 480 * Math.cos(e)); }
    sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
    sky.stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: '#dfe6ff', size: 1.4, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85 })); sky.stars.position.set(cx, 0, cz); world.add(sky.stars);
    sky.moon = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial('#fff4d6'), fog: false, transparent: true, depthWrite: false })); sky.moon.scale.set(60, 60, 1); sky.moon.position.set(cx - 150, 120, cz - 280); world.add(sky.moon);
    const far = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), M.far, 110); const m4 = new THREE.Matrix4(); const R = Math.max(W, D) / 2 + 90;
    for (let i = 0; i < 110; i += 1) { const a = (i / 110) * Math.PI * 2; const h = 10 + ((i * 37) % 38); const w = 5 + ((i * 13) % 6);
      m4.compose(new THREE.Vector3(cx + Math.cos(a) * R, h / 2 - 0.6, cz + Math.sin(a) * R), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -a, 0)), new THREE.Vector3(w, h, w)); far.setMatrixAt(i, m4); }
    world.add(far);
    // islands: the open land (grass + a promenade ring + a quay wall) and the asphalt grid on top; a neon trim on every shore
    const trees = []; const walkPaths = [];
    for (const i of p.islands) {
      box(i.w + 0.8, 1.1, i.d + 0.8, null, i.x + i.w / 2, -0.56, i.z + i.d / 2, world, M.quay);
      box(i.w, 0.08, i.d, null, i.x + i.w / 2, -0.02, i.z + i.d / 2, world, M.grass);
      const pr = { x: i.x + 0.5, z: i.z + 0.5, w: i.w - 1, d: i.d - 1 };   // the promenade: a paved ring at the shore
      [[pr.w, 0.9, pr.x + pr.w / 2, pr.z + 0.45], [pr.w, 0.9, pr.x + pr.w / 2, pr.z + pr.d - 0.45], [0.9, pr.d, pr.x + 0.45, pr.z + pr.d / 2], [0.9, pr.d, pr.x + pr.w - 0.45, pr.z + pr.d / 2]]
        .forEach(([w, d, x, z]) => box(w, 0.05, d, null, x, 0.03, z, world, M.walk));
      walkPaths.push([[pr.x + 0.45, pr.z + 0.45], [pr.x + pr.w - 0.45, pr.z + 0.45], [pr.x + pr.w - 0.45, pr.z + pr.d - 0.45], [pr.x + 0.45, pr.z + pr.d - 0.45]]);
      box(i.gw, 0.06, i.gd, null, i.gx + i.gw / 2, 0.02, i.gz + i.gd / 2, world, M.asphalt);
      frame({ x: i.x - 0.4, z: i.z - 0.4, w: i.w + 0.8, d: i.d + 0.8 }, i.color || '#d4af37', world, 0.03, 0.07);
      // trees + food stalls + benches on the land ring (never on a bridge landing)
      const lane = (x, z) => p.bridges.concat(p.gates).some(b => (b.axis === 'x' ? Math.abs(z - b.z) < 1.4 : Math.abs(x - b.x) < 1.4));
      const ringPts = []; for (let x = i.x + 1.6; x < i.x + i.w - 1.4; x += 2.2) ringPts.push([x, i.z + 1.7], [x, i.z + i.d - 1.7]);
      for (let z = i.z + 3.8; z < i.z + i.d - 3.6; z += 2.2) ringPts.push([i.x + 1.7, z], [i.x + i.w - 1.7, z]);
      let food = 0;
      ringPts.forEach(([x, z], k) => { if (lane(x, z)) return;
        if (k % 9 === 4 && food < 3) { food += 1; stall(x, z, FOOD[(k + i.key.length) % FOOD.length]); return; }
        trees.push([x + ((k * 7) % 5) * 0.08, z]); });
      const s = sign([i.name, i.sub], { color: i.color || '#d4af37', w: 600 }); s.position.set(i.x + i.w / 2, 1.6, i.z + i.d + 0.4); s.scale.multiplyScalar(1.4); world.add(s);
    }
    function stall(x, z, [word, col]) {   // 🍕 a food stall: counter, striped awning, a neon word, a warm glow on the ground
      const g = new THREE.Group(); g.position.set(x, 0, z); world.add(g);
      box(0.9, 0.5, 0.7, '#3a2a1a', 0, 0.3, 0, g);
      const aw = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.06, 0.9), new THREE.MeshStandardMaterial({ map: stripes(col, '#f4efe4'), roughness: 0.8 })); aw.position.set(0, 0.78, 0.1); aw.rotation.x = 0.18; g.add(aw);
      const gl = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 2.4), new THREE.MeshBasicMaterial({ map: radial(col), transparent: true, opacity: 0.18, depthWrite: false }));
      gl.rotation.x = -Math.PI / 2; gl.position.y = 0.06; g.add(gl);
      const s = sign([word], { color: col, w: 280 }); s.position.set(0, 1.4, 0); s.scale.multiplyScalar(0.55); s.userData.small = true; g.add(s);
    }
    // the trees: one instanced trunk + one instanced crown for every island
    const trunk = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.07, 0.1, 0.5, 6), M.trunk, Math.max(1, trees.length));
    const crown = new THREE.InstancedMesh(new THREE.ConeGeometry(0.42, 1.1, 8), M.leaf, Math.max(1, trees.length));
    trees.forEach(([x, z], k) => { m4.makeTranslation(x, 0.25, z); trunk.setMatrixAt(k, m4); m4.compose(new THREE.Vector3(x, 0.95, z), new THREE.Quaternion(), new THREE.Vector3(1, 0.85 + (k % 3) * 0.15, 1)); crown.setMatrixAt(k, m4); });
    world.add(trunk, crown);
    // lane dashes (one instanced mesh)
    const dashes = []; for (const r of p.roads) for (const s of r.segs) {
      if (s.axis === 'x') for (let x = s.x0 + 0.4; x < s.x1 - 0.3; x += 0.7) dashes.push([x, s.z, 0]);
      else for (let z = s.z0 + 0.4; z < s.z1 - 0.3; z += 0.7) dashes.push([s.x, z, Math.PI / 2]); }
    const dm = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.32, 0.045), new THREE.MeshBasicMaterial({ color: '#c9b26a' }), Math.max(1, dashes.length));
    dashes.forEach(([x, z, a], k) => { m4.compose(new THREE.Vector3(x, 0.06, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, a)), new THREE.Vector3(1, 1, 1)); dm.setMatrixAt(k, m4); });
    world.add(dm);
    // bridges + gates: a deck on pillars, rails, two pylons with lit tips, the cables between them
    const deck = (b, gate) => { const len = Math.abs(b.b - b.a); const mid = (b.a + b.b) / 2; const along = b.axis === 'x';
      const g = new THREE.Group(); world.add(g);
      box(along ? len + 1 : 1.5, 0.22, along ? 1.5 : len + 1, null, along ? mid : b.x, 0.02, along ? b.z : mid, g, M.asphalt);
      [-0.76, 0.76].forEach(o => box(along ? len : 0.06, 0.25, along ? 0.06 : len, '#8a7a4a', along ? mid : b.x + o, 0.25, along ? b.z + o : mid, g));
      [0.22, 0.78].forEach(f => { const at = b.a + (b.b - b.a) * f; [-0.84, 0.84].forEach(o => { box(0.2, 3.6, 0.2, '#3a3020', along ? at : b.x + o, 1.8, along ? b.z + o : at, g);
        box(0.2, 0.2, 0.2, null, along ? at : b.x + o, 3.65, along ? b.z + o : at, g, neon(gate ? '#ff8fa3' : '#ffd76a', 1.4)); }); });
      const cable = neon(gate ? '#ff8fa3' : '#ffd76a', 0.75);
      [-0.84, 0.84].forEach(o => { const a0 = b.a + (b.b - b.a) * 0.22; const a1 = b.a + (b.b - b.a) * 0.78; const pts = [];
        for (let k = 0; k <= 16; k += 1) { const t = k / 16; const at = a0 + (a1 - a0) * t; const y = 3.6 - Math.sin(t * Math.PI) * 2.6; pts.push(along ? new THREE.Vector3(at, y, b.z + o) : new THREE.Vector3(b.x + o, y, at)); }
        g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: cable.color, toneMapped: false }))); });
      for (let k = 1; k < 5; k += 1) { const at = b.a + ((b.b - b.a) * k) / 5; box(0.34, 0.7, 0.34, '#2b2e36', along ? at : b.x, -0.38, along ? b.z : at, g); }
      return g; };
    p.bridges.forEach(b => deck(b, false));
    p.gates.forEach(gt => { deck(gt, true); const end = gt.at === 'n' || gt.at === 'w' ? gt.a : gt.b;
      const s = sign([gt.name, gt.held ? `▸ ${gt.held}` : '▸ cross'], { color: '#ff8fa3', w: 460 });
      const pos = gt.axis === 'x' ? [end, 2.8, gt.z] : [gt.x, 2.8, end]; s.position.set(...pos); world.add(s);
      proxy({ x: pos[0] - 1.8, z: pos[2] - 1.8, w: 3.6, d: 3.6 }, 3.4, { gate: gt.key }, `Cross to ${gt.name}`, true); });
    // street lamps on the grid corners (instanced) + their glow bulbs + the light they throw on the street
    const lampAt = []; for (const r of p.roads) r.nodes.forEach((n, k) => { if (k % 2 === 0) lampAt.push([n.x + 0.42, n.z + 0.42]); });
    const lampSrc = await load(MODELS.lamp[0]);
    if (lampSrc) lampSrc.traverse(n => { if (!n.isMesh) return; const im = new THREE.InstancedMesh(n.geometry, n.material, Math.max(1, lampAt.length));
      lampAt.forEach(([x, z], k) => { m4.compose(new THREE.Vector3(x, 0.05, z), new THREE.Quaternion(), new THREE.Vector3(1.6, 1.6, 1.6)); im.setMatrixAt(k, m4); }); world.add(im); });
    sky.bulbs = new THREE.InstancedMesh(new THREE.SphereGeometry(0.06, 8, 6), neon('#ffd27a', 1.3), Math.max(1, lampAt.length));
    lampAt.forEach(([x, z], k) => { m4.makeTranslation(x, 1.0, z - 0.3); sky.bulbs.setMatrixAt(k, m4); }); world.add(sky.bulbs);
    sky.pools = new THREE.InstancedMesh(new THREE.PlaneGeometry(1.8, 1.8), new THREE.MeshBasicMaterial({ map: radial('#ffc46b'), transparent: true, opacity: 0.16, depthWrite: false, toneMapped: false }), Math.max(1, lampAt.length));
    lampAt.forEach(([x, z], k) => { m4.compose(new THREE.Vector3(x, 0.07, z - 0.3), new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0)), new THREE.Vector3(1, 1, 1)); sky.pools.setMatrixAt(k, m4); }); world.add(sky.pools);
    // 🚦 stoplights: the kit's pole + a lamp per direction whose colour follows the phase
    lightNodes = p.lights.map(n => ({ x: n.x, z: n.z }));
    const sigSrc = await load(MODELS.signal[0]);
    if (sigSrc) sigSrc.traverse(n => { if (!n.isMesh) return; const im = new THREE.InstancedMesh(n.geometry, n.material, Math.max(1, lightNodes.length));
      lightNodes.forEach((l, k) => { m4.compose(new THREE.Vector3(l.x - 0.55, 0.05, l.z - 0.55), new THREE.Quaternion(), new THREE.Vector3(1.9, 1.9, 1.9)); im.setMatrixAt(k, m4); }); world.add(im); });
    lights = new THREE.InstancedMesh(new THREE.SphereGeometry(0.12, 10, 8), new THREE.MeshBasicMaterial({ toneMapped: false }), Math.max(2, lightNodes.length * 2));
    lightNodes.forEach((l, k) => { m4.makeTranslation(l.x - 0.55, 1.04, l.z - 0.42); lights.setMatrixAt(k * 2, m4); m4.makeTranslation(l.x - 0.42, 1.04, l.z - 0.55); lights.setMatrixAt(k * 2 + 1, m4); });
    world.add(lights);
    // 🚗 traffic on every loop + both lanes of every bridge
    const loops = [...p.loops, ...p.bridges.map(b => (b.axis === 'x' ? [[b.a - 0.5, b.z], [b.b + 0.5, b.z], [b.b + 0.5, b.z], [b.a - 0.5, b.z]] : [[b.x, b.a - 0.5], [b.x, b.b + 0.5], [b.x, b.b + 0.5], [b.x, b.a - 0.5]]))];
    const perLoop = lite ? 1 : 4; const headTex = radial('#fff1c4');
    for (let li = 0; li < loops.length; li += 1) {
      const pts = loops[li]; const segs = pts.map((a, k) => { const b = pts[(k + 1) % pts.length]; return { a, b, len: Math.hypot(b[0] - a[0], b[1] - a[1]) }; });
      const total = segs.reduce((s, x) => s + x.len, 0); if (total < 2) continue;
      segs.forEach(s => { s.stops = lightNodes.filter(n => (Math.abs(s.a[1] - s.b[1]) < 0.01 ? Math.abs(n.z - s.a[1]) < 0.05 && n.x > Math.min(s.a[0], s.b[0]) && n.x < Math.max(s.a[0], s.b[0])
        : Math.abs(n.x - s.a[0]) < 0.05 && n.z > Math.min(s.a[1], s.b[1]) && n.z < Math.max(s.a[1], s.b[1]))).map(n => Math.hypot(n.x - s.a[0], n.z - s.a[1])).sort((x, y) => x - y); });
      const n = li < p.loops.length ? perLoop + (li === 0 ? 3 : 0) : (lite ? 0 : 2);
      for (let k = 0; k < n; k += 1) {
        const o = await make(MODELS.cars[(li * 3 + k) % MODELS.cars.length]); fit(o, 0.42, 0.8);
        const car = new THREE.Group(); car.add(o);
        const hl = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1.6), new THREE.MeshBasicMaterial({ map: headTex, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false }));
        hl.rotation.x = -Math.PI / 2; hl.position.set(0, 0.06, 1.1); hl.userData.head = true; car.add(hl);
        [-0.12, 0.12].forEach(x => { const tl = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.05, 0.02), neon('#ff2a3d', 2.8)); tl.position.set(x, 0.17, -0.41); car.add(tl); });
        world.add(car); cars.push({ obj: car, segs, total, s: (total / n) * k + li * 1.7, v: 0, vmax: 1.8 + ((li + k) % 3) * 0.4, loop: li });
      }
    }
    // 🚶 people on the promenades (one instanced mesh, moved every frame)
    const N = lite ? 0 : Math.min(90, walkPaths.length * 14);
    if (N) { walkers = { mesh: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.07, 0.22, 3, 6), new THREE.MeshStandardMaterial({ roughness: 0.8 }), N), list: [] };
      const col = new THREE.Color(); const tints = ['#e8e3d6', '#d4af37', '#ff8fa3', '#6ad7ff', '#b388ff', '#45e486', '#2a2a30'];
      for (let k = 0; k < N; k += 1) { const path = walkPaths[k % walkPaths.length]; const segs = path.map((a, j) => { const b = path[(j + 1) % 4]; return { a, b, len: Math.hypot(b[0] - a[0], b[1] - a[1]) }; });
        const total = segs.reduce((s, x) => s + x.len, 0); walkers.list.push({ segs, total, s: Math.random() * total, v: (0.35 + Math.random() * 0.3) * (k % 2 ? 1 : -1), off: (k % 3 - 1) * 0.22 });
        walkers.mesh.setColorAt(k, col.set(tints[k % tints.length])); }
      world.add(walkers.mesh); }
    applyMode();
  }

  // ── content: plots, landmarks, markets, places (rebuilt on every data refresh, built OFF-screen then swapped) ──
  async function buildContent(p, live = {}) {
    const old = content; content = new THREE.Group(); const keep = anim.slice(0, 1); const was = pickables.splice(0); anim.length = 0; anim.push(...keep);
    const side = (r, color = '#30333c') => box(r.w, 0.12, r.d, color, r.x + r.w / 2, 0.08, r.z + r.d / 2, content);
    // 🌳 a building's YARD: its cell is bigger than the building (FOOT) — grass round it + a tree in each free corner (one instanced set per refresh)
    const yardAt = []; const yard = (r, fw) => { if (r.w - fw < 1.1) return; box(r.w - 0.3, 0.04, r.d - 0.3, null, r.x + r.w / 2, 0.15, r.z + r.d / 2, content, M.grass);
      [[0.55, 0.55], [r.w - 0.55, 0.55], [0.55, r.d - 0.55], [r.w - 0.55, r.d - 0.55]].forEach(([dx, dz]) => yardAt.push([r.x + dx, r.z + dz])); };
    for (const l of p.lots) {
      side(l.rect, '#2d3038'); const c = centerOf(l.rect);
      if (l.kind === 'free') {   // a free plot is LAND: a park, a car park, or a vacant building with a FOR SALE sign
        if (l.seed % 3 === 2) { const o = await make(MODELS.mid[l.seed % MODELS.mid.length], { lit: true }); yard(l.rect, FOOT.lot); fit(o, Math.min(FOOT.lot, l.rect.w - 0.8), Math.min(FOOT.lot, l.rect.d - 0.8)); o.position.set(c.x, 0.14, c.z); o.rotation.y = (l.seed % 4) * (Math.PI / 2);
          o.traverse(n => { if (n.isMesh) { n.material = n.material.clone(); n.material.color.multiplyScalar(0.62); n.material.emissiveIntensity = 0.12; } }); content.add(o);
          const fs = sign(['FOR SALE'], { color: '#c9b38a', w: 300, glow: false }); fs.position.set(c.x, sizeOf(o).y + 0.6, c.z); fs.scale.multiplyScalar(0.55); fs.userData.small = true; content.add(fs); }
        else if (l.seed % 3 === 1) { box(l.rect.w - 0.3, 0.05, l.rect.d - 0.3, null, c.x, 0.15, c.z, content, M.grass);
          for (let t = 0; t < 5; t += 1) { const tr = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.9, 7), M.leaf); tr.position.set(c.x - 0.9 + (t % 3) * 0.9, 0.62, c.z + (t < 3 ? -0.5 : 0.5)); content.add(tr); } }
        else { box(l.rect.w - 0.3, 0.04, l.rect.d - 0.3, '#1b1d24', c.x, 0.14, c.z, content);
          for (let k = 0; k < 3; k += 1) { const o = await make(MODELS.cars[(l.seed + k) % MODELS.cars.length]); fit(o, 0.4, 0.8); o.position.set(c.x - 0.8 + k * 0.8, 0.15, c.z); content.add(o); } }
        proxy(l.rect, 0.8, l.pick, 'For sale'); continue;
      }
      const lvl = Math.max(1, Math.min(6, Math.round(Math.log10(1 + l.power) * 1.6)));
      const set = l.home || lvl >= 5 ? MODELS.sky : lvl >= 3 ? MODELS.big : MODELS.mid;
      const fw = Math.min(FOOT.lot, l.rect.w - 0.6); yard(l.rect, fw);
      const o = await make(set[l.seed % set.length], { lit: true }); fit(o, fw, Math.min(FOOT.lot, l.rect.d - 0.6));
      o.position.set(c.x, 0.14, c.z); o.rotation.y = (l.seed % 4) * (Math.PI / 2); content.add(o);
      const shut = l.state === 'shut';   // 💡 an unfunded turf block goes dark: windows off, the walls dimmed, a grey frame, "SHUT" on its sign
      if (shut) o.traverse(n => { if (n.isMesh) { n.material = n.material.clone(); n.material.color.multiplyScalar(0.42); n.material.emissiveIntensity = 0.02; } });
      const h = sizeOf(o).y; const col = shut ? '#6b6f78' : l.link ? MKT[l.link.kind] || KIND[l.kind] : KIND[l.kind] || KIND.family; frame(l.rect, col);
      if (l.launch?.symbol) {   // 🚀 the family's pinned launch: a neon spire beside its home with the ticker on top
        const sp = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.16, h + 1.6, 8), neon('#ff9f45', 1.4)); sp.position.set(c.x + l.rect.w / 2 - 0.45, (h + 1.6) / 2 + 0.14, c.z - l.rect.d / 2 + 0.45); content.add(sp);
        const ls = sign([`LAUNCH $${String(l.launch.symbol).slice(0, 10)}`], { color: '#ff9f45', w: 300 }); ls.position.set(sp.position.x, h + 2.2, sp.position.z); ls.scale.multiplyScalar(0.6); content.add(ls);
        anim.push(t => { sp.scale.x = sp.scale.z = 1 + 0.06 * Math.sin(t * 1.4); }); }
      if (l.kind === 'mine' || l.link) edges(o, c, col);
      const lines = shut ? [`[${l.tag}] · SHUT`] : l.link ? [`[${l.tag}] ${l.link.sym}`, `${l.link.proto} · APY ${apyTxt(l.link.apy)}`] : l.tag ? [`[${l.tag}]`] : [];
      if (lines.length) { const s = sign(lines, { color: col, w: l.link ? 420 : 260, glow: l.kind === 'mine' || !!l.link }); s.position.set(c.x, h + 0.9, c.z); s.scale.multiplyScalar(l.link ? 0.85 : 0.7); s.userData.small = !l.link; content.add(s); }
      const roof = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 8), neon(col, 3)); roof.position.set(c.x, h + 0.3, c.z); roof.visible = !shut; content.add(roof);
      if (l.link) anim.push(t => { roof.scale.setScalar(0.95 + 0.08 * Math.sin(t * 1.6)); });   // calm: a slow breath, never a flash
      if (l.owner && live.raided?.has(l.owner)) { const rf = frame(l.rect, '#ff2a3d', content, 0.18, 0.14); const rm = rf.children[0]?.material; anim.push(t => { if (rm) rm.color.set('#ff2a3d').multiplyScalar(1.15 + 0.2 * Math.sin(t * 1.4)); }); }   // under raid: a steady red ring that breathes
      proxy(l.rect, h + 0.3, l.pick, l.link ? `[${l.tag}] · ${l.link.sym}` : l.tag ? `[${l.tag}]` : 'Plot');
    }
    for (const m of p.marks) { side(m.rect, '#33302a'); await landmark(m, live); }
    if (p.plaza) { const r = p.plaza; box(r.w, 0.12, r.d, '#4a4235', r.x + r.w / 2, 0.08, r.z + r.d / 2, content);
      const c = centerOf({ ...r, x: r.x + 6, w: r.w - 12 });   // the fountain between the Wire (west) and the Job Board (east)
      const f1 = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.3, 0.3, 28), new THREE.MeshStandardMaterial({ color: '#6b5a3a', roughness: 0.6 })); f1.position.set(c.x, 0.28, c.z); content.add(f1);
      const jet = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.2, 1.4, 10), new THREE.MeshBasicMaterial({ color: new THREE.Color('#9fe3ff').multiplyScalar(2), toneMapped: false, transparent: true, opacity: 0.7 }));
      jet.position.set(c.x, 1.05, c.z); content.add(jet); anim.push(t => { jet.scale.y = 0.85 + Math.sin(t * 3) * 0.15; });
      for (let k = 0; k < 8; k += 1) { const tr = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.9, 7), M.leaf); tr.position.set(r.x + 1.2 + k * 2.4, 0.6, r.z + (k % 2 ? r.d - 0.5 : 0.5)); content.add(tr); }
      const sg = sign(['FEE PLAZA'], { color: '#d4af37', w: 360 }); sg.position.set(c.x, 2.6, c.z); content.add(sg); }
    for (const m of p.markets) {   // 🏦 a real market / pool: a tower by TVL, neon edges, a billboard, a roof light pulsing at its volume
      side(m.rect, '#2a2e2a'); const c = centerOf(m.rect); const col = MKT[m.kind] || '#45e486';
      const want = Math.max(2.4, m.h * 2.1); const pool_ = want > 6 ? MODELS.sky : want > 3.6 ? [...MODELS.big, ...MODELS.sky.slice(0, 2)] : [...MODELS.mid, ...MODELS.big];
      const fw = Math.min(FOOT.tower, m.rect.w - 0.7); const fd = Math.min(FOOT.tower, m.rect.d - 0.7); yard(m.rect, fw);
      const o = await make(await tallest(pool_, fw, fd, want), { lit: true }); fit(o, fw, fd, want);
      o.position.set(c.x, 0.14, c.z); content.add(o); const h = sizeOf(o).y;
      const tone = m.kind === 'coin' && m.move != null ? (m.move >= 0 ? '#45e486' : '#ff5d73') : col;
      edges(o, c, tone);
      const beacon = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.06, 8, 30), neon(tone, 1.5)); beacon.rotation.x = Math.PI / 2; beacon.position.set(c.x, h + 0.35, c.z); content.add(beacon);
      const hz = m.hz || 1; beacon.rotation.y = 0.35;   // activity = how FAST the halo turns (volume), never a flash
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), neon(tone, 1.8)); content.add(dot);
      anim.push(t => { const a = t * hz * 1.6; beacon.rotation.z = a; dot.position.set(c.x + Math.cos(a) * 0.62, h + 0.35, c.z + Math.sin(a) * 0.62); beacon.scale.setScalar(1 + 0.04 * Math.sin(t * 1.2)); });
      frame(m.rect, col);
      const sub = m.pool ? `${m.proto} · APY ${apyTxt(m.apy)}` : m.kind === 'coin' ? `${usd(m.tvl)} MC${m.move != null ? ` · ${m.move >= 0 ? '+' : ''}${Number(m.move).toFixed(1)}%` : ''}` : `TVL ${usd(m.tvl)}`;
      const s = sign(m.pool ? [m.name, sub, `TVL ${usd(m.tvl)}`] : [m.name, sub], { color: tone, w: 440 }); s.position.set(c.x, h + 1.7, c.z); content.add(s);
      proxy(m.rect, h + 0.4, m.pick, m.pool ? `${m.name} · ${m.proto}` : m.name);
    }
    for (const x of p.spare) { side(x.rect, '#25272d'); const c = centerOf(x.rect); const all = [...MODELS.shop, ...MODELS.mid];
      const o = await make(all[Math.abs(Math.round(x.rect.x * 7 + x.rect.z * 3)) % all.length], { lit: true }); yard(x.rect, FOOT.tower - 0.6); fit(o, Math.min(FOOT.tower - 0.6, x.rect.w - 1), Math.min(FOOT.tower - 0.6, x.rect.d - 1)); o.position.set(c.x, 0.14, c.z); content.add(o); }
    for (const pl of p.places) await place(pl, yard);
    if (yardAt.length) { const m4 = new THREE.Matrix4(); const crown = new THREE.InstancedMesh(new THREE.ConeGeometry(0.3, 0.8, 7), M.leaf, yardAt.length);
      const trunk = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.05, 0.07, 0.3, 6), M.trunk, yardAt.length);
      yardAt.forEach(([x, z], k) => { m4.makeTranslation(x, 0.7, z); crown.setMatrixAt(k, m4); m4.makeTranslation(x, 0.3, z); trunk.setMatrixAt(k, m4); }); content.add(crown, trunk); }
    scene.add(content); scene.remove(old); clear(old); was.length = 0;
    applyMode();
  }

  async function landmark(m, live) {
    const r = m.rect; const c = centerOf(r); const lv = live.marks?.[m.key] || m.live || {};
    if (m.key === 'arena') {   // ⚔ the stadium: a lathe bowl, crowd, a lit pitch, four floodlight masts (the real Fuse cards stand on the pitch as DOM)
      const g = new THREE.Group(); g.position.set(c.x, 0.14, c.z); content.add(g);
      const prof = [[2.3, 0], [2.4, 0.15], [3.1, 1.25], [3.25, 1.35], [3.25, 0]].map(([x, y]) => new THREE.Vector2(x, y));
      const bowl = new THREE.Mesh(new THREE.LatheGeometry(prof, 56), new THREE.MeshStandardMaterial({ color: '#3a3d48', roughness: 0.7, side: THREE.DoubleSide }));
      const ky = Math.max(1, r.d / 11); bowl.scale.set(r.w / 6.6, 1.4 * ky, r.d / 6.6); g.add(bowl);   // taller stands on a bigger pitch
      const rim = new THREE.Mesh(new THREE.TorusGeometry(3.25, 0.05, 6, 80), neon('#ffd76a', 2.6)); rim.rotation.x = Math.PI / 2; rim.position.y = 1.9 * ky; rim.scale.set(r.w / 6.6, r.d / 6.6, 1); g.add(rim);
      const pc = document.createElement('canvas'); pc.width = 256; pc.height = 160; const pg = pc.getContext('2d');
      for (let i = 0; i < 8; i += 1) { pg.fillStyle = i % 2 ? '#1e7a3c' : '#22883f'; pg.fillRect(i * 32, 0, 32, 160); }
      pg.strokeStyle = '#e8f5e8'; pg.lineWidth = 3; pg.strokeRect(8, 8, 240, 144); pg.beginPath(); pg.moveTo(128, 8); pg.lineTo(128, 152); pg.stroke(); pg.beginPath(); pg.arc(128, 80, 22, 0, Math.PI * 2); pg.stroke();
      const pt = new THREE.CanvasTexture(pc); pt.colorSpace = THREE.SRGBColorSpace;
      const pitch = new THREE.Mesh(new THREE.PlaneGeometry(r.w * 0.62, r.d * 0.6), new THREE.MeshStandardMaterial({ map: pt, roughness: 0.9, emissive: '#0a3a18', emissiveIntensity: 0.7 }));
      pitch.rotation.x = -Math.PI / 2; pitch.position.y = 0.06; g.add(pitch);
      const crowd = new THREE.InstancedMesh(new THREE.BoxGeometry(0.14, 0.18, 0.14), new THREE.MeshStandardMaterial({ roughness: 1 }), 420); const m4 = new THREE.Matrix4(); const col = new THREE.Color();
      for (let k = 0; k < 420; k += 1) { const a = (k / 420) * Math.PI * 2 * 3; const t = (k % 3) / 3; const rr = 2.55 + t * 0.55; m4.makeTranslation(Math.cos(a) * rr * r.w / 6.6, (0.45 + t * 1.2) * ky, Math.sin(a) * rr * r.d / 6.6);
        crowd.setMatrixAt(k, m4); crowd.setColorAt(k, col.set(['#d4af37', '#45e486', '#ff8fa3', '#e8e3d6', '#b388ff'][k % 5])); }
      g.add(crowd);
      [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sz]) => { box(0.14, 4.6, 0.14, '#55585f', sx * r.w * 0.47, 2.3, sz * r.d * 0.45, g);
        const head = box(0.6, 0.26, 0.24, null, sx * r.w * 0.47, 4.6, sz * r.d * 0.45, g, neon('#fff6d8', 3.2)); head.lookAt(0, 0, 0);
        const cone = new THREE.Mesh(new THREE.ConeGeometry(1.4, 4.4, 18, 1, true), new THREE.MeshBasicMaterial({ color: '#fff6d8', transparent: true, opacity: 0.06, depthWrite: false, side: THREE.DoubleSide }));
        cone.position.set(sx * r.w * 0.36, 2.4, sz * r.d * 0.34); cone.rotation.set(sz * 0.5, 0, -sx * 0.5); cone.userData.beam = true; g.add(cone); });
      const hot = (lv.raids || 0) > 0 || live.fight;
      anim.push(t => { crowd.position.y = hot ? Math.abs(Math.sin(t * 6)) * 0.06 : 0; rim.material.color.set('#ffd76a').multiplyScalar(1.3 + Math.sin(t * 1.2) * 0.1); });
      const s = sign([m.name || 'FUSE ARENA', live.fight ? 'FAMILY FUSE LIVE' : `${Math.round(lv.raids || 0)} raids live`], { color: '#d4af37', w: 460 }); s.position.set(c.x, 5.8, c.z); content.add(s);
      proxy(r, 2, m.pick, m.name); return;
    }
    if (m.key === 'launch') {   // 🚀 a rocket on its pad, exhaust breathing
      box(r.w - 0.6, 0.24, r.d - 0.6, '#3a3a40', c.x, 0.24, c.z, content);
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.36, 0.42, 2.8, 18), new THREE.MeshStandardMaterial({ color: '#e8e3d6', metalness: 0.3, roughness: 0.4 })); body.position.set(c.x, 1.75, c.z); content.add(body);
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.36, 0.8, 18), neon('#ffb35a', 1.6)); nose.position.set(c.x, 3.55, c.z); content.add(nose);
      const fire = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial('#ff9a3d'), transparent: true, depthWrite: false, toneMapped: false })); fire.position.set(c.x, 0.45, c.z); fire.scale.set(1.6, 1.8, 1); content.add(fire);
      anim.push(t => { const k = 0.92 + Math.sin(t * 2.4) * 0.06; fire.scale.set(1.6 * k, 2 * k, 1); });
      const s = sign([m.name || 'LAUNCH PAD', `${Math.round(lv.coins || 0)} coins launched`], { color: '#ffb35a', w: 420 }); s.position.set(c.x, 4.8, c.z); content.add(s);
      proxy(r, 3.6, m.pick, m.name); return;
    }
    const pickModel = { house: MODELS.sky[3], mansion: MODELS.big[3], shield: MODELS.sky[1] }[m.key];
    const o = await make(pickModel, { lit: true }); fit(o, r.w - 0.6, r.d - 0.6);
    o.position.set(c.x, 0.14, c.z); content.add(o); const h = sizeOf(o).y; edges(o, c, '#ffd76a');
    if (m.key === 'house') { const crown = new THREE.Mesh(new THREE.TorusGeometry(0.85, 0.1, 8, 32), neon('#ffd76a', 3)); crown.rotation.x = Math.PI / 2; crown.position.set(c.x, h + 0.25, c.z); content.add(crown);
      anim.push(t => { crown.rotation.z = t * 0.6; }); }
    if (m.key === 'mansion') { box(r.w - 0.2, 0.05, r.d - 0.2, null, c.x, 0.17, c.z, content, M.grass); box(r.w - 0.3, 0.3, 0.06, null, c.x, 0.32, r.z + r.d - 0.15, content, neon('#d4af37', 1.8)); }
    if (m.key === 'shield') {   // 🛡 a searchlight sweeping the sky — its speed follows the flagged wallets it watches
      const cone = new THREE.Mesh(new THREE.ConeGeometry(2, 12, 24, 1, true), new THREE.MeshBasicMaterial({ color: '#9fe3ff', transparent: true, opacity: 0.08, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }));
      cone.geometry.translate(0, -6, 0); cone.userData.beam = true; const piv = new THREE.Group(); piv.position.set(c.x, h + 0.1, c.z); piv.add(cone); cone.rotation.x = Math.PI * 0.82; content.add(piv);
      const sp = 0.25 + Math.min(1.2, Math.log10(1 + (lv.flagged || 0)) / 4); anim.push(t => { piv.rotation.y = t * sp; }); }
    const lines = { house: `${Math.round(lv.mp || 0).toLocaleString('en-US')} MP vault`, mansion: lv.tag ? `[${lv.tag}] ${lv.name || ''}` : 'the creator family', shield: `${Math.round(lv.flagged || 0)} flagged` }[m.key];
    const s = sign([m.name || m.key, lines], { color: '#d4af37', w: 440 }); s.position.set(c.x, h + 1.6, c.z); content.add(s);
    proxy(r, h + 0.3, m.pick, m.name);
  }

  // 🛣 FEELESS AVENUE: every tool's building wears what it does — drawn here, transform-only motion, calm (never a strobe)
  function avenueProps(pl, r, c, h, o) {
    const col = pl.color; const top = h + 0.14;
    if (pl.art === 'radar') {   // a dish on a mast turning + a radar sweep over the roof
      const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.07, 0.7, 8), new THREE.MeshStandardMaterial({ color: '#55585f' })); mast.position.set(c.x, top + 0.35, c.z); content.add(mast);
      const piv = new THREE.Group(); piv.position.set(c.x, top + 0.75, c.z); content.add(piv);
      const dish = new THREE.Mesh(new THREE.SphereGeometry(0.62, 22, 10, 0, Math.PI * 2, 0, Math.PI / 2.4), new THREE.MeshStandardMaterial({ color: '#d8dde6', metalness: 0.4, roughness: 0.35, side: THREE.DoubleSide }));
      dish.rotation.x = -Math.PI / 2.6; piv.add(dish); const tip = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), neon(col, 2.6)); tip.position.set(0, 0.32, 0.5); piv.add(tip);
      const sweep = new THREE.Mesh(new THREE.CircleGeometry(Math.max(r.w, r.d) * 0.48, 28, 0, Math.PI / 3), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(1.2), transparent: true, opacity: 0.18, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }));
      sweep.rotation.x = -Math.PI / 2; const sp = new THREE.Group(); sp.position.set(c.x, 0.2, c.z); sp.add(sweep); content.add(sp);
      anim.push(t => { piv.rotation.y = t * 0.9; sp.rotation.y = -t * 0.9; }); return; }
    if (pl.art === 'track') {   // an oval running track round the clubhouse, a runner lapping it
      const oval = new THREE.Mesh(new THREE.TorusGeometry(1, 0.06, 6, 60), neon(col, 1.6)); oval.rotation.x = Math.PI / 2; oval.scale.set((r.w - 1) / 2, (r.d - 1) / 2, 1); oval.position.set(c.x, 0.2, c.z); content.add(oval);
      const lane = new THREE.Mesh(new THREE.RingGeometry(0.86, 1, 60), new THREE.MeshStandardMaterial({ color: '#8a3a22', roughness: 0.9, side: THREE.DoubleSide })); lane.rotation.x = -Math.PI / 2; lane.scale.set((r.w - 1) / 2, (r.d - 1) / 2, 1); lane.position.set(c.x, 0.17, c.z); content.add(lane);
      const runner = new THREE.Mesh(new THREE.CapsuleGeometry(0.1, 0.22, 3, 6), neon(col, 2.2)); content.add(runner);
      anim.push(t => { const a = t * 0.8; runner.position.set(c.x + Math.cos(a) * (r.w - 1.15) / 2, 0.35, c.z + Math.sin(a) * (r.d - 1.15) / 2); }); return; }
    if (pl.art === 'watch') {   // a searchlight sweeping from the top of the tower
      const cone = new THREE.Mesh(new THREE.ConeGeometry(1.6, 10, 24, 1, true), new THREE.MeshBasicMaterial({ color: '#9fe3ff', transparent: true, opacity: 0.07, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }));
      cone.geometry.translate(0, -5, 0); cone.userData.beam = true; const piv = new THREE.Group(); piv.position.set(c.x, top, c.z); piv.add(cone); cone.rotation.x = Math.PI * 0.78; content.add(piv);
      anim.push(t => { piv.rotation.y = t * 0.35; }); return; }
    if (pl.art === 'court') {   // columns + a gold pediment on the front
      const z0 = c.z + Math.min(FOOT.tower, r.d - 0.7) / 2 + 0.25; const stone = new THREE.MeshStandardMaterial({ color: '#e8e3d6', roughness: 0.6 });
      for (let k = 0; k < 4; k += 1) { const cl = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, Math.min(2.2, h * 0.7), 10), stone); cl.position.set(c.x - 0.9 + k * 0.6, 0.14 + Math.min(2.2, h * 0.7) / 2, z0); content.add(cl); }
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 2.3, 3), neon(col, 1.4)); ped.rotation.z = Math.PI / 2; ped.scale.set(1, 1, 0.35); ped.position.set(c.x, 0.14 + Math.min(2.2, h * 0.7) + 0.2, z0); content.add(ped); return; }
    if (pl.art === 'cat') {   // ears on the roof + two eyes that blink slowly
      [-1, 1].forEach(sx => { const ear = new THREE.Mesh(new THREE.ConeGeometry(0.32, 0.7, 4), neon(col, 1.2)); ear.position.set(c.x + sx * 0.55, top + 0.35, c.z); content.add(ear); });
      const eyes = [-1, 1].map(sx => { const e = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), neon('#ffd36b', 3)); e.scale.set(1, 1.5, 0.5); e.position.set(c.x + sx * 0.4, top - 0.45, c.z + Math.min(FOOT.tower, r.d - 0.7) / 2 + 0.06); content.add(e); return e; });
      anim.push(t => { const b = 1 - 0.92 * Math.pow(Math.max(0, Math.sin(t * 0.7)), 60); eyes.forEach(e => { e.scale.y = 1.5 * b; }); }); return; }
    if (pl.art === 'fuel') {   // a canopy on four posts over two pumps, a neon edge on the canopy
      const cx = c.x + r.w * 0.18; const cw = r.w * 0.5; const cd = r.d * 0.55;
      [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([sx, sz]) => box(0.1, 1.3, 0.1, '#c9ccd2', cx + sx * (cw / 2 - 0.15), 0.8, c.z + sz * (cd / 2 - 0.15), content));
      box(cw, 0.14, cd, '#f4efe4', cx, 1.5, c.z, content); frame({ x: cx - cw / 2, z: c.z - cd / 2, w: cw, d: cd }, col, content, 1.58, 0.05);
      [-0.45, 0.45].forEach(dz => { box(0.3, 0.6, 0.22, '#2a2d34', cx, 0.45, c.z + dz, content); box(0.3, 0.08, 0.22, null, cx, 0.78, c.z + dz, content, neon(col, 2)); }); return; }
    if (pl.art === 'news') {   // a live ticker band round the kiosk (its text scrolls: a texture offset, no layout)
      const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 64; const g = cv.getContext('2d'); g.fillStyle = '#05140f'; g.fillRect(0, 0, 1024, 64);
      g.font = 'bold 34px JetBrains Mono, monospace'; g.fillStyle = col; g.textBaseline = 'middle'; g.fillText('FEEd · CALLS · 2× 5× 10× · LIVE · THE TRENCHES TALKING · ', 12, 33);
      const tx = new THREE.CanvasTexture(cv); tx.wrapS = THREE.RepeatWrapping; tx.colorSpace = THREE.SRGBColorSpace;
      const s = sizeOf(o); const band = new THREE.Mesh(new THREE.CylinderGeometry(Math.max(s.x, s.z) * 0.62, Math.max(s.x, s.z) * 0.62, 0.32, 40, 1, true), new THREE.MeshBasicMaterial({ map: tx, toneMapped: false, side: THREE.DoubleSide }));
      band.position.set(c.x, top + 0.25, c.z); content.add(band); anim.push(t => { tx.offset.x = (t * 0.05) % 1; }); return; }
    if (pl.art === 'bank') {   // a giant FEE coin turning over the vault
      const cv = document.createElement('canvas'); cv.width = 128; cv.height = 128; const g = cv.getContext('2d'); g.fillStyle = '#0c3a20'; g.beginPath(); g.arc(64, 64, 62, 0, Math.PI * 2); g.fill();
      g.strokeStyle = '#45e486'; g.lineWidth = 6; g.beginPath(); g.arc(64, 64, 54, 0, Math.PI * 2); g.stroke(); g.fillStyle = '#e8ffe9'; g.font = 'bold 40px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('FEE', 64, 66);
      const face = new THREE.CanvasTexture(cv); face.colorSpace = THREE.SRGBColorSpace; const rim = new THREE.MeshStandardMaterial({ color: '#15d16a', metalness: 0.7, roughness: 0.3, emissive: '#0a5a2c', emissiveIntensity: 0.6 });
      const fm = new THREE.MeshBasicMaterial({ map: face, toneMapped: false }); const coin = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 0.14, 40), [rim, fm, fm]);
      coin.rotation.x = Math.PI / 2; const piv = new THREE.Group(); piv.position.set(c.x, top + 1.1, c.z); piv.add(coin); content.add(piv);
      anim.push(t => { piv.rotation.y = t * 0.8; piv.position.y = top + 1.1 + Math.sin(t * 1.1) * 0.08; }); }
  }

  async function place(pl, yard = () => {}) {   // 📍 a lens you walk into: its own building, neon edges, a sign (+ the Avenue's drawn props)
    const r = pl.rect; const c = centerOf(r);
    if (pl.virtual) { proxy({ x: r.x - 0.2, z: r.z - 0.2, w: r.w + 0.4, d: 0.4 }, 0.3, pl.pick, pl.name); return; }   // the HQ is your own block (or the Mansion): no new building
    box(r.w, 0.12, r.d, '#2c2a33', c.x, 0.08, c.z, content);
    const url = { hall: MODELS.big[2], tower: MODELS.sky[2], war: MODELS.big[1], podium: MODELS.mid[2], precinct: MODELS.mid[4], pawn: MODELS.mid[0], board: MODELS.shop[2], gym: MODELS.big[0], casino: MODELS.big[3], warehouse: MODELS.mid[4],
      radar: MODELS.mid[1], track: MODELS.shop[1], watch: MODELS.sky[4], court: MODELS.mid[3], cat: MODELS.sky[0], fuel: MODELS.shop[0], news: MODELS.shop[3], bank: MODELS.big[3] }[pl.art] || MODELS.mid[0];
    const small = pl.art === 'track' || pl.art === 'fuel'; const fw = Math.min(small ? FOOT.lot : FOOT.tower, r.w - 0.7); const fd = Math.min(small ? FOOT.lot : FOOT.tower, r.d - 0.7);
    if (pl.art !== 'track') yard(r, fw);
    const o = await make(url, { lit: true }); fit(o, fw, fd); o.position.set(c.x + (pl.art === 'fuel' ? -r.w * 0.2 : 0), 0.14, c.z); content.add(o); const h = sizeOf(o).y;
    frame(r, pl.color); edges(o, { x: o.position.x, z: c.z }, pl.color);
    if (pl.tool) avenueProps(pl, r, c, h, o);
    if (pl.art === 'precinct') { const a = box(0.4, 0.14, 0.14, null, c.x - 0.24, h + 0.12, c.z, content, neon('#ff2a3d', 3.2)); const b2 = box(0.4, 0.14, 0.14, null, c.x + 0.24, h + 0.12, c.z, content, neon('#2a6bff', 3.2));
      anim.push(t => { const k = 0.5 + 0.5 * Math.sin(t * 1.3); a.material.color.set('#ff2a3d').multiplyScalar(0.7 + 0.7 * k); b2.material.color.set('#2a6bff').multiplyScalar(0.7 + 0.7 * (1 - k)); }); }   // a slow cross-fade, never a strobe
    else if (!pl.tool) { const n = new THREE.Mesh(new THREE.TorusGeometry(0.46, 0.06, 8, 26), neon(pl.color, 2.8)); n.position.set(c.x, h + 0.45, c.z); content.add(n); anim.push(t => { n.rotation.y = t * 1.4; }); }
    const s = sign([pl.name, pl.sub], { color: pl.color, w: 480 }); s.position.set(c.x, h + (pl.tool && pl.art !== 'track' && pl.art !== 'fuel' ? 2.5 : 1.6), c.z); content.add(s);
    proxy(r, h + 0.3, pl.pick, pl.name);
  }

  // ── ☀ / 🌙 ──
  function applyMode() {
    const d = mode === 'day';
    scene.background = d ? skyD : skyN; scene.fog.color.set(d ? '#bcd3e6' : '#0a1022'); scene.fog.near = d ? 140 : 90; scene.fog.far = d ? 520 : 330;
    hemi.color.set(d ? '#d8ecff' : '#4a5a95'); hemi.groundColor.set(d ? '#5a5444' : '#0b0b14'); hemi.intensity = d ? 1.7 : 1.25;
    key.color.set(d ? '#fff2d6' : '#a9bcff'); key.intensity = d ? 2.6 : 1.35; key.position.set(d ? 90 : -60, d ? 140 : 90, d ? 40 : -40); dusk.intensity = d ? 0.25 : 0.55;
    renderer.toneMappingExposure = d ? 1.0 : 0.98;
    if (bloom) { bloom.strength = d ? 0.12 : 0.42; bloom.threshold = d ? 0.97 : 0.86; bloom.radius = d ? 0.25 : 0.4; }   // owner: LESS glow
    glowMats.forEach(m => { m.emissiveIntensity = d ? 0.04 : 0.42; });
    M.water.color.set(d ? '#2a6a9a' : '#071528'); M.water.emissive.set(d ? '#000000' : '#02060f'); M.water.metalness = d ? 0.35 : 0.55;
    M.grass.color.set(d ? '#4f8a4a' : '#173a22'); M.leaf.color.set(d ? '#3f9a50' : '#1f6b3a'); M.walk.color.set(d ? '#c9bfa8' : '#3a352c'); M.asphalt.color.set(d ? '#3a3d44' : '#15171d');
    M.quay.color.set(d ? '#8a8576' : '#262a33'); M.far.color.set(d ? '#8a96a8' : '#0b0f1c'); M.far.emissiveIntensity = d ? 0.03 : 0.32;
    if (sky.stars) sky.stars.visible = !d;
    if (sky.moon) { sky.moon.material.map = radial(d ? '#fff3c4' : '#fff4d6'); sky.moon.scale.setScalar(d ? 90 : 60); sky.moon.material.opacity = d ? 0.9 : 1; }
    if (sky.pools) sky.pools.visible = !d; if (sky.bulbs) sky.bulbs.material.color.set('#ffd27a').multiplyScalar(d ? 1 : 1.3);
    for (const g of [content, world]) g.traverse(n => { if (n.userData?.beam) n.visible = !d; if (n.userData?.head) n.visible = !d; });
    dirty = true;
  }

  // ── camera ──
  let fly = null;
  const frameAll = () => { const bx = plan.bounds; const span = Math.max(bx.x1 - bx.x0, bx.z1 - bx.z0); return { x: plan.center.x, z: plan.center.z, dist: span * 0.58 }; };
  function flyTo(spot, dist = 12, ms = 900) {
    if (!plan) return;
    const to = spot || frameAll(); const d = spot ? (spot.span ? spot.span * 1.15 : dist) : to.dist;
    const cine = new THREE.Vector3(0.5, 0.5, 0.75).normalize();   // the whole city / a district = the cinematic angle; a pick keeps the angle you turned to
    let dir = camera.position.clone().sub(controls.target); dir = !spot || spot.span || dir.lengthSq() < 1e-6 ? cine : dir.normalize(); if (dir.y < 0.38) { dir.y = 0.5; dir.normalize(); }
    fly = { t0: performance.now(), ms: still ? 1 : ms, fromT: controls.target.clone(), toT: new THREE.Vector3(to.x, 0, to.z), fromP: camera.position.clone(), toP: new THREE.Vector3(to.x, 0, to.z).add(dir.multiplyScalar(d)) };
    ring.visible = !!spot && !spot.span; if (ring.visible) ring.position.set(spot.x, 0.18, spot.z);
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
  const green = new THREE.Color('#2dff7a').multiplyScalar(1.5); const amber = new THREE.Color('#ffb020').multiplyScalar(1.5); const red = new THREE.Color('#ff2a3d').multiplyScalar(1.5);
  const phaseOf = tt => { const c = tt % 10; return c < 4.2 ? 0 : c < 5 ? 1 : c < 9.2 ? 2 : 3; };   // 0 x-green · 1 x-amber · 2 z-green · 3 z-amber
  const goFor = (ph, axis) => (axis === 'x' ? ph === 0 : ph === 2);
  const along = (segs, total, s0) => { let s = ((s0 % total) + total) % total; let k = 0; while (k < segs.length - 1 && s > segs[k].len) { s -= segs[k].len; k += 1; } return [segs[k], s]; };
  function stepCars(dt, ph) {
    const byLoop = {}; cars.forEach(c => { (byLoop[c.loop] = byLoop[c.loop] || []).push(c); });
    Object.values(byLoop).forEach(list => list.sort((a, b) => a.s - b.s));
    for (const c of cars) {
      const [sg, s] = along(c.segs, c.total, c.s); const axis = Math.abs(sg.a[1] - sg.b[1]) < 0.01 ? 'x' : 'z'; let want = c.vmax;
      const stop = sg.stops.find(d => d - s > 0.25 && d - s < 1.25); if (stop != null && !goFor(ph, axis)) want = Math.max(0, (stop - s - 0.45) * 1.8);
      const list = byLoop[c.loop]; const i = list.indexOf(c); const ahead = list[(i + 1) % list.length];
      if (ahead && ahead !== c) { const gap = ((ahead.s - c.s) % c.total + c.total) % c.total; if (gap < 1.1) want = Math.min(want, Math.max(0, (gap - 0.75) * 2)); }
      c.v += (want - c.v) * Math.min(1, dt * 3); c.s += c.v * dt;
      const f = sg.len ? s / sg.len : 0; const dx = sg.b[0] - sg.a[0]; const dz = sg.b[1] - sg.a[1]; const L = Math.hypot(dx, dz) || 1;
      const nx = -dz / L; const nz = dx / L;   // keep right: the lane sits off the centre line
      c.obj.position.set(sg.a[0] + dx * f - nx * 0.22, 0.09, sg.a[1] + dz * f - nz * 0.22); if (L > 0.01) c.obj.rotation.y = Math.atan2(dx, dz);
    }
  }
  const m4w = new THREE.Matrix4(); const q0 = new THREE.Quaternion(); const one = new THREE.Vector3(1, 1, 1); const pv = new THREE.Vector3();
  function stepWalkers(dt) {
    if (!walkers) return;
    walkers.list.forEach((w, k) => { w.s += w.v * dt; const [sg, s] = along(w.segs, w.total, w.s); const f = sg.len ? s / sg.len : 0; const dx = sg.b[0] - sg.a[0]; const dz = sg.b[1] - sg.a[1]; const L = Math.hypot(dx, dz) || 1;
      pv.set(sg.a[0] + dx * f - (dz / L) * w.off, 0.2 + Math.abs(Math.sin((t + k) * 8)) * 0.02, sg.a[1] + dz * f + (dx / L) * w.off); m4w.compose(pv, q0, one); walkers.mesh.setMatrixAt(k, m4w); });
    walkers.mesh.instanceMatrix.needsUpdate = true;
  }
  const av = new THREE.Vector3();
  function emitAnchors() {
    if (!anchors.length || !onAnchors) return;
    const rc = renderer.domElement.getBoundingClientRect(); const out = {};
    anchors.forEach(a => { av.set(a.x, a.y, a.z).project(camera); const dist = camera.position.distanceTo(new THREE.Vector3(a.x, a.y, a.z));
      out[a.id] = { x: (av.x * 0.5 + 0.5) * rc.width, y: (-av.y * 0.5 + 0.5) * rc.height, s: Math.max(0.2, Math.min(1.4, 26 / dist)), vis: av.z < 1 && Math.abs(av.x) < 1.15 && Math.abs(av.y) < 1.15 && dist < 120 }; });
    onAnchors(out);
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
        if (hover?.rect) { const c = centerOf(hover.rect); const s = Math.max(hover.rect.w, hover.rect.d) * 0.78; hoverFrame.position.set(c.x, 0.22, c.z); hoverFrame.scale.set(s, s, 1); hoverFrame.visible = true; } else hoverFrame.visible = false;
        onHover?.(hover ? { label: hover.label, x: hoverAt.clientX, y: hoverAt.clientY } : null); }
      else if (hover) onHover?.({ label: hover.label, x: hoverAt.clientX, y: hoverAt.clientY });
      hoverAt = null; dirty = true; }
    if (!still) {
      const ph = phaseOf(t); stepCars(dt, ph); stepWalkers(dt); anim.forEach(fn => fn(t));
      if (lights && ph !== phaseWas) { phaseWas = ph; lightNodes.forEach((_, k) => { lights.setColorAt(k * 2, ph === 0 ? green : ph === 1 ? amber : red); lights.setColorAt(k * 2 + 1, ph === 2 ? green : ph === 3 ? amber : red); });
        if (lights.instanceColor) lights.instanceColor.needsUpdate = true; }
      if (ring.visible) { const k = 1 + Math.sin(t * 1.6) * 0.05; ring.scale.set(k, k, 1); ring.material.opacity = 0.8 + Math.sin(t * 1.6) * 0.1; }
      dirty = true;
    }
    const far = camera.position.distanceTo(controls.target) > 60;
    if (dirty) for (const g of [content, world]) g.traverse(n => { if (!n.userData?.sign) return;   // 🪧 a sign never fills the screen: it shrinks as you get close
      if (!n.userData.base) n.userData.base = n.scale.clone(); const wp = n.getWorldPosition(pv); const f = Math.max(0.28, Math.min(1, camera.position.distanceTo(wp) / 34)); n.scale.copy(n.userData.base).multiplyScalar(f);
      if (n.userData.small) n.visible = !far; });
    if (!dirty) return; dirty = false;
    if (composer) composer.render(); else renderer.render(scene, camera);
    emitAnchors();
  }

  size(); raf = requestAnimationFrame(frameLoop);
  return {
    async setPlan(p, live = {}) {
      const key_ = `${p.kind}:${p.key || ''}:${p.islands.map(i => i.key).join(',')}`; const first = planKey !== key_; plan = p;
      if (first) { planKey = key_; sig = null; await buildWorld(p); const f = frameAll(); camera.position.set(f.x + f.dist * 0.5, f.dist * 0.5, f.z + f.dist * 0.75); controls.target.set(f.x, 0, f.z); }   // a low, cinematic first look
      const nextSig = JSON.stringify([p.kind, p.key, p.lots.map(l => [l.id, l.kind, l.tag, Math.round(Math.log10(1 + l.power) * 1.6), l.link?.pool, l.link?.apy]), p.markets.map(m => [m.key, usd(m.tvl), m.move == null ? null : Math.round(m.move), m.apy]),
        [...(live.raided || [])], live.fight ? [live.fight.id, live.fight.a?.pct, live.fight.b?.pct] : null, Object.values(live.marks || {}).map(x => JSON.stringify(x))]);
      if (first || nextSig !== sig) { sig = nextSig; await buildContent(p, live); }
      if (lights) { phaseWas = -1; lightNodes.forEach((_, k) => { lights.setColorAt(k * 2, green); lights.setColorAt(k * 2 + 1, red); }); if (lights.instanceColor) lights.instanceColor.needsUpdate = true; }
      dirty = true; return first;
    },
    flyTo, frameAll: () => flyTo(null),
    setMode(m) { mode = m === 'day' ? 'day' : 'night'; applyMode(); },
    setAnchors(list) { anchors = list || []; dirty = true; },
    zoom(f) { const off = camera.position.clone().sub(controls.target); off.multiplyScalar(1 / f); const L = off.length(); if (L > controls.minDistance && L < controls.maxDistance) camera.position.copy(controls.target).add(off); dirty = true; },
    spin(on) { controls.autoRotate = !!on && !still; controls.autoRotateSpeed = 0.6; },
    resize: size,
    dispose() { cancelAnimationFrame(raf); io?.disconnect(); ro?.disconnect(); controls.dispose(); clear(world); clear(content); composer?.dispose?.(); renderer.dispose(); renderer.domElement.remove(); },
  };
}
export { LAND };
