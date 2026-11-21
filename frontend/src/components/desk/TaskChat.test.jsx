import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TaskCard, TaskChatProvider, TaskStrip } from './TaskChat';
import { ProofWorkspace } from '../command/ProofWorkspace';
import { elapsed, inScope, scopeKey, taskCommand, thoughtLabel } from '../../lib/taskChats';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// 🧵 Slice 35: task chats. Every control here calls the server's own op (fc_taskchat.op) — click → op → what it shows comes back from the server.
const CARD = { id: 'tc1', title: 'Review the WIF filing', state: 'working', step: 'Check the exit', stepN: 2, steps: 3, secs: 75, cost: 0.0123, recap: '', scope: { kind: 'pow', ref: 'pw1' }, by: 'owner' };
const DONE = { ...CARD, id: 'tc0', title: 'Old one', state: 'done', stepN: 3, recap: 'Read the call.\nThree fixes listed.', scope: { kind: 'desk', ref: '' } };
const TASK = { ...CARD, brief: 'Check this PoW and list three fixes', model: 'm/a', cap: 0.2,
  checklist: [{ text: 'Read the call', state: 'done', cost: 0.005, did: 'The call was **long**.', secs: 3 }, { text: 'Check the exit', state: 'doing', cost: 0 }, { text: 'List fixes', state: 'pending', cost: 0 }],
  thoughts: [{ step: -1, text: 'Three checks cover it.', s: 2.2 }, { step: 0, text: 'Looking at the numbers.', s: 3.1 }],
  logs: [{ at: Date.now() / 1000 - 30, text: 'Planned 3 steps.' }, { at: Date.now() / 1000 - 20, text: 'read the folder', step: 0 }], msgs: [] };

function setup(over = {}) {
  const calls = []; let task = { ...TASK, ...over };
  const call = async b => { calls.push(b);
    if (b.op === 'task_list') return { tasks: [CARD, DONE], parallel: 1 };
    if (b.op === 'task_new') return { task: { ...TASK, id: 'tc9', title: b.text, state: 'starting', checklist: [], thoughts: [], logs: [] }, tasks: [DONE, CARD, { ...CARD, id: 'tc9', title: b.text, state: 'starting' }] };
    if (b.op === 'task_get') return { task };
    if (b.op === 'task_pause') { task = { ...task, state: 'paused' }; return { task }; }
    if (b.op === 'task_say') { task = { ...task, msgs: [{ by: 'you', text: b.text }] }; return { task }; }
    if (b.op === 'task_stop') { task = { ...task, state: 'stopped' }; return { task }; }
    if (b.op === 'task_parallel') return { parallel: b.cap };
    return {}; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  return { calls, call, el, root };
}
const q = (sel, root = document) => root.querySelector(`[data-testid="${sel}"]`);
const typeIn = async (inp, v) => { await act(async () => { Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(inp, v); inp.dispatchEvent(new Event('input', { bubbles: true })); }); };
const submit = async form => { await act(async () => { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }); };

afterEach(() => { document.body.innerHTML = ''; });

test('🧵 a proof chat splits a task off its filing; the card shows title, live state, step, time, cost; one click opens the task chat', async () => {
  const { calls, call, el, root } = setup();
  await act(async () => { root.render(<TaskChatProvider call={call}><ProofWorkspace id="t-pow" kind="pow" name="PoW #3" taskRef="pw1" chat={<p>thread</p>}><p>work</p></ProofWorkspace></TaskChatProvider>); });
  const strip = q('tch-strip-pow', el); expect(strip).not.toBeNull(); expect(el.textContent).toContain('thread');   // above the proof's own chat, nothing lost
  const card = q('tch-card-tc1', el);
  expect(q('tch-card-state', card).textContent).toBe('working'); expect(card.textContent).toContain('2/3'); expect(card.textContent).toContain('Check the exit');
  expect(q('tch-card-time', card).textContent).toBe('1m 15s'); expect(q('tch-card-cost', card).textContent).toBe('$0.01');
  expect(q('tch-card-tc0', el)).toBeNull();   // a desk task is not this filing's
  await typeIn(q('tch-split-in-pow', el), 'Compare 3 exits');
  await submit(q('tch-split-in-pow', el).closest('form'));
  expect(calls.find(c => c.op === 'task_new')).toMatchObject({ op: 'task_new', text: 'Compare 3 exits', job: 'pow:pw1' });   // saved on the server, scoped to the filing
  expect(q('tch-dock')).not.toBeNull();   // the new task chat opens docked beside the chat
  await act(async () => { q('tch-close').click(); });
  await act(async () => { q('tch-open-tc1', el).click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'task_get', job: 'tc1' });
});

test('🧵 the task chat: checklist (done ✓ · doing spinner · pending dashed), thoughts as fold-open dropdowns (newest open), logs with times, cost per step; steer / pause / stop', async () => {
  const { calls, call, root } = setup();
  await act(async () => { root.render(<TaskChatProvider call={call}><TaskStrip scope="pow" /></TaskChatProvider>); });
  await act(async () => { q('tch-open-tc1').click(); });
  const pane = q('tch-pane'); expect(pane).not.toBeNull();
  expect([...q('tch-checklist', pane).children].map(li => li.className)).toEqual(['is-done', 'is-doing', 'is-pending']);
  expect(q('tch-step-0', pane).textContent).toContain('$0.0050');
  const th = [...pane.querySelectorAll('[data-testid="tch-thought"]')];
  expect(th.map(d => d.querySelector('summary').textContent)).toEqual(['Thought for 2 s', 'Thought for 3 s']);
  expect(th.map(d => d.open)).toEqual([false, false]);   // a step is doing: the mind moved on from both thoughts, so both are closed
  expect(pane.textContent).toContain('read the folder'); expect(pane.querySelectorAll('.tch-log time').length).toBe(2);
  expect(q('tch-block-0', pane).querySelector('strong, b').textContent).toBe('long');   // what step 1 did, as markdown
  await typeIn(q('tch-steer-in', pane), 'use only DexScreener');
  await submit(q('tch-steer-in', pane).closest('form'));
  expect(calls.find(c => c.op === 'task_say')).toMatchObject({ job: 'tc1', text: 'use only DexScreener' });
  await act(async () => { q('tch-pause').click(); });
  expect(calls.find(c => c.op === 'task_pause')).toMatchObject({ job: 'tc1' }); expect(q('tch-pane-state').textContent).toBe('paused'); expect(q('tch-resume')).not.toBeNull();
  await act(async () => { q('tch-stop').click(); });
  expect(calls.find(c => c.op === 'task_stop')).toMatchObject({ job: 'tc1' }); expect(q('tch-steer-in')).toBeNull();   // ended: no input left
});

test('🧵 the newest thought stays open while it is the mind\'s latest; a finished task shows its recap and can carry on in the chat', async () => {
  const { call, root } = setup({ checklist: TASK.checklist.map((s, i) => (i === 1 ? { ...s, state: 'done', did: 'ok' } : s)) });
  await act(async () => { root.render(<TaskChatProvider call={call}><TaskStrip scope="pow" /></TaskChatProvider>); });
  await act(async () => { q('tch-open-tc1').click(); });
  expect([...document.querySelectorAll('[data-testid="tch-thought"]')].map(d => d.open)).toEqual([false, true]);
  const seen = [];
  const el0 = document.createElement('div'); document.body.appendChild(el0); const r0 = createRoot(el0);
  await act(async () => { r0.render(<TaskChatProvider call={call}><TaskCard c={DONE} /></TaskChatProvider>); });
  expect(q('tch-continue-tc0', el0)).toBeNull();   // no chat to carry on in → no dead button
  function Host() { return <TaskChatProvider call={call}><Reg on={c => seen.push(c)} /><TaskCard c={DONE} /></TaskChatProvider>; }
  function Reg({ on }) { const ctx = require('./TaskChat').useTaskChats(); React.useEffect(() => { ctx.onContinue(on); }, [ctx, on]); return null; }
  const el2 = document.createElement('div'); document.body.appendChild(el2); const r2 = createRoot(el2);
  await act(async () => { r2.render(<Host />); });
  expect(q('tch-card-recap', el2).textContent).toContain('Three fixes listed.');
  await act(async () => { q('tch-continue-tc0', el2).click(); });
  expect(seen[0].id).toBe('tc0');
});

test('🧵 pure helpers', () => {
  expect(taskCommand('/task  compare pools')).toBe('compare pools'); expect(taskCommand('task x')).toBeNull(); expect(taskCommand('/task ab')).toBeNull();
  expect(scopeKey('pow', 'pw1')).toBe('pow:pw1'); expect(scopeKey('desk')).toBe('desk'); expect(scopeKey('poc', '')).toBe('poc');
  expect(inScope(CARD, 'pow')).toBe(true); expect(inScope(CARD, 'pow:pw1')).toBe(true); expect(inScope(CARD, 'pow:zz')).toBe(false); expect(inScope(DONE, 'desk')).toBe(true);
  expect(elapsed(9)).toBe('9s'); expect(elapsed(3700)).toBe('1h 1m'); expect(thoughtLabel({ s: 0.2 })).toBe('Thought for 1 s');
});
