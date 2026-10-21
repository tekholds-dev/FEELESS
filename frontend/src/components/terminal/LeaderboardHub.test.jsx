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

test('one Leaderboard tab with lenses; ?lens= picks the board, the old trench wars lens is gone', () => {
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<LeaderboardHub callers={<p>CALLERS</p>} crew={<p>CREW</p>} />));
  expect(host.textContent).toContain('CALLERS');
  expect(host.querySelector('[data-testid="lb-wars"]')).toBeNull();
  act(() => host.querySelector('[data-testid="lb-crew"]').click());
  expect(mockSet).toHaveBeenCalledWith({ lens: 'crew' });
  act(() => root.unmount());
});

test('held-coin signals: ripping, dumping or steady', () => {
  expect(signalOf({ priceChange: { h1: 12 } })[0]).toBe('pump');
  expect(signalOf({ priceChange: { m5: -5 } })[0]).toBe('dump');
  expect(signalOf({ priceChange: { h1: 2 } })[0]).toBe('calm');
});
