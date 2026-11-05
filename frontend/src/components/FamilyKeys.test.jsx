import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamilyKeys } from './FamilyKeys';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./command/CatWorkbench', () => ({ ApiSlot: ({ cat }) => <div data-testid="slot">{cat.name}</div> }));
test('🔑 one vault: every agent, how many keys are saved, its keys one click away', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cats: [{ id: 'a', name: 'Happy', apiDrawer: [{ saved: true }, { saved: false }] }, { id: 'b', name: 'Old', revoked: true }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamilyKeys />); });
  expect(el.textContent).toContain('1 key sealed'); expect(el.textContent).not.toContain('Old');
  await act(async () => { el.querySelector('[data-testid="fky-a"]').click(); });
  expect(el.querySelector('[data-testid="slot"]').textContent).toBe('Happy');
  await act(async () => root.unmount());
});
