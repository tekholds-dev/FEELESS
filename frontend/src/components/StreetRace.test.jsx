import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { StreetRace } from './StreetRace';
jest.mock('three', () => ({ WebGLRenderer: function NoGl() { throw new Error('no WebGL in jest'); } }));

const TRACK = { kind: 'race', start: [0, 0, 0], cps: [[114, 0], [114, 114]], par: 30000, min: 4000, len: 228 };
const q = id => document.querySelector(`[data-testid="${id}"]`);

test('🏁 the Raceway: today\'s board, a vehicle pick that sticks, START asks the server for the track (errand mode names its store)', async () => {
  const calls = [];
  global.fetch = jest.fn((url, opt) => { calls.push([String(url), opt?.body ? JSON.parse(opt.body) : null]);
    const body = String(url).includes('/start') ? { token: 't1', track: TRACK, practice: true } : { day: '2026-10-27', track: TRACK, board: [{ place: 1, name: 'Sicario', tag: 'FRT', vehicle: 'bike', ms: 41230 }], mp: { finish: 120, par: 280 } };
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) }); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StreetRace blocks={[{ owner: 'f', tag: 'FRT' }]} mode="errand" store="pizza" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  expect(q('sr-panel').textContent).toContain('[FRT] Sicario'); expect(q('sr-panel').textContent).toContain('0:41.23');
  await act(async () => { q('sr-veh-truck').click(); });
  expect(localStorage.getItem('feeless.race.veh')).toBe('truck');
  await act(async () => { q('sr-go').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  const start = calls.find(([u]) => u.includes('/familia-race/start'));
  expect(start[1]).toMatchObject({ mode: 'errand', store: 'pizza' });
  act(() => root.unmount());
});
