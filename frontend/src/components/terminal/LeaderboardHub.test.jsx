import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

let mockParams = new URLSearchParams('lens=callers');
const mockSet = jest.fn(p => { mockParams = new URLSearchParams(p); });
jest.mock('react-router-dom', () => ({ useSearchParams: () => [mockParams, mockSet], Link: ({ children }) => children }), { virtual: true });
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({}) }));
// eslint-disable-next-line import/first
import { LeaderboardHub } from './LeaderboardHub';
// eslint-disable-next-line import/first
import { signalOf } from './HeldSignals';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('one Leaderboard tab with lenses; ?lens= picks the board', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<LeaderboardHub wars={<p>WARS</p>} callers={<p>CALLERS</p>} crew={<p>CREW</p>} />));
  expect(host.textContent).toContain('CALLERS');
  act(() => host.querySelector('[data-testid="lb-wars"]').click());
  expect(mockSet).toHaveBeenCalledWith({ lens: 'wars' });
  act(() => root.unmount());
  const host2 = document.createElement('div'); document.body.appendChild(host2);
  mockParams = new URLSearchParams('lens=wars');
  act(() => createRoot(host2).render(<LeaderboardHub wars={<p>WARS</p>} callers={<p>CALLERS</p>} crew={<p>CREW</p>} />));
  expect(host2.textContent).toContain('WARS');
});

test('held-coin signals: ripping, dumping or steady', () => {
  expect(signalOf({ priceChange: { h1: 12 } })[0]).toBe('pump');
  expect(signalOf({ priceChange: { m5: -5 } })[0]).toBe('dump');
  expect(signalOf({ priceChange: { h1: 2 } })[0]).toBe('calm');
});
