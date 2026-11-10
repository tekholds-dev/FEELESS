import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeDesk } from './FeeCatsPlatform';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => null }));
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => ({ isAdmin: true, call: jest.fn() }) }));
jest.mock('./ProfileFeeCat', () => ({ ProfileFeeCat: () => <p data-testid="nexa">nexa</p>, ProfileFeeBanner: () => null }));
jest.mock('./FeeCatProfile', () => ({ FeeCatProfile: () => <p data-testid="book">book</p> }));
jest.mock('./FeeLiveTab', () => ({ FeeLiveTab: () => <p data-testid="live">live</p> }));

test('🐱 one Fee: the creator\'s door opens the same desk as the leaderboard, showing what everyone sees until the owner presses Owner only', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cat: { id: 'leader', name: 'Fee', handle: 'fee', isLeader: true, status: 'running', positions: [], risk: {}, wallet: 'W'.repeat(44) } }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeeDesk onBack={() => {}} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  ['cat-desk', 'fee-owner-btn', 'kd-pub-live', 'kd-pub-record', 'kd-pub-tools'].forEach(id => expect(q(id)).not.toBeNull()); expect(q('nexa')).toBeNull();   // by default, what everyone sees: tabbed (SITE-6), not one long scroll
  const seen = new Set(); for (const t of ['live', 'record', 'tools']) { await act(async () => { q(`kd-pub-${t}`).click(); }); ['fee-tools', 'book', 'live'].forEach(id => q(id) && seen.add(id)); }
  expect([...seen].sort()).toEqual(['book', 'fee-tools', 'live']);   // every part is still there, one tab at a time
  await act(async () => { q('fee-owner-btn').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  ['cat-desk', 'fee-tools', 'nexa', 'live'].forEach(id => expect(q(id)).not.toBeNull()); expect(q('book')).toBeNull();
  act(() => root.unmount());
});
