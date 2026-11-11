import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { DeskBell } from './DeskShell';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🔔 the desk bell: unread count from the agent feed, the list shows done vs worth a look, opening marks them seen, a row opens its proof', async () => {
  localStorage.removeItem('feeless:bell:c1');
  const rows = [{ at: 200, tone: 'look', kind: 'PoW', text: 'PoW reviewed: fail 0/100', ref: 'pow1' }, { at: 100, tone: 'done', kind: 'PoC', text: 'Your video is ready (Seedance 2.0 fast)', ref: 'w1' }];
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ rows }) }));
  const opened = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<DeskBell catId="c1" onOpen={r => opened.push(r.kind)} />));
  await act(async () => { await Promise.resolve(); });
  const q = s => el.querySelector(`[data-testid="${s}"]`);
  expect(global.fetch.mock.calls[0][0]).toContain('/api/cats/c1/feed');
  expect(q('desk-bell').textContent).toContain('2');
  await act(async () => q('desk-bell').click());
  expect(q('desk-bell-list').textContent).toContain('1 done · 1 worth a look');
  expect(q('desk-bell').textContent).not.toContain('2');   // seen
  expect(localStorage.getItem('feeless:bell:c1')).toBe('200');
  await act(async () => q('desk-bell-0').click());
  expect(opened).toEqual(['PoW']);
  await act(async () => root.unmount());
});
