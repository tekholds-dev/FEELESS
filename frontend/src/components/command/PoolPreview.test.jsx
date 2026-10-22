import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { PoolPreview, poolMath, decayPath } from './PoolPreview';

test('pure: the pool numbers from the form', () => {
  const m = poolMath({ tokens: '100000000', sol: '10', feeBps: '100', launchFeeBps: '5000', launchMinutes: '30', supply: 1e9 });
  expect(m.price).toBeCloseTo(1e-7); expect(m.share).toBeCloseTo(10); expect(m.impact1).toBeCloseTo(100 / 11); expect(m.fee).toBe(1); expect(m.start).toBe(50); expect(m.snipe).toBe(true);
  expect(poolMath({ tokens: '0', sol: '1' })).toBeNull(); expect(poolMath({ tokens: '5', sol: '1', feeBps: '100', launchFeeBps: '0', launchMinutes: '0' }).snipe).toBe(false);
  expect(decayPath(50, 1)).toMatch(/^M4 /);
});

test('the preview draws the piles, the depth meter and the lock', () => {
  const html = renderToStaticMarkup(<PoolPreview form={{ tokens: '100000000', sol: '10', feeBps: '100', launchFeeBps: '5000', launchMinutes: '30', lock: true }} supply={1e9} solPx={150} />).replace(/<[^>]+>/g, '');
  expect(html).toContain('OPENS AT'); expect(html).toContain('9.1%'); expect(html).toContain('LOCKED · RUG-PROOF'); expect(html).toContain('50% → 1% · 30m');
  expect(renderToStaticMarkup(<PoolPreview form={{ tokens: '', sol: '' }} />)).toContain('draws itself');
});
