import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const { CircleMove } = require('./CircleWallets');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const setVal = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };

test('Circle moves only to same-network Command Center wallets, after the typed last 4', async () => {
  const w = { id: 'cw', name: 'Ops', blockchain: 'SOL', address: 'Self1111111111111111111111111111111111111111', balances: [{ tokenId: 'sol', symbol: 'SOL', amount: '2' }] };
  const dests = [{ address: 'Resv111111111111111111111111111111111111WXYZ', label: 'Season reserve · S1', kind: 'reserve' },
    { address: '0x000000000000000000000000000000000000dEaD', label: 'EVM route', kind: 'route' }, { address: w.address, label: 'itself', kind: 'circle' }];
  const call = jest.fn(async () => ({ state: 'INITIATED' }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<CircleMove w={w} call={call} dests={dests} />); });
  const opts = [...el.querySelectorAll('[role="option"]')];
  expect(opts.map(o => o.textContent)).toEqual([expect.stringContaining('Season reserve')]);
  await act(async () => { opts[0].click(); });
  await act(async () => { setVal(el.querySelector('input[inputmode="decimal"]'), '1'); });
  const send = el.querySelector('[data-testid="circle-move-send"]');
  expect(send.disabled).toBe(true);
  await act(async () => { setVal(el.querySelector('input[aria-label^="Type the last 4"]'), 'WXYZ'); });
  expect(send.disabled).toBe(false);
  await act(async () => { send.click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ walletId: 'cw', tokenId: 'sol', to: dests[0].address, amount: '1', confirm: 'WXYZ' });
  act(() => root.unmount());
});
