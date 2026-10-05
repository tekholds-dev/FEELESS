import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { RpcKey } from './FuseWallet';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const type = async (input, v) => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; await act(async () => { set.call(input, v); input.dispatchEvent(new Event('input', { bubbles: true })); }); };

test('RPC keys: every lane out of quota glows ADD A KEY; one paste is tested, saved, never shown again', async () => {
  let state = { needsKey: true, slots: [{ slot: 1, set: true }, { slot: 2, set: false }], lanes: [{ lane: 1, slot: 1, provider: 'quiknode.pro', spent: true, backInMin: 420 }] };
  const call = jest.fn(async (path, o) => {
    if (!o) return state;
    const b = JSON.parse(o.body);
    if (b.url.includes('dead')) throw new Error('Not saved — this key is out of quota.');
    state = { needsKey: false, slots: [{ slot: 1, set: true }, { slot: 2, set: true }], lanes: [...state.lanes, { lane: 2, slot: 2, provider: 'helius-rpc.com', spent: false, backInMin: 0 }] };
    return { ok: true, slot: b.slot, provider: 'helius-rpc.com', holders: true, ms: 80 };
  });
  const el = await mount(<RpcKey call={call} />);
  expect(el.querySelector('[data-testid="rpc-need"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="rpc-key"]').className).toContain('is-need');
  expect(el.textContent).toContain('quiknode.pro out of quota · back in 7h');
  expect(el.querySelector('[data-testid="rpc-slot-2"]').className).toBe('on');           // the empty lane is preselected
  const input = el.querySelector('[data-testid="rpc-url"]');
  expect(input.type).toBe('password'); expect(el.querySelector('[data-testid="rpc-save"]').disabled).toBe(true);
  await type(input, 'https://x.helius-rpc.com/?api-key=dead');
  await act(async () => { el.querySelector('.rpck-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }); await tick(20);
  expect(el.querySelector('[data-testid="rpc-msg"]').textContent).toContain('out of quota');
  await type(el.querySelector('[data-testid="rpc-url"]'), 'https://x.helius-rpc.com/?api-key=good');
  await act(async () => { el.querySelector('.rpck-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }); await tick(20);
  expect(JSON.parse(call.mock.calls.filter(c => c[1]).pop()[1].body)).toEqual({ slot: 2, url: 'https://x.helius-rpc.com/?api-key=good' });
  expect(el.querySelector('[data-testid="rpc-msg"]').textContent).toContain('Lane 2 is live on helius-rpc.com');
  expect(el.querySelector('[data-testid="rpc-url"]').value).toBe('');                    // the key is gone from the screen
  expect(el.innerHTML).not.toContain('api-key=good');
  expect(el.querySelector('[data-testid="rpc-need"]')).toBeNull();
});
