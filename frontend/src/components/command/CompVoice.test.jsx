import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { CompVoice } from './CompVoice';

const base = { ready: true, adapter: 'best', trainedAt: 1700000000, rows: 305, running: false, listening: false, idleMin: 20, base: 'Qwen3.5-9B', chat: [] };

test('🗣 COMP Voice: asleep until woken, then a question goes to the owner route and the answer lands with its time', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  let st = { ...base };
  const call = jest.fn(async (path, o) => {
    const b = o ? JSON.parse(o.body) : null;
    if (b?.op === 'start') st = { ...st, running: true, listening: true };
    if (b?.op === 'ask') st = { ...st, chat: [{ role: 'user', content: b.text, at: 1 }, { role: 'assistant', content: 'Revoked authorities, burned LP, no bundle. Miss two and pass.', at: 2, secs: 1.4, tokens: 18 }] };
    return st;
  });
  await act(async () => { root.render(<CompVoice call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(call).toHaveBeenCalledWith('/admin/model-lab/voice');
  const posts = () => call.mock.calls.filter(c => c[1]).map(c => JSON.parse(c[1].body));
  expect(q('cv-state').textContent).toMatch(/Asleep/); expect(q('cv-q').disabled).toBe(true); expect(el.textContent).toMatch(/305 lessons/);
  await act(async () => { q('cv-wake').click(); });
  expect(posts().at(-1)).toEqual({ op: 'start', text: '' });
  expect(q('cv-state').textContent).toMatch(/Awake/);
  const input = q('cv-q');
  await act(async () => { Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, 'How do I spot a rug?'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('cv-send').click(); });
  expect(posts().at(-1)).toEqual({ op: 'ask', text: 'How do I spot a rug?' });
  expect(q('cv-assistant').textContent).toMatch(/burned LP/); expect(q('cv-assistant').textContent).toMatch(/1\.4s · 18 tokens/);
  await act(async () => { root.unmount(); });
});

test('🗣 COMP Voice: not trained yet says how to train it and cannot be woken', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CompVoice call={async () => ({ ...base, ready: false, adapter: '', trainedAt: 0, rows: 0 })} />); });
  expect(el.textContent).toMatch(/comp-voice\.py/); expect(el.querySelector('[data-testid="cv-wake"]').disabled).toBe(true);
  await act(async () => { root.unmount(); });
});
