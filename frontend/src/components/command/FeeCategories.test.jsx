import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeCategories } from './FeeCategories';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

test('💲 fees by category: trading / agents / fuse / families, the agent cut saves through the admin fee route', async () => {
  const posted = [];
  const call = jest.fn((path, o) => {
    if (o) { posted.push([path, JSON.parse(o.body)]); return Promise.resolve({}); }
    if (path === '/admin/fees') return Promise.resolve({ fees: { platformFeeBps: 1500, catFeeUsd: 2, crews: { createUsd: 25, packUsd: 5 } } });
    if (path === '/admin/crews/revenue') return Promise.resolve({ totalUsd: 75, payments: 3, crews: 2 });
    return Promise.resolve({});
  });
  try { localStorage.removeItem('feeless.hq.feeCat'); } catch { /* none */ }
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<FeeCategories call={call} Trading={<i data-testid="trading-x" />} Fuse={<i data-testid="fuse-x" />} />); });
  const $ = s => el.querySelector(s); const click = s => act(async () => { $(s).click(); });
  expect($('[data-testid="trading-x"]')).not.toBeNull();
  await click('[data-testid="fct-agents"]');
  expect(el.textContent).toContain('$2.00'); expect(el.textContent).toContain('$0.05'); expect(el.textContent).toContain('$0.10'); expect(el.textContent).toContain('STAFF-OWNED');
  await act(async () => { const i = $('[data-testid="fct-cat-cut"]'); Object.getOwnPropertyDescriptor(Object.getPrototypeOf(i), 'value').set.call(i, '3'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await click('[data-testid="fct-cat-save"]');
  expect(posted[0]).toEqual(['/admin/fees', expect.objectContaining({ catFeeUsd: 3, platformFeeBps: 1500 })]);
  await click('[data-testid="fct-families"]'); expect(el.textContent).toContain('$75.00'); expect(el.textContent).toContain('$25.00');
  await click('[data-testid="fct-fuse"]'); expect($('[data-testid="fuse-x"]')).not.toBeNull();
});
