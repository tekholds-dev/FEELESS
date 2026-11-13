import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { JudgeMeters } from './ProofDoors';

test('each judge shows how often it agrees with the real result, against a judge that fails everything', async () => {
  const rows = [{ judge: 'g4', n: 9, rightPct: 44, baselinePct: 44, beats: false, say: 'G4 is right 44%' }, { judge: 'ossy', n: 10, rightPct: 50, baselinePct: 40, beats: true, say: 'OSSY is right 50%' }];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<JudgeMeters rows={rows} />); });
  expect(el.querySelector('[data-testid="judge-g4"]').textContent).toContain('no better than failing everything yet');
  expect(el.querySelector('[data-testid="judge-ossy"]').className).toContain('is-beats');
  await act(async () => { createRoot(el).render(<JudgeMeters rows={[]} />); });
});
