import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HqDeck } from './HqDeck';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('react-router-dom', () => ({ useNavigate: () => () => {}, Link: ({ children }) => children, useLocation: () => ({ pathname: '/' }) }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({}) }));
jest.mock('./AgentDesk', () => ({ AgentDesk: () => null }));
jest.mock('./TreasuryHub', () => ({ TreasuryHub: () => <div data-testid="treasury" /> }));
const A = 'HQnav1111111111111111111111111111111111111';
const q = id => document.querySelector(`[data-testid="${id}"]`);

test('🧭 HQ sidebar: every tool once under its group, one click switches the page, one header, the phone drawer closes on a pick', async () => {
  localStorage.setItem('feeless:cc-session', JSON.stringify({ address: A, ts: Math.floor(Date.now() / 1000), sig: 'x' }));
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ yourRole: 'owner', owner: true }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HqDeck address={A} signMessage={async () => 'x'} onClose={() => {}} startTab="agents" />); });
  const tools = [...document.querySelectorAll('.hqs-nav button')].map(b => b.dataset.testid);
  expect(tools.length).toBe(new Set(tools).size);                         // no tool twice (the old pinned row repeated five)
  expect(tools).toEqual(expect.arrayContaining(['cc-tab-agents', 'cc-tab-money', 'cc-tab-fuse', 'cc-tab-bugs']));
  expect(q('cc-group-money').textContent).toContain('Fuse'); expect(q('cc-group-system').textContent).toContain('Looks');   // grouped by the job (owner 2026-11-11)
  await act(async () => { q('hq-menu').click(); });
  expect(q('hq-shell').className).toContain('is-nav');
  await act(async () => { q('cc-tab-money').click(); });
  expect(q('hq-shell').className).not.toContain('is-nav');
  expect(q('cc-tab-money').getAttribute('aria-current')).toBe('page');
  expect([...document.querySelectorAll('.hqm-head h3')].map(h => h.textContent)).toHaveLength(1);   // header + body once shared a key → a ghost header
  expect(q('cc-tab-hero').textContent).toContain('Money');
});
