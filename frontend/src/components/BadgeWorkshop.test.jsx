import { unlockProgress, rollBadge, COLOR_PAIRS } from './Crews';

test('lock progress reads the family numbers; a place line has no bar', () => {
  expect(unlockProgress({ ok: true }, {})).toBe(1);
  expect(unlockProgress({ ok: false, metric: 'members', min: 5 }, { members: 2 })).toBeCloseTo(0.4);
  expect(unlockProgress({ ok: false, metric: 'best', min: 1 }, { best: 3 })).toBeNull();
});

test('a roll only picks unlocked parts and a listed colour pair', () => {
  const cat = { parts: { emblem: [{ key: 'rose', ok: true }, { key: 'crown', ok: false }], frame: [{ key: 'iron', ok: true }], fx: [{ key: 'none', ok: true }] } };
  for (let i = 0; i < 20; i++) {
    const d = rollBadge(cat, { emblem: 'rose', frame: 'iron', fx: 'none' });
    expect(d.emblem).toBe('rose'); expect(COLOR_PAIRS.some(([a, b]) => a === d.c1 && b === d.c2)).toBe(true);
  }
});
