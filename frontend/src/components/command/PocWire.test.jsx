import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import PocWire, { parseDays, replyAfter, flowState, browseAsk } from './PocWire';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
beforeEach(() => { try { localStorage.clear(); } catch { /* no store */ } });
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('the week is read from the agent reply, one card per day, in week order', () => {
  expect(parseDays('Here you go:\n**Fri:** Check demo links\nMon - Draft 3 hooks\nWednesday: Record a street clip\nMon: again')).toEqual([{ d: 'Mon', text: 'Draft 3 hooks' }, { d: 'Wed', text: 'Record a street clip' }, { d: 'Fri', text: 'Check demo links' }]);
  expect(parseDays('no days here')).toEqual([]);
});

test('each step reads its state from the real doc: asked → running → done', () => {
  const doc = { messages: [{ by: 'you', at: '100', text: 'x' }], busy: { at: 100 } };
  expect(flowState({ mode: 'ai' }, doc, true)).toMatchObject({ char: 'done', browse: 'todo', at: 1 });
  expect(flowState({ mode: 'ai', browseAt: 100 }, doc, true)).toMatchObject({ browse: 'running', at: 1 });
  const done = { messages: [...doc.messages, { by: 'Mind A', at: '130', text: '1. hook' }] };
  expect(flowState({ mode: 'ai', browseAt: 100 }, done, true)).toMatchObject({ browse: 'done', draft: 'todo', review: 'waiting', at: 2 });
  expect(replyAfter(done, 200)).toBeNull();
  expect(flowState({ mode: 'ai', browseAt: 100, draftAt: 140, days: [{ d: 'Mon', text: 'a' }], approvedAt: 150 }, done, true).at).toBe(4);
  expect(flowState({ mode: 'self', browseDone: true }, {}, true)).toMatchObject({ browse: 'done', at: 2 });
});

test('Browse sends the agent its real ask; Plan myself never calls a model', async () => {
  const work = jest.fn(async () => ({ doc: { id: 'w1', messages: [], busy: { at: 1 } } })); const setDoc = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<PocWire src="/p.png" from="m1" title="Bishop" cat={{ id: 'c' }} doc={{ id: 'w1', messages: [] }} work={work} setDoc={setDoc} onClose={() => {}} />));
  expect($(el, 'cwf-here').textContent).toContain('2/4');
  await act(async () => $(el, 'cwf-browse').click());
  expect(work).toHaveBeenCalledWith('c', { op: 'ws_build', job: 'w1', text: browseAsk('Bishop'), to: 'both' }); expect(setDoc).toHaveBeenCalled();
  work.mockClear();
  await act(async () => $(el, 'cwf-mode-self').click());
  await act(async () => root.render(<PocWire src="/p.png" from="m1" title="Bishop" cat={{ id: 'c' }} doc={{ id: 'w1', messages: [] }} work={work} setDoc={setDoc} onClose={() => {}} />));
  await act(async () => $(el, 'cwf-browse').click());
  await act(async () => $(el, 'cwf-draft').click());
  expect($(el, 'cwf-day-Mon')).not.toBeNull(); expect(work).not.toHaveBeenCalled();
  act(() => root.unmount()); el.remove();
});
