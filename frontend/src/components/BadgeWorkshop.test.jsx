import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { unlockProgress, rollBadge, COLOR_PAIRS, LAYERS } from './CrestForge';
import { FamilyCrest, chargeXf, shade, inkOn, SHAPES, CHARGE_WORD } from './FamilyCrest';

test('lock progress reads the family numbers; a place line has no bar', () => {
  expect(unlockProgress({ ok: true }, {})).toBe(1);
  expect(unlockProgress({ ok: false, metric: 'members', min: 5 }, { members: 2 })).toBeCloseTo(0.4);
  expect(unlockProgress({ ok: false, metric: 'best', min: 1 }, { best: 3 })).toBeNull();
});

test('a roll only picks unlocked parts on every layer, a listed colour pair, and keeps the charge adjustments', () => {
  const cat = { parts: { shape: [{ key: 'kite', ok: true }], field: [{ key: 'split', ok: true }], emblem: [{ key: 'rose', ok: true }, { key: 'crown', ok: false }], frame: [{ key: 'iron', ok: true }], banner: [{ key: 'scroll', ok: true }], fx: [{ key: 'none', ok: true }] } };
  for (let i = 0; i < 20; i++) {
    const d = rollBadge(cat, { emblem: 'rose', frame: 'iron', fx: 'none', es: 1.2, er: -9, ef: true });
    expect([d.emblem, d.shape, d.field, d.banner]).toEqual(['rose', 'kite', 'split', 'scroll']);
    expect([d.es, d.er, d.ef]).toEqual([1.2, -9, true]);
    expect(COLOR_PAIRS.some(([a, b]) => a === d.c1 && b === d.c2)).toBe(true);
  }
  expect(LAYERS.map(l => l[0])).toEqual(['shape', 'field', 'emblem', 'frame', 'banner', 'fx']);
});

test('the charge transform centres on the shape and clamps scale / rotate / flip', () => {
  expect(chargeXf({ es: 1, er: 0 }, 'coin')).toBe('translate(50 56) rotate(0) scale(1.15 1.15) translate(-30 -30)');
  expect(chargeXf({ es: 9, er: -99, ef: true }, 'heater')).toBe('translate(50 48) rotate(-30) scale(-1.495 1.495) translate(-30 -30)');
  expect(shade('#808080', 1)).toBe('#ffffff'); expect(shade('#808080', -1)).toBe('#000000');
  expect(inkOn('#ffd36b')).toBe('#160f05'); expect(inkOn('#111111')).toBe('#fff4dc');
});

test('every shape and every charge draws as SVG (no emoji art) with the tag on the banner', () => {
  const box = document.createElement('div');
  Object.keys(SHAPES).forEach(shape => Object.keys(CHARGE_WORD).forEach(emblem => {
    box.innerHTML = renderToStaticMarkup(<FamilyCrest b={{ shape, emblem, frame: 'warlord', field: 'quarterly', banner: 'plate', tag: 'SIC' }} px={80} />);
    expect(box.querySelectorAll('path, circle, polygon, ellipse, rect').length).toBeGreaterThan(12);
    expect(box.textContent).toBe('SIC');
    expect(/\p{Extended_Pictographic}/u.test(box.innerHTML)).toBe(false);
  }));
  box.innerHTML = renderToStaticMarkup(<FamilyCrest b={{ tag: 'FEE', banner: 'ribbon' }} px={24} banner={false} />);
  expect(box.textContent).toBe('');
});
