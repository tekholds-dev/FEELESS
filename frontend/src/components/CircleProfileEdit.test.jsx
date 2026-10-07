import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CircleProfileEditButton } from './CircleProfileEdit';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const W = 'Fuse1111111111111111111111111111111111111111';
let mockAdmin = { isAdmin: true, call: jest.fn() };
jest.mock('../lib/adminCall', () => ({ useAdmin: () => mockAdmin, uploadImage: jest.fn() }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mount = async addr => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<CircleProfileEditButton address={addr} />); }); return el; };

test('the creator gets ✏️ Edit profile on a wallet page; it opens the form for their own Circle wallet and saves it', async () => {
  mockAdmin = { isAdmin: true, call: jest.fn(async (p, o) => (o ? { ok: true } : { wallets: [{ id: 'w1', address: W, name: 'Fuse', profile: { name: 'Fuse', handle: 'fuse', bio: '', avatar: '', banner: '' } }] })) };
  const el = await mount(W);
  await act(async () => { el.querySelector('[data-testid=cp-edit-here]').click(); });
  const pop = document.querySelector('[data-testid=cp-pop]'); expect(pop.textContent).toMatch(/Upload image \/ GIF/);
  await act(async () => { pop.querySelector('[data-testid=cp-save]').click(); });
  const [path, opts] = mockAdmin.call.mock.calls[1]; expect(path).toBe('/admin/circle/profile'); expect(JSON.parse(opts.body).address).toBe(W);
  expect(document.querySelector('[data-testid=cp-pop]')).toBeNull();
});
test('nobody else sees the button; a wallet that is not yours opens nothing', async () => {
  mockAdmin = { isAdmin: false, call: jest.fn() }; expect((await mount(W)).querySelector('button')).toBeNull();
  mockAdmin = { isAdmin: true, call: jest.fn(async () => ({ wallets: [] })) }; const el = await mount(W);
  await act(async () => { el.querySelector('[data-testid=cp-edit-here]').click(); });
  expect(document.querySelector('[data-testid=cp-pop]')).toBeNull();
});
