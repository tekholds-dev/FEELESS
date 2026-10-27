// 🏁 THE RACEWAY ENGINE — pure (no three.js here, so it tests in jest): the race city laid out from the Familia world, the vehicles, one physics
// step, checkpoints. The SERVER deals the track (backend/raceway.py — the same grid: a road every `cell` metres) and checks every time.
export const RACE = { grid: 8, cell: 38, road: 12 };
export const VEHICLES = {
  car: { name: 'MUSCLE CAR', max: 46, accel: 15, brake: 30, turn: 2.1, drag: 0.55, len: 4.4, wid: 2.0, h: 1.3, color: '#15d16a', tip: 'Balanced: quick, grips, top speed 166 km/h' },
  bike: { name: 'STREET BIKE', max: 52, accel: 19, brake: 24, turn: 2.7, drag: 0.7, len: 2.2, wid: 0.8, h: 1.1, color: '#ff5d73', tip: 'Fastest + nimblest — bounces hard off walls (187 km/h)' },
  truck: { name: 'BOX TRUCK', max: 34, accel: 9, brake: 20, turn: 1.5, drag: 0.45, len: 7, wid: 2.6, h: 3, color: '#f5c451', tip: 'Slow but heavy — barely loses speed on a hit (122 km/h)' },
};
const PALETTE = ['#1c2a33', '#24202e', '#1e2b22', '#2a2320', '#202634'];
const rnd = seed => { let s = seed >>> 0 || 1; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
const hash = str => { let h = 7; for (const ch of String(str)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };

// pure: the buildings lining the streets — one block per grid cell, the world's blocks mapped onto them (a family's block is taller and wears
// its colour + tag on a sign); free blocks are low shops. → [{x, z, w, d, h, color, tag, lit}] (x, z = centre)
export function cityOf(blocks, seed = 'feeless') {
  const { grid, cell, road } = RACE; const r = rnd(hash(seed)); const bs = (blocks || []).filter(Boolean); const out = [];
  for (let i = 0; i < grid; i += 1) for (let j = 0; j < grid; j += 1) {
    const b = bs.length ? bs[(i * grid + j) % bs.length] : null; const x0 = i * cell + road / 2; const z0 = j * cell + road / 2; const span = cell - road;
    const owned = !!b?.owner; const fam = owned && b.kind !== 'cpu' && b.kind !== 'cartel';
    const n = owned ? 1 + Math.floor(r() * 2) : 2 + Math.floor(r() * 2);
    for (let k = 0; k < n; k += 1) {
      const w = n === 1 ? span - 4 : (span - 4) / 2 - 1; const d = n <= 2 ? span - 4 : (span - 4) / 2 - 1;
      const cx = x0 + 2 + (n === 1 ? w / 2 : (k % 2) * (w + 2) + w / 2); const cz = z0 + 2 + (n <= 2 ? d / 2 : Math.floor(k / 2) * (d + 2) + d / 2);
      const h = owned ? 22 + Math.min(60, Math.log10(1 + (Number(b.power) || 1000)) * 8) * (0.7 + r() * 0.5) : 6 + r() * 14;
      out.push({ x: cx, z: cz, w, d, h: Math.round(h * 10) / 10, color: fam ? (b.color || '#d4af37') : b?.kind === 'cartel' ? '#3ddc84' : b?.kind === 'cpu' ? '#ff5d73' : PALETTE[Math.floor(r() * PALETTE.length)],
        tag: k === 0 && owned ? (b.tag || '') : '', own: owned ? (fam ? 'fam' : b.kind) : '', lit: 0.25 + r() * 0.6 });
    }
  }
  return out;
}

// pure: one physics step. s = {x, z, yaw, speed}; inp = {gas: -1…1, steer: -1…1, brake}; boxes = the buildings. → {…s, hit}
export function step(s, inp, dt, veh, boxes = []) {
  const v = VEHICLES[veh] || VEHICLES.car; const { grid, cell } = RACE; const gas = Math.max(-1, Math.min(1, inp?.gas || 0)); const steer = Math.max(-1, Math.min(1, inp?.steer || 0));
  let speed = s.speed;
  if (gas > 0) speed += v.accel * gas * dt;
  else if (gas < 0) speed -= (speed > 0.5 ? v.brake : v.accel * 0.6) * -gas * dt;
  if (inp?.brake) speed -= Math.sign(speed) * Math.min(Math.abs(speed), v.brake * dt);
  speed -= speed * v.drag * 0.1 * dt * (gas ? 1 : 3);                     // rolling drag (coasting slows faster)
  speed = Math.max(-v.max * 0.35, Math.min(v.max, speed));
  const grip = Math.min(1, Math.abs(speed) / 10);
  const yaw = s.yaw + steer * v.turn * dt * grip * Math.sign(speed || 1) * (1 - Math.min(0.45, Math.abs(speed) / v.max * 0.45));
  let x = s.x + Math.sin(yaw) * speed * dt; let z = s.z + Math.cos(yaw) * speed * dt; let hit = false;
  const lim = grid * cell; x = Math.max(-8, Math.min(lim + 8, x)); z = Math.max(-8, Math.min(lim + 8, z));
  const rad = v.wid / 2 + 0.4;
  for (const b of boxes) {
    const dx = x - b.x; const dz = z - b.z; const hx = b.w / 2 + rad; const hz = b.d / 2 + rad;
    if (Math.abs(dx) < hx && Math.abs(dz) < hz) {                         // inside: push out on the shallow side, lose speed
      const px = hx - Math.abs(dx); const pz = hz - Math.abs(dz);
      if (px < pz) x += Math.sign(dx || 1) * px; else z += Math.sign(dz || 1) * pz;
      hit = true;
    }
  }
  if (hit) speed *= veh === 'truck' ? 0.7 : veh === 'bike' ? -0.3 : 0.35;
  return { x, z, yaw, speed, hit };
}

export const atCheckpoint = (s, cp, r = 8) => !!cp && Math.hypot(s.x - cp[0], s.z - cp[1]) <= r;
export const kmh = mps => Math.round(Math.abs(mps) * 3.6);
export const fmtMs = ms => { if (ms == null) return '—'; const t = Math.max(0, Math.round(ms)); const m = Math.floor(t / 60000); const s = ((t % 60000) / 1000).toFixed(2).padStart(5, '0'); return `${m}:${s}`; };
// pure: the heading (radians, 0 = +z) from the car to a point — the HUD arrow
export const bearing = (s, p) => Math.atan2(p[0] - s.x, p[1] - s.z) - s.yaw;
// pure: traffic — a few cars looping the avenues (row / column roads), each at its own pace. t = seconds → [{x, z, yaw}]
export function traffic(t, n = 8) {
  const { grid, cell } = RACE; const L = grid * cell;
  return Array.from({ length: n }, (_, i) => {
    const lane = 1 + (i % (grid - 1)); const along = ((t * (9 + (i % 4) * 3) + i * 47) % L + L) % L; const back = i % 2;
    return i % 3 === 0 ? { x: lane * cell + (back ? -2.5 : 2.5), z: back ? L - along : along, yaw: back ? Math.PI : 0 }
      : { x: back ? L - along : along, z: lane * cell + (back ? 2.5 : -2.5), yaw: back ? -Math.PI / 2 : Math.PI / 2 };
  });
}
