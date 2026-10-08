import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { clone as cloneSkinned } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { crowdTargets, boneClass, garmentPick } from './crowdMath';

// 🧍 RINGSIDE CROWD: small versions of the REAL rigged avatars (CC0 Quaternius bodies in /assets/avatars) walk the foot of a fight, gather
// under the card that is winning and cheer. Skin, hair and outfit differ per walker; garments are cut from the real body mesh (same
// vertices + skin weights), so everything bends with the 65-bone skeleton. The walk / pause / cheer are bone rotations on that
// skeleton (the pack ships no clips). Assets missing (not deployed) → `start()` rejects and the caller shows nothing.
const A = '/assets/avatars/';
const TONES = { m: { light: A + 'tex/T_Superhero_Male_Ligh.png', dark: A + 'base/T_Superhero_Male_Dark.png' }, f: { light: A + 'tex/T_Superhero_Female_Light_BaseColor.png', dark: A + 'base/T_Superhero_Female_Dark_BaseColor.png' } };
const SKIN = [['light', 0xffffff], ['light', 0xd9a878], ['dark', 0xffffff], ['dark', 0x8a6a58]];
const HAIRS = { m: [null, 'Hair_Buzzed', 'Hair_SimpleParted'], f: ['Hair_Long', 'Hair_Buns', 'Hair_BuzzedFemale'] };
const HAIR_CLR = [0x7a5a3c, 0x2a2420, 0xe8c878, 0xd0603a, 0xf070b0, 0xc8ccd0];
const TOPC = [0x15d16a, 0xe9eeec, 0x1b1d1f, 0x5a3aa8, 0xb02a3c, 0x3a9ad6, 0xf2b01e], PANTC = [0x27406e, 0x17191b, 0x9a8a5a, 0x59616a], SHOEC = [0xf2f4f3, 0x1b1d1f, 0x15d16a, 0xc0392b];
const TOP = { arm: 0.21 }, PANTS = { minH: 0.065 };

// ---- assets (loaded once for every crowd on the page) ----
let kitP = null;
const gltfC = new Map(), texC = new Map(), garmentC = new Map(), restC = new Map();
const loader = new GLTFLoader(), texLoader = new THREE.TextureLoader();
const gltf = url => { if (!gltfC.has(url)) gltfC.set(url, loader.loadAsync(url)); return gltfC.get(url); };
const tex = url => { if (!texC.has(url)) { const t = texLoader.load(url); t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 2; texC.set(url, t); } return texC.get(url); };
export const loadKit = () => (kitP ||= Promise.all([gltf(A + 'base/Superhero_Male_FullBody.gltf'), gltf(A + 'base/Superhero_Female_FullBody.gltf')]).catch(e => { kitP = null; throw e; }));
const bone = (root, name) => { let b = null; root.traverse(o => { if (o.isBone && o.name === name) b = o; }); return b; };

function readBody(body) {
  const g = body.geometry, n = g.attributes.position.count, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, names = body.skeleton.bones.map(b => boneClass(b.name));
  const cls = new Array(n), rest = new Float32Array(n * 3), v = new THREE.Vector3(); let ymin = 1e9, ymax = -1e9;
  for (let i = 0; i < n; i++) {
    const w = {}; for (let k = 0; k < 4; k++) { const c = names[si.getComponent(i, k)]; w[c] = (w[c] || 0) + sw.getComponent(i, k); }
    cls[i] = Object.keys(w).sort((p, q) => w[q] - w[p])[0]; body.getVertexPosition(i, v); v.applyMatrix4(body.matrixWorld); rest.set([v.x, v.y, v.z], i * 3); ymin = Math.min(ymin, v.y); ymax = Math.max(ymax, v.y);
  }
  return { cls, rest, ymin, H: ymax - ymin };
}
function garmentGeo(kind, spec, src, d) {
  const g = src.geometry, idx = g.index, pos = g.attributes.position, nor = g.attributes.normal, keep = [];
  const ok = i => garmentPick(kind, spec, d.cls[i], (d.rest[i * 3 + 1] - d.ymin) / d.H, Math.abs(d.rest[i * 3]) / d.H);
  for (let t = 0; t < idx.count; t += 3) { const a = idx.getX(t), b = idx.getX(t + 1), c = idx.getX(t + 2); if (ok(a) && ok(b) && ok(c)) keep.push(a, b, c); }
  const geo = new THREE.BufferGeometry(), off = (kind === 'top' ? 0.0055 : 0.0085) * d.H, p2 = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) { p2[i * 3] = pos.getX(i) + nor.getX(i) * off / src.scale.x; p2[i * 3 + 1] = pos.getY(i) + nor.getY(i) * off / src.scale.y; p2[i * 3 + 2] = pos.getZ(i) + nor.getZ(i) * off / src.scale.z; }
  geo.setAttribute('position', new THREE.BufferAttribute(p2, 3)); geo.setAttribute('normal', nor); geo.setAttribute('skinIndex', g.attributes.skinIndex); geo.setAttribute('skinWeight', g.attributes.skinWeight); geo.setIndex(keep); return geo;
}

async function makeWalker(scene, sex, rnd, i) {
  const g = await gltf(A + 'base/Superhero_' + (sex === 'm' ? 'Male' : 'Female') + '_FullBody.gltf');
  const root = cloneSkinned(g.scene); root.updateMatrixWorld(true);
  let body = null; root.traverse(o => { if (o.isSkinnedMesh) { o.frustumCulled = false; if (/Superhero/i.test(o.material.name)) body = o; } });
  if (!restC.has(sex)) { let src = null; g.scene.traverse(o => { if (o.isSkinnedMesh && /Superhero/i.test(o.material.name)) src = o; }); g.scene.updateMatrixWorld(true); restC.set(sex, { d: readBody(src), src }); }
  const rd = restC.get(sex), pickOf = a => a[Math.floor(rnd() * a.length)];
  const [map, tint] = pickOf(SKIN); body.material = body.material.clone(); body.material.map = tex(TONES[sex][map]); body.material.color.setHex(tint); body.material.normalScale.set(0.22, 0.22);
  const q = new THREE.Quaternion(), pw = new THREE.Quaternion(), bw = new THREE.Quaternion(), Z = new THREE.Vector3(0, 0, 1), X = new THREE.Vector3(1, 0, 0);
  const swing = (bn, ang) => { bn.updateWorldMatrix(true, false); bn.parent.getWorldQuaternion(pw); bn.getWorldQuaternion(bw); bn.quaternion.copy(pw.clone().invert().multiply(q.setFromAxisAngle(Z, ang)).multiply(bw)); };
  const names = { ual: 'upperarm_l', uar: 'upperarm_r', thl: 'thigh_l', thr: 'thigh_r', cl: 'calf_l', cr: 'calf_r', sp: 'spine_02', hd: 'Head' };
  const B = {}; for (const k in names) B[k] = bone(root, names[k]);
  swing(B.ual, -1.2); swing(B.uar, 1.2);
  ['upperarm_l', 'upperarm_r'].forEach(n => { const b = bone(root, n); b.scale.set(0.86, b.scale.y, 0.86); }); ['thigh_l', 'thigh_r'].forEach(n => { const b = bone(root, n); b.scale.set(0.88, b.scale.y, 0.88); });
  root.updateMatrixWorld(true);
  const rig = {}; for (const k in B) { const b = B[k]; if (!b) continue; b.getWorldQuaternion(bw); const inv = bw.clone().invert(); rig[k] = { b, q0: b.quaternion.clone(), ax: X.clone().applyQuaternion(inv), az: Z.clone().applyQuaternion(inv) }; }
  const mk = (kind, spec, color) => { const key = sex + kind + JSON.stringify(spec); if (!garmentC.has(key)) garmentC.set(key, garmentGeo(kind, spec, rd.src, rd.d));
    const m = new THREE.SkinnedMesh(garmentC.get(key), new THREE.MeshStandardMaterial({ color, roughness: kind === 'shoes' ? 0.55 : 0.92, side: THREE.DoubleSide })); m.position.copy(body.position); m.quaternion.copy(body.quaternion); m.scale.copy(body.scale); m.frustumCulled = false; body.parent.add(m); m.bind(body.skeleton, body.bindMatrix); };
  mk('top', TOP, pickOf(TOPC)); mk('pants', PANTS, pickOf(PANTC)); mk('shoes', {}, pickOf(SHOEC));
  const hf = pickOf(HAIRS[sex]);
  if (hf) { const hg = await gltf(A + 'hair/' + hf + '.gltf'); const h = hg.scene.clone(true); const col = pickOf(HAIR_CLR); h.traverse(m => { if (m.isMesh) { m.material = m.material.clone(); m.material.side = THREE.DoubleSide; m.material.color.setHex(col); m.frustumCulled = false; } }); (B.hd || root).attach(h); }
  const group = new THREE.Group(); group.add(root); scene.add(group);
  return { group, rig, phase: rnd() * 6.28, speed: 0.34 + rnd() * 0.16, x: 0, tx: 0, state: 'walk', until: 0, cheer: false, face: 0, i };
}

const swingBone = (r, ang, axis = 'ax') => { if (r) r.b.quaternion.copy(r.q0).multiply(_q.setFromAxisAngle(r[axis], ang)); };
const _q = new THREE.Quaternion();
function pose(w, dt, time, lead, half) {
  const R = w.rig, dx = w.tx - w.x, walking = Math.abs(dx) > 0.04;
  if (walking) {
    const dir = Math.sign(dx); w.x += dir * Math.min(Math.abs(dx), w.speed * dt); w.phase += dt * 6.4;
    w.face += ((dir * Math.PI / 2) - w.face) * Math.min(1, dt * 9);
    const s = Math.sin(w.phase);
    swingBone(R.thl, s * 0.45); swingBone(R.thr, -s * 0.45); swingBone(R.cl, Math.max(0, Math.sin(w.phase + 1.6)) * 0.65); swingBone(R.cr, Math.max(0, Math.sin(w.phase + 1.6 + Math.PI)) * 0.65);
    swingBone(R.ual, -s * 0.4); swingBone(R.uar, s * 0.4); swingBone(R.sp, s * 0.06, 'az'); swingBone(R.hd, -s * 0.04, 'az');
    w.group.position.y = Math.abs(s) * 0.02;
  } else {   // arrived: face the ring; cheer for the leader, breathe otherwise
    w.face += (0 - w.face) * Math.min(1, dt * 7);
    const cheer = lead && time < w.cheerUntil; ['thl', 'thr', 'cl', 'cr'].forEach(n => swingBone(R[n], 0));
    const up = cheer ? 2.6 + Math.sin(time * 9 + w.phase) * 0.25 : 0;
    swingBone(R.ual, up, 'az'); swingBone(R.uar, -up, 'az'); swingBone(R.sp, Math.sin(time * 2 + w.phase) * 0.02);
    swingBone(R.hd, cheer ? -0.3 : 0.08);
    w.group.position.y = cheer ? Math.abs(Math.sin(time * 9 + w.phase)) * 0.05 : 0;
    if (!lead && time > w.until) { w.tx = (Math.random() * 2 - 1) * half * 0.8; w.until = time + 2 + Math.random() * 3; }
  }
  w.group.position.x = w.x; w.group.rotation.y = w.face;
}

/** One crowd on one canvas. start() → loads the kit, builds `count` walkers; setLead('a'|'b'|'') moves + cheers; setActive(bool) pauses drawing. */
export function createCrowd(canvas, { count = 3, seed = 1, onFrame = null } = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.1;
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xe6dcff, 0x1a1030, 1.5));
  const key = new THREE.DirectionalLight(0xfff3e4, 2.3); key.position.set(2, 4, 5); scene.add(key);
  const rimV = new THREE.PointLight(0xa86bff, 22, 14); rimV.position.set(-3, 2, -2); scene.add(rimV);
  const rimG = new THREE.PointLight(0x15d16a, 18, 14); rimG.position.set(3, 1.5, -2); scene.add(rimG);
  const cam = new THREE.OrthographicCamera(-1, 1, 2.72, -0.08, 0.1, 30); cam.position.set(0, 0, 8); cam.lookAt(0, 0, 0);
  let walkers = [], width = 6, lead = '', active = true, raf = 0, last = performance.now(), dead = false;
  let s = seed * 9301 + 49297; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const fit = () => { const w = canvas.clientWidth || 300, h = canvas.clientHeight || 120; renderer.setSize(w, h, false); const half = (2.8 * w / h) / 2; width = half * 2; cam.left = -half; cam.right = half; cam.updateProjectionMatrix(); };
  const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(fit) : null; ro && ro.observe(canvas); fit();
  const retarget = () => { const t = crowdTargets(lead, width, walkers.length), now = performance.now() / 1000; walkers.forEach((w, i) => { w.tx = t[i] + (rnd() - 0.5) * 0.25; w.cheerUntil = lead ? now + 3 + rnd() : 0; w.until = now + 2 + rnd() * 2; }); };
  const frame = now => {
    raf = requestAnimationFrame(frame); if (dead || !active || document.hidden) { last = now; return; }
    const dt = Math.min(0.05, (now - last) / 1000); last = now; const time = now / 1000;
    walkers.forEach(w => { if (lead && time > w.cheerUntil + 6 + w.phase) w.cheerUntil = time + 2.5; pose(w, dt, time, lead, width / 2); });
    renderer.render(scene, cam);
    if (onFrame) {   // where each walker's head is on the canvas, in CSS px — the name tags ride on these
      const W = canvas.clientWidth || 1, H = canvas.clientHeight || 1, span = cam.top - cam.bottom;
      onFrame(walkers.map(w => ({ x: ((w.x + width / 2) / width) * W, y: (1 - (1.98 + w.group.position.y - cam.bottom) / span) * H })));
    }
  };
  return {
    async start() {
      await loadKit(); if (dead) return;
      for (let i = 0; i < count; i++) { const w = await makeWalker(scene, (i + seed) % 2 ? 'f' : 'm', rnd, i); if (dead) return; w.x = (rnd() * 2 - 1) * width * 0.4; walkers.push(w); }
      retarget(); raf = requestAnimationFrame(frame);
    },
    setLead(l) { if (l !== lead) { lead = l; retarget(); } },
    setActive(a) { active = a; },
    dispose() { dead = true; cancelAnimationFrame(raf); ro && ro.disconnect(); walkers.forEach(w => scene.remove(w.group)); renderer.dispose(); try { renderer.forceContextLoss(); } catch { /* already gone */ } },
  };
}
