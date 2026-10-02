import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GuardPanel } from './GuardPanel';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const view = (sus, blocks = []) => ({ rules: { writesPerMin: 90, adminFails: 8, adminWindowMin: 10, adminCoolMin: 15 }, busiest: [], cooling: [],
  suspects: sus, blocks, log: [] });

test('guard: suspects wait with evidence; a block happens only when the admin approves it, and can be lifted', async () => {
  const now = Date.now() / 1000;
  const call = jest.fn(async (path, opts) => {
    if (!opts) return view([{ ip: '8.8.4.4', last: now, evidence: [{ rule: 'admin-brute', claim: '8 failed HQ signatures in 10 min' }] }]);
    const b = JSON.parse(opts.body); return b.action === 'block' ? view([], [{ ip: b.ip, by: 'ADMINxyz', at: now }]) : view([]);
  });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<GuardPanel call={call} />); });
  expect(el.textContent).toContain('8 failed HQ signatures'); expect(el.textContent).toContain('No blocks.');
  expect(call.mock.calls.every(c => !c[1])).toBe(true);                                // nothing blocked on its own
  await act(async () => { el.querySelector('[data-testid="gd-block-8.8.4.4"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ ip: '8.8.4.4', action: 'block' });
  expect(el.textContent).toContain('Nobody flagged'); expect(el.textContent).toContain('Lift');
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Lift').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).action).toBe('unblock');
});
