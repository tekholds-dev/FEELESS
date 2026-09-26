import * as THREE from 'three';

// Particle bursts on the globe, one per real activity event (chat message, price tick, big mover).
// Each burst = a spray of additive glow particles + a light pillar, animated on the GPU-side
// buffers and disposed after its lifetime so nothing leaks while the globe spins for hours.

const LIFE_MS = 2200;
let dotTex = null;
function dotTexture() {
  if (dotTex) return dotTex;
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'); const grad = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.35, 'rgba(255,255,255,.7)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 32, 32);
  dotTex = new THREE.CanvasTexture(c);
  return dotTex;
}

export const BURST_COLORS = {
  pump: '#ffb020', moon: '#ff5a1f', dump: '#ff4d7a', chat: null, signal: '#b388ff', whale: '#f5c542', catch: '#ff2d55', tick: '#5ee0ff',
};

// Builds the three.js object for one burst. Positioned by the globe's custom layer; animated by tickBurst.
export function burstObject(b) {
  const group = new THREE.Group();
  const n = Math.round(18 + b.power * 46);
  const pos = new Float32Array(n * 3);
  const vel = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    // Spray mostly outward from the surface (+z after lookAt), fanned across the tangent plane.
    const a = Math.random() * Math.PI * 2;
    const spread = 0.35 + Math.random() * 0.9;
    const up = 0.6 + Math.random() * 1.4;
    vel[i * 3] = Math.cos(a) * spread; vel[i * 3 + 1] = Math.sin(a) * spread; vel[i * 3 + 2] = up;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const color = new THREE.Color(b.color);
  const mat = new THREE.PointsMaterial({ map: dotTexture(), color, size: 1.4 + b.power * 1.6, transparent: true, opacity: 1, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true });
  const pts = new THREE.Points(geo, mat);
  group.add(pts);

  // Light pillar for the loud events — reads from across the planet.
  let pillar = null;
  if (b.power >= 0.55) {
    const pg = new THREE.CylinderGeometry(0.12, 0.5, 1, 10, 1, true);
    pg.rotateX(Math.PI / 2); pg.translate(0, 0, 0.5);
    pillar = new THREE.Mesh(pg, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
    group.add(pillar);
  }
  // Flash at the impact point.
  const flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), color, transparent: true, opacity: 1, depthWrite: false, blending: THREE.AdditiveBlending }));
  group.add(flash);

  group.userData = { born: b.born, vel, pos, pts, pillar, flash, power: b.power, geo };
  return group;
}

// Advance one burst to `now`. Returns false once it has finished (caller drops it).
export function tickBurst(obj, now) {
  const u = obj.userData;
  const t = (now - u.born) / LIFE_MS;
  if (t >= 1) return false;
  const ease = 1 - (1 - t) ** 3;
  const reach = 5 + u.power * 11;
  for (let i = 0; i < u.vel.length; i += 3) {
    u.pos[i] = u.vel[i] * reach * ease;
    u.pos[i + 1] = u.vel[i + 1] * reach * ease;
    u.pos[i + 2] = u.vel[i + 2] * reach * ease - 3 * t * t; // a touch of gravity back to the surface
  }
  u.geo.attributes.position.needsUpdate = true;
  u.pts.material.opacity = 1 - t;
  const f = Math.max(0, 1 - t * 3);
  u.flash.scale.setScalar(4 + u.power * 10 * (1 - f) + 2);
  u.flash.material.opacity = f;
  if (u.pillar) {
    u.pillar.scale.set(1, 1, 4 + u.power * 12 * Math.min(1, t * 4));
    u.pillar.material.opacity = 0.8 * (1 - t);
  }
  return true;
}

export function disposeBurst(obj) {
  obj.traverse(o => { o.geometry?.dispose?.(); o.material?.dispose?.(); });
}

// How loud a coin is right now: its real 24h move and volume, 0..1.
export function coinHeat(t) {
  const ch = Math.abs(Number(t.change24h) || 0);
  const vol = Number(t.volume24h) || 0;
  return Math.min(1, ch / 30 * 0.7 + Math.log10(1 + vol / 1e5) / 5 * 0.3);
}

export function kindFor(t) {
  const ch = Number(t.change24h) || 0;
  if (ch >= 25) return 'moon';
  if (ch >= 5) return 'pump';
  if (ch <= -5) return 'dump';
  return 'tick';
}
