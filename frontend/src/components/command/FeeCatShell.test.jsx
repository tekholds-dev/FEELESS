import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeCatShell, pickMyAgent } from './FeeCatShell';

jest.mock('../../lib/feeLeader', () => ({ useFeeLook: () => null, useLeaderProfile: () => null, feeHeadline: () => ({ nap: false, open: 0, roi: -1.9, trades: 3, lives: 9, maxLives: 9 }) }));

test('the bar wears the agent you opened last, never Fee, else your newest', () => {
  const cats = [{ id: 'leader', isLeader: true }, { id: 'h', name: 'Happy' }, { id: 's', name: "Sicario's" }];
  expect(pickMyAgent(cats, 's').id).toBe('s'); expect(pickMyAgent(cats, 'gone').id).toBe('h'); expect(pickMyAgent([{ id: 'leader' }], null)).toBe(null);
});

test("your real agent's character portrait replaces the old drawn cat in the bar", async () => {
  try { localStorage.setItem('feeless.lastAgent', 'h'); } catch { /* jsdom */ }
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ cats: [{ id: 'h', name: 'Happy Assistant', face: { id: 'custom-h', at: 1 } }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FeeCatShell tab="agents"><p>x</p></FeeCatShell>); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(el.querySelector('[data-testid="fcx-face"]')).not.toBeNull();
  expect(el.querySelector('[data-testid="fcx-mine"]').textContent).toContain('HAPPY ASSISTANT');
  expect(String(global.fetch.mock.calls[0][0])).toContain('/api/cats?');
});
