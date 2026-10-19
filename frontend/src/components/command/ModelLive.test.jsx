import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { ModelLive, who, ago } from './ModelLive';

global.IS_REACT_ACT_ENVIRONMENT = true;

test('names the two models and reads relative time', () => {
  expect(who('lan')).toBe('G4'); expect(who('local')).toBe('OSSY'); expect(who('groq')).toBe('GROQ');
  expect(ago(100, 130)).toBe('30s'); expect(ago(0, 7200)).toBe('2h');
});

test('shows a live % bar for a call in flight and the prompt log', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const call = jest.fn(async () => ({ inflight: [{ prov: 'lan', role: 'seat', at: 1, sec: 6, pct: 42, typical: 14 }], avgMs: { local: 9000 },
    log: [{ at: 1, prov: 'local', role: 'advise', ms: 8100, ok: true, tok: 900, prompt: 'NOW: G4 holds $X', answer: '{"action":"HOLD"}', system: 'sys' }] }));
  await act(async () => { createRoot(el).render(<ModelLive call={call} />); });
  expect(call).toHaveBeenCalledWith('/admin/ai/calls');
  expect(el.querySelector('[data-testid="mlv-lan"]').textContent).toContain('42%');
  expect(el.querySelector('[data-testid="mlv-local"]').textContent).toContain('idle');
  await act(async () => { el.querySelector('[data-testid="mlv-call"] button').click(); });
  expect(el.textContent).toContain('NOW: G4 holds $X');
});
