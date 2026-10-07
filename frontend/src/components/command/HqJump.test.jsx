import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HqJump } from './HqJump';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async (tabs, onGo) => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<HqJump tabs={tabs} onGo={onGo} />); }); return el; };
const type = async (el, v) => { const input = el.querySelector('[data-testid=hq-jump-input]'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(input, v); input.dispatchEvent(new Event('input', { bubbles: true })); }); return input; };
const list = el => el.querySelector('[data-testid=hq-jump-list]');
const TABS = [['latency', 'Lag catcher'], ['fuse', 'Fuse']];

test('typing "profiles" + Enter jumps to the wallet profiles panel', async () => {
  const onGo = jest.fn(), el = await mount(TABS, onGo); const input = await type(el, 'profiles');
  expect(list(el).textContent).toMatch(/Wallet profiles/);
  await act(async () => { input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); });
  expect(onGo).toHaveBeenCalledWith(expect.objectContaining({ tab: 'fuse', panel: 'profiles' }));
  expect(list(el)).toBeNull();
});
test('a plain tab is found by its label and clicked; no match says so', async () => {
  const onGo = jest.fn(), el = await mount(TABS, onGo); await type(el, 'lag');
  await act(async () => { list(el).querySelector('button').click(); });
  expect(onGo).toHaveBeenCalledWith(expect.objectContaining({ tab: 'latency' }));
  await type(el, 'qqqq'); expect(list(el).textContent).toMatch(/Nothing called that/);
});
test('a scoped role never sees places outside its tabs', async () => {
  const el = await mount([['latency', 'Lag catcher']], () => {}); await type(el, 'profiles');
  expect(list(el).textContent).toMatch(/Nothing called that/);
});
