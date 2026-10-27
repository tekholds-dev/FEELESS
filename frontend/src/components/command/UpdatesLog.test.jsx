import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { UpdatesLog, screenNow, DUO_SCREENS } from './UpdatesLog';

const q = id => document.querySelector(`[data-testid="${id}"]`);
const D = { rows: [{ sha: 'a1', at: '2026-10-27', type: 'new', parts: ['site', 'backend'], area: 'perps', items: ['swipe provider rail'] },
  { sha: 'b2', at: '2026-10-26', type: 'fix', parts: ['site', 'mobile'], area: 'duo', items: ['trench chart fits phones'] }], counts: { site: 2, backend: 1, mobile: 1, new: 1, fix: 1 } };

test('📜 the updates log: NEW vs FIX, lenses per part, and the four Duo screens with the live one lit', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(D) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<UpdatesLog />); });
  await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  expect(q('updates-log').textContent).toContain('swipe provider rail'); expect(q('updates-log').textContent).toContain('1 FIXES');
  await act(async () => { q('upl-backend').click(); });
  expect(q('updates-log').textContent).not.toContain('trench chart fits phones');
  await act(async () => { q('upl-duo').click(); });
  expect(document.querySelectorAll('.upl-scr')).toHaveLength(4); expect(DUO_SCREENS.map(s => s[0])).toEqual(['closed-port', 'closed-land', 'open-port', 'open-land']);
  act(() => root.unmount());
});

test('📱 which Duo screen this is: a desktop mouse = none, a phone upright / sideways = closed, an unfolded one = open', () => {
  const w = (W, H, coarse) => ({ innerWidth: W, innerHeight: H, navigator: {}, matchMedia: q => ({ matches: coarse && q.includes('coarse') }) });
  expect(screenNow(w(1400, 900, false))).toBeNull();
  expect(screenNow(w(390, 844, true))).toBe('closed-port');
  expect(screenNow(w(844, 390, true))).toBe('closed-land');   // a phone sideways (short screen)
  expect(screenNow(w(1100, 800, true))).toBe('open-land');    // unfolded, sideways
  expect(screenNow(w(700, 900, true))).toBe('open-port');
});
