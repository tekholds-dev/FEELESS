import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import SpendChip from './SpendChip';
import { MediaCard } from './MediaStudio';

const q = id => document.querySelector(`[data-testid="${id}"]`);
const mount = async el => { const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box); await act(async () => root.render(el)); await act(async () => { await new Promise(r => setTimeout(r, 0)); }); return { root, box }; };
const SPEND = { capUsd: 10, spentUsd: 2.5, makingUsd: 1, leftUsd: 6.5, calls: 2, byProvider: { OpenRouter: 2.5 }, over: false,
  rows: [{ at: 1794956339, agent: 'Happy Assistant', what: 'aleph-2', provider: 'OpenRouter', usd: 2.4, how: 'list price' }, { at: 1794956119, agent: 'Fee', what: 'hy4', provider: 'OpenRouter', usd: 0.1, how: 'provider reported' }] };

test('💵 the day spend on his keys: total of the cap, every receipt row, and he names the cap', async () => {
  const work = jest.fn(async (_id, b) => (b.op === 'spend_cap' ? { spend: { ...SPEND, capUsd: Number(b.text), leftUsd: Number(b.text) - 3.5 } } : { spend: SPEND }));
  const { root } = await mount(<SpendChip cat={{ id: 'c1' }} work={work} />);
  expect(work).toHaveBeenCalledWith('c1', { op: 'spend' });
  expect(q('spend-open').textContent).toContain('$2.50'); expect(q('spend-open').textContent).toContain('$10.00');
  await act(async () => q('spend-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('spend-rows').querySelectorAll('li')).toHaveLength(2); expect(q('spend-pop').textContent).toContain('$1.00 still making'); expect(q('spend-pop').textContent).toContain('Happy Assistant');
  const input = q('spend-cap'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, '25'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => q('spend-cap-save').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'spend_cap', text: '25' }); expect(q('spend-open').textContent).toContain('$25.00');
  act(() => root.unmount());
});

test('💵 over the cap it shows a stop, and a seed means no extra read', async () => {
  const work = jest.fn(async () => ({ spend: SPEND }));
  const { root } = await mount(<SpendChip cat={{ id: 'c1' }} work={work} seed={{ ...SPEND, spentUsd: 10, leftUsd: 0, over: true }} compact />);
  expect(work).not.toHaveBeenCalled(); expect(q('spend-chip').className).toContain('is-over'); expect(q('spend-open').textContent).toContain('⛔');
  act(() => root.unmount());
});

test('🔁 any failed make can run again on the same model and words, and the reason is said once', async () => {
  const work = jest.fn(async () => ({ doc: { messages: [] } }));
  const m = { media: { id: 'm1', kind: 'image', status: 'failed', provider: 'openrouter', modelId: 'or-nano-banana', label: 'Nano Banana', prompt: 'a chrome rat', refs: [{ mid: 'mref' }],
    why: 'The provider is busy right now. Nothing was charged. Try again in a minute. (429: slow down)' } };
  const { root } = await mount(<MediaCard m={m} cat={{ id: 'c1' }} doc={{ id: 'w1', messages: [] }} work={work} setDoc={() => {}} />);
  const fail = q('media-fail'); expect(fail.textContent).not.toContain('Nothing more is charged');
  expect(fail.querySelector('p').textContent).not.toContain('429'); expect(fail.querySelector('code').textContent).toBe('429: slow down');   // one calm line; the raw words fold away
  await act(async () => q('media-retry-make-btn').click());
  expect(work).toHaveBeenLastCalledWith('c1', { op: 'media_make', job: 'w1', text: 'a chrome rat', tools: { model: 'or-nano-banana', kind: 'image', noChar: true, refs: ['mref'] } });
  act(() => root.unmount());
});

test('✅ Check before paying runs the $0 check and lists each row', async () => {
  const work = jest.fn(async (_id, b) => (b.op === 'money_ready' ? { ok: false, rows: [{ id: 'or-key', ok: true, what: 'OpenRouter key', say: 'Works.' }, { id: 'or-credit', ok: false, what: 'OpenRouter credit', say: '$1.00 left. Top up first.' }] } : { spend: SPEND }));
  const { root } = await mount(<SpendChip cat={{ id: 'c1' }} work={work} />);
  await act(async () => q('spend-open').click()); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  await act(async () => q('money-ready').click());
  expect(work).toHaveBeenCalledWith('c1', { op: 'money_ready' });
  const rows = q('money-ready-rows').querySelectorAll('li'); expect(rows).toHaveLength(2); expect(rows[1].className).toBe('is-no'); expect(q('money-ready').textContent).toContain('Check again');
  act(() => root.unmount());
});
