import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'MeWa11et' }, signMessage: jest.fn() }) }));
jest.mock('../lib/chatSession', () => ({ getChatSession: async () => 'sess' }));
// eslint-disable-next-line import/first
import { QuestBoard } from './QuestBoard';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const now = Date.now() / 1000;
const task = (id, have, target) => ({ id, label: id, metric: 'trades', have, target, pct: Math.min(100, Math.round(have / target * 100)), done: have >= target });
const board = {
  level: { level: 2, name: 'Degen', xp: 450, next: 1200 }, metrics: { streak: 4 }, earned: 1, total: 3, next: ['q-pro'], rarity: { 'q-trader': 12.5 },
  quests: { daily: { resetsAt: now + 3600, tasks: [{ id: 'checkin', label: 'Check in', have: 0, target: 1, xp: 10, done: false }] }, weekly: { resetsAt: now + 86400, tasks: [] } },
  badges: [
    { id: 'q-trader', set: 'feeless', name: 'Trader', tier: 'common', art: '/assets/badges/feeless/trader', earned: true, pct: 100, xp: 50, tasks: [task('t', 10, 10)] },
    { id: 'q-pro', set: 'feeless', name: 'Pro', tier: 'rare', art: '/assets/badges/feeless/pro', earned: false, pct: 40, xp: 150, tasks: [task('p', 20, 50)] },
    { id: 'frsv-vip', set: 'frsv', name: 'FRSV VIP', tier: 'legendary', art: '/assets/badges/frsv/vip', earned: false, pct: 0, xp: 1000, tasks: [task('v', 0, 1000)] },
  ],
};

test('badges tab: level, streak, quests, sets, posters (GIF only in detail), daily check-in', async () => {
  const calls = [];
  global.fetch = jest.fn(async (url, opts) => { calls.push([String(url), opts?.method]); return { ok: true, json: async () => (String(url).includes('checkin') ? { fresh: true, streak: 5 } : String(url).includes('leaderboard') ? { paused: true, rows: [], season: { name: 'Season 1', paused: true } } : board) }; });
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<QuestBoard />); });
  await act(async () => { await Promise.resolve(); });
  expect(host.textContent).toContain('LEVEL 2 · DEGEN'); expect(host.textContent).toContain('🔥 4'); expect(host.textContent).toContain('1/3');
  expect(host.querySelectorAll('.qb-grid .qb-slot')).toHaveLength(2);
  expect(host.querySelector('[data-testid="quest-season"]').textContent).toContain('paused until launch');
  expect(host.querySelector('[data-testid="badge-q-trader"] image').getAttribute('href')).toContain('/assets/badges/feeless/trader.jpg');   // poster, not GIF
  expect(host.querySelector('[data-testid="badge-q-trader"] .mc-stage').className).toContain('is-alive');   // earned = alive
  expect(host.querySelector('[data-testid="badge-q-pro"] .mc-stage').className).not.toContain('is-alive');
  expect(host.querySelector('.qb-grid').textContent).toContain('12.5% hold');
  act(() => host.querySelector('[data-testid="badge-set-frsv"]').click());
  expect(host.querySelector('[data-testid="badge-frsv-vip"]')).not.toBeNull();
  act(() => host.querySelector('[data-testid="badge-frsv-vip"] [data-testid="meta-card"]').click());
  expect(host.querySelector('[data-testid="badge-detail"] image').getAttribute('href')).toContain('/assets/badges/frsv/vip.gif');
  expect(host.querySelector('[data-testid="badge-detail"] .qbc-back').textContent).toContain('v');
  await act(async () => host.querySelector('[data-testid="quest-checkin"]').click());
  expect(calls.some(([u, m]) => u.includes('/quests/checkin') && m === 'POST')).toBe(true);
});
