import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ForkBoard, StashForks } from './StashForks';

const V0 = { v: '1.00', at: 1, note: 'From the stash, unchanged', by: 'stash', usd: 0 };
const V1 = { v: '1.01', at: 2, note: 'night theme', by: 'coder', usd: 0.0021, added: 12, removed: 4 };
async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; }
const q = (el, t) => el.querySelector(`[data-testid="${t}"]`);

test('fork a stash build for free, then the next version shows its price before it runs', async () => {
  const calls = []; let forks = [];
  const view = () => ({ forks, sources: [{ id: 'b1', name: 'Pulse', kits: ['echarts'], works: true }], price: { model: 'x/coder', usd: 0.0123 }, prices: Object.fromEntries(forks.map(f => [f.id, 0.0123])), limits: { forks: 24 } });
  const work = async (_, b) => { calls.push(b); if (b.op === 'fork_open') return { preview: `<html>${b.text}</html>` }; if (b.op === 'fork_make') forks = [{ id: 'f1', name: 'Pulse', src: 'b1', at: 1, v: '1.00', versions: [V0], spentUsd: 0, offered: null, taken: null }]; if (b.op === 'fork_tune') forks = [{ ...forks[0], v: '1.01', versions: [V1, V0], spentUsd: 0.0021 }]; return view(); };
  const el = await mount(<StashForks cat={{ id: 'c' }} work={work} />);
  expect(q(el, 'fork-make-b1').textContent).toBe('Fork · free');
  await act(async () => { q(el, 'fork-make-b1').click(); });
  expect(q(el, 'fork-make-b1').textContent).toBe('Forked'); expect(q(el, 'fork-tune').textContent).toBe('Make v1.01 · ≈$0.01');
  expect(q(el, 'fork-offer').disabled).toBe(true);   // v1.00 is the stash's own copy
  const box = q(el, 'fork-ask'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(box, 'night theme'); box.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q(el, 'fork-tune').closest('form').requestSubmit ? q(el, 'fork-tune').closest('form').requestSubmit() : q(el, 'fork-tune').click(); });
  expect(calls.find(c => c.op === 'fork_tune')).toEqual({ op: 'fork_tune', job: 'f1', text: 'night theme' });
  expect(q(el, 'fork-v-1.01')).not.toBeNull(); expect(q(el, 'fork-frame').getAttribute('srcdoc')).toContain('1.01'); expect(q(el, 'fork-offer').disabled).toBe(false);
});

test("Fee's board lists offered forks first, by tag, and takes one into the stash", async () => {
  const calls = [];
  const work = async (_, b) => { calls.push(b); return { counts: { forks: 1, agents: 1, versions: 2, offered: 1, taken: 0 }, board: [{ id: 'f1', name: 'Pulse', agent: 'agent-ab12cd', v: '1.01', versions: [V1, V0], spentUsd: 0.0021, offered: { v: '1.01' }, taken: null }] }; };
  const el = await mount(<ForkBoard cat={{ id: 'leader' }} work={work} />);
  expect(q(el, 'fork-row-f1').textContent).toContain('agent-ab12cd'); expect(q(el, 'fork-row-f1').textContent).toContain('v1.01 OFFERED');
  await act(async () => { q(el, 'fork-take-f1').click(); });
  expect(calls.at(-1)).toEqual({ op: 'fork_take', job: 'f1' });
});
