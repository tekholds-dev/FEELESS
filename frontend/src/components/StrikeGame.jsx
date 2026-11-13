import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../lib/api';
import { gunStats, rayBody, damageAt, spreadNow, botBrain, BOT_DIFF, MATCH, mapOf } from '../lib/strikeGame';
import { tgHaptic, tgApp } from '../lib/telegram';
import '../styles/strikeZone.css';
import { Ic3 } from '../lib/icon3d';

// 🎯 STRIKE ZONE — the match. FIRST-PERSON (owner 2026-11-12: "make the familia shooter a fps instead of third… make sumn real and different maps").
// Built on three.js's own open-source pieces: the FPS example's Octree + Capsule physics (examples/jsm/math), GLTFLoader + SkeletonUtils, and
// the three.js Soldier (rigged, Idle / Walk / Run — /models/soldier.glb, MIT). Your eyes are the camera, your built gun rides in your hands
// (hip low-right, centered when you aim, kicks on every shot), bots with a reaction time + accuracy by difficulty, online rooms over a
// WebSocket. Three maps (lib/strikeGame MAPS): THE YARD (day containers), FEE STREETS (neon night blocks), THE VAULT (underground close
// quarters). The server deals the match token and checks the result on its own clock (arena.check) before it pays XP.
const GRAVITY = 30; const R = 0.35;
// THE YARD's layout: shipping containers, crate stacks, two warehouses with open doors, ramps onto their roofs — every piece also a collider
const CONTAINERS = [[-20, -8, 0, '#1f7a4d'], [-20, -4.6, 0, '#b8322f'], [-14, 18, 1.57, '#2b5d9c'], [-7, 18, 1.57, '#d8892a'], [12, -22, 0.4, '#1f7a4d'], [18, -14, 1.2, '#7a2f8f'],
  [28, 10, 0, '#b8322f'], [28, 13.4, 0, '#2b5d9c'], [0, 34, 0, '#d8892a'], [-34, 30, 0.8, '#1f7a4d'], [36, -36, 0.3, '#2b5d9c'], [-40, -34, 1.1, '#b8322f'], [6, 6, 0.78, '#9b6bff']];
const CRATES = [[-4, -14], [-2.6, -14], [-3.3, -14, 1], [10, 2], [10, 3.3], [22, 26], [23.3, 26], [-26, 8], [-26, 9.3], [-26, 8.6, 1], [40, 22], [-10, -32], [-8.7, -32], [30, -4]];
const HOUSES = [[-38, 4, 16, 12], [34, -16, 14, 18]];
// FEE STREETS: city blocks with lit windows around a lamp-lit plaza, dumpsters + cars as cover
const BLDGS = [[-42, -40, 22, 18, 16], [40, -44, 18, 18, 20], [-44, 40, 20, 20, 13], [42, 42, 18, 16, 18], [0, -44, 20, 12, 11], [-46, 2, 14, 20, 15], [46, -2, 12, 22, 12], [10, 44, 22, 12, 14], [-16, 44, 14, 12, 10]];
const DUMPS = [[-10, -8, 0.4], [14, 10, 1.2], [-18, 14, 0.9], [18, -14, 0.2], [0, 20, 0.5], [6, -20, 1], [-24, -20, 0.6], [24, 22, 0.4], [-2, 2, 0.78], [-28, 26, 1.3], [28, -26, 0.7]];
const LAMPS = [[-8, -20], [8, 20], [-24, 8], [24, -6], [0, -2], [-30, -34], [30, 34]];
// THE VAULT: a pillar hall with a raised vault floor in the middle
const PILLARS = [[-18, -18], [18, -18], [-18, 18], [18, 18], [0, -12], [0, 12], [-12, 0], [12, 0]];
const VCRATES = [[-24, 0], [-24, 1.4], [24, 2], [8, -24], [9.4, -24], [-6, 24], [20, -8], [-20, 10]];

function tex(THREE, w, h, draw, rx = 1, ry = 1) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry); t.colorSpace = THREE.SRGBColorSpace; return t; }
function sfx() {   // gunshots + hits synthesized with WebAudio (no files)
  let ctx = null; const get = () => { try { ctx = ctx || new (window.AudioContext || window.webkitAudioContext)(); } catch { /* no audio */ } return ctx; };
  return { shot(vol = 1, low = false) { const a = get(); if (!a) return; const n = a.createBufferSource(); const b = a.createBuffer(1, a.sampleRate * 0.18, a.sampleRate); const d = b.getChannelData(0);
      for (let i = 0; i < d.length; i += 1) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 3); n.buffer = b; const f = a.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = low ? 900 : 2600;
      const g = a.createGain(); g.gain.value = 0.35 * vol; n.connect(f).connect(g).connect(a.destination); n.start(); },
    tick() { const a = get(); if (!a) return; const o = a.createOscillator(); const g = a.createGain(); o.frequency.value = 1400; g.gain.setValueAtTime(0.12, a.currentTime); g.gain.exponentialRampToValueAtTime(0.001, a.currentTime + 0.08); o.connect(g).connect(a.destination); o.start(); o.stop(a.currentTime + 0.09); } };
}

export function StrikeGame({ catalog, loadout, mode = 'bots', diff = 'normal', room = 'fee-city', map = 'yard', who = {}, name = 'you', onExit }) {
  const mount = useRef(null); const api = useRef({}); const MM = mapOf(map); const miniRef = useRef([]);
  const [hud, setHud] = useState({ hp: 100, ammo: 0, mag: 0, reload: false, k: 0, d: 0, left: 0, feed: [], hit: 0, hurt: 0, ads: false, spread: 0, peers: 0, board: [], me: { x: 0, z: 0, yaw: 0 }, bots: [] });
  const [phase, setPhase] = useState('loading'); const [result, setResult] = useState(null); const [err, setErr] = useState(''); const [locked, setLocked] = useState(false);
  const touch = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches;
  const g = gunStats(catalog, loadout); const M = MATCH[mode] || MATCH.bots;

  useEffect(() => {
    let alive = true; let raf = 0; let ws = null; const el = mount.current; const audio = sfx(); const cleanup = [];
    try { el.requestFullscreen?.().catch(() => {}); } catch { /* not allowed */ } try { tgApp()?.expand(); screen.orientation?.lock?.('landscape').catch(() => {}); } catch { /* fine */ }
    Promise.all([import('three'), import('three/examples/jsm/math/Octree.js'), import('three/examples/jsm/math/Capsule.js'), import('three/examples/jsm/loaders/GLTFLoader.js'), import('three/examples/jsm/utils/SkeletonUtils.js')])
      .then(async ([THREE, { Octree }, { Capsule }, { GLTFLoader }, SkU]) => {
        if (!alive) return;
        const low = document.body.classList.contains('fx-lite');
        const renderer = new THREE.WebGLRenderer({ antialias: !low, powerPreference: 'high-performance' }); renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, low ? 1 : 1.5));
        renderer.setSize(window.innerWidth, window.innerHeight); renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.shadowMap.enabled = !low; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        el.prepend(renderer.domElement);
        const MAP = MM.size; const SPAWNS = MM.spawns;
        const scene = new THREE.Scene(); scene.background = new THREE.Color(MM.sky); scene.fog = new THREE.Fog(MM.fog[0], MM.fog[1], MM.fog[2]);
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.05, 400); const baseFov = 75;
        scene.add(new THREE.HemisphereLight(MM.hemi[0], MM.hemi[1], MM.hemi[2] + (low && map !== 'yard' ? 0.45 : 0)));   // fx-lite skips the lamps, so the dark maps lift their base light
        const sun = new THREE.DirectionalLight(MM.sun.color, MM.sun.int); sun.position.set(MM.sun.pos[0], MM.sun.pos[1], MM.sun.pos[2]); sun.castShadow = !low && map === 'yard'; Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, far: 220 }); sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0005; scene.add(sun);
        // ── the map (every mesh in `world` is a collider + blocks bullets, sight and the camera) ──
        const world = new THREE.Group(); scene.add(world); const solids = []; const mini = [];
        const box = (w, h, d, mat, x, y, z, ry = 0) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); m.rotation.y = ry; m.castShadow = m.receiveShadow = true; world.add(m); solids.push(m); return m; };
        const flat = (px, draw, size, rough = 0.9) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(MAP * 2 + 20, MAP * 2 + 20), new THREE.MeshStandardMaterial({ map: tex(THREE, px, px, draw, size, size), roughness: rough })); m.rotation.x = -Math.PI / 2; m.receiveShadow = true; world.add(m); solids.push(m); return m; };
        const signTex = (txt, color) => tex(THREE, 512, 128, (x, w, h) => { x.fillStyle = '#07090c'; x.fillRect(0, 0, w, h); x.font = '900 64px Unbounded, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.shadowColor = color; x.shadowBlur = 24; x.fillStyle = color; x.fillText(txt, w / 2, h / 2); });
        const plate = (txt, color, w, hgt, x, y, z, ry = 0) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, hgt), new THREE.MeshBasicMaterial({ map: signTex(txt, color) })); m.position.set(x, y, z); m.rotation.y = ry; scene.add(m); return m; };
        const wallM = new THREE.MeshStandardMaterial({ map: tex(THREE, 128, 64, (x, w, h) => { x.fillStyle = map === 'streets' ? '#3a3d45' : '#c7b9a0'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(0,0,0,.18)'; for (let r = 0; r < 4; r += 1) for (let cc = 0; cc < 4; cc += 1) x.strokeRect(cc * 32 + (r % 2) * 16, r * 16, 32, 16); }, 20, 2), roughness: 0.9 });
        const logo = tex(THREE, 512, 512, (x, w, h) => { x.clearRect(0, 0, w, h); x.font = '900 120px Unbounded, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillStyle = map === 'yard' ? 'rgba(155, 107, 255,.55)' : 'rgba(25, 230, 140,.5)'; x.fillText('FEE', w / 2, h / 2 - 60); x.fillText('CITY', w / 2, h / 2 + 70); });
        const decal = new THREE.Mesh(new THREE.PlaneGeometry(22, 22), new THREE.MeshBasicMaterial({ map: logo, transparent: true, depthWrite: false })); decal.rotation.x = -Math.PI / 2; decal.position.y = 0.03; scene.add(decal);
        const wallH = map === 'vault' ? 7.4 : 5;
        [[0, -MAP - 0.5, MAP * 2 + 2, 1], [0, MAP + 0.5, MAP * 2 + 2, 1], [-MAP - 0.5, 0, 1, MAP * 2 + 2], [MAP + 0.5, 0, 1, MAP * 2 + 2]].forEach(([x, z, w, d]) => box(w, wallH, d, wallM, x, wallH / 2, z));
        if (map === 'yard') {
          // THE YARD — the original daylight container yard
          flat(256, (x, w, h) => { x.fillStyle = '#9a9d98'; x.fillRect(0, 0, w, h); for (let i = 0; i < 1600; i += 1) { x.fillStyle = `rgba(0,0,0,${Math.random() * 0.06})`; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); } x.strokeStyle = 'rgba(0,0,0,.18)'; x.lineWidth = 2; x.strokeRect(0, 0, w, h); }, 28, 0.95);
          const corr = color => new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.35, map: tex(THREE, 64, 64, (x, w, h) => { x.fillStyle = '#ffffff'; x.fillRect(0, 0, w, h); for (let i = 0; i < w; i += 8) { x.fillStyle = 'rgba(0,0,0,.18)'; x.fillRect(i, 0, 3, h); } }, 6, 1) });
          CONTAINERS.forEach(([x, z, ry, c]) => { box(6.1, 2.6, 2.4, corr(c), x, 1.3, z, ry); mini.push([x, z, 6, 2.4, '']); });
          const wood = new THREE.MeshStandardMaterial({ map: tex(THREE, 64, 64, (x, w, h) => { x.fillStyle = '#b08a55'; x.fillRect(0, 0, w, h); x.strokeStyle = '#7d5f35'; x.lineWidth = 5; x.strokeRect(3, 3, w - 6, h - 6); x.beginPath(); x.moveTo(3, 3); x.lineTo(w - 3, h - 3); x.stroke(); }), roughness: 0.85 });
          CRATES.forEach(([x, z, up]) => box(1.3, 1.3, 1.3, wood, x, up ? 1.95 : 0.65, z));
          const roofM = new THREE.MeshStandardMaterial({ color: '#4c5357', roughness: 0.8 });
          HOUSES.forEach(([x, z, w, d]) => { const t = 0.5; const hgt = 5;
            box(w, hgt, t, wallM, x, hgt / 2, z - d / 2); box(t, hgt, d, wallM, x - w / 2, hgt / 2, z); box(t, hgt, d, wallM, x + w / 2, hgt / 2, z);
            const door = 3.2; const side = (w - door) / 2; box(side, hgt, t, wallM, x - w / 2 + side / 2, hgt / 2, z + d / 2); box(side, hgt, t, wallM, x + w / 2 - side / 2, hgt / 2, z + d / 2); box(door, hgt - 3, t, wallM, x, hgt - (hgt - 3) / 2, z + d / 2);
            box(w + 0.6, 0.4, d + 0.6, roofM, x, hgt + 0.2, z);
            const ramp = box(3, 0.4, 11, roofM, x + w / 2 + 1.6, hgt / 2, z); ramp.rotation.x = Math.atan2(hgt, 11); mini.push([x, z, w, d, 'is-house']); });
          plate('STRIKE ZONE', '#9b6bff', 20, 5, 0, 9, -MAP + 0.1);
        } else if (map === 'streets') {
          // FEE STREETS — neon night blocks: lit windows, lamp pools, dumpsters and cars for cover
          flat(256, (x, w, h) => { x.fillStyle = '#1d2026'; x.fillRect(0, 0, w, h); for (let i = 0; i < 1200; i += 1) { x.fillStyle = `rgba(255,255,255,${Math.random() * 0.035})`; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); } x.fillStyle = 'rgba(245,214,120,.5)'; x.fillRect(w / 2 - 2, 0, 4, h); }, 22, 0.85);
          let seed = 7; const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
          const winM = () => { const t = tex(THREE, 128, 256, (x, w, h) => { x.fillStyle = '#10131b'; x.fillRect(0, 0, w, h);
            for (let r = 10; r < h - 10; r += 24) for (let c = 10; c < w - 14; c += 22) { const on = rnd() < 0.42; x.fillStyle = on ? (rnd() < 0.3 ? '#8fd3ff' : '#ffd27a') : '#171b26'; x.fillRect(c, r, 13, 15); } }, 2, 3);
            return new THREE.MeshStandardMaterial({ map: t, emissiveMap: t, emissive: '#ffffff', emissiveIntensity: 0.85, roughness: 0.9 }); };
          BLDGS.forEach(([x, z, w, d, hgt]) => { box(w, hgt, d, winM(), x, hgt / 2, z); mini.push([x, z, w, d, 'is-house']); });
          const metal = new THREE.MeshStandardMaterial({ color: '#2c3138', metalness: 0.55, roughness: 0.5 });
          const carM = new THREE.MeshStandardMaterial({ color: '#1d4b3a', metalness: 0.6, roughness: 0.35 });
          DUMPS.forEach(([x, z, ry], i) => { const car = i % 3 === 0; if (car) { box(4.2, 1.1, 1.9, carM, x, 0.55, z, ry); box(2.2, 0.75, 1.7, carM, x, 1.45, z, ry); } else box(2.4, 1.2, 1.4, metal, x, 0.6, z, ry); mini.push([x, z, car ? 4.2 : 2.4, car ? 1.9 : 1.4, '']); });
          const poleM = new THREE.MeshStandardMaterial({ color: '#15171c', roughness: 0.6 }); const bulbM = new THREE.MeshBasicMaterial({ color: '#ffd9a0' });
          LAMPS.forEach(([x, z]) => { box(0.22, 5.6, 0.22, poleM, x, 2.8, z); const b = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 8), bulbM); b.position.set(x, 5.7, z); scene.add(b);
            if (!low) { const pl = new THREE.PointLight('#ffd9a0', 14, 27, 1.7); pl.position.set(x, 5.4, z); scene.add(pl); } });
          plate('FEE CITY', '#19e68c', 16, 4, -42, 11, -40 + 9.1); plate('STRIKE ZONE', '#ff5dbb', 14, 3.5, 40, 13, -44 + 9.1);
          plate('$FEE', '#f5c451', 10, 3, -44, 9, 40 - 10.1, Math.PI); plate('RUG FREE ZONE', '#8fd3ff', 14, 3, 42, 12, 42 - 8.1, Math.PI);
        } else {
          // THE VAULT — an underground hall: pillar grid, a raised vault floor, green strip light
          flat(256, (x, w, h) => { x.fillStyle = '#15181a'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(73,240,160,.10)'; x.lineWidth = 2; x.strokeRect(0, 0, w, h); for (let i = 0; i < 700; i += 1) { x.fillStyle = `rgba(0,0,0,${Math.random() * 0.1})`; x.fillRect(Math.random() * w, Math.random() * h, 2, 2); } }, 16, 0.8);
          const conc = new THREE.MeshStandardMaterial({ color: '#23282c', roughness: 0.85 });
          box(MAP * 2 + 2, 0.5, MAP * 2 + 2, conc, 0, 7.45, 0);   // the ceiling
          const strip = new THREE.MeshBasicMaterial({ color: '#49f0a0' });
          PILLARS.forEach(([x, z]) => { box(2.2, 7.2, 2.2, conc, x, 3.6, z); mini.push([x, z, 2.2, 2.2, '']);
            [[1.16, 0], [-1.16, 0], [0, 1.16], [0, -1.16]].forEach(([ox, oz]) => { const s = new THREE.Mesh(new THREE.BoxGeometry(ox ? 0.08 : 1.6, 4.6, oz ? 0.08 : 1.6), strip); s.position.set(x + ox, 2.6, z + oz); s.scale.setScalar(0.999); scene.add(s); }); });
          const steel = new THREE.MeshStandardMaterial({ color: '#2e343a', metalness: 0.7, roughness: 0.35 });
          box(8, 0.9, 8, steel, 0, 0.45, 0); mini.push([0, 0, 8, 8, 'is-house']);
          [6.5, -6.5].forEach((x, i) => { const r = box(5, 0.3, 3.4, steel, x, 0.42, 0); r.rotation.z = (i ? -1 : 1) * Math.atan2(0.9, 5); });
          const wood = new THREE.MeshStandardMaterial({ color: '#6e5a3a', roughness: 0.85 });
          VCRATES.forEach(([x, z]) => box(1.3, 1.3, 1.3, wood, x, z === 1.4 ? 1.95 : 0.65, z === 1.4 ? 0 : z));
          plate('$FEE VAULT', '#49f0a0', 14, 3.4, 0, 4.4, -MAP + 0.6);
          if (!low) [[0, 0], [-18, -18], [18, 18], [18, -18]].forEach(([x, z]) => { const pl = new THREE.PointLight('#49f0a0', 9, 24, 1.7); pl.position.set(x, 6.4, z); scene.add(pl); });
        }
        miniRef.current = mini;
        const octree = new Octree(); octree.fromGraphNode(world);
        // ── characters (the three.js Soldier, cloned; a capsule figure if the model can't load) ──
        let gltf = null; try { gltf = await new GLTFLoader().loadAsync('/models/soldier.glb'); } catch { gltf = null; }
        if (!alive) return;
        const actor = (tint) => {
          const root = new THREE.Group(); let mixer = null; const acts = {};
          if (gltf) { const m = SkU.clone(gltf.scene); m.traverse(o => { if (o.isMesh) { o.castShadow = true; if (tint) { o.material = o.material.clone(); o.material.color.multiply(new THREE.Color(tint)); } } });
            m.rotation.y = Math.PI; root.add(m); mixer = new THREE.AnimationMixer(m); gltf.animations.forEach(a => { acts[a.name] = mixer.clipAction(a); }); acts.Idle?.play(); }
          else { const mat = new THREE.MeshStandardMaterial({ color: tint || '#4a6b52' }); const b = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 1.0, 6, 12), mat); b.position.y = 0.85; b.castShadow = true; root.add(b);
            const h = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 10), mat); h.position.y = 1.62; root.add(h); }
          const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.45, 16), new THREE.MeshBasicMaterial({ color: '#000', transparent: true, opacity: 0.25, depthWrite: false })); shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.02; root.add(shadow);
          let cur = 'Idle'; const set = n => { if (!mixer || !acts[n] || n === cur) return; acts[n].reset().fadeIn(0.18).play(); acts[cur]?.fadeOut(0.18); cur = n; };
          scene.add(root); return { root, mixer, set };
        };
        // 🔫 Real gun models (Kenney Blaster Kit, CC0): one per gun, with its scope, silencer and clip. If one cannot load, the drawn gun below still plays the same.
        const GUN_FILE = { rifle: 'blaster-f', smg: 'blaster-j', shotgun: 'blaster-o', sniper: 'blaster-p' }; const GUN_PARTS = ['scope-small', 'scope-large-a', 'silencer-small', 'clip-small', 'clip-large'];
        const gunKit = {}; await Promise.all([...Object.values(GUN_FILE), ...GUN_PARTS].map(n => new GLTFLoader().loadAsync(`/models/guns/${n}.glb`).then(g => { gunKit[n] = g.scene; }).catch(() => {})));
        const fitted = (scene, length) => { const m = scene.clone(true); const size = new THREE.Box3().setFromObject(m).getSize(new THREE.Vector3()); m.scale.setScalar(length / Math.max(size.x, size.y, size.z, 1e-6)); m.traverse(o => { if (o.isMesh) o.castShadow = true; }); return m; };
        const modelGun = (lo, col) => { const base = gunKit[GUN_FILE[lo.gun] || GUN_FILE.rifle]; if (!base) return null; const big = lo.gun === 'sniper' ? 1.05 : lo.gun === 'smg' ? 0.62 : lo.gun === 'shotgun' ? 0.78 : 0.86; const grp = new THREE.Group(); const body = fitted(base, big); body.rotation.y = Math.PI; const tint = new THREE.Color(col);
          body.traverse(o => { if (!o.isMesh) return; o.material = o.material.clone(); o.material.color?.lerp(tint, 0.45); }); grp.add(body); const box = new THREE.Box3().setFromObject(body);
          const part = (name, len, y, z) => { if (!gunKit[name]) return; const m = fitted(gunKit[name], len); m.rotation.y = Math.PI; m.position.set(0, y, z); grp.add(m); };
          if (lo.optic === 'scope') part('scope-large-a', 0.28, box.max.y + 0.02, 0.02); else if (lo.optic === 'dot' || lo.optic === 'holo') part('scope-small', 0.14, box.max.y + 0.015, 0.04);
          if (lo.barrel === 'supp') part('silencer-small', 0.16, 0, box.max.z + 0.07); part(lo.mag === 'ext' || lo.mag === 'drum' ? 'clip-large' : 'clip-small', lo.mag === 'ext' || lo.mag === 'drum' ? 0.18 : 0.13, box.min.y - 0.02, 0.02);
          return grp; };
        const gunMesh = (lo, skin) => {   // the gun YOU built: body + barrel length + optic + magazine + stock, in your skin
          const col = { green: '#9b6bff', carbon: '#2b2f33', pink: '#ff5dbb', ice: '#8fd3ff', gold: '#f5c451' }[skin] || '#9b6bff';
          const body = new THREE.MeshStandardMaterial({ color: '#1c2024', metalness: 0.6, roughness: 0.4 }); const accent = new THREE.MeshStandardMaterial({ color: col, metalness: 0.5, roughness: 0.35, emissive: col, emissiveIntensity: 0.12 });
          const model = modelGun(lo, col); if (model) { scene.add(model); return model; }
          const grp = new THREE.Group(); const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; grp.add(m); return m; };
          const len = lo.barrel === 'long' ? 0.55 : lo.barrel === 'short' ? 0.22 : lo.barrel === 'supp' ? 0.5 : 0.38; const big = lo.gun === 'sniper' ? 1.25 : lo.gun === 'smg' ? 0.8 : 1;
          add(new THREE.BoxGeometry(0.08, 0.12, 0.5 * big), accent, 0, 0, 0);
          const br = add(new THREE.CylinderGeometry(lo.barrel === 'supp' ? 0.035 : 0.02, lo.barrel === 'supp' ? 0.035 : 0.02, len, 10), body, 0, 0.02, 0.25 * big + len / 2); br.rotation.x = Math.PI / 2;
          if (lo.optic === 'scope') { const s = add(new THREE.CylinderGeometry(0.03, 0.03, 0.26, 10), body, 0, 0.11, 0.02); s.rotation.x = Math.PI / 2; }
          else if (lo.optic === 'dot' || lo.optic === 'holo') add(new THREE.BoxGeometry(0.05, 0.05, lo.optic === 'holo' ? 0.09 : 0.06), body, 0, 0.1, 0.05);
          add(new THREE.BoxGeometry(0.05, lo.mag === 'drum' ? 0.12 : lo.mag === 'ext' ? 0.2 : 0.14, lo.mag === 'drum' ? 0.12 : 0.06), body, 0, -0.12, 0.06);
          add(new THREE.BoxGeometry(0.06, lo.stock === 'heavy' ? 0.12 : 0.08, lo.stock === 'light' ? 0.14 : 0.22), lo.stock === 'heavy' ? accent : body, 0, -0.01, -0.3 * big);
          scene.add(grp); return grp;
        };
        // ── you ──
        const me = actor(null); me.root.visible = false;   // first person: you never see your own body, only your gun
        const myGun = gunMesh(loadout || {}, loadout?.skin); myGun.traverse(o => { if (o.isMesh) { o.castShadow = false; o.frustumCulled = false; } });
        const sp0 = SPAWNS[Math.floor(Math.random() * SPAWNS.length)];
        const cap = new Capsule(new THREE.Vector3(sp0[0], R, sp0[1]), new THREE.Vector3(sp0[0], 1.45, sp0[1]), R); const vel = new THREE.Vector3(); let onFloor = false;
        const S = { yaw: Math.atan2(-sp0[0], -sp0[1]), pitch: -0.05, hp: 100, lastHurt: 0, ammo: g.mag, reloadT: 0, fireT: 0, bloom: 0, k: 0, d: 0, heads: 0, shots: 0, hits: 0, dead: 0, ads: false, keys: new Set(), fire: false, joy: { x: 0, y: 0 }, t0: performance.now(), feed: [], hitT: 0, hurtT: 0, over: false, safeUntil: performance.now() + 2500 };
        const collide = (c, v) => { const r = octree.capsuleIntersect(c); let floor = false; if (r) { floor = r.normal.y > 0.3; if (!floor) v.addScaledVector(r.normal, -r.normal.dot(v)); if (r.depth >= 1e-10) c.translate(r.normal.multiplyScalar(r.depth)); } return floor; };
        const feetOf = c => ({ x: c.start.x, y: c.start.y - R, z: c.start.z });
        const respawnAt = (c, v, far) => { const pick = SPAWNS.slice().sort((a, b) => (far ? Math.hypot(b[0] - far.x, b[1] - far.z) - Math.hypot(a[0] - far.x, a[1] - far.z) : Math.random() - 0.5))[Math.floor(Math.random() * 2)];
          c.start.set(pick[0], R, pick[1]); c.end.set(pick[0], 1.45, pick[1]); v.set(0, 0, 0); };
        // ── bots (offline, or filling an empty online room) ──
        const D = BOT_DIFF[diff] || BOT_DIFF.normal; const NAMES = ['RUGGER', 'SNIPEY', 'BUNDLE', 'JEET', 'DEVWALLET', 'PAPERHAND', 'EXITLIQ'];
        const bots = []; const botDmg = { easy: 10, normal: 14, hard: 18 }[diff] || 14;
        const nameTag = txt => { const c = document.createElement('canvas'); c.width = 256; c.height = 64; const t = new THREE.CanvasTexture(c); const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false })); sp.scale.set(1.6, 0.4, 1); sp.position.y = 2.15;
          const draw = (label, hp) => { const x = c.getContext('2d'); x.clearRect(0, 0, 256, 64); x.font = '800 26px "JetBrains Mono", monospace'; x.textAlign = 'center'; x.fillStyle = '#ff8fa3'; x.fillText(label, 128, 26); x.fillStyle = 'rgba(0,0,0,.5)'; x.fillRect(48, 40, 160, 10); x.fillStyle = hp > 50 ? '#b48cff' : hp > 25 ? '#f5c451' : '#ff3b3b'; x.fillRect(48, 40, 160 * Math.max(0, hp) / 100, 10); t.needsUpdate = true; };
          draw(txt, 100); return { sp, draw }; };
        const addBot = i => { const a = actor('#ff9a8a'); const sp = SPAWNS[(i * 3 + 2) % SPAWNS.length]; const c = new Capsule(new THREE.Vector3(sp[0], R, sp[1]), new THREE.Vector3(sp[0], 1.45, sp[1]), R);
          const tag = nameTag(NAMES[i % NAMES.length]); a.root.add(tag.sp); const gun = gunMesh({ gun: 'rifle' }, 'carbon');
          bots.push({ i, name: NAMES[i % NAMES.length], a, c, v: new THREE.Vector3(), hp: D.hp, max: D.hp, yaw: 0, seen: 0, cool: 1, los: false, losT: 0, dead: 0, kills: 0, t: Math.random() * 10, tag, gun, last: [sp[0], sp[1]], stuck: 0, wander: null }); };
        if (mode === 'bots') for (let i = 0; i < D.n; i += 1) addBot(i);
        // ── online peers ──
        const peers = new Map(); let myId = '';
        if (mode === 'online') {
          try {
            ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/reputation/arena/ws?room=${encodeURIComponent(room)}&name=${encodeURIComponent(name)}`);
            const mk = (id, nm) => { if (peers.has(id)) return peers.get(id); const a = actor('#8fbfff'); const tag = nameTag(nm || 'player'); a.root.add(tag.sp); const p = { id, name: nm || 'player', a, tag, pos: new THREE.Vector3(0, 0, 0), to: new THREE.Vector3(0, 0, 0), yaw: 0, hp: 100, k: 0, anim: 'Idle', gun: gunMesh({ gun: 'rifle' }, 'ice') }; peers.set(id, p); return p; };
            ws.onmessage = ev => { let m = null; try { m = JSON.parse(ev.data); } catch { return; }
              if (m.t === 'hello') { myId = m.id; (m.peers || []).forEach(p => mk(p.id, p.name)); }
              else if (m.t === 'join') mk(m.id, m.name);
              else if (m.t === 'leave') { const p = peers.get(m.id); if (p) { scene.remove(p.a.root); scene.remove(p.gun); peers.delete(m.id); } }
              else if (m.t === 'state') { const p = mk(m.id, m.name); p.to.set(m.p[0], m.p[1], m.p[2]); p.yaw = m.yaw; p.hp = m.hp; p.k = m.k || 0; p.anim = m.anim || 'Idle'; p.tag.draw(p.name, p.hp); }
              else if (m.t === 'shot') { const p = peers.get(m.id); if (p) { tracer(new THREE.Vector3(...m.a), new THREE.Vector3(...m.b), '#8fd3ff'); audio.shot(0.4, true); } }
              else if (m.t === 'hit' && m.target === myId) hurt(m.dmg, peers.get(m.id)?.name || 'a player', m.id);
              else if (m.t === 'dead' && m.by === myId) { S.k += 1; feed(`you ⚔ ${peers.get(m.id)?.name || 'player'}`); } };
          } catch { setErr('Online rooms are unavailable right now — playing bots.'); }
        }
        const send = m => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); };
        // ── effects ──
        const fx = [];
        const tracer = (a, b, color = '#fff6c0') => { const geo = new THREE.BufferGeometry().setFromPoints([a, b]); const l = new THREE.Line(geo, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 })); scene.add(l); fx.push({ o: l, t: 0.08 }); };
        const spark = p => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 4), new THREE.MeshBasicMaterial({ color: '#ffd27a' })); m.position.copy(p); scene.add(m); fx.push({ o: m, t: 0.12, grow: true }); };
        const flash = new THREE.PointLight('#ffd27a', 0, 6); scene.add(flash);
        const feed = txt => { S.feed = [{ txt, at: performance.now() }, ...S.feed].slice(0, 5); };
        const hurt = (dmg, by, byId) => { if (S.dead || S.over || performance.now() < S.safeUntil) return;   // 2 s of spawn protection S.hp -= dmg; S.lastHurt = performance.now(); S.hurtT = 0.4; tgHaptic('light');
          if (S.hp <= 0) { S.hp = 0; S.d += 1; S.dead = 3; feed(`${by} ⚔ you`); tgHaptic('error'); if (byId) send({ t: 'dead', by: byId }); } };
        // ── input ──
        const kd = e => { if (e.code === 'Escape') return; S.keys.add(e.code); if (e.code === 'KeyR') reload(); if (e.code === 'Tab') e.preventDefault(); if (['Space', 'ArrowUp', 'ArrowDown'].includes(e.code)) e.preventDefault(); };
        const ku = e => S.keys.delete(e.code);
        const mm = e => { if (document.pointerLockElement !== renderer.domElement) return; const k = S.ads ? 0.0011 : 0.0022; S.yaw -= e.movementX * k; S.pitch = Math.max(-1.1, Math.min(0.9, S.pitch - e.movementY * k)); };
        const md = e => { if (touch) return; if (document.pointerLockElement !== renderer.domElement) { renderer.domElement.requestPointerLock?.(); return; } if (e.button === 0) S.fire = true; if (e.button === 2) S.ads = true; };
        const mu = e => { if (e.button === 0) S.fire = false; if (e.button === 2) S.ads = false; };
        const plc = () => setLocked(document.pointerLockElement === renderer.domElement);
        window.addEventListener('keydown', kd); window.addEventListener('keyup', ku); window.addEventListener('mousemove', mm); renderer.domElement.addEventListener('mousedown', md); window.addEventListener('mouseup', mu);
        renderer.domElement.addEventListener('contextmenu', e => e.preventDefault()); document.addEventListener('pointerlockchange', plc);
        const onResize = () => { renderer.setSize(window.innerWidth, window.innerHeight); camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); }; window.addEventListener('resize', onResize);
        cleanup.push(() => { window.removeEventListener('keydown', kd); window.removeEventListener('keyup', ku); window.removeEventListener('mousemove', mm); window.removeEventListener('mouseup', mu); document.removeEventListener('pointerlockchange', plc); window.removeEventListener('resize', onResize); });
        function reload() { if (S.reloadT > 0 || S.ammo === g.mag) return; S.reloadT = g.reload; }
        api.current = { look: (dx, dy) => { const k = S.ads ? 0.003 : 0.006; S.yaw -= dx * k; S.pitch = Math.max(-1.1, Math.min(0.9, S.pitch - dy * k)); }, joy: (x, y) => { S.joy = { x, y }; },
          fire: on => { S.fire = on; }, ads: () => { S.ads = !S.ads; }, jump: () => { S.keys.add('Space'); setTimeout(() => S.keys.delete('Space'), 120); }, reload, quit: () => end(true) };
        // ── the match clock + result ──
        let token = ''; post('/api/reputation/arena/start', { ...who, mode }).then(r => { token = r.token; }).catch(() => {});
        function end(quit) {
          if (S.over) return; S.over = true; document.exitPointerLock?.(); const secs = (performance.now() - S.t0) / 1000;
          const top = Math.max(0, ...bots.map(b => b.kills), ...[...peers.values()].map(p => p.k));
          const won = !quit && (S.k >= M.kills || S.k > top);
          const base = { k: S.k, d: S.d, heads: S.heads, acc: S.shots ? Math.round((S.hits / S.shots) * 100) : 0, won, secs: Math.round(secs), quit };
          setPhase('over'); setResult({ ...base, saving: true });
          if (!token || secs < 20) { setResult({ ...base, note: secs < 20 ? 'Too short to count — play a full match for XP.' : 'Offline — XP not saved.' }); return; }
          post('/api/reputation/arena/result', { ...who, token, kills: S.k, deaths: S.d, heads: S.heads, won }).then(r => setResult({ ...base, ...r })).catch(e => setResult({ ...base, note: e.message }));
        }
        // ── the loop ──
        const ray = new THREE.Raycaster(); const v3 = new THREE.Vector3(); let last = performance.now(); let hudAt = 0; let sendAt = 0;
        const fwd = () => new THREE.Vector3(Math.sin(S.yaw), 0, Math.cos(S.yaw)); const right = () => new THREE.Vector3(Math.sin(S.yaw - Math.PI / 2), 0, Math.cos(S.yaw - Math.PI / 2));
        const sightBlocked = (a, b) => { ray.set(a, v3.copy(b).sub(a).normalize()); ray.far = a.distanceTo(b); return ray.intersectObjects(solids, false).length > 0; };
        setPhase('play');
        const loop = now => {
          raf = requestAnimationFrame(loop);
          if (document.hidden) { last = now; return; }
          const dt = Math.min(0.05, (now - last) / 1000); last = now;
          // you: move + jump + gravity (the FPS example's capsule physics)
          if (!S.dead && !S.over) {
            const dir = new THREE.Vector3(); const k = S.keys;
            if (k.has('KeyW') || k.has('ArrowUp')) dir.add(fwd()); if (k.has('KeyS') || k.has('ArrowDown')) dir.sub(fwd()); if (k.has('KeyA') || k.has('ArrowLeft')) dir.sub(right()); if (k.has('KeyD') || k.has('ArrowRight')) dir.add(right());
            if (S.joy.x || S.joy.y) { dir.addScaledVector(fwd(), -S.joy.y); dir.addScaledVector(right(), S.joy.x); }
            if (dir.lengthSq() > 1) dir.normalize();
            const sprint = (k.has('ShiftLeft') || k.has('ShiftRight') || Math.hypot(S.joy.x, S.joy.y) > 0.92) && !S.ads; const spd = (onFloor ? 24 : 7) * g.speed * (sprint ? 1.55 : S.ads ? 0.55 : 1);
            vel.addScaledVector(dir, spd * dt);
            if (onFloor && k.has('Space')) vel.y = 11;
          }
          let damp = Math.exp(-4 * dt) - 1; if (!onFloor) { vel.y -= GRAVITY * dt; damp *= 0.1; } vel.addScaledVector(vel, damp);
          cap.translate(v3.copy(vel).multiplyScalar(dt)); onFloor = collide(cap, vel);
          if (cap.start.y < -10) respawnAt(cap, vel);
          const feet = feetOf(cap); const moving = Math.hypot(vel.x, vel.z) > 1.2;
          me.root.position.set(feet.x, feet.y, feet.z); me.root.rotation.y = S.yaw; me.set(!onFloor ? 'Idle' : Math.hypot(vel.x, vel.z) > 6 ? 'Run' : moving ? 'Walk' : 'Idle');
          // 👁 the first-person camera (owner 2026-11-12: FPS instead of third person): your eyes ride the capsule
          const head = new THREE.Vector3(feet.x, feet.y + 1.55, feet.z);
          S.bob = (S.bob || 0) + dt * (moving && onFloor ? 9.5 : 2);
          camera.position.set(head.x, head.y + (moving && onFloor ? Math.sin(S.bob) * 0.028 : 0), head.z);
          const aimDir = new THREE.Vector3(Math.sin(S.yaw) * Math.cos(S.pitch), Math.sin(S.pitch), Math.cos(S.yaw) * Math.cos(S.pitch));
          camera.lookAt(camera.position.clone().add(aimDir)); const fov = S.ads ? baseFov / g.zoom : baseFov; if (Math.abs(camera.fov - fov) > 0.1) { camera.fov += (fov - camera.fov) * Math.min(1, dt * 12); camera.updateProjectionMatrix(); }
          // the gun in your hands: low-right at the hip, centered under the crosshair when you aim, kicks back on every shot
          S.kick = Math.max(0, (S.kick || 0) - dt * 3.2);
          const camUp = new THREE.Vector3(0, 1, 0);
          const gunPos = camera.position.clone().addScaledVector(aimDir, (S.ads ? 0.42 : 0.52) - S.kick * 0.09)
            .addScaledVector(right(), S.ads ? 0.015 : 0.18).addScaledVector(camUp, (S.ads ? -0.08 : -0.16) + (moving && onFloor ? Math.sin(S.bob) * 0.008 : 0));
          myGun.position.copy(gunPos); myGun.lookAt(gunPos.clone().add(aimDir));
          const muzzle = gunPos.clone().addScaledVector(aimDir, 0.4);
          // shooting (hitscan from the camera's crosshair; the bullet's tracer leaves your muzzle)
          S.fireT -= dt; S.bloom = Math.max(0, S.bloom - dt * 0.05);
          if (S.reloadT > 0) { S.reloadT -= dt; if (S.reloadT <= 0) S.ammo = g.mag; }
          if (S.fire && !S.dead && !S.over && S.reloadT <= 0 && S.fireT <= 0) {
            if (S.ammo <= 0) reload();
            else { S.fireT = g.interval; S.ammo -= 1; S.shots += 1; audio.shot(1); flash.position.copy(muzzle); flash.intensity = 6;
              let any = false;
              for (let p = 0; p < (g.pellets || 1); p += 1) {
                const sp = spreadNow(g, { moving, ads: S.ads, bloom: S.bloom }); const d = aimDir.clone().add(new THREE.Vector3((Math.random() - 0.5) * 2 * sp, (Math.random() - 0.5) * 2 * sp, (Math.random() - 0.5) * 2 * sp)).normalize();
                ray.set(camera.position, d); ray.far = 400; const wall = ray.intersectObjects(solids, false)[0]; const wallD = wall ? wall.distance : 400;
                let best = null;
                bots.forEach(b => { if (b.dead) return; const h = rayBody(camera.position, d, feetOf(b.c)); if (h && h.dist < wallD && (!best || h.dist < best.h.dist)) best = { b, h }; });
                peers.forEach(pe => { const h = rayBody(camera.position, d, pe.pos); if (h && h.dist < wallD && (!best || h.dist < best.h.dist)) best = { pe, h }; });
                const end_ = camera.position.clone().addScaledVector(d, best ? best.h.dist : wallD);
                tracer(muzzle, end_); if (!best && wall) spark(wall.point);
                if (best) { any = true; const dmg = damageAt(g, best.h.dist, best.h.head);
                  if (best.b) { const b = best.b; b.hp -= dmg; b.seen = Math.max(b.seen, D.react); b.tag.draw(b.name, (b.hp / b.max) * 100);
                    if (b.hp <= 0) { b.dead = 4; S.k += 1; if (best.h.head) S.heads += 1; feed(`you ⚔ ${b.name}${best.h.head ? ' · HEADSHOT' : ''}`); tgHaptic('medium'); } }
                  else { send({ t: 'hit', target: best.pe.id, dmg, head: best.h.head }); if (best.h.head && best.pe.hp - dmg <= 0) S.heads += 1; }
                  S.hitT = best.h.head ? 0.25 : 0.15; }
              }
              if (any) { S.hits += 1; audio.tick(); }
              send({ t: 'shot', a: muzzle.toArray().map(x => Math.round(x * 100) / 100), b: camera.position.clone().addScaledVector(aimDir, 60).toArray().map(x => Math.round(x * 100) / 100) });
              S.pitch = Math.min(0.9, S.pitch + g.recoil * 0.018 * (S.ads ? 0.6 : 1)); S.yaw += (Math.random() - 0.5) * g.recoil * 0.01; S.bloom = Math.min(0.06, S.bloom + g.recoil * 0.004); S.kick = Math.min(1, (S.kick || 0) + 0.45 + g.recoil * 0.4);
              if (!g.auto && g.rpm < 120) S.fire = touch ? S.fire : false; }
          }
          flash.intensity = Math.max(0, flash.intensity - dt * 60);
          // bots
          bots.forEach(b => { b.t += dt;
            if (b.dead) { b.dead -= dt; b.a.root.rotation.x = Math.max(-Math.PI / 2, b.a.root.rotation.x - dt * 6); b.gun.visible = false;
              if (b.dead <= 0) { respawnAt(b.c, b.v, feet); b.hp = b.max; b.dead = 0; b.a.root.rotation.x = 0; b.gun.visible = true; b.tag.draw(b.name, 100); } b.a.mixer?.update(dt); return; }
            const bf = feetOf(b.c); b.losT -= dt;
            if (b.losT <= 0) { b.losT = 0.2; b.los = !S.dead && !sightBlocked(new THREE.Vector3(bf.x, bf.y + 1.6, bf.z), head); }
            const brain = botBrain({ x: bf.x, z: bf.z, hp: (b.hp / b.max) * 100, seen: b.seen, cool: b.cool, t: b.t }, { x: feet.x, z: feet.z, moving }, b.los && !S.dead, dt, diff);
            b.seen = brain.seen; b.cool = brain.cool;
            let face = brain.face; if (brain.mode === 'hunt' && !b.los) { if (!b.wander || b.t > b.wander.until) b.wander = { a: face + (Math.random() - 0.5) * 1.4, until: b.t + 2.5 }; face = b.wander.a; }
            b.yaw += Math.atan2(Math.sin(face - b.yaw), Math.cos(face - b.yaw)) * Math.min(1, dt * 6);
            const mv = new THREE.Vector3(Math.sin(b.yaw), 0, Math.cos(b.yaw)).multiplyScalar(brain.go || 0); if (brain.strafe) mv.addScaledVector(new THREE.Vector3(Math.cos(b.yaw), 0, -Math.sin(b.yaw)), brain.strafe * 0.6);
            b.v.addScaledVector(mv, 16 * dt); let bd = Math.exp(-4 * dt) - 1; b.v.y -= GRAVITY * dt; b.v.addScaledVector(b.v, bd); b.c.translate(v3.copy(b.v).multiplyScalar(dt)); collide(b.c, b.v);
            const moved = Math.hypot(bf.x - b.last[0], bf.z - b.last[1]); b.stuck = moved < 0.01 && (brain.go || 0) > 0.3 ? b.stuck + dt : 0; b.last = [bf.x, bf.z]; if (b.stuck > 0.8) { b.wander = { a: b.yaw + Math.PI / 2 * (Math.random() > 0.5 ? 1 : -1), until: b.t + 1.2 }; b.stuck = 0; }
            b.a.root.position.set(bf.x, bf.y, bf.z); b.a.root.rotation.y = b.yaw; const bs = Math.hypot(b.v.x, b.v.z); b.a.set(bs > 5 ? 'Run' : bs > 0.8 ? 'Walk' : 'Idle'); b.a.mixer?.update(dt);
            const bdir = new THREE.Vector3(head.x - bf.x, head.y - (bf.y + 1.35), head.z - bf.z).normalize(); const bm = new THREE.Vector3(bf.x, bf.y + 1.35, bf.z).addScaledVector(new THREE.Vector3(Math.cos(b.yaw), 0, -Math.sin(b.yaw)), -0.25);
            b.gun.position.copy(bm); b.gun.lookAt(bm.clone().add(b.los ? bdir : new THREE.Vector3(Math.sin(b.yaw), 0, Math.cos(b.yaw))));
            if (brain.shoot && !S.over) { const hit = Math.random() < brain.hitOdds; const tgt = hit ? head.clone() : head.clone().add(new THREE.Vector3((Math.random() - 0.5) * 3, (Math.random() - 0.5) * 2, (Math.random() - 0.5) * 3));
              tracer(bm, tgt, '#ff9a8a'); audio.shot(Math.max(0.15, 1 - head.distanceTo(bm) / 80), true); if (hit) { hurt(botDmg, b.name); if (S.dead === 3) b.kills += 1; } }
          });
          if (mode === 'online' && peers.size === 0 && bots.length === 0 && now - S.t0 > 4000) for (let i = 0; i < 2; i += 1) addBot(i);   // an empty room gets two bots
          if (mode === 'online' && peers.size > 0 && bots.length) bots.splice(0).forEach(b => { scene.remove(b.a.root); scene.remove(b.gun); });
          peers.forEach(p => { p.pos.lerp(p.to, Math.min(1, dt * 10)); p.a.root.position.copy(p.pos); p.a.root.rotation.y = p.yaw; p.a.set(p.anim); p.a.mixer?.update(dt);
            const pm = p.pos.clone().add(new THREE.Vector3(0, 1.35, 0)); p.gun.position.copy(pm); p.gun.lookAt(pm.clone().add(new THREE.Vector3(Math.sin(p.yaw), 0, Math.cos(p.yaw)))); });
          // regen, death, the clock
          if (!S.dead && S.hp < 100 && now - S.lastHurt > 4000) S.hp = Math.min(100, S.hp + 22 * dt);
          if (S.dead) { S.dead -= dt; if (S.dead <= 0) { S.dead = 0; S.hp = 100; respawnAt(cap, vel, bots[0] ? feetOf(bots[0].c) : null); S.ammo = g.mag; S.yaw = Math.atan2(-cap.start.x, -cap.start.z); S.pitch = -0.05; S.safeUntil = performance.now() + 2000; } }
          const left = Math.max(0, M.secs - (now - S.t0) / 1000);
          if (!S.over && (S.k >= M.kills || left <= 0)) end(false);
          me.mixer?.update(dt); S.hitT = Math.max(0, S.hitT - dt); S.hurtT = Math.max(0, S.hurtT - dt);
          for (let i = fx.length - 1; i >= 0; i -= 1) { const f = fx[i]; f.t -= dt; if (f.grow) f.o.scale.multiplyScalar(1 + dt * 8); f.o.material.opacity = Math.max(0, f.t * 10); f.o.material.transparent = true; if (f.t <= 0) { scene.remove(f.o); f.o.geometry.dispose(); f.o.material.dispose(); fx.splice(i, 1); } }
          renderer.render(scene, camera);
          if (now - sendAt > 100) { sendAt = now; send({ t: 'state', p: [feet.x, feet.y, feet.z].map(x => Math.round(x * 100) / 100), yaw: Math.round(S.yaw * 100) / 100, hp: Math.round(S.hp), k: S.k, anim: Math.hypot(vel.x, vel.z) > 6 ? 'Run' : moving ? 'Walk' : 'Idle' }); }
          if (now - hudAt > 90) { hudAt = now;
            setHud({ hp: S.hp, ammo: S.ammo, mag: g.mag, reload: S.reloadT > 0, k: S.k, d: S.d, left, feed: S.feed.filter(f => now - f.at < 5000), hit: S.hitT, hurt: S.hurtT, ads: S.ads, dead: S.dead,
              spread: spreadNow(g, { moving, ads: S.ads, bloom: S.bloom }), peers: peers.size, me: { x: feet.x, z: feet.z, yaw: S.yaw },
              bots: bots.filter(b => !b.dead && b.los).map(b => ({ x: feetOf(b.c).x, z: feetOf(b.c).z })),
              board: [{ name: `${name} (you)`, k: S.k, d: S.d, me: true }, ...bots.map(b => ({ name: b.name, k: b.kills, d: 0 })), ...[...peers.values()].map(p => ({ name: p.name, k: p.k, d: 0 }))].sort((a, b) => b.k - a.k) }); }
        };
        raf = requestAnimationFrame(loop);
        cleanup.push(() => { scene.traverse(o => { o.geometry?.dispose?.(); const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : []; ms.forEach(m => { m.map?.dispose?.(); m.dispose?.(); }); }); renderer.dispose(); renderer.domElement.remove(); });
      }).catch(e => { setErr(`The game could not start on this device (${String(e?.message || e).slice(0, 80)}).`); setPhase('over'); });
    return () => { alive = false; cancelAnimationFrame(raf); try { ws?.close(); } catch { /* closed */ } cleanup.forEach(f => f()); try { if (document.fullscreenElement) document.exitFullscreen(); } catch { /* fine */ } document.exitPointerLock?.(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 📱 thumbs: a move stick on the left, look by dragging the right, FIRE / AIM / JUMP / RELOAD
  const stick = useRef(null); const lookAt = useRef(null);
  const onStick = e => { const r = stick.current.getBoundingClientRect(); const x = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / (r.width / 2))); const y = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / (r.height / 2))); api.current.joy?.(x, y); stick.current.style.setProperty('--sx', x); stick.current.style.setProperty('--sy', y); };
  const mmss = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  return createPortal(<div className={`szg ${hud.ads ? 'is-ads' : ''} ${hud.hurt ? 'is-hurt' : ''}`} ref={mount} data-testid="strike-game">
    {phase === 'loading' ? <div className="szg-load"><b>STRIKE ZONE</b><small>loading {MM.name} + the soldiers…</small><i /></div> : null}
    <div className="szg-hud">
      <span className="szg-score"><b className="m-num">{hud.k}</b><em>KILLS</em><small className="m-num">{hud.d} deaths · first to {M.kills}</small></span>
      <span className="szg-clock m-num">{mmss(hud.left)}</span>
      <svg className="szg-map" viewBox={`${-MM.size} ${-MM.size} ${MM.size * 2} ${MM.size * 2}`} aria-hidden="true">{miniRef.current.map(([x, z, w, d, cls], i) => <rect key={i} x={x - w / 2} y={z - d / 2} width={w} height={d} className={cls || undefined} />)}
        {hud.bots.map((b, i) => <circle key={i} cx={b.x} cy={b.z} r="2.4" className="is-bot" />)}<g transform={`translate(${hud.me.x} ${hud.me.z}) rotate(${(-hud.me.yaw * 180) / Math.PI})`}><path d="M0 4 L-2.6 -3 L0 -1.6 L2.6 -3 Z" className="is-me" /></g></svg>
      <ol className="szg-feed">{hud.feed.map((f, i) => <li key={f.at + i}>{f.txt}</li>)}</ol>
      <span className="szg-hp"><em>HP</em><u><s style={{ transform: `scaleX(${hud.hp / 100})` }} className={hud.hp < 35 ? 'is-low' : ''} /></u><b className="m-num">{Math.ceil(hud.hp)}</b></span>
      <span className="szg-ammo"><b className="m-num">{hud.reload ? '…' : hud.ammo}</b><small className="m-num">/ {hud.mag}</small><em>{g.name}{hud.reload ? ' · RELOADING' : ''}</em></span>
      <i className={`szg-cross ${hud.hit ? 'is-hit' : ''}`} style={{ '--sp': `${Math.min(60, 8 + hud.spread * 900)}px` }} aria-hidden="true"><s /><s /><s /><s /></i>
      {mode === 'online' ? <span className="szg-online"><Ic3 e="🌐" /> {room} · {hud.peers} other{hud.peers === 1 ? '' : 's'} here</span> : null}
      {!touch && !locked && phase === 'play' ? <p className="szg-click">Click to aim · WASD move · Shift sprint · Space jump · right-click ADS · R reload · Esc frees the mouse</p> : null}
    </div>
    {hud.dead ? <div className="szg-dead"><b>DOWN</b><small>back in {Math.ceil(hud.dead)}…</small></div> : null}
    {touch && phase === 'play' ? <div className="szg-touch">
      <div className="szg-stick" ref={stick} onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); onStick(e); }} onPointerMove={e => { if (e.buttons || e.pointerType === 'touch') onStick(e); }} onPointerUp={() => { api.current.joy?.(0, 0); stick.current.style.setProperty('--sx', 0); stick.current.style.setProperty('--sy', 0); }} aria-label="Move"><i /></div>
      <div className="szg-look" onPointerDown={e => { e.currentTarget.setPointerCapture(e.pointerId); lookAt.current = [e.clientX, e.clientY]; }} onPointerMove={e => { if (!lookAt.current) return; api.current.look?.(e.clientX - lookAt.current[0], e.clientY - lookAt.current[1]); lookAt.current = [e.clientX, e.clientY]; }} onPointerUp={() => { lookAt.current = null; }} aria-label="Look" />
      <div className="szg-btns">
        <button type="button" className="is-fire" onPointerDown={e => { e.preventDefault(); api.current.fire?.(true); }} onPointerUp={() => api.current.fire?.(false)} onPointerCancel={() => api.current.fire?.(false)} aria-label="Fire">FIRE</button>
        <button type="button" onPointerDown={e => { e.preventDefault(); api.current.ads?.(); }} aria-label="Aim">AIM</button>
        <button type="button" onPointerDown={e => { e.preventDefault(); api.current.jump?.(); }} aria-label="Jump">JUMP</button>
        <button type="button" onPointerDown={e => { e.preventDefault(); api.current.reload?.(); }} aria-label="Reload">R</button></div>
    </div> : null}
    <button type="button" className="szg-quit" onClick={() => (phase === 'over' ? onExit?.(result) : api.current.quit?.())} data-tip="End the match" data-testid="szg-quit">{phase === 'over' ? 'EXIT' : '✕ END'}</button>
    {phase === 'over' ? <div className="szg-over" data-testid="szg-over"><em>{err ? 'HEADS UP' : result?.won ? 'VICTORY' : result?.quit ? 'MATCH ENDED' : 'MATCH OVER'}</em>
      {err ? <p>{err}</p> : null}
      {result ? <><div className="szg-stats">{[['KILLS', result.k], ['DEATHS', result.d], ['HEADSHOTS', result.heads], ['ACCURACY', `${result.acc}%`]].map(([k, v]) => <span key={k}><em>{k}</em><b className="m-num">{v}</b></span>)}</div>
        <p className="szg-xp">{result.saving ? 'Saving your XP…' : result.note ? result.note : result.guest ? `+${result.xp} XP (guest — sign in to keep it)` : `+${result.xp} XP${result.mp ? ` · +${result.mp} MP to the family bank` : ''}${result.levelUp ? ` · 🎉 LEVEL ${result.me?.level}!` : ''}`}</p></> : null}
      <div className="szg-acts"><button type="button" className="m-btn m-go" onClick={() => onExit?.({ ...result, again: true })} data-testid="szg-again">🔁 PLAY AGAIN</button><button type="button" className="m-btn" onClick={() => onExit?.(result)} data-testid="szg-exit">BACK TO THE GUNSMITH</button></div>
    </div> : null}
  </div>, document.body);
}

const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'The server said no.'); return j; });
