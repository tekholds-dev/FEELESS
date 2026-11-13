import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ReviewReel } from './ProofDoors';

test('a proof its own minds built shows NO JUDGE and says why; one-family judges are flagged', async () => {
  const rows = [{ id: 'a', title: 'GLINT', score: null, verdict: null, recused: ['ossy', 'g4'], why: 'Every judge built this proof, so none may judge it', by: {}, hidden: { passed: 8, total: 9, failed: ['no-fake-data'] } },
    { id: 'b', title: 'GLINT v1', score: 48, verdict: 'fail', agree: false, oneFamily: true, families: ['qwen'], by: { ossy: { score: 0, verdict: 'fail', checks: [] } } }];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ReviewReel rows={rows} />); });
  expect(el.querySelector('[data-testid="prv-score"]').textContent).toContain('NO JUDGE · IT BUILT IT');
  expect(el.querySelector('[data-testid="prv-recused"]').textContent).toContain('OSSY and G4 built this proof');
  expect(el.querySelector('[data-testid="prv-hidden"]').textContent).toContain('8/9 · missed: made-up or sample numbers');
  await act(async () => { el.querySelectorAll('[role="tab"]')[1].click(); });
  expect(el.querySelector('[data-testid="prv-score"]').textContent).toContain('SPLIT · ONE FAMILY');
  expect(el.querySelector('[data-testid="prv-recused"]')).toBeNull();
});
