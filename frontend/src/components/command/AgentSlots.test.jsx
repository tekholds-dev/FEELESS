import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AgentSlots } from './FeeCatDesk';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🎟 the command center shows agent slots (bought · left · open of 1,000) and opens more / pauses sales through the owner route', async () => {
  const calls = []; let st = { open: 100, taken: 40, left: 60, max: 1000 };
  const call = async (u, o) => { calls.push([u, o?.body ? JSON.parse(o.body) : null]); if (o?.method === 'POST') { const n = JSON.parse(o.body).open; st = { ...st, open: n, left: n - st.taken }; } return st; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AgentSlots call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('fch-slots').textContent).toContain('40'); expect(q('fch-slots').textContent).toContain('60');
  await act(async () => { q('fch-slots-250').click(); }); expect(calls.at(-1)).toEqual(['/admin/agent-slots', { open: 350 }]);
  await act(async () => { q('fch-slots-close').click(); }); expect(calls.at(-1)[1]).toEqual({ open: 40 });
  await act(async () => { q('fch-slots-all').click(); }); expect(calls.at(-1)[1]).toEqual({ open: 1000 }); expect(q('fch-slots-all').disabled).toBe(true);
});
