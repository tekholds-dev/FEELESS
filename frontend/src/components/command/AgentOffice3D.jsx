import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { AGENTS, screensOf, packetsOf, spinSec } from './AgentRoom';

// 🏢 THE AGENT OFFICE (owner, 2026-10-09: "a 3rd-person view of a WHITE office, small white bots moving, the printer with all coins being
// scanned, a drawer for good, a shredder for bad"). Third-person camera over a bright white room. Every moving thing is the real pass:
//   · 🖨 the SCANNER reads each coin of the pass (green scan bar, its counter = coins read) and prints it as a sheet
//   · the four small white bots (colour band = who) CARRY each sheet desk to desk — Tally → Sherlock → Trigger → Devil — typing at the
//     speed of their real work this pass; the sheet is stamped with how it ended
//   · 🟢 GO → Devil files it in the GOOD drawer (it slides open) · ✕ / ⛔ / ⏳ → the BAD shredder (strips fall)
//   · desk monitors = each bot's real output · wall board = coins read · GO · green % · 👑 over the bot with the best record (≥ 10 judged)
//     and its latest call pinned on the board · a bot reborn in the last 10 min drops in from the ceiling
// Click a bot → AgentRoom shows its rules / rulings / record. Own lazy chunk; still frames when hidden / fx-lite / reduced motion.
const BAND = { tally: 0x1fd178, sherlock: 0x8a63ff, trigger: 0xf2a900, devil: 0xff4466 };
const LIFE = { alive: 0x45e486, probation: 0xf5c451, scrap: 0xff3355 };
const DESK = [[-3.2, -1.2], [-1.1, -1.2], [1.0, -1.2], [3.1, -1.2]];
const PRINTER = [-6.2, 0.6], DRAWER = [6.0, 1.6], SHRED = [6.0, -1.0];
const SLIP_COL = { go: '#c9ffe0', obj: '#ffd9e0', wait: '#fff1c9', skip: '#ececec' };
const IC = { go: '🟢', obj: '✕', wait: '⏳', skip: '⛔' };
const cut = (s, n) => { const t = String(s || ''); return t.length > n ? `${t.slice(0, n - 1)}…` : t; };
const mono = (px, w = 700) => `${w} ${px}px "JetBrains Mono", ui-monospace, monospace`;
const lerp = (a, b, t) => a + (b - a) * t;

function tex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  t.userData.redraw = (...a) => { const g = c.getContext('2d'); g.clearRect(0, 0, w, h); draw(g, w, h, ...a); t.needsUpdate = true; }; return t;
}
function drawScreen(g, w, h, k, s) {
  g.fillStyle = '#0b1a14'; g.fillRect(0, 0, w, h); g.fillStyle = '#45e486'; g.font = mono(34, 800);
  if (k === 'tally') { g.fillText(`${s.n} READ`, 20, 44); s.bars.forEach((b, i) => { const bh = Math.max(6, Math.min(200, Math.abs(b.v) * 20)); g.fillStyle = b.v >= 0 ? '#45e486' : '#ff6b86'; g.fillRect(22 + i * 47, h - 20 - bh, 32, bh); }); }
  else if (k === 'sherlock') { g.fillText('WHY', 20, 44); g.font = mono(28, 600); g.fillStyle = '#d8efe2'; (s.tags.length ? s.tags : [['no clues', '']]).forEach(([t, n], i) => g.fillText(`${cut(t, 18)}${n ? ` ×${n}` : ''}`, 20, 108 + i * 60)); }
  else if (k === 'trigger') { g.fillStyle = '#f5c451'; g.font = mono(110, 800); g.fillText(String(s.enters), 30, 190); g.font = mono(30, 700); g.fillText('ENTER', 30, 240); g.fillStyle = '#8fb3a1'; g.fillText(`${s.waits} WAIT`, 30, 286); }
  else { g.fillText('DOCKET', 20, 44); g.font = mono(30, 700); (s.verdicts.length ? s.verdicts : [{ none: true }]).forEach((v, i) => { g.fillStyle = v.none ? '#8fb3a1' : v.ok ? '#45e486' : '#ff8fa3'; g.fillText(v.none ? 'nothing to argue' : `${v.ok ? (v.go ? '● GO ' : '✓  ') : '✕  '}$${cut(v.sym, 10)}`, 20, 108 + i * 60); }); }
}
function drawBoard(g, w, h, s, at, rg, best) {
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, w, h); g.strokeStyle = '#15d16a'; g.lineWidth = 8; g.strokeRect(4, 4, w - 8, h - 8);
  g.fillStyle = '#5b6b64'; g.font = mono(30, 700); g.fillText(`THE AGENT DESK · ${at ? `pass ${Math.max(0, Math.round(Date.now() / 1000 - at))}s ago` : 'starting'}`, 32, 52);
  const cell = (x, v, l, c) => { g.fillStyle = c; g.font = mono(84, 800); g.fillText(v, x, 150); g.fillStyle = '#7b8a84'; g.font = mono(22, 700); g.fillText(l, x, 186); };
  cell(32, String(s.n), 'COINS READ', '#14241c'); cell(330, String(s.go), 'GO', '#0e9b52'); cell(520, rg?.green != null ? `${rg.green}%` : '—', `GREEN · ${String(rg?.word || '—').toUpperCase()}`, '#14241c');
  if (best) { g.fillStyle = '#9a6f00'; g.font = mono(24, 800); g.fillText(`👑 ${best}`, 32, 234); }
}
function drawLabel(g, w, h, text, bg, fg) { g.fillStyle = bg; g.fillRect(0, 0, w, h); g.fillStyle = fg; g.font = mono(54, 800); g.textAlign = 'center'; g.fillText(text, w / 2, h / 2 + 19); }
function drawSheet(g, w, h, p) { g.fillStyle = SLIP_COL[p.end] || '#fff'; g.fillRect(0, 0, w, h); g.fillStyle = '#1d2b24'; g.font = mono(40, 800); g.textAlign = 'center'; g.fillText(`${IC[p.end] || ''} $${cut(p.sym, 7)}`, w / 2, h / 2 + 14); }

function makeBot(k) {
  const g = new THREE.Group(); const white = new THREE.MeshPhysicalMaterial({ color: 0xf7f9fb, roughness: 0.32, clearcoat: 0.7, clearcoatRoughness: 0.25 });
  const band = new THREE.MeshStandardMaterial({ color: BAND[k], roughness: 0.4 }); const dark = new THREE.MeshPhysicalMaterial({ color: 0x0b1118, roughness: 0.1, clearcoat: 1 });
  const eyeM = new THREE.MeshStandardMaterial({ color: 0, emissive: 0x7fe8ff, emissiveIntensity: 2.2 }); const antM = new THREE.MeshStandardMaterial({ color: 0, emissive: LIFE.alive, emissiveIntensity: 2 });
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true; p.add(o); return o; };
  const body = new THREE.Group(); g.add(body);
  add(new THREE.CapsuleGeometry(0.26, 0.22, 8, 24), white, 0, 0.42, 0, body);
  add(new THREE.TorusGeometry(0.265, 0.035, 10, 40), band, 0, 0.44, 0, body).rotation.x = Math.PI / 2;
  const head = new THREE.Group(); head.position.y = 0.92; body.add(head);
  add(new THREE.SphereGeometry(0.24, 32, 24), white, 0, 0, 0, head).scale.set(1.15, 0.9, 1);
  add(new THREE.SphereGeometry(0.22, 32, 16, -Math.PI * 0.4, Math.PI * 0.8, Math.PI * 0.3, Math.PI * 0.38), dark, 0, 0.01, 0.04, head).scale.set(1.18, 1, 1);
  const eyes = [-0.08, 0.08].map(x => add(new THREE.SphereGeometry(0.035, 12, 12), eyeM, x, 0.02, 0.25, head));
  add(new THREE.CylinderGeometry(0.012, 0.012, 0.16, 6), dark, 0, 0.26, 0, head);
  add(new THREE.SphereGeometry(0.045, 12, 12), antM, 0, 0.36, 0, head);
  if (k === 'sherlock') add(new THREE.CylinderGeometry(0.3, 0.3, 0.025, 32), band, 0, 0.16, 0, head);
  if (k === 'devil') [-0.15, 0.15].forEach(x => { add(new THREE.ConeGeometry(0.04, 0.16, 12), band, x, 0.22, 0, head).rotation.z = -x * 2; });
  if (k === 'trigger') add(new THREE.TorusGeometry(0.28, 0.018, 8, 32, Math.PI), band, 0, 0.02, 0, head);
  if (k === 'tally') [-0.08, 0.08].forEach(x => add(new THREE.TorusGeometry(0.055, 0.01, 8, 20), band, x, 0.02, 0.26, head));
  const arms = [-1, 1].map(sd => { const p = new THREE.Group(); p.position.set(sd * 0.3, 0.6, 0); body.add(p); add(new THREE.CapsuleGeometry(0.05, 0.22, 4, 12), white, 0, -0.15, 0, p); return p; });
  add(new THREE.SphereGeometry(0.16, 20, 16), dark, 0, 0.12, 0).scale.y = 0.7;
  const crown = add(new THREE.ConeGeometry(0.12, 0.2, 5), new THREE.MeshStandardMaterial({ color: 0xffc83d, metalness: 0.9, roughness: 0.2, emissive: 0x6a4a00, emissiveIntensity: 0.5 }), 0, 1.5, 0); crown.visible = false;
  g.traverse(o => { o.userData.k = k; });
  return { g, body, head, eyes, antM, arms, crown, white };
}

export default function AgentOffice3D({ d, sel, setSel, paused }) {
  const box = useRef(null); const api = useRef(null); const dRef = useRef(d); const selRef = useRef(sel); const pausedRef = useRef(paused);
  dRef.current = d; selRef.current = sel; pausedRef.current = paused;

  useEffect(() => {
    const host = box.current; if (!host) return undefined;
    const W = () => host.clientWidth || 1000, H = () => host.clientHeight || Math.round((host.clientWidth || 1000) * 0.5);
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(1.5, window.devicePixelRatio || 1)); renderer.setSize(W(), H());
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.78;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    host.prepend(renderer.domElement); renderer.domElement.className = 'agr3-canvas';
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0xdfe5ea); scene.fog = new THREE.Fog(0xdfe5ea, 20, 36);
    const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.45;
    const cam = new THREE.PerspectiveCamera(40, W() / H(), 0.1, 80); const home = new THREE.Vector3(0.4, 5.4, 7.6); cam.position.copy(home); const look = new THREE.Vector3(0.2, 0.7, -0.7); cam.lookAt(look);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xb8c4cc, 0.5));
    const key = new THREE.DirectionalLight(0xffffff, 2.0); key.position.set(-5, 11, 7); key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -9, right: 9, top: 7, bottom: -7, near: 1, far: 30 }); key.shadow.normalBias = 0.03; key.shadow.radius = 5; scene.add(key);

    const M = (c, r = 0.5, m = 0) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
    const box3 = (w, h, dd, mat, x, y, z, cast = true) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, dd), mat); o.position.set(x, y, z); o.castShadow = cast; o.receiveShadow = true; scene.add(o); return o; };
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 20), new THREE.MeshStandardMaterial({ color: 0xf4f6f8, roughness: 0.18, metalness: 0.05 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
    const grid = new THREE.GridHelper(30, 30, 0xdfe5ea, 0xe6ebef); grid.position.y = 0.003; scene.add(grid);
    box3(18, 4, 0.2, M(0xffffff, 0.9), 0, 2, -3.4);
    box3(18, 0.06, 0.04, new THREE.MeshStandardMaterial({ color: 0, emissive: 0x15d16a, emissiveIntensity: 1.2 }), 0, 0.15, -3.28, false);
    const board = tex(1024, 256, drawBoard);
    const boardM = new THREE.Mesh(new THREE.PlaneGeometry(5.6, 1.4), new THREE.MeshStandardMaterial({ map: board, roughness: 0.6 })); boardM.position.set(0, 2.5, -3.28); scene.add(boardM);
    const label = (text, bg, fg, w, x, y, z) => { const t = tex(512, 112, drawLabel); t.userData.redraw(text, bg, fg); const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w * 0.22), new THREE.MeshStandardMaterial({ map: t, roughness: 0.6 })); m.position.set(x, y, z); scene.add(m); return m; };
    [[-7.8, -2.6], [7.6, -2.8]].forEach(([x, z]) => { box3(0.5, 0.6, 0.5, M(0xffffff, 0.4), x, 0.3, z); const leaf = M(0x3fbf74, 0.6);
      for (let i = 0; i < 6; i++) { const l = new THREE.Mesh(new THREE.ConeGeometry(0.1, 1, 8), leaf); l.position.set(x, 1, z); l.rotation.set(Math.sin(i * 2) * 0.5, i, Math.cos(i) * 0.5); l.castShadow = true; scene.add(l); } });

    // 🖨 scanner
    const [px, pz] = PRINTER; box3(1.5, 1.0, 1.1, M(0xffffff, 0.35), px, 0.5, pz); box3(1.3, 0.08, 0.9, M(0x22303d, 0.3), px, 1.04, pz);
    const scan = box3(0.06, 0.04, 0.86, new THREE.MeshStandardMaterial({ color: 0, emissive: 0x2cff8a, emissiveIntensity: 3 }), px, 1.1, pz, false);
    const pScr = tex(256, 96, drawLabel); const pScrM = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.26), new THREE.MeshBasicMaterial({ map: pScr, toneMapped: false })); pScrM.position.set(px + 0.25, 0.75, pz + 0.56); scene.add(pScrM);
    box3(0.9, 0.05, 0.5, M(0xdfe5ea), px + 0.95, 0.55, pz);
    label('SCANNER', '#ffffff', '#14241c', 1.3, px, 1.6, pz);
    // 🗄 GOOD drawer
    const [dx, dz] = DRAWER; box3(1.3, 1.4, 1.0, M(0xffffff, 0.4), dx, 0.7, dz);
    const drawer = box3(1.16, 0.4, 0.95, M(0xf3f6f8, 0.4), dx, 1.05, dz + 0.05); const z0 = dz + 0.05; box3(0.5, 0.06, 0.06, M(0x15d16a, 0.3, 0.4), dx, 1.05, dz + 0.55, false);
    label('GOOD', '#15d16a', '#ffffff', 1.0, dx, 1.75, dz + 0.51);
    // ✂ BAD shredder
    const [sx, sz] = SHRED; box3(1.0, 1.0, 0.8, M(0x2a3540, 0.35, 0.3), sx, 0.5, sz); box3(1.04, 0.18, 0.84, M(0xff4466, 0.4), sx, 1.09, sz);
    label('BAD', '#ff4466', '#ffffff', 0.9, sx, 1.6, sz + 0.43);
    const strips = Array.from({ length: 10 }, (_, i) => { const s = box3(0.05, 0.22, 0.01, M(0xffffff, 0.7), sx - 0.3 + i * 0.07, 0.8, sz + 0.42, false); s.visible = false; return s; });

    const deskM = M(0xffffff, 0.35); const legM = M(0xb9c3cb, 0.3, 0.7);
    const bots = AGENTS.map(([k, , name], i) => { const [x, z] = DESK[i];
      box3(1.6, 0.06, 0.8, deskM, x, 0.78, z); [[-0.72, -0.32], [0.72, -0.32], [-0.72, 0.32], [0.72, 0.32]].forEach(([a, b]) => box3(0.05, 0.76, 0.05, legM, x + a, 0.38, z + b));
      const scr = tex(512, 320, drawScreen); box3(0.86, 0.56, 0.04, M(0x1c2632, 0.4), x, 1.15, z - 0.25);
      const sm = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.5), new THREE.MeshBasicMaterial({ map: scr, toneMapped: false })); sm.position.set(x, 1.15, z - 0.228); scene.add(sm);
      box3(0.06, 0.3, 0.06, legM, x, 0.92, z - 0.25);
      const b = makeBot(k); const homePos = new THREE.Vector3(x, 0, z + 0.75); b.g.position.copy(homePos); b.g.rotation.y = Math.PI; scene.add(b.g);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.025, 8, 48), new THREE.MeshStandardMaterial({ color: 0, emissive: 0x15d16a, emissiveIntensity: 2 })); ring.rotation.x = -Math.PI / 2; ring.position.y = 0.02; ring.visible = false; scene.add(ring);
      return { k, name, i, b, scr, home: homePos, ring, bub: null, spin: 3, st: 'alive', drop: 0, dropped: false }; });

    // sheets: scanner → each desk → GOOD drawer / BAD shredder, one at a time, every coin of the pass in turn
    const sheetGeo = new THREE.PlaneGeometry(0.42, 0.3); let sheets = [];
    const build = pk => { sheets.forEach(s => { scene.remove(s.m); s.m.material.map.dispose(); s.m.material.dispose(); });
      sheets = pk.map(p => { const t = tex(256, 180, drawSheet); t.userData.redraw(p); const m = new THREE.Mesh(sheetGeo, new THREE.MeshStandardMaterial({ map: t, roughness: 0.8, side: THREE.DoubleSide })); m.castShadow = true; m.visible = false; scene.add(m); return { m, end: p.end }; }); };
    const deskPt = i => new THREE.Vector3(DESK[i][0], 0.84, DESK[i][1] + 0.1);
    const ROUTE = { go: [new THREE.Vector3(px + 0.95, 0.6, pz), ...[0, 1, 2, 3].map(deskPt), new THREE.Vector3(dx, 1.3, dz)] };
    ROUTE.bad = [...ROUTE.go.slice(0, 5), new THREE.Vector3(sx, 1.25, sz)];
    const LEG = 2.2;

    const apply = () => { const dd = dRef.current; const s = screensOf(dd);
      const best = (dd?.agents || []).filter(a => a.n >= 10).sort((a, b) => (b.right ?? b.med ?? 0) - (a.right ?? a.med ?? 0))[0];
      const bestCall = (dd?.thoughts || []).find(l => l.who === best?.key)?.text;
      board.userData.redraw(s, dd?.perf?.at || 0, dd?.perf?.regime, best ? `${best.name} leads${best.right != null ? ` · ${best.right}% right` : ''}${bestCall ? ` — ${cut(bestCall, 34)}` : ''}` : '');
      pScr.userData.redraw(`${s.n} READ`, '#0b1a14', '#45e486');
      bots.forEach(bt => { const l = dd?.life?.[bt.k] || {}; bt.st = l.status || 'alive'; bt.spin = spinSec(dd?.perf?.[bt.k]); bt.scr.userData.redraw(bt.k, s);
        bt.b.antM.emissive.setHex(LIFE[bt.st] || LIFE.alive); bt.b.crown.visible = !!best && best.key === bt.k;
        if (l.born && Date.now() / 1000 - l.born < 600 && (l.gen || 1) > 1 && !bt.dropped) { bt.drop = 1; bt.dropped = true; } });
      build(packetsOf(dd?.table)); };
    apply();

    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2(); let hover = null; const par = { x: 0, y: 0 };
    const pick = e => { const rc = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ptr, cam); const hit = ray.intersectObjects(bots.map(b => b.b.g), true)[0]; return hit ? hit.object.userData.k : null; };
    const onMove = e => { hover = pick(e); renderer.domElement.style.cursor = hover ? 'pointer' : 'default'; const rc = renderer.domElement.getBoundingClientRect(); par.x = (e.clientX - rc.left) / rc.width - 0.5; par.y = (e.clientY - rc.top) / rc.height - 0.5; };
    const onClick = e => { const k = pick(e); if (k) setSel(k); };
    renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('click', onClick);
    const bubWrap = host.querySelector('.agr3-bubs'); bots.forEach(b => { b.bub = bubWrap?.children[b.i]; });

    const still = () => document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let seen = true; const io = new IntersectionObserver(es => { seen = es[0]?.isIntersecting ?? true; }); io.observe(host);
    const v = new THREE.Vector3(); const tmp = new THREE.Vector3(); const tgt = new THREE.Vector3(); const prev = new THREE.Vector3(); const clock = new THREE.Clock(); let raf = 0, last = 0, prevT = 0;
    const frame = moving => {
      const t = clock.getElapsedTime(); const dt = Math.min(0.1, t - prevT); prevT = t;
      cam.position.set(home.x + (moving ? par.x * 1.6 : 0), home.y - (moving ? par.y * 0.8 : 0), home.z); cam.lookAt(look);
      const cyc = LEG * 5 + 0.8; const n = sheets.length; const si = n ? Math.floor(t / cyc) % n : -1; const lt = t % cyc;
      const leg = Math.min(4, Math.floor(lt / LEG)); const f = Math.min(1, (lt - leg * LEG) / LEG); const ease = f * f * (3 - 2 * f);
      sheets.forEach((s, i) => { s.m.visible = i === si && (moving ? lt < LEG * 5 - 0.3 : false); });
      scan.position.x = px + Math.sin(t * 3) * 0.6;
      const cur = si >= 0 ? sheets[si] : null;
      if (cur) { const r = cur.end === 'go' ? ROUTE.go : ROUTE.bad; tmp.copy(r[leg]).lerp(r[leg + 1], ease); tmp.y += Math.sin(ease * Math.PI) * 0.5;
        cur.m.position.copy(tmp); cur.m.rotation.set(-Math.PI / 2 + 0.3, 0, Math.sin(t * 4) * 0.2); }
      drawer.position.z = lerp(drawer.position.z, z0 + (moving && cur?.end === 'go' && leg === 4 ? 0.55 : 0), 0.15);
      strips.forEach((st, j) => { st.visible = moving && !!cur && cur.end !== 'go' && leg === 4 && f > 0.6; st.position.y = 0.9 - ((t * 2 + j * 0.13) % 0.6); });
      bots.forEach(bt => { const { b } = bt; const sp = (Math.PI * 2) / (bt.spin || 3);
        const carrying = moving && !!cur && (leg === bt.i || (bt.i === 3 && leg === 4));
        if (carrying) tgt.set(tmp.x, 0, tmp.z + 0.45); else tgt.copy(bt.home);
        prev.copy(b.g.position); b.g.position.x = lerp(b.g.position.x, tgt.x, carrying ? 0.12 : 0.06); b.g.position.z = lerp(b.g.position.z, tgt.z, carrying ? 0.12 : 0.06);
        const mv = Math.hypot(b.g.position.x - prev.x, b.g.position.z - prev.z);
        b.g.rotation.y = mv > 0.002 ? Math.atan2(b.g.position.x - prev.x, b.g.position.z - prev.z) : lerp(b.g.rotation.y, Math.PI, 0.08);
        if (bt.drop > 0) { bt.drop = Math.max(0, bt.drop - dt * 0.6); b.g.position.y = bt.drop * bt.drop * 5; } else b.g.position.y = 0;   // 🐣 reborn: drops in
        if (moving) { b.body.position.y = Math.abs(Math.sin(t * (mv > 0.002 ? 10 : 2) + bt.i)) * (mv > 0.002 ? 0.06 : 0.02);
          b.arms[0].rotation.x = carrying ? -1.2 : -0.6 + Math.sin(t * sp * 2) * 0.35; b.arms[1].rotation.x = carrying ? -1.2 : -0.6 + Math.sin(t * sp * 2 + Math.PI) * 0.35;
          b.head.rotation.y = Math.sin(t * 0.6 + bt.i) * 0.3; const blink = ((t + bt.i) % 4) < 0.12 ? 0.1 : 1; b.eyes.forEach(e => { e.scale.y = blink; });
          b.antM.emissiveIntensity = 1.4 + Math.sin(t * (bt.st === 'scrap' ? 14 : 3)) * 0.9; b.crown.rotation.y = t; }
        bt.ring.visible = selRef.current === bt.k; bt.ring.position.x = b.g.position.x; bt.ring.position.z = b.g.position.z;
        b.white.emissive.setHex(hover === bt.k ? 0x16351f : 0);
        if (bt.bub) { v.set(b.g.position.x, b.g.position.y + 1.75, b.g.position.z); v.project(cam); bt.bub.style.transform = `translate(${(v.x * 0.5 + 0.5) * renderer.domElement.clientWidth}px, ${(-v.y * 0.5 + 0.5) * renderer.domElement.clientHeight}px) translate(-50%, -100%)`; } });
      renderer.render(scene, cam);
    };
    const loop = now => { raf = requestAnimationFrame(loop); if (!seen || pausedRef.current) return;
      if (document.hidden || still()) { if (now - last > (document.hidden ? 2000 : 1000)) { last = now; frame(false); } return; }   // a still frame — never a blank office
      frame(true); };
    raf = requestAnimationFrame(loop);
    const ro = new ResizeObserver(() => { renderer.setSize(W(), H()); cam.aspect = W() / H(); cam.updateProjectionMatrix(); }); ro.observe(host);
    api.current = { apply };
    return () => { cancelAnimationFrame(raf); io.disconnect(); ro.disconnect(); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('click', onClick);
      scene.traverse(o => { if (o.geometry) o.geometry.dispose(); const m = o.material; (Array.isArray(m) ? m : m ? [m] : []).forEach(mm => { if (mm.map) mm.map.dispose(); mm.dispose(); }); });
      pm.dispose(); renderer.dispose(); renderer.domElement.remove(); api.current = null; };
  }, [setSel]);

  useEffect(() => { api.current?.apply(); }, [d]);   // a new pass → monitors, board, scanner count, sheets
  return <div className="agr3" ref={box} data-testid="agr-3d">
    <div className="agr3-bubs" aria-hidden>{AGENTS.map(([k, ic, name]) => <span key={k} className={`agr3-bub is-${k}`}>{ic} {name}</span>)}</div>
  </div>;
}
