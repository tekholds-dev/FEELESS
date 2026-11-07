import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { atomSpot, ridgeXY, RIDGES } from '../../lib/atomSpot';

// ⚛ The Collective's print in 3D (owner 2026-11-07). The small dim atoms only make up the shape. Every larger atom is one real proof, and you can tap it for a few basic facts. Only an active proof glows.
const KIND = { PoW: 'Proof of Work', PoP: 'Proof of Perps', PoB: 'Proof of Bids', PoC: 'Proof of Content', PoStatic: 'Proof of Static' };
const RESULT = { won: 'It won', lost: 'It lost', open: 'Still running', filed: 'Filed' };
const SCALE = 1 / 95;
const lift = (x, y, ridge) => { const r = Math.hypot(x, y) / 480; return new THREE.Vector3(x * SCALE, -y * SCALE, (0.9 - r * r * 2.6) + Math.sin(ridge * 0.5 + x * 0.012) * 0.1); };

export default function AtomPrint({ proofs = [], colors }) {
  const host = useRef(null); const card = useRef(null); const api = useRef({}); const [sel, setSel] = useState(null); const [fail, setFail] = useState(false);
  const rows = useMemo(() => (proofs || []).map(p => ({ p, at: atomSpot(p.id) })), [proofs]); const rowsRef = useRef(rows); rowsRef.current = rows;
  useEffect(() => {
    const el = host.current; if (!el) return undefined; let renderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch { setFail(true); return undefined; }
    const lite = document.body.classList.contains('fx-lite'); const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    renderer.setPixelRatio(lite ? 1 : Math.min(window.devicePixelRatio || 1, 1.75)); renderer.toneMapping = THREE.ACESFilmicToneMapping; el.appendChild(renderer.domElement);
    const scene = new THREE.Scene(); const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 80); camera.position.set(0, 0, 13); scene.add(new THREE.HemisphereLight('#ffffff', '#1a1030', 1.6)); const key = new THREE.DirectionalLight('#ffffff', 1.6); key.position.set(3, 5, 8); scene.add(key);
    const print = new THREE.Group(); scene.add(print); const tint = colors.map(c => new THREE.Color(c));
    // the shape: each ridge a faint line, with small dim atoms along it
    const dot = new THREE.IcosahedronGeometry(0.028, 1); const FILL = lite ? 1200 : 3200; const fill = new THREE.InstancedMesh(dot, new THREE.MeshStandardMaterial({ roughness: 0.55, metalness: 0.2 }), FILL); const m = new THREE.Matrix4(); const c = new THREE.Color();
    for (let i = 0; i < FILL; i += 1) { const ridge = i % RIDGES; const a = ((i * 2.399963) % (Math.PI * 2.08)) - 0.12; const [x, y] = ridgeXY(ridge, a); m.makeScale(0.7 + (i % 5) * 0.14, 0.7 + (i % 5) * 0.14, 0.7 + (i % 5) * 0.14); m.setPosition(lift(x, y, ridge)); fill.setMatrixAt(i, m); fill.setColorAt(i, c.copy(tint[ridge % 3]).multiplyScalar(0.42)); }
    print.add(fill);
    const lineMats = tint.map(t => new THREE.LineBasicMaterial({ color: t.clone().multiplyScalar(0.55), transparent: true, opacity: 0.22 }));
    for (let ridge = 0; ridge < RIDGES; ridge += 2) { const pts = []; for (let j = 0; j <= 150; j += 1) { const [x, y] = ridgeXY(ridge, (j / 150) * Math.PI * 2.08 - 0.12); pts.push(lift(x, y, ridge)); } print.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMats[ridge % 3])); }
    let reals = []; let orbits = []; const realGroup = new THREE.Group(); print.add(realGroup); const body = new THREE.IcosahedronGeometry(0.075, 2); const ringGeo = new THREE.TorusGeometry(0.19, 0.005, 6, 48); const electron = new THREE.SphereGeometry(0.017, 8, 8);
    const hot = () => new THREE.MeshBasicMaterial({ color: new THREE.Color(colors[0]).multiplyScalar(3.4) }); const cool = new THREE.MeshStandardMaterial({ color: '#b9c0d0', roughness: 0.35, metalness: 0.5 }); const hit = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.012, 8, 48), new THREE.MeshBasicMaterial({ color: '#ffffff' })); hit.visible = false; print.add(hit);
    const build = () => { realGroup.clear(); reals = []; orbits = []; rowsRef.current.forEach(({ p, at }, i) => { const pos = lift(at.x, at.y, at.ridge); const atom = new THREE.Mesh(body, p.active ? hot() : cool); atom.position.copy(pos); realGroup.add(atom); reals.push({ p, pos }); if (p.active) { [0, 1].forEach(n => { const ring = new THREE.Group(); ring.position.copy(pos); ring.rotation.set(1.1 + n * 1.2 + i, i * 0.7, n * 0.8); ring.add(new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(colors[1]).multiplyScalar(1.5), transparent: true, opacity: 0.55 }))); const e = new THREE.Mesh(electron, new THREE.MeshBasicMaterial({ color: new THREE.Color(colors[1]).multiplyScalar(4) })); e.position.x = 0.19; ring.add(e); realGroup.add(ring); orbits.push({ ring, speed: 1.1 + n * 0.5 + (i % 3) * 0.2 }); }); } }); };
    build(); api.current.build = build;
    const orbit = new OrbitControls(camera, renderer.domElement); orbit.enablePan = false; orbit.enableDamping = true; orbit.minDistance = 6; orbit.maxDistance = 20; orbit.zoomSpeed = 0.6;
    let composer = null; let bloom = null;
    if (!lite) { composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 2 })); composer.addPass(new RenderPass(scene, camera)); bloom = new UnrealBloomPass(new THREE.Vector2(4, 4), 0.85, 0.55, 1.15); composer.addPass(bloom); composer.addPass(new OutputPass()); }
    const size = () => { const w = el.clientWidth || 1; const h = el.clientHeight || 1; renderer.setSize(w, h); composer?.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); print.position.x = w > 760 ? 2.1 : 0; print.position.y = w > 760 ? 0 : -0.6; const fitD = w > 760 ? 12.5 : 16; if (!api.current.placed) { camera.position.z = fitD; api.current.placed = true; } }; size(); const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(size) : null; ro?.observe(el);
    // tap: the nearest real atom on screen, so a thumb can hit one
    const v = new THREE.Vector3(); const screenOf = pos => { v.copy(pos).applyMatrix4(print.matrixWorld).project(camera); const r = renderer.domElement.getBoundingClientRect(); return [(v.x + 1) / 2 * r.width, (1 - v.y) / 2 * r.height, v.z]; };
    const nearest = (x, y, reach) => { let best = null; let d0 = reach * reach; reals.forEach(a => { const [sx, sy, z] = screenOf(a.pos); const d = (sx - x) ** 2 + (sy - y) ** 2; if (z < 1 && d < d0) { d0 = d; best = a; } }); return best; };
    const dom = renderer.domElement; let down = null; let chosen = null; const local = e => { const r = dom.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const pd = e => { down = local(e); }; const pm = e => { const [x, y] = local(e); dom.style.cursor = nearest(x, y, 22) ? 'pointer' : 'grab'; }; const pu = e => { if (!down) return; const [x, y] = local(e); const moved = Math.hypot(x - down[0], y - down[1]) > 6; down = null; if (moved) return; const a = nearest(x, y, 26); chosen = a; hit.visible = !!a; if (a) hit.position.copy(a.pos); setSel(a ? a.p : null); };
    dom.addEventListener('pointerdown', pd); dom.addEventListener('pointermove', pm); dom.addEventListener('pointerup', pu); api.current.clear = () => { chosen = null; hit.visible = false; setSel(null); };
    let seen = true; const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(x => { seen = x[0]?.isIntersecting; }) : null; io?.observe(el); const clock = new THREE.Clock(); let slow = 0;
    renderer.setAnimationLoop(() => { const dt = clock.getDelta(); if (!seen || document.hidden) return; const t = clock.elapsedTime; if (!still && !lite) { print.rotation.y = Math.sin(t * 0.16) * 0.32 - 0.1; print.rotation.x = Math.sin(t * 0.11) * 0.08 - 0.12; orbits.forEach(o => { o.ring.rotation.z += dt * o.speed; }); } orbit.update(); if (composer) { slow = dt > 0.05 ? slow + 1 : Math.max(0, slow - 1); if (slow > 50) { composer = null; renderer.setPixelRatio(1); size(); } } if (chosen && card.current) { const [x, y] = screenOf(chosen.pos); const w = el.clientWidth; const h = el.clientHeight; const cw = card.current.offsetWidth; const ch = card.current.offsetHeight; card.current.style.transform = `translate(${Math.max(8, Math.min(w - cw - 8, x > w * 0.55 ? x - cw - 26 : x + 26))}px, ${Math.max(8, Math.min(h - ch - 8, y - ch / 2))}px)`; } if (composer) composer.render(); else renderer.render(scene, camera); });
    return () => { renderer.setAnimationLoop(null); ro?.disconnect(); io?.disconnect(); dom.removeEventListener('pointerdown', pd); dom.removeEventListener('pointermove', pm); dom.removeEventListener('pointerup', pu); orbit.dispose(); composer?.dispose?.(); renderer.dispose(); dom.remove(); api.current = {}; };
  }, [colors]);   // a new theme repaints the print
  useEffect(() => { api.current.build?.(); }, [rows]);
  const active = rows.filter(r => r.p.active).length;
  return <div className="cll-atoms" ref={host} data-testid="cll-print" aria-label="The Collective's print. Larger atoms are real proofs">{fail ? <p className="cll-empty" data-testid="cll-nogl">This browser cannot draw 3D. {rows.length} real proofs are on the print.</p> : null}
    <div className="cll-legend" data-testid="cll-legend"><span data-tip="Working right now, in the Pool, or filed today"><i className="is-hot" /><b className="m-num" data-testid="cll-active">{active}</b> active</span><span data-tip="A real proof on the record. Tap it"><i className="is-real" /><b className="m-num" data-testid="cll-real">{rows.length}</b> real proofs</span><span data-tip="These only make up the shape"><i className="is-fill" />the print</span></div>
    {rows.length ? (sel ? null : <p className="cll-hint">Tap a larger atom for its proof</p>) : <p className="cll-empty">No proof yet. The first one lights up here.</p>}
    {sel ? <article ref={card} className="cll-card" data-testid="cll-card"><header><small className={sel.active ? 'is-active' : ''}>{sel.active ? 'ACTIVE PROOF' : 'REAL PROOF'}</small><button type="button" onClick={() => api.current.clear?.()} aria-label="Close" data-tip="Close" data-testid="cll-card-close">✕</button></header><b>{KIND[sel.kind] || 'Proof'}</b><dl><div><dt>Rank</dt><dd className="m-num">{sel.rank || '–'}</dd></div><div><dt>Result</dt><dd>{RESULT[sel.result] || 'Filed'}</dd></div><div><dt>Filed</dt><dd>{sel.age ? `${sel.age} d ago` : 'today'}</dd></div></dl></article> : null}
  </div>;
}
