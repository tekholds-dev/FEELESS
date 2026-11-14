import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Guardrails } from './Guardrails';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const view = (on, cap) => ({ switches: [{ key: 'agentsWork', label: 'Agents work on their own', say: 'x', on, value: null, max: null, min: null, unit: '' },
  { key: 'taskCap', label: 'Most one task may spend', say: 'y', on: true, value: cap, max: 2, min: 0.005, unit: '$' }], hard: [{ t: 'Money', say: 'never' }] });

test('a switch flips through the owner route; a number saves only when changed; hard limits are locked rows', async () => {
  const sent = []; let state = view(true, 2);
  const call = jest.fn(async (path, opts) => { if (opts?.body) { const b = JSON.parse(opts.body); sent.push(b); if (b.agentsWork) state = view(b.agentsWork.on, state.switches[1].value); if (b.taskCap) state = view(state.switches[0].on, b.taskCap.value); } return state; });
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<Guardrails call={call} />); });
  expect(host.textContent).toContain("All at today's settings"); expect(host.querySelector('[data-testid=grl-save-taskCap]')).toBeNull();
  await act(async () => { host.querySelector('[data-testid=grl-on-agentsWork]').click(); });
  expect(sent[0]).toEqual({ agentsWork: { on: false } }); expect(host.querySelector('[data-testid=grl-agentsWork]').className).toContain('is-off');
  const inp = host.querySelector('[data-testid=grl-val-taskCap]');
  act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, '0.25'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { host.querySelector('[data-testid=grl-save-taskCap]').click(); });
  expect(sent[1]).toEqual({ taskCap: { value: 0.25 } }); expect(host.textContent).toContain('2 tightened');
  expect(host.querySelector('[data-testid=grl-hard]').textContent).toContain('Money');
  act(() => root.unmount()); host.remove();
});
