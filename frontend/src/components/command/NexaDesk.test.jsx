import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { NexaDesk, nexaState } from './NexaDesk';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('nexa desk says when she is offline and shows her call, record and notebook when live', async () => {
  expect(nexaState({ provider: { on: false } })).toBe('offline');
  expect(nexaState({ provider: { on: true }, at: 1, busy: true })).toBe('thinking');
  const d = { provider: { on: true, model: 'Ministral' }, at: Date.now() / 1000 - 30, ok: true, cfg: { tune: true }, memN: 1,
    last: { why: 'buyers fading on $X', avoid: ['PAIRAAAAAA'], exit: [], favor: ['PAIRBBBBBB'], at: Date.now() / 1000 },
    record: { favor: { n: 4, rightPct: 75, typical: 6 }, avoid: { n: 0 } }, tunes: [{ at: 1, set: { hardStop: -22 }, was: { hardStop: -25 } }],
    memory: [{ kind: 'discovery', text: 'cat coins trending https://x.com/a', at: 1 }] };
  const call = jest.fn(() => Promise.resolve(d));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<NexaDesk call={call} />); });
  expect(el.querySelector('[data-testid="nexa-state"]').textContent).toContain('ON THE DESK');
  expect(el.textContent).toContain('skip PAIRAA'); expect(el.textContent).toContain('75% right');
  expect(el.textContent).toContain('hardStop -25 → -22'); expect(el.textContent).toContain('cat coins trending');
  expect(el.querySelector('[data-testid="nexa-tune"]').getAttribute('aria-pressed')).toBe('true');
});
