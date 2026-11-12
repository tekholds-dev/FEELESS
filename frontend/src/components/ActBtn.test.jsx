import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn(), warning: jest.fn() } }));
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

test('🔘 twoTap: the 1st tap arms that button and says so; the 2nd tap on the same button confirms, even if the price ticked; another button never confirms it', () => {
  const { twoTap } = require('./ActBtn'); const saved = window.confirm; window.confirm = () => false;   // a plain (unmocked) confirm: twoTap must not call it
  const a = document.createElement('button'); const b = document.createElement('button'); document.body.append(a, b);
  const tap = (el, msg) => { el.dispatchEvent(new Event('pointerdown', { bubbles: true })); return twoTap(msg); };
  expect(tap(a, 'Sell 25% (about $4.10)?')).toBe(false); expect(a.classList.contains('act-armed')).toBe(true); expect(toast.warning).toHaveBeenCalled();
  expect(tap(b, 'Sell 50% (about $8.20)?')).toBe(false); expect(a.classList.contains('act-armed')).toBe(false);   // a different button re-arms, never fires
  expect(tap(b, 'Sell 50% (about $8.31)?')).toBe(true); expect(b.classList.contains('act-armed')).toBe(false);   // same button, price moved: confirms
  window.confirm = saved; a.remove(); b.remove();
});
