import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AiPlayground } from './AiPlayground';

test('the playground shows a creation in a sandboxed frame and makes a new one on request', async () => {
  const item = { id: 'p1', prompt: 'neon grid', html: '<html><head></head><body>x</body></html>', by: 'LOCAL AI', at: 1 };
  const call = jest.fn((path, opts) => Promise.resolve(opts ? { item: { ...item, id: 'p2', prompt: 'card' }, items: [{ ...item, id: 'p2', prompt: 'card' }, item] } : { items: [item] }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AiPlayground call={call} />); });
  await act(async () => { await Promise.resolve(); });
  const f = el.querySelector('[data-testid="apg-frame"]');
  expect(f.getAttribute('sandbox')).toBe('allow-scripts');   // no same-origin: the creation can't reach the site, cookies or the HQ session
  const input = el.querySelector('[data-testid="apg-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(input, 'a holo card'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="apg-make"]').click(); });
  await act(async () => { await Promise.resolve(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai/playground', expect.objectContaining({ method: 'POST' }));
  expect(el.querySelector('[data-testid="apg-frame"]').getAttribute('title')).toBe('card');
});
