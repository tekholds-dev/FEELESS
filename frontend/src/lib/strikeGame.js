// 🎯 STRIKE ZONE — the pure game rules (no three.js here, so jest tests them): the gun's stats with its attachments (the server's arena.py
// catalog, mirrored), a ray vs a standing body (head / body), damage falloff, the bots' brain, recoil + spread, the level bar.

// pure: a loadout → the gun's live stats (same math as backend/arena.stats; `catalog` = GET /api/reputation/arena)
export function gunStats(catalog, loadout) {
  const guns = catalog?.guns || {}; const parts = catalog?.parts || {}; const lo = loadout || catalog?.default || {};
  const g = { ...(guns[lo.gun] || guns.rifle || { name: 'FX-7 RIFLE', dmg: 24, rpm: 600, mag: 30, reload: 2.1, range: 120, spread: 0.012, recoil: 0.35, speed: 1, pellets: 1 }) }; let zoom = 1.25;
  Object.entries(parts).forEach(([slot, list]) => {
    const p = list.find(x => x.id === lo[slot]) || list[0]; if (!p) return;
    Object.entries(p.mod || {}).forEach(([k, v]) => { if (k === 'zoom') zoom = v; else if (k in g) g[k] *= 1 + v; });
  });
  g.mag = Math.round(g.mag); g.zoom = zoom; g.interval = 60 / g.rpm; return g;
}

// pure: does a ray hit a standing body? body = feet {x, y, z}, height h, radius r → {dist, head} | null. The body is a vertical segment.
export function rayBody(o, d, feet, h = 1.8, r = 0.38) {
  // closest points between the ray o + t·d (t ≥ 0) and the segment feet → feet + (0, h, 0)
  const ux = d.x, uy = d.y, uz = d.z; const wx = o.x - feet.x, wy = o.y - feet.y, wz = o.z - feet.z;
  const a = ux * ux + uy * uy + uz * uz; const b = uy; const c = 1; const dd = ux * wx + uy * wy + uz * wz; const e = wy;
  const den = a * c - b * b; let t = den > 1e-9 ? (b * e - c * dd) / den : 0; let s = den > 1e-9 ? (a * e - b * dd) / den : e;
  s = Math.max(0, Math.min(h, s)); t = Math.max(0, (s * b - dd) / a);
  const px = o.x + ux * t - feet.x, py = o.y + uy * t - (feet.y + s), pz = o.z + uz * t - feet.z;
  const dist2 = px * px + py * py + pz * pz;
  return dist2 <= r * r ? { dist: t * Math.sqrt(a), head: s >= h * 0.82 } : null;
}

// pure: damage of one pellet at a distance (full to the gun's range, then fading to 30 % at twice the range), ×2 on the head
export function damageAt(g, dist, head) {
  const fall = dist <= g.range ? 1 : Math.max(0.3, 1 - ((dist - g.range) / g.range) * 0.7);
  return Math.round(g.dmg * fall * (head ? 2 : 1));
}

// pure: how wide the shot goes right now — the gun's spread, ×2.2 hip-firing on the move, ×0.45 aimed, + the bloom from firing fast
export const spreadNow = (g, { moving = false, ads = false, bloom = 0 } = {}) => g.spread * (moving ? 2.2 : 1) * (ads ? 0.45 : 1) + bloom;

export const BOT_DIFF = { easy: { n: 3, acc: 0.18, react: 0.9, hp: 80 }, normal: { n: 5, acc: 0.3, react: 0.55, hp: 100 }, hard: { n: 7, acc: 0.45, react: 0.3, hp: 120 } };
// pure: one bot's decision. bot = {x, z, hp, seen (s it has had sight), cool (s to next shot)}; you = {x, z, moving}; los = it can see you.
// → {mode: 'hunt' | 'fight' | 'retreat', face (radians toward the goal), go (0…1 move), shoot (true when it fires this tick), hitOdds}
export function botBrain(bot, you, los, dt, diff = 'normal') {
  const D = BOT_DIFF[diff] || BOT_DIFF.normal; const dx = you.x - bot.x; const dz = you.z - bot.z; const dist = Math.hypot(dx, dz);
  const toYou = Math.atan2(dx, dz); const seen = los ? (bot.seen || 0) + dt : 0; const cool = Math.max(0, (bot.cool || 0) - dt);
  if (bot.hp < 30 && los) return { mode: 'retreat', face: toYou + Math.PI, go: 1, shoot: false, seen, cool, hitOdds: 0 };
  if (!los || dist > 75) return { mode: 'hunt', face: toYou, go: dist > 6 ? 0.8 : 0, shoot: false, seen, cool, hitOdds: 0 };
  const shoot = seen >= D.react && cool === 0;
  const hitOdds = Math.max(0.03, D.acc * (1 - Math.min(1, dist / 90)) * (you.moving ? 0.65 : 1));
  return { mode: 'fight', face: toYou, go: dist > 22 ? 0.6 : dist < 8 ? -0.4 : 0.15, strafe: Math.sin((bot.t || 0) * 1.7), shoot, seen, cool: shoot ? 0.28 + Math.random() * 0.25 : cool, hitOdds };
}

// pure: the XP bar from the profile
export const xpBar = me => (me?.need ? Math.max(0, Math.min(1, (me.into || 0) / me.need)) : 0);
export const MATCH = { bots: { kills: 25, secs: 360 }, online: { kills: 30, secs: 480 } };
