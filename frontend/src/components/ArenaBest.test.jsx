import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { ArenaBest } from './ArenaBest';

test('🏆 best settings show the top styles, top quarter vs the rest, and the three best cards', async () => {
  const D = { n: 300, styles: [{ style: 'steady', n: 26, medFit: 90.4 }, { style: 'gen-27', n: 53, medFit: 75.7 }], top: { fit: 88, legs: 3, maxW: 48.4, majorW: 17.7 },
    rest: { fit: 71.1, legs: 3, maxW: 46.5, majorW: 35.6 }, cards: [{ id: 'a', style: 'steady', fitness: 97, legs: [{ symbol: 'PUMP', weight: 54 }, { symbol: 'WETH', weight: 28 }] }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(D) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ArenaBest />); }); await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  const t = el.querySelector('[data-testid="arena-best"]').textContent;
  expect(t).toContain('steady'); expect(t).toContain('90.4'); expect(t).toContain('17.7%'); expect(t).toContain('PUMP 54%');
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ n: 0 }) }));
  await act(async () => { root.unmount(); });
});
