import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TeachBox } from './TeachBox';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../../lib/adminCall', () => ({ uploadImage: jest.fn(async () => '/api/reputation/uploads/x1.webp') }));

test('🎓 teach the desk: a narrative on this coin is sent, the list shows what you taught, ✕ removes it', async () => {
  const call = jest.fn(async () => ({}));
  const o = { teach: { items: [{ id: 't1', kind: 'chart', text: 'first higher low after the bond dip', img: '/api/reputation/uploads/a.webp', at: Date.now() / 1000 - 90 }], counts: { note: 0, narrative: 0, chart: 1 }, narratives: ['frog'] },
    ai: { learn: { vitals: [{ bucket: 'TAUGHT', n: 22, med: 3.4 }] } } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TeachBox o={o} mint="So11111111111111111111111111111111111111112" sym="SOL" call={call} isOwner />); });
  expect(el.querySelector('[data-testid="teach-record"]').textContent).toContain('22 judged');
  expect(el.querySelector('[data-testid="teach-list"]').textContent).toContain('first higher low');
  await act(async () => { el.querySelector('[data-testid="teach-kind-narrative"]').click(); });
  const ta = el.querySelector('[data-testid="teach-text"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; set.call(ta, 'frog season keeps running'); ta.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="teach-oncoin"]').click(); });
  await act(async () => { el.querySelector('[data-testid="teach-send"]').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ teach: { kind: 'narrative', text: 'frog season keeps running', mint: 'So11111111111111111111111111111111111111112', sym: 'SOL' } });
  await act(async () => { el.querySelector('[data-testid="teach-rm-t1"]').click(); });
  expect(JSON.parse(call.mock.calls[1][1].body)).toEqual({ teach: { remove: 't1' } });
  await act(async () => { root.unmount(); });
});
