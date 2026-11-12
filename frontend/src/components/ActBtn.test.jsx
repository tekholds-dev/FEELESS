import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { toast } = require('sonner');

const mount = async el => { const d = document.createElement('div'); document.body.appendChild(d); await act(async () => { createRoot(d).render(el); }); return d.querySelector('button'); };
const res = (ok, body, status = ok ? 200 : 403) => ({ ok, status, json: async () => body });

test('🔘 money takes two taps; ✓ only after the server says OK', async () => {
  const run = jest.fn(async () => res(true, { signature: 'abc' })); const onDone = jest.fn();
  const b = await mount(<ActBtnT money run={run} onDone={onDone}>Withdraw</ActBtnT>);
  await act(async () => { b.click(); }); expect(run).not.toHaveBeenCalled(); expect(b.dataset.state).toBe('armed'); expect(b.textContent).toContain('Tap again');
  await act(async () => { b.click(); }); expect(run).toHaveBeenCalledTimes(1); expect(b.dataset.state).toBe('ok'); expect(onDone).toHaveBeenCalledWith({ signature: 'abc' });
});

test('🔘 a server no shakes and shows the server\'s own reason, never a ✓', async () => {
  const b = await mount(<ActBtnT run={async () => res(false, { detail: 'Sign in again to change your theme.' }, 401)}>Save</ActBtnT>);
  await act(async () => { b.click(); }); expect(b.dataset.state).toBe('fail'); expect(toast.error).toHaveBeenCalledWith('Sign in again to change your theme.');
});
const { ActBtn: ActBtnT } = require('./ActBtn');
