import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { RewardsDash } from './RewardsDash';

jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a> }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: jest.fn() }));
jest.mock('../lib/chatSession', () => ({ getChatSession: jest.fn(async () => 'tok'), readChatSession: jest.fn(), agentAuth: jest.fn(), agentAuthQuery: jest.fn(() => '') }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('./command/DeskShell', () => ({ ShaderWall: () => null }));
const { useWallet } = require('../hooks/useWallet');
const { getChatSession } = require('../lib/chatSession');
beforeEach(() => { getChatSession.mockResolvedValue('tok'); });

const REWARDS = { address: 'me', total: 500, streak: 3, rank: 7, log: [], items: [{ id: 'daily', label: 'Daily check-in', how: 'Come back', amount: 25, claimable: true }, { id: 'post', label: 'Post', how: 'Post today', amount: 5, claimable: true }, { id: 'link', label: 'Link', how: 'Link both', amount: 40, claimable: false, once: true, claimed: 1 }] };
const SHOP = { points: 500, spent: 100, boosts: 1, tickets: 2, unlocks: {}, items: [{ id: 'mp1', kind: 'mp', label: '10 MP to your bank', cost: 300, grant: {} }, { id: 'mp2', kind: 'mp', label: '100 MP to your bank', cost: 3000, grant: {} }, { id: 'boost', kind: 'boost', label: 'Boost', cost: 50, grant: { boosts: 1 } }] };
const QUESTS = { level: { level: 2, name: 'Soldier', xp: 150, next: 300 }, earned: 1, total: 2, next: ['b2'], rarity: {}, editions: {}, editionCap: 100, badges: [{ id: 'b1', name: 'Recruit', tier: 'common', art: '/a', earned: true, pct: 100, tasks: [] }, { id: 'b2', name: 'Trader', tier: 'rare', art: '/b', earned: false, pct: 40, tasks: [{ metric: 'trades', label: 'Make 5 trades', done: false }] }] };

async function mount() {
  const calls = [];
  global.fetch = jest.fn(async (u, o) => { calls.push([String(u), o]); const url = String(u);
    const body = url.includes('/rewards/claim') ? { ok: true, gained: 25, total: 525, streak: 4 } : url.includes('/shop/buy') ? { ok: true } : url.includes('/rewards-board') ? { rows: [{ address: 'me', handle: 'happy', points: 500 }] } : url.includes('/rewards/') ? REWARDS : url.includes('/shop') ? SHOP : url.includes('/quests') ? QUESTS : {};
    return { ok: true, json: async () => body }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<RewardsDash />); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  return { el, root, calls, q: id => el.querySelector(`[data-testid="${id}"]`) };
}

test('🎁 signed out it asks for a wallet and shows no made-up numbers', async () => {
  useWallet.mockReturnValue({ wallet: null });
  const { q, root, el } = await mount();
  expect(q('rwd-connect')).toBeTruthy(); expect(q('rwd-balance')).toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('🎁 one page: what you can spend is earned minus spent, claims go to the server, a deposit you can afford works', async () => {
  useWallet.mockReturnValue({ wallet: { address: 'me' }, signMessage: jest.fn() });
  const { q, calls, root, el } = await mount();
  ['rwd-claims', 'rwd-hunt', 'rwd-bank', 'rwd-wall', 'rwd-shop', 'rwd-board', 'rwd-level', 'rwd-streak'].forEach(id => expect(q(id)).toBeTruthy());
  expect(q('rwd-claim-all').textContent).toContain('30');
  await act(async () => { q('rwd-claim-daily').click(); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(JSON.parse(calls.find(([u]) => u.includes('/rewards/claim'))[1].body)).toMatchObject({ address: 'me', session: 'tok', reward: 'daily' });
  expect(q('rwd-deposit-mp1').disabled).toBe(false);
  expect(q('rwd-deposit-mp2').disabled).toBe(true);
  await act(async () => { q('rwd-deposit-mp1').click(); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(JSON.parse(calls.find(([u]) => u.includes('/shop/buy'))[1].body)).toMatchObject({ item: 'mp1' });
  expect(q('rwd-target-b2')).toBeTruthy(); expect(q('rwd-medal-b1')).toBeTruthy();
  await act(async () => { root.unmount(); }); el.remove();
});
