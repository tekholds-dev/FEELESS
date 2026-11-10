import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PartsShelf } from './PartsShelf';

test('🧩 the shelf shows each proven part, its licenses, how often it was reused, and what went stale (COL-26)', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ staleDays: 30, parts: [
    { id: 'pt_a', title: 'Tokenomics', tag: 'section', kind: 'pos', licenses: ['MIT'], uses: 3, reusedBy: [{ kind: 'pos', ref: 'w2' }], stale: false, mine: true },
    { id: 'pt_b', title: 'Old hero', tag: 'header', kind: 'pos', licenses: ['FEELESS'], uses: 0, reusedBy: [], stale: true, mine: false }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PartsShelf cat={{ id: 'c1' }} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(globalThis.fetch.mock.calls[0][0]).toContain('/api/cats/c1/parts?');
  expect(el.textContent).toContain('1 offered · 1 reused · 1 stale');
  expect(el.querySelector('[data-testid="part-pt_a"]').textContent).toContain('MIT'); expect(el.querySelector('[data-testid="part-pt_a"]').textContent).toContain('of this agent');
  expect(el.querySelector('[data-testid="part-pt_b"]').className).toBe('is-stale');
  act(() => root.unmount());
});
