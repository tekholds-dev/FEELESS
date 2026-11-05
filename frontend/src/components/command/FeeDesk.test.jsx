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
  ['cat-desk', 'fee-tools', 'book', 'live', 'fee-owner-btn'].forEach(id => expect(q(id)).not.toBeNull()); expect(q('nexa')).toBeNull();   // by default, what everyone sees
  await act(async () => { q('fee-owner-btn').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  ['cat-desk', 'fee-tools', 'nexa', 'live'].forEach(id => expect(q(id)).not.toBeNull()); expect(q('book')).toBeNull();
  act(() => root.unmount());
});
