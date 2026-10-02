import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ children, ...p }) => <a {...p}>{children}</a> }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({}) }));
jest.mock('./RugReport', () => ({ RugReport: () => null, ShieldLeaderboard: () => null }));
import { MemeTerms } from './RepStanding';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });

test('trench dictionary: new terms flip to their meaning, each kind has its own card', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ learned: 812, terms: [
    { term: 'skibidi', today: 9, new: true, known: false, kind: 'wave', meaning: '🌊 ticker wave — 9 coins', coins: ['MINT1234'] },
    { term: 'cto', today: 4, spike: 4, known: true, kind: 'meta', meaning: 'community takeover', coins: [] }] }) }));
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<MemeTerms />); }); await tick();
  const card = host.querySelector('[data-testid="term-skibidi"]');
  expect(card.className).toContain('k-wave'); expect(card.textContent).toContain('NEW'); expect(host.textContent).toContain('812');
  act(() => card.click());
  expect(card.className).toContain('is-open'); expect(card.getAttribute('aria-expanded')).toBe('true');
  expect(host.querySelector('[data-testid="term-cto"]').textContent).toContain('community takeover');
});
