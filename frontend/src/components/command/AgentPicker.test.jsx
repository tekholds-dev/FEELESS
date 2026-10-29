import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentPicker, AGENT_MAX } from './AgentPicker';
import FeeCatsPlatform from './FeeCatsPlatform';

jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => require('react').createElement('a', { href: to, ...p }, children) }), { virtual: true });   // v7 does not resolve under jest here (FeeCatLore.test does the same)

beforeEach(() => { global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('/models') ? { live: false, models: [] } : { cats: [], events: [] }) })); });
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test('🤖 one door, two AI cats (Trading · General) that both walk models → your wallet → REAL; the rule trader is a paper test link; 2 agents max', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const pick = jest.fn();
  await act(async () => { root.render(<AgentPicker count={1} onPick={pick} />); });
  expect(el.textContent).toContain(`1/${AGENT_MAX} RUNNING`);
  expect(q(el, 'agent-trading').textContent).toContain('REAL · ITS OWN WALLET'); expect(q(el, 'agent-general').textContent).toContain('you OK each move');
  expect(q(el, 'agent-trading').querySelector('.agp-flow').textContent).toBe('🧠 models👛 your wallet💵 REAL');
  expect(q(el, 'agent-general').textContent).toContain('model calls off');   // honest when the owner's model switch is off
  expect(q(el, 'agent-create').textContent).toContain('Test first on paper');
  act(() => q(el, 'agent-general').click()); expect(pick).toHaveBeenCalledWith('general');
  act(() => q(el, 'agent-create').click()); expect(pick).toHaveBeenLastCalledWith('create');
  await act(async () => { root.render(<AgentPicker count={AGENT_MAX} onPick={pick} />); });
  expect(q(el, 'agent-create').disabled).toBe(true); expect(q(el, 'agent-full')).not.toBeNull();
  act(() => root.unmount());
});

test('🤖 the agents page: no agents → the brain picker right there; the rule trader opens its wizard wearing YOUR built cat; Fee\'s desk is not repeated here', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  localStorage.setItem('feeless.myCat', JSON.stringify({ coat: 3, pattern: 'spots', look: { gear: 'crown', aura: 'gold', eyes: 'laser', tag: '' }, name: 'Specter' }));
  await act(async () => { root.render(<FeeCatsPlatform />); });
  expect(q(el, 'fc-tab-cats').textContent).toContain(`0/${AGENT_MAX}`);
  expect(q(el, 'agent-picker')).not.toBeNull();                                         // empty "My agents" = pick a brain, no dead end
  expect(q(el, 'fc-tab-live')).toBeNull(); expect(q(el, 'fc-tab-build')).toBeNull(); expect(q(el, 'leader-panel')).toBeNull();   // cut: Fee lives in the shell's other tabs
  await act(async () => { q(el, 'fc-tab-activity').click(); });
  expect(q(el, 'agent-picker')).toBeNull();
  await act(async () => { q(el, 'fc-tab-new').click(); });
  await act(async () => { q(el, 'agent-create').click(); });
  expect(document.body.querySelector('#create-cat-title')?.textContent).toBe('Create a paper agent');
  expect(document.body.querySelector('[data-testid="cat-name"]').value).toBe('Specter');   // 🎨 the agent starts from the cat you built
  expect(document.body.querySelector('[data-testid="cat-look-avatar"]').getAttribute('data-gear')).toBe('crown');
  act(() => root.unmount()); localStorage.removeItem('feeless.myCat'); document.body.innerHTML = '';
});

test('🎨 Build a cat › "Give it a job" (?create=1) lands on the brain pick — never the paper wizard; a General cat launches with brainKind general', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  window.history.pushState({}, '', '/terminal/feecat/agents?create=1&avatar=2');
  await act(async () => { root.render(<FeeCatsPlatform />); });
  expect(q(el, 'agent-picker')).not.toBeNull(); expect(document.body.querySelector('#create-cat-title')).toBeNull();
  await act(async () => { q(el, 'agent-general').click(); });
  expect(q(el, 'lct-kind').textContent).toBe('🧭 GENERAL AI CAT · ITS OWN WALLET');
  expect(q(el, 'lct-step-3').textContent).toContain('go real');
  act(() => root.unmount()); window.history.pushState({}, '', '/'); document.body.innerHTML = '';
});
