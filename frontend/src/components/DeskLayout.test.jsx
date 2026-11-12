import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a>, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { address: 'W1' } }) }));
jest.mock('./QuestBoard', () => ({ useQuests: () => [{ level: { level: 3, name: 'Degen', xp: 450, next: 600 }, quests: { daily: { tasks: [{ id: 'trade', label: 'Make a trade', have: 1, target: 1, done: true }, { id: 'chat', label: 'Say gm', have: 0, target: 1, done: false }] } } }] }));
jest.mock('../lib/sharedJson', () => ({ sharedJson: jest.fn(async () => ({ rows: [] })), _resetShared: () => {} }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('🖥 Desk widgets show only the server\'s numbers: rank from the quest record, quests done/total, an honest empty board', async () => {
  const { DeskWidgets, DeskDock } = require('./DeskLayout');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><DeskWidgets /><DeskDock page="trade" /></>); });
  const q = id => el.querySelector(`[data-testid="${id}"]`).textContent;
  expect(q('desk-rank')).toContain('L3'); expect(q('desk-rank')).toContain('450 XP · 150 to next');
  expect(q('desk-quests')).toContain('1/2'); expect(q('desk-board')).toContain('No calls this week yet');
  expect(el.querySelector('[data-testid="desk-dock"] .is-on').getAttribute('aria-label')).toBe('Trade');
  el.remove();
});
