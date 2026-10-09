import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LadderCard } from './ArenaPrime';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('size ladder: current stage lit, next stage named, one tap toggles it', async () => {
  const stages = [['trench', '🗑 TRENCH', 0], ['runner', '🏃 RUNNER', 10], ['sniper', '🎯 SNIPER', 100], ['bluechip', '🐋 BLUE-CHIP', 1000], ['majors', '👑 MAJORS', 10000]].map(([key, name, from]) => ({ key, name, from }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const toggle = jest.fn();
  await act(async () => { root.render(<LadderCard l={{ key: 'trench', name: '🗑 TRENCH', why: 'w.', on: false, value: 2.48, next: { name: '🏃 RUNNER', at: 10 }, stages }} onToggle={toggle} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('lad-trench').className).toBe('now'); expect(q('ladder-card').textContent).toContain('Next: 🏃 RUNNER at $10');
  expect(q('lad-majors').textContent).toContain('$10K+');
  await act(async () => { q('ladder-toggle').click(); }); expect(toggle).toHaveBeenCalledWith(true);
  await act(async () => { root.unmount(); });
});
