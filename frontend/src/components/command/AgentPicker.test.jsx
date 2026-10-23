import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentPicker, AGENT_MAX } from './AgentPicker';
import FeeCatsPlatform from './FeeCatsPlatform';

beforeEach(() => { global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('/models') ? { live: false, models: [] } : { cats: [], events: [] }) })); });
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('🤖 one door, two different agents: the rule trader (free) or the AI trader (talk to it); 2 agents max', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const pick = jest.fn();
  await act(async () => { root.render(<AgentPicker count={1} onPick={pick} />); });
  expect(el.textContent).toContain(`1/${AGENT_MAX} RUNNING`);
  expect(q(el, 'agent-create').textContent).toContain('FREE'); expect(q(el, 'agent-launch').textContent).toContain('PAY AS YOU GO');
  expect(q(el, 'agent-launch').textContent).toContain("model calls off");   // honest when the owner's model switch is off
  act(() => q(el, 'agent-launch').click()); expect(pick).toHaveBeenCalledWith('launch');
  await act(async () => { root.render(<AgentPicker count={AGENT_MAX} onPick={pick} />); });
  expect(q(el, 'agent-create').disabled).toBe(true); expect(q(el, 'agent-full')).not.toBeNull();
  act(() => root.unmount());
});

test('🐱 the lab: New agent opens the picker, the rule trader opens its wizard, 🎨 Build your cat goes to the look collection', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const nav = jest.fn(); window.addEventListener('popstate', nav);
  await act(async () => { root.render(<FeeCatsPlatform />); });
  expect(q(el, 'fc-tab-cats').textContent).toContain(`0/${AGENT_MAX}`);
  await act(async () => { q(el, 'fc-new-agent').click(); });
  expect(q(el, 'agent-picker')).not.toBeNull();
  await act(async () => { q(el, 'agent-create').click(); });
  expect(document.body.querySelector('#create-cat-title')?.textContent).toBe('Create a paper agent');
  await act(async () => { q(el, 'fc-tab-build').click(); });
  expect(window.location.pathname).toBe('/terminal/feecat/cats'); expect(nav).toHaveBeenCalled();
  act(() => root.unmount()); window.history.pushState({}, '', '/');
});
