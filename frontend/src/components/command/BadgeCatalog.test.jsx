import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const { BadgeCatalog } = require('./BadgeCatalog');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('lists custom, built-in and season-tier badges and saves % + SOL each per pool', async () => {
  const posts = [];
  const call = jest.fn(async (path, opts) => {
    if (opts?.method === 'POST') { posts.push(JSON.parse(opts.body)); return { ok: true }; }
    if (path === '/admin/badges') return { rows: [{ address: 'A', badges: [{ id: 'custom-og', label: 'OG', icon: '⭐', tone: 'gold' }] }], builtin: [{ id: 'trusted-creator', label: 'Trusted Creator', icon: '🛡️', holders: 4, builtin: true }] };
    return { pools: [{ id: 'p1', name: 'Reserve', wallet: 'W', pct: 50, seasonId: 's1', weights: {}, fixed: {} }] };
  });
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<BadgeCatalog call={call} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.textContent).toContain('Trusted Creator');
  expect(el.textContent).toContain('earned automatically');
  expect(el.textContent).toContain('Gold tier');
  const set = (label, v) => { const i = el.querySelector(`input[aria-label="${label}"]`); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, v); i.dispatchEvent(new Event('input', { bubbles: true })); };
  await act(async () => { set('Trusted Creator SOL each from Reserve', '0.2'); set('Trusted Creator % of Reserve', '10'); });
  const rows = [...el.querySelectorAll('.bc-row')];
  await act(async () => { rows.find(r => r.textContent.includes('Trusted Creator')).querySelector('.btn-primary').click(); });
  expect(posts[0]).toMatchObject({ id: 'p1', weights: { 'badge:trusted-creator': 10 }, fixed: { 'badge:trusted-creator': 0.2 } });
});
