import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
const mockCall = jest.fn(async () => ({ ok: true }));
let mockOwner = true;
jest.mock('../lib/adminCall', () => ({ useAdmin: () => ({ isAdmin: true, isOwner: mockOwner, call: mockCall }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
// eslint-disable-next-line import/first
import { DataCheck } from './ArenaPrime';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// 🩺 Slice 34: a card whose numbers rest on bad data says so and since when; only the owner restarts its record, in two taps.
const BAD = { tpl: 'next', label: 'Prime Next', dataCheck: { bad: true, since: 1793560354, flags: [
  { k: 'impossible', since: 1793560354, why: '2 record lines show an impossible move (+43210%, +11822%)' },
  { k: 'no-price', since: 1793600000, why: 'no live price for $BBB: counted at what was paid, not what it is worth' }] } };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return [el, root]; };

test('a flagged card says data was wrong since when, with every reason; two taps restart its record', async () => {
  const heard = jest.fn(); window.addEventListener('feeless:prime', heard);
  const [el, root] = await mount(<DataCheck c={BAD} />);
  const box = el.querySelector('[data-testid="prime-dc-next"]');
  expect(box.textContent).toContain('Data was wrong since');
  expect(el.querySelector('[data-testid="prime-dc-flag-impossible"]').textContent).toContain('+43210%');
  expect(el.querySelector('[data-testid="prime-dc-flag-no-price"]').textContent).toContain('$BBB');
  const btn = () => el.querySelector('[data-testid="prime-restart-next"]');
  await act(async () => { btn().click(); });
  expect(mockCall).not.toHaveBeenCalled(); expect(btn().textContent).toContain('Tap again');   // one tap never restarts
  await act(async () => { btn().click(); });
  expect(mockCall).toHaveBeenCalledTimes(1);
  const [path, opts] = mockCall.mock.calls[0];
  expect(path).toBe('/admin/arena/prime'); expect(opts.method).toBe('POST');
  const body = JSON.parse(opts.body);
  expect(body.restart.tpl).toBe('next'); expect(body.restart.why).toContain('impossible move');   // the reasons ride into the kept history
  expect(Object.keys(body)).toEqual(['restart']);                                                  // nothing else in the call: no trade, no config
  expect(heard).toHaveBeenCalled();                                                                // the cards reload at once
  window.removeEventListener('feeless:prime', heard);
  await act(async () => { root.unmount(); }); el.remove();
});

test('a clean card shows nothing (or when its record was restarted); an admin who is not the owner sees the flag but no button', async () => {
  let [el, root] = await mount(<DataCheck c={{ tpl: 'safe', dataCheck: { bad: false, flags: [] } }} />);
  expect(el.textContent).toBe('');
  await act(async () => { root.render(<DataCheck c={{ tpl: 'safe', restartedAt: 1793600000, dataCheck: { bad: false, flags: [] } }} />); });
  expect(el.textContent).toContain('Record restarted'); expect(el.textContent).toContain('old one is kept');
  await act(async () => { root.unmount(); }); el.remove();
  mockOwner = false;   // an admin who is not the owner
  [el, root] = await mount(<DataCheck c={BAD} />);
  expect(el.textContent).toContain('Data was wrong'); expect(el.querySelector('[data-testid="prime-restart-next"]')).toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});
