import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CatBrainSwitch } from './CatBrainSwitch';

const NEXA = { id: 'nexa', name: 'NEXA', state: 'live', ageMin: 6, favor: 2, exit: 1, avoid: 3, why: 'BBB has real buyers', record: { favor: { n: 40, rightPct: 55, typical: 1.2 } } };
beforeEach(() => { global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ brains: [NEXA, { id: 'gpt-astra' }] }) })); });

test('🪟 a cat can be handed to NEXA: her live read (age, picks / exits / avoids, record) and one tap to assign or go back to rules', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const act_ = jest.fn(() => Promise.resolve());
  await act(async () => { root.render(<CatBrainSwitch cat={{ id: 'c1' }} act={act_} />); });
  const [rules, nexa] = el.querySelectorAll('[role="radio"]');
  expect(rules.getAttribute('aria-checked')).toBe('true');
  expect(el.textContent).toContain('her read · 6 min old');
  expect(el.querySelector('.cb-nums').textContent).toBe('2picks1exits3avoid');
  expect(el.querySelector('.cb-rec').textContent).toContain('55%');
  await act(async () => { nexa.click(); });
  expect(act_).toHaveBeenCalledWith('brain', { text: 'nexa' });
  await act(async () => { root.render(<CatBrainSwitch cat={{ id: 'c1', modelBrain: 'nexa' }} act={act_} />); });
  expect(el.textContent).toContain('NEXA trades this cat');
  expect(el.querySelector('.cb-why').textContent).toContain('BBB has real buyers');
  await act(async () => { el.querySelectorAll('[role="radio"]')[0].click(); });
  expect(act_).toHaveBeenLastCalledWith('brain', { text: 'rules' });
  await act(async () => { root.render(<CatBrainSwitch cat={{ id: 'lead', isLeader: true }} act={act_} />); });
  expect(el.querySelectorAll('[role="radio"]')[1].disabled).toBe(true);   // FeeCat herself runs the desk
  act(() => root.unmount());
});
