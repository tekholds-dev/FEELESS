import { gunStats, rayBody, damageAt, spreadNow, botBrain, xpBar } from './strikeGame';

const CAT = { guns: { rifle: { name: 'FX-7 RIFLE', dmg: 24, rpm: 600, mag: 30, reload: 2.1, range: 120, spread: 0.012, recoil: 0.35, speed: 1, pellets: 1 }, smg: { name: 'VIPER', dmg: 16, rpm: 900, mag: 32, reload: 1.7, range: 55, spread: 0.024, recoil: 0.25, speed: 1.08, pellets: 1 } },
  parts: { barrel: [{ id: 'std', mod: {} }, { id: 'long', mod: { range: 0.35, spread: -0.25, speed: -0.03 } }], optic: [{ id: 'iron', mod: { zoom: 1.25 } }, { id: 'dot', mod: { zoom: 1.45, spread: -0.1 } }], mag: [{ id: 'std', mod: {} }, { id: 'ext', mod: { mag: 0.5, reload: 0.15 } }] },
  default: { gun: 'rifle', barrel: 'std', optic: 'iron', mag: 'std' } };

test('🔫 the gun\'s stats follow its attachments (the server\'s math)', () => {
  const g = gunStats(CAT, { gun: 'smg', barrel: 'long', optic: 'dot', mag: 'ext' });
  expect(g.mag).toBe(48); expect(g.range).toBeCloseTo(55 * 1.35); expect(g.spread).toBeCloseTo(0.024 * 0.75 * 0.9); expect(g.zoom).toBe(1.45); expect(g.interval).toBeCloseTo(60 / 900);
  expect(gunStats(CAT, null).name).toBe('FX-7 RIFLE');
});

test('🎯 a ray hits a body in the chest or the head and misses beside it; damage falls off past the range', () => {
  const feet = { x: 0, y: 0, z: 10 };
  const chest = rayBody({ x: 0, y: 1.2, z: 0 }, { x: 0, y: 0, z: 1 }, feet); expect(chest.head).toBe(false); expect(chest.dist).toBeCloseTo(10, 0);
  expect(rayBody({ x: 0, y: 1.7, z: 0 }, { x: 0, y: 0, z: 1 }, feet).head).toBe(true);
  expect(rayBody({ x: 1.2, y: 1.2, z: 0 }, { x: 0, y: 0, z: 1 }, feet)).toBeNull();
  expect(rayBody({ x: 0, y: 1.2, z: 0 }, { x: 0, y: 0, z: -1 }, feet)).toBeNull();          // behind you
  const g = gunStats(CAT, null);
  expect(damageAt(g, 50, false)).toBe(24); expect(damageAt(g, 50, true)).toBe(48); expect(damageAt(g, 240, false)).toBe(Math.round(24 * 0.3));
  expect(spreadNow(g, { moving: true })).toBeGreaterThan(spreadNow(g, { ads: true }));
});

test('🤖 a bot hunts when it can\'t see you, fights after its reaction time, retreats when hurt', () => {
  const you = { x: 0, z: 30, moving: false };
  expect(botBrain({ x: 0, z: 0, hp: 100 }, you, false, 0.1).mode).toBe('hunt');
  const first = botBrain({ x: 0, z: 0, hp: 100 }, you, true, 0.1, 'normal'); expect(first.mode).toBe('fight'); expect(first.shoot).toBe(false);   // still reacting
  const later = botBrain({ x: 0, z: 0, hp: 100, seen: 1, cool: 0 }, you, true, 0.1, 'normal'); expect(later.shoot).toBe(true); expect(later.hitOdds).toBeGreaterThan(0);
  expect(botBrain({ x: 0, z: 0, hp: 20 }, you, true, 0.1).mode).toBe('retreat');
  expect(xpBar({ into: 300, need: 600 })).toBe(0.5);
});
