import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { SupportHub, heat } = require('./SupportHub');

const board = { reports: [{ id: 'a', title: '💥 boom', area: 'fuse', kind: 'bug', count: 4, status: 'open', plus: 2, importance: 80 }, { id: 'b', title: 'old', area: 'trade', kind: 'idea', count: 1, status: 'fixed', plus: 0, importance: 3 }],
  mine: [], polls: [{ id: 'p', q: 'Pink panther?', options: ['yes', 'no'], tally: [3, 1], votes: 4, mine: null, stage: { key: 'idea', label: '💡 IDEA', next: { need: 6, label: '🔥 HOT' } } }],
  ladder: [{ at: 0, key: 'idea', label: '💡 IDEA' }, { at: 10, key: 'hot', label: '🔥 HOT' }], counts: { open: 1, fixing: 0, fixed: 1, polls: 1 } };

test('the hub grids reports by importance and shows polls on the ladder', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(board) }));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<SupportHub />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelectorAll('[data-testid="sup-card"]').length).toBe(2);
  expect(el.querySelector('.sup-card.h-hot')).toBeTruthy(); expect(heat(80)).toBe('hot');
  await act(async () => { el.querySelector('[data-testid="sup-lens-polls"]').click(); });
  expect(el.textContent).toContain('Pink panther?'); expect(el.textContent).toContain('75%'); expect(el.textContent).toContain('6 more');
});
