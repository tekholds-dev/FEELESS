import { act } from 'react';
import { createRoot } from 'react-dom/client';
import ProofLive, { proofOf } from './ProofLive';
import { LOOKS_PER_PROOF, SCENES, pickLook } from '../../lib/proofFx';

test('a running proof is named from the desk state; nothing running is null', () => {
  expect(proofOf({ powFolder: { phase: 'scout' } }, true)).toBe('pow');
  expect(proofOf({ popFolder: {} }, true)).toBe('pop');
  expect(proofOf({ task: { proofKind: 'pos' } }, true)).toBe('pos');
  expect(proofOf({ task: {} }, true)).toBe(null);
  expect(proofOf({ task: {} }, false)).toBe(null);
});

test('every proof has 100 looks: 5 backgrounds × 5 of its own scenes × 4 foregrounds, and a run keeps its look', () => {
  expect(LOOKS_PER_PROOF).toBe(100);
  ['pow', 'pop', 'pob', 'poc', 'poe', 'pos'].forEach(k => expect(SCENES[k]).toHaveLength(5));
  expect(pickLook('pow', 'run-1')).toEqual(pickLook('pow', 'run-1'));
  const seen = new Set(Array.from({ length: 60 }, (_, i) => JSON.stringify(pickLook('pow', `r${i}`))));
  expect(seen.size).toBeGreaterThan(20);
});

test('the stage shows the live vitals and hands back to the chat', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const show = jest.fn(); const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<ProofLive kind="pow" name="Happy" spent={0.0123} onShowChat={show}
    d={{ task: { id: 't1' }, powFolder: { phase: 'scout', sym: 'BONK' }, chat: [{ by: 'cats', text: 'Reading dexscreener' }] }}
    wins={[{ model: 'tencent/hy4', status: 'working', steps: [1, 2], bubble: 'reading the pool' }, { model: 'z-ai/glm', status: 'idle', steps: [3] }]} />); });
  const t = host.textContent;
  expect(t).toContain('PROOF OF WORK'); expect(t).toContain('$BONK'); expect(t).toContain('reading the pool'); expect(t).toContain('Reading dexscreener');
  await act(async () => { host.querySelector('[data-testid="proof-live-chat"]').click(); });
  expect(show).toHaveBeenCalled();
  await act(async () => { root.unmount(); });
});
