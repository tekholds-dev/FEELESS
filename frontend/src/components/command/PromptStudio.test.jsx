import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PromptStudio, windowOf } from './PromptStudio';
import { STUDIO } from './__fixtures__/promptStudio';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🎭 the context window: each layer\'s share of the loaded window', () => {
  const w = windowOf(STUDIO.models[0]);
  expect(w.used).toBe(2600 + 105 + 2300); expect(w.total).toBe(8704); expect(w.pct).toBe(58); expect(w.segs.map(s => s.k)).toEqual(['job', 'identity', 'brain']);
  expect(windowOf({ layers: [{ k: 'job', tok: 100 }] })).toMatchObject({ known: false, pct: 100 });
});

test('🎭 pick a model → its context, record, habits and four mindsets; apply / edit / revert post to the server', async () => {
  const posts = []; let state = JSON.parse(JSON.stringify(STUDIO));
  const call = jest.fn(async (path, o) => {
    if (o?.method === 'POST') { const b = JSON.parse(o.body); posts.push(b);
      state = { ...state, models: state.models.map(m => (m.key !== b.key ? m : { ...m, active: b.revert ? null : { set: b.set, text: b.text || 'x', at: Date.now() / 1000, edited: !!b.text, since: { n: 0 } } })) }; }
    return state;
  });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PromptStudio call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(el.querySelectorAll('.pst-set').length).toBe(4); expect(q('pst-rec').textContent).toContain('17%'); expect(q('pst-rec').textContent).toContain('rides winners back to red');
  expect(q('pst-ctx').textContent).toContain('58%');
  await act(async () => { q('pst-layer-job').click(); }); expect(el.querySelector('.pst-pre').textContent).toContain('TURNS');
  await act(async () => { q('pst-apply-elite').click(); });
  expect(posts[0]).toEqual({ key: 'lan', set: 'elite' }); expect(q('pst-set-elite').className).toContain('is-on'); expect(q('pst-apply-elite').textContent).toBe('Applied');
  await act(async () => { q('pst-edit-btn-degen').click(); });
  const ta = q('pst-edit-degen'); const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  await act(async () => { set.call(ta, 'hold the germ, not the candle'); ta.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('pst-apply-edit-degen').click(); });
  expect(posts[1]).toEqual({ key: 'lan', set: 'degen', text: 'hold the germ, not the candle' });
  await act(async () => { q('pst-revert').click(); }); expect(posts[2]).toEqual({ key: 'lan', revert: true });
  await act(async () => { q('pst-model-local').click(); });
  expect(q('pst-set-progressive').className).toContain('is-on'); expect(q('pst-since').textContent).toContain('4 trades · 50% won · +2.6% avg');
  await act(async () => { q('pst-model-win').click(); });
  expect(q('pst-rec').textContent).toContain('45%'); expect(q('pst-rec').textContent).toContain('YES CALLS');
  act(() => root.unmount());
});
