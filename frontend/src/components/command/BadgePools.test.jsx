import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn(), message: jest.fn() } }));
const { BadgePools } = require('./BadgePools');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const W = 'Pool111111111111111111111111111111111111111';

test('each badge gets its own % of each pool; totals over 100% cannot be saved', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({}) }));
  const saved = [];
  const call = jest.fn(async (path, opts) => {
    if (path === '/admin/badge-pools') {
      if (opts?.method === 'POST') { saved.push(JSON.parse(opts.body)); return { ok: true }; }
      return { pools: [{ id: 'p1', name: 'OG pool', wallet: W, pct: 50, weights: { 'badge:custom-og': 30 }, mode: 'pct' }],
        badges: [{ id: 'custom-og', label: 'OG', icon: '⭐', count: 3 }, { id: 'custom-bug', label: 'Bug Hunter', icon: '🐞', count: 1 }], tiers: [], seasons: [] };
    }
    return { potSol: 2, paidSol: 0.6, rows: [{ address: 'A', sol: 0.6 }], cooldownLeft: 0 };
  });
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<BadgePools call={call} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const cell = el.querySelector('input[aria-label="🐞 Bug Hunter share of OG pool"]');
  const setVal = v => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(cell, v); cell.dispatchEvent(new Event('input', { bubbles: true })); };
  await act(async () => setVal('80'));
  expect(el.querySelector('tfoot td.bad').textContent).toBe('110%');
  const saveBtn = () => [...el.querySelectorAll('button')].find(b => b.textContent === 'Save shares');
  expect(saveBtn().disabled).toBe(true);
  await act(async () => setVal('20'));
  expect(saveBtn().disabled).toBe(false);
  await act(async () => { saveBtn().click(); });
  expect(saved[0]).toMatchObject({ id: 'p1', mode: 'pct', weights: { 'badge:custom-og': 30, 'badge:custom-bug': 20 } });
});
