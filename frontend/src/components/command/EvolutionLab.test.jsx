import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { EvolutionLab } from './EvolutionLab';

// 🧪 COL-11: the panel shows the server's verdict, both duels, the shadow trades and the history — nothing computed here.
test('the lab shows the gate verdict, learn vs held-out, shadow trades and generation history', async () => {
  const side = (b, c, n) => ({ n, base: { mean: b }, chall: { mean: c }, edge: +(c - b).toFixed(3) });
  const d = { exits: 300, take: 10, note: 'The lab keeps its own ledger.', gate: { minHeld: 20, minChanged: 5, edgePts: 0.5 }, baseline: { gen: 1, hash: 'abc123' },
    judge: { verdict: 'REJECT', why: 'Held-out edge -0.30 pts', learn: side(-1.35, -1.18, 180), held: side(-1.28, -1.58, 120), shadow: [{ sym: 'FLOATER', base: 50, chall: 2.58, diff: -47.42 }] },
    history: [{ action: 'challenge', gen: 1, verdict: 'REJECT', why: 'Held-out edge -0.30 pts' }, { action: 'freeze', gen: 1, params: { protectAt: 6 } }] };
  const real = global.fetch; global.fetch = jest.fn(async () => ({ ok: true, json: async () => d }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<EvolutionLab />); }); await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(global.fetch.mock.calls[0][0]).toContain('/api/reputation/evolution/reaper');
  expect(q('evo-verdict').textContent).toBe('REJECT'); expect(q('evo-why').textContent).toContain('-0.30');
  expect(q('evo-shadow').textContent).toContain('FLOATER'); expect(q('evo-history').textContent).toContain('FREEZE');
  expect(el.textContent).toContain('NEVER SEEN');
  await act(async () => root.unmount()); el.remove(); global.fetch = real;
});
